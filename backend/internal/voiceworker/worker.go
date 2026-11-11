// Package voiceworker is the Spark side of the player voice (docs/voice-backend.md): it polls the
// voice queue of webtoon-api on JODA, takes a spark-broker lease of `tts` only while there is
// work, and drives the AiStack audio service (clone with chatterbox-cs, lines via /v1/audio/tts).
// Ported from Hajánek forge/internal/worker, plus the broker lease.
package voiceworker

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"mime"
	"net"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
	"unicode"
	"unicode/utf8"

	"github.com/ol1n/webtoon/backend/internal/voice"
)

// Config of the worker (env, see ConfigFromEnv).
type Config struct {
	Language      string        // engine language fallback, cs
	Engine        string        // AiStack engine, chatterbox (chatterbox-cs for cs)
	Source        string        // AiStack voice "source", toonfork-app
	Idle          time.Duration // sleep when the queue is empty or a task went back (engine down)
	LeaseIdle     time.Duration // release the broker lease after the queue has been empty this long
	Heartbeat     time.Duration // task heartbeat to the API
	Poll          time.Duration // audio job polling
	TTSTimeout    time.Duration // per take, including the engine queue
	TakeAttempts  int           // redo a bad take with a new seed
	MinSPerLetter float64       // shorter = truncated take (chatterbox-cs: ~0.04 cut, 0.065–0.09 whole)
	MaxSPerLetter float64       // longer (+1.5 s) = hallucinated tail
	MinTakeLUFS   float64       // quieter = near-silent take
	Encode        EncodeOpts
}

func DefaultConfig() Config {
	return Config{Language: "cs", Engine: "chatterbox", Source: "toonfork-app", Idle: 30 * time.Second,
		LeaseIdle: 2 * time.Minute, Heartbeat: 60 * time.Second, Poll: time.Second, TTSTimeout: 15 * time.Minute,
		TakeAttempts: 3, MinSPerLetter: 0.055, MaxSPerLetter: 0.25, MinTakeLUFS: -45,
		Encode: EncodeOpts{LUFS: -16, TruePeak: -1.5, LRA: 11, Bitrate: "96k", SampleRate: 48000, GapS: 0.3, TrimDB: -45, KeepS: 0.05}}
}

// Encoder and Measurer are swapped out in tests (ffmpeg is not needed for the queue logic).
type (
	Encoder  func(ctx context.Context, parts []string, out string) (float64, error)
	Measurer func(ctx context.Context, path string) (durS, lufs float64, err error)
)

// Leaser hands out broker leases; nil Leaser = no broker (local runs, tests).
type Leaser interface {
	Acquire(ctx context.Context) (*Lease, error)
}

type Worker struct {
	API     *APIClient
	Audio   *AudioClient
	Broker  Leaser
	Cfg     Config
	Encode  Encoder
	Measure Measurer // nil: takes are not checked
	TmpDir  string
	Log     *slog.Logger
	Now     func() time.Time
}

// Result of one task.
type Result struct {
	OK    bool
	Retry bool
	Err   error
	Lines int // lines voiced (for metrics)
	Bad   int // lines skipped
}

func sleep(ctx context.Context, d time.Duration) bool {
	t := time.NewTimer(d)
	defer t.Stop()
	select {
	case <-ctx.Done():
		return false
	case <-t.C:
		return true
	}
}

// Run works the queue until ctx ends. With once it returns when the queue is empty.
func (w *Worker) Run(ctx context.Context, once bool) error {
	var lease *Lease
	release := func(msg string) {
		if lease != nil {
			lease.Release(msg)
			lease = nil
		}
	}
	defer release("")
	lastWork := w.Now()
	for ctx.Err() == nil {
		n, err := w.API.Pending(ctx)
		if err != nil {
			w.Log.Warn("voice queue unreachable", "err", err)
			if once {
				return err
			}
			sleep(ctx, w.Cfg.Idle)
			continue
		}
		if n == 0 {
			if lease != nil && (once || w.Now().Sub(lastWork) >= w.Cfg.LeaseIdle) {
				release("")
			}
			if once && lease == nil {
				return nil
			}
			sleep(ctx, min(w.Cfg.Idle, w.Cfg.LeaseIdle))
			continue
		}
		if lease != nil && !lease.Usable() {
			release("")
		}
		if lease == nil && w.Broker != nil {
			lease, err = w.Broker.Acquire(ctx)
			if err != nil {
				w.Log.Warn("no broker lease", "err", err)
				if once {
					return err
				}
				sleep(ctx, w.Cfg.Idle)
				continue
			}
		}
		task, err := w.API.Claim(ctx)
		if err != nil || task == nil {
			if err != nil {
				w.Log.Warn("claim", "err", err)
			}
			sleep(ctx, w.Cfg.Idle/6)
			continue
		}
		tctx, stop := ctx, func() {}
		if lease != nil {
			tctx, stop = mergeCtx(ctx, lease.Ctx())
		}
		r := w.Handle(tctx, *task)
		stop()
		lastWork = w.Now()
		msg := ""
		if r.Err != nil {
			msg = r.Err.Error()
			w.Log.Warn("voice task", "task", task.TaskID, "kind", task.Kind, "err", r.Err, "retry", r.Retry)
		} else {
			w.Log.Info("voice task done", "task", task.TaskID, "kind", task.Kind, "lines", r.Lines)
		}
		if lease != nil {
			for range r.Lines {
				lease.Count("lines", true)
			}
			for range r.Bad {
				lease.Count("lines", false)
			}
			if task.Kind != voice.KindLines {
				lease.Count("voices", r.OK)
			}
		}
		cctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		if err := w.API.Complete(cctx, task.TaskID, r.OK, msg, r.Retry); err != nil && !errors.Is(err, ErrLeaseLost) {
			w.Log.Warn("complete", "task", task.TaskID, "err", err)
		}
		cancel()
		if r.Retry {
			// Typically the engine is down in this profile: give the GPU back and wait.
			release("")
			if once || !sleep(ctx, w.Cfg.Idle) {
				return nil
			}
		}
	}
	return nil
}

// mergeCtx is cancelled when either parent is.
func mergeCtx(a, b context.Context) (context.Context, context.CancelFunc) {
	ctx, cancel := context.WithCancel(a)
	stop := context.AfterFunc(b, cancel)
	return ctx, func() { stop(); cancel() }
}

// Handle runs one task with a background task heartbeat; a lost task lease cancels it.
func (w *Worker) Handle(ctx context.Context, t voice.WorkerTask) Result {
	hctx, cancel := context.WithCancel(ctx)
	defer cancel()
	go w.keepAlive(hctx, t.TaskID, cancel)
	switch t.Kind {
	case voice.KindVoiceCreate:
		return w.create(hctx, t)
	case voice.KindVoiceDelete:
		return w.remove(hctx, t)
	case voice.KindLines:
		return w.lines(hctx, t)
	}
	return Result{Err: fmt.Errorf("unknown task kind %q", t.Kind)}
}

func (w *Worker) keepAlive(ctx context.Context, id string, cancel context.CancelFunc) {
	tk := time.NewTicker(w.Cfg.Heartbeat)
	defer tk.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-tk.C:
		}
		if err := w.API.Heartbeat(ctx, id); errors.Is(err, ErrLeaseLost) {
			w.Log.Info("task lease lost (cancelled or reclaimed)", "task", id)
			cancel()
			return
		}
	}
}

func fail(err error) Result { return Result{Err: err, Retry: retryable(err)} }

// retryable: network trouble, 5xx/429 (503 = engine not up in this profile), a lost broker lease
// and timeouts are retried; other 4xx (403 license, 422 bad sample, …) fail the task for good.
func retryable(err error) bool {
	var ae *AudioError
	var he *HTTPError
	var ne net.Error
	var ue *url.Error
	switch {
	case errors.As(err, &ae):
		return ae.Status >= 500 || ae.Status == http.StatusTooManyRequests
	case errors.As(err, &he):
		return he.Status >= 500 || he.Status == http.StatusTooManyRequests
	case errors.Is(err, context.Canceled), errors.Is(err, context.DeadlineExceeded), errors.Is(err, ErrLeaseLost):
		return true
	case errors.As(err, &ne), errors.As(err, &ue):
		return true
	}
	return false
}

func sampleExt(ctype string) string {
	mt, _, _ := mime.ParseMediaType(ctype)
	switch mt {
	case "audio/wav", "audio/x-wav", "audio/wave":
		return ".wav"
	}
	return ".m4a"
}

func (w *Worker) create(ctx context.Context, t voice.WorkerTask) Result {
	sample, ctype, err := w.API.Sample(ctx, t.VoiceID)
	if err != nil {
		return fail(fmt.Errorf("sample: %w", err))
	}
	defer clear(sample)
	lang := t.Lang
	if lang == "" {
		lang = w.Cfg.Language
	}
	if err := w.Audio.CreateVoice(ctx, t.AudioVoice, sample, "sample"+sampleExt(ctype), lang, w.Cfg.Source); err != nil {
		return fail(err)
	}
	return Result{OK: true}
}

func (w *Worker) remove(ctx context.Context, t voice.WorkerTask) Result {
	if _, err := w.Audio.DeleteVoice(ctx, t.AudioVoice); err != nil {
		return fail(err)
	}
	return Result{OK: true}
}

func (w *Worker) lines(ctx context.Context, t voice.WorkerTask) Result {
	dir, err := os.MkdirTemp(w.TmpDir, "lines-")
	if err != nil {
		return fail(err)
	}
	defer os.RemoveAll(dir)
	var res Result
	var bad []error
	for _, l := range t.Lines {
		if err := w.line(ctx, t, l, dir); err != nil {
			if retryable(err) {
				res.Err, res.Retry = err, true
				return res
			}
			// A bad line must not cost the others: skip it, the app reads it with the system voice.
			w.Log.Warn("line skipped", "task", t.TaskID, "hash", l.Hash[:12], "err", err)
			bad = append(bad, err)
			res.Bad++
			continue
		}
		res.Lines++
	}
	if len(bad) > 0 {
		res.Err = fmt.Errorf("%d of %d lines failed, first: %w", len(bad), len(t.Lines), bad[0])
		return res
	}
	res.OK = true
	return res
}

func (w *Worker) line(ctx context.Context, t voice.WorkerTask, l voice.WorkerLine, dir string) error {
	var parts []string
	for i, s := range sentences(ttsText(l.Text)) {
		wav := filepath.Join(dir, l.Hash+"."+strconv.Itoa(i)+".wav")
		if err := w.take(ctx, t, s, wav); err != nil {
			return err
		}
		parts = append(parts, wav)
	}
	if len(parts) == 0 {
		return fmt.Errorf("line has no speakable text")
	}
	out := filepath.Join(dir, l.Hash+".m4a")
	d, err := w.Encode(ctx, parts, out)
	if err != nil {
		return fmt.Errorf("encode: %w", err)
	}
	b, err := os.ReadFile(out)
	if err != nil {
		return err
	}
	if err := w.API.PutLine(ctx, t.VoiceID, l.Hash, t.Lang, b, d); err != nil {
		return fmt.Errorf("upload line: %w", err)
	}
	return nil
}

// take voices one sentence into dst, redoing it with another seed while it does not look like
// the whole sentence (truncated, runaway or near silent).
func (w *Worker) take(ctx context.Context, t voice.WorkerTask, text, dst string) error {
	var bad error
	for a := range max(w.Cfg.TakeAttempts, 1) {
		req := TTSRequest{Text: text, Language: t.Lang, Voice: t.AudioVoice, Engine: w.Cfg.Engine,
			CommercialOnly: false, Speed: 1, Format: "wav"}
		if a > 0 {
			seed := a
			req.Seed = &seed
		}
		id, err := w.Audio.SubmitTTS(ctx, req)
		if err != nil {
			return err
		}
		st, err := w.await(ctx, id)
		if err != nil {
			return err
		}
		if len(st.Outputs) == 0 {
			return fmt.Errorf("audio job %s: no outputs", id)
		}
		if err := w.Audio.Download(ctx, st.Outputs[0].URL, dst); err != nil {
			return err
		}
		if w.Measure == nil {
			return nil
		}
		d, lufs, err := w.Measure(ctx, dst)
		if err != nil {
			return fmt.Errorf("measure take: %w", err)
		}
		why := w.badTake(d, lufs, letters(text))
		if why == "" {
			return nil
		}
		bad = fmt.Errorf("take: %s", why)
		w.Log.Info("take redone", "task", t.TaskID, "attempt", a+1, "why", why)
	}
	return bad
}

func (w *Worker) badTake(d, lufs float64, n int) string {
	c := w.Cfg
	switch {
	case lufs < c.MinTakeLUFS:
		return fmt.Sprintf("near silent (%.1f LUFS)", lufs)
	case d < c.MinSPerLetter*float64(n):
		return fmt.Sprintf("truncated (%.2f s for %d letters)", d, n)
	case d > c.MaxSPerLetter*float64(n)+1.5:
		return fmt.Sprintf("too long (%.2f s for %d letters)", d, n)
	}
	return ""
}

func (w *Worker) await(ctx context.Context, id string) (*audioJob, error) {
	deadline := w.Now().Add(w.Cfg.TTSTimeout)
	for {
		st, err := w.Audio.job(ctx, id)
		if err != nil {
			return nil, err
		}
		switch st.Status {
		case "done":
			return st, nil
		case "error":
			// The engine failed mid-job (crash, OOM): treated like a 502, i.e. retried.
			return nil, &AudioError{Op: "job " + id, Status: http.StatusBadGateway, Detail: st.Error}
		}
		if w.Now().After(deadline) {
			return nil, fmt.Errorf("audio job %s: %w", id, context.DeadlineExceeded)
		}
		if !sleep(ctx, w.Cfg.Poll) {
			return nil, ctx.Err()
		}
	}
}

func letters(s string) int {
	n := 0
	for _, r := range s {
		if unicode.IsLetter(r) {
			n++
		}
	}
	return n
}

// ttsText drops quotation marks: they are not read and a lone closing quote makes engines stop
// early. The cache hash still uses the line text.
func ttsText(s string) string {
	return strings.Join(strings.Fields(strings.NewReplacer("„", "", "“", "", "”", "", "\"", "", "‚", "", "‘", "", "«", "", "»", "").Replace(s)), " ")
}

// sentences splits a line after . ? ! or … when the next word starts with a capital letter
// (chatterbox-cs often stops after the first of several sentences).
func sentences(s string) []string {
	var out []string
	words := strings.Fields(s)
	start := 0
	for i := 0; i < len(words)-1; i++ {
		last, _ := utf8.DecodeLastRuneInString(strings.TrimRight(words[i], ")"))
		next, _ := utf8.DecodeRuneInString(words[i+1])
		if strings.ContainsRune(".?!…", last) && unicode.IsUpper(next) {
			out = append(out, strings.Join(words[start:i+1], " "))
			start = i + 1
		}
	}
	if start < len(words) {
		out = append(out, strings.Join(words[start:], " "))
	}
	return out
}
