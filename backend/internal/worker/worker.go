// Package worker runs the episode pipeline (§3, §5) off the Postgres job table:
//
//	episode job: [moderate free text] → storyboard (LLM) → validator → one panel job per panel
//	panel job:   build prompt → ComfyUI → WD14 safety (max 2 reseeds) → save PNG → update
//	last panel:  apply state_diff to the campaign, mark the episode ready
//
// LLM / ComfyUI / WD14 outages (they run on a schedule) requeue the job after Backoff
// without counting an attempt and without failing the episode.
package worker

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"hash/fnv"
	"log/slog"
	"math/rand/v2"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/ol1n/webtoon/backend/internal/comfy"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/prompt"
	"github.com/ol1n/webtoon/backend/internal/state"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/upstream"
	"github.com/ol1n/webtoon/backend/internal/wd14"
)

type Config struct {
	ID           string
	MediaDir     string
	Backoff      time.Duration // upstream down → run_after += Backoff (default 5 min)
	RetryBase    time.Duration // ordinary failure → RetryBase * 2^(attempt-1)
	PollInterval time.Duration // idle polling of the job table
	StaleAfter   time.Duration // running jobs older than this are requeued
	MaxAttempts  int           // for the panel jobs this worker enqueues
	Clock        func() time.Time
}

type Worker struct {
	cfg   Config
	store Store
	llm   llm.JSONCaller
	gen   *storyboard.Generator
	comfy *comfy.Client
	wd14  *wd14.Client
	log   *slog.Logger
	wake  chan struct{}
	now   func() time.Time
}

func New(cfg Config, s Store, gen *storyboard.Generator, c *comfy.Client, t *wd14.Client) *Worker {
	if cfg.Backoff <= 0 {
		cfg.Backoff = 5 * time.Minute
	}
	if cfg.RetryBase <= 0 {
		cfg.RetryBase = 30 * time.Second
	}
	if cfg.PollInterval <= 0 {
		cfg.PollInterval = 2 * time.Second
	}
	if cfg.StaleAfter <= 0 {
		cfg.StaleAfter = 30 * time.Minute
	}
	if cfg.MaxAttempts <= 0 {
		cfg.MaxAttempts = 3
	}
	if cfg.ID == "" {
		host, _ := os.Hostname()
		cfg.ID = fmt.Sprintf("%s-%d", host, os.Getpid())
	}
	if cfg.Clock == nil {
		cfg.Clock = time.Now
	}
	return &Worker{cfg: cfg, store: s, llm: gen.LLM, gen: gen, comfy: c, wd14: t,
		log: slog.Default().With("component", "worker"), wake: make(chan struct{}, 1), now: cfg.Clock}
}

// Wake nudges idle workers (the API calls it after enqueueing when running in-process).
func (w *Worker) Wake() {
	select {
	case w.wake <- struct{}{}:
	default:
	}
}

// Run starts n worker goroutines and blocks until ctx is cancelled.
func (w *Worker) Run(ctx context.Context, n int) {
	if n <= 0 {
		n = 1
	}
	if k, err := w.store.RequeueStaleJobs(ctx, w.now().Add(-w.cfg.StaleAfter)); err == nil && k > 0 {
		w.log.Info("requeued stale jobs", "count", k)
	}
	w.log.Info("worker pool started", "workers", n, "id", w.cfg.ID)
	var wg sync.WaitGroup
	for i := range n {
		wg.Add(1)
		go func() {
			defer wg.Done()
			w.loop(ctx, fmt.Sprintf("%s/%d", w.cfg.ID, i))
		}()
	}
	wg.Wait()
}

func (w *Worker) loop(ctx context.Context, id string) {
	for ctx.Err() == nil {
		did, err := w.RunOnce(ctx, id)
		if err != nil && ctx.Err() == nil {
			w.log.Error("job loop", "err", err)
		}
		if did {
			continue
		}
		select {
		case <-ctx.Done():
		case <-w.wake:
		case <-time.After(w.cfg.PollInterval):
		}
	}
}

// RunOnce claims and processes one due job. Reports whether a job was found.
func (w *Worker) RunOnce(ctx context.Context, id string) (bool, error) {
	job, err := w.store.ClaimJob(ctx, id)
	if err != nil || job == nil {
		return false, err
	}
	log := w.log.With("job", job.ID, "kind", job.Kind, "attempt", job.Attempts)
	var perr error
	switch job.Kind {
	case KindEpisode:
		perr = w.episodeJob(ctx, job)
	case KindPanel:
		perr = w.panelJob(ctx, job)
	default:
		perr = permanent(fmt.Errorf("unknown job kind %q", job.Kind))
	}
	return true, w.settle(ctx, log, job, perr)
}

type permanentErr struct{ error }

func (p permanentErr) Unwrap() error { return p.error }

// permanent marks an error that retrying cannot fix.
func permanent(err error) error { return permanentErr{err} }

// settle records the job outcome: done, deferred (upstream down), retried or failed.
func (w *Worker) settle(ctx context.Context, log *slog.Logger, job *Job, err error) error {
	if ctx.Err() != nil {
		// Shutting down mid-job: hand it back without burning the attempt.
		bg := context.WithoutCancel(ctx)
		return w.store.DeferJob(bg, job.ID, w.now(), "interrupted by shutdown")
	}
	switch {
	case err == nil:
		return w.store.CompleteJob(ctx, job.ID)
	case upstream.IsUnavailable(err):
		at := w.now().Add(w.cfg.Backoff)
		log.Warn("upstream unavailable, backing off", "err", err, "run_after", at)
		w.onDefer(ctx, job, err, at)
		return w.store.DeferJob(ctx, job.ID, at, err.Error())
	}
	var perm permanentErr
	if !errors.As(err, &perm) && job.Attempts < job.MaxAttempts {
		at := w.now().Add(w.cfg.RetryBase << (job.Attempts - 1))
		log.Warn("job failed, retrying", "err", err, "run_after", at)
		w.onRetry(ctx, job, err)
		return w.store.RetryJob(ctx, job.ID, at, err.Error())
	}
	log.Error("job failed permanently", "err", err)
	w.onFail(ctx, job, err)
	return w.store.FailJob(ctx, job.ID, err.Error())
}

func (w *Worker) onDefer(ctx context.Context, job *Job, err error, at time.Time) {
	msg := fmt.Sprintf("waiting: %v (next try %s)", err, at.Format(time.RFC3339))
	switch job.Kind {
	case KindEpisode:
		var p EpisodePayload
		if json.Unmarshal(job.Payload, &p) == nil {
			_ = w.store.SetEpisodeStatus(ctx, p.EpisodeID, "queued", msg)
		}
	case KindPanel:
		var p PanelPayload
		if json.Unmarshal(job.Payload, &p) == nil {
			_ = w.store.SetPanelStatus(ctx, p.EpisodeID, p.Panel, "pending", msg)
		}
	}
}

func (w *Worker) onRetry(ctx context.Context, job *Job, err error) {
	if job.Kind == KindPanel {
		var p PanelPayload
		if json.Unmarshal(job.Payload, &p) == nil {
			_ = w.store.SetPanelStatus(ctx, p.EpisodeID, p.Panel, "pending", err.Error())
		}
	}
}

func (w *Worker) onFail(ctx context.Context, job *Job, err error) {
	switch job.Kind {
	case KindEpisode:
		var p EpisodePayload
		if json.Unmarshal(job.Payload, &p) == nil {
			_ = w.store.SetEpisodeStatus(ctx, p.EpisodeID, "failed", err.Error())
		}
	case KindPanel:
		var p PanelPayload
		if json.Unmarshal(job.Payload, &p) == nil {
			_ = w.store.SetPanelStatus(ctx, p.EpisodeID, p.Panel, "failed", err.Error())
			_ = w.maybeFinalize(ctx, p.EpisodeID)
		}
	}
}

// --- episode job -------------------------------------------------------------

func (w *Worker) episodeJob(ctx context.Context, job *Job) error {
	var p EpisodePayload
	if err := json.Unmarshal(job.Payload, &p); err != nil {
		return permanent(err)
	}
	ec, err := w.store.LoadEpisodeContext(ctx, p.EpisodeID)
	if err != nil {
		return err
	}
	ep := ec.Episode
	if ep.Status == "ready" || ep.Status == "failed" || ep.PanelsTotal > 0 {
		return nil // already past the storyboard stage
	}
	if err := w.store.SetEpisodeStatus(ctx, ep.ID, "generating", ""); err != nil {
		return err
	}

	if ep.Chosen != nil && ep.Chosen.Kind == "free" && ep.Moderation == nil {
		v, err := storyboard.Moderate(ctx, w.llm, ec.World, ep.Chosen.Text)
		if err != nil {
			return err
		}
		if err := w.store.SetEpisodeModeration(ctx, ep.ID, v); err != nil {
			return err
		}
		ep.Moderation = &v
	}
	if ep.Moderation != nil && !ep.Moderation.Allowed {
		return permanent(fmt.Errorf("player input rejected by moderation: %s", ep.Moderation.Reason))
	}

	sb, err := w.gen.Generate(ctx, ec.World, ec.Campaign.State, ec.Campaign.CanonProgress, ep.Premise)
	if err != nil {
		return err
	}
	AssignChoiceIDs(sb.Choices)
	return w.store.SaveStoryboard(ctx, ep.ID, sb, w.cfg.MaxAttempts)
}

// AssignChoiceIDs gives choices stable ids: c1, c2, … for closed, "free" for the free one.
func AssignChoiceIDs(choices []domain.Choice) {
	n := 0
	for i := range choices {
		switch choices[i].Kind {
		case "free":
			choices[i].ID = "free"
		default:
			n++
			choices[i].ID = fmt.Sprintf("c%d", n)
		}
	}
}

// --- panel job ---------------------------------------------------------------

// BaseSeed is deterministic per episode and panel (the prototype used 1000 + i*100).
func BaseSeed(episodeID string, idx int) int64 {
	h := fnv.New32a()
	h.Write([]byte(episodeID))
	return int64(h.Sum32()%1_000_000_000) + int64(idx)*100
}

func (w *Worker) panelJob(ctx context.Context, job *Job) error {
	var pp PanelPayload
	if err := json.Unmarshal(job.Payload, &pp); err != nil {
		return permanent(err)
	}
	panel, err := w.store.GetPanel(ctx, pp.EpisodeID, pp.Panel)
	if err != nil {
		return err
	}
	if (panel.Status == "ready" || panel.Status == "failed") && !pp.Regenerate {
		return w.maybeFinalize(ctx, pp.EpisodeID)
	}
	ec, err := w.store.LoadEpisodeContext(ctx, pp.EpisodeID)
	if err != nil {
		return err
	}
	sfw := ec.World.Audience != "adult"
	pr, err := prompt.Build(&panel.SB, ec.World, ec.Styles, "", sfw)
	if err != nil {
		return permanent(err)
	}
	// Never start ComfyUI from here; just check whether it is up (Spark window 07–13).
	if err := w.comfy.Ping(ctx); err != nil {
		return err
	}
	if err := w.store.SetPanelStatus(ctx, pp.EpisodeID, pp.Panel, "rendering", ""); err != nil {
		return err
	}
	refName, err := w.uploadReference(ctx, ec.World, &panel.SB)
	if err != nil {
		return err
	}

	seed := BaseSeed(pp.EpisodeID, pp.Panel)
	if pp.Regenerate {
		seed = rand.Int64N(1 << 31)
	}
	prefix := fmt.Sprintf("webtoon/%s/p%02d", pp.EpisodeID, pp.Panel)
	var (
		png      []byte
		tagged   *wd14.Tags
		bad      map[string]float64
		attempts []RenderAttempt
	)
	for attempt := 0; attempt <= wd14.MaxReseed; attempt++ {
		s := seed
		if attempt > 0 {
			s = rand.Int64N(1<<31 + 1)
		}
		g := comfy.Workflow(pr.Positive, pr.Negative, pr.Width, pr.Height, s, pr.Preset, prefix, refName, 0.6)
		images, err := w.comfy.Run(ctx, g)
		if err != nil {
			return err
		}
		png = images[0]
		tagged, err = w.wd14.Tag(ctx, png)
		if err != nil {
			return err
		}
		bad = map[string]float64{}
		if sfw {
			bad = wd14.Safety(tagged)
		}
		attempts = append(attempts, RenderAttempt{Seed: s, Unsafe: bad})
		seed = s
		if len(bad) == 0 {
			break
		}
	}

	res := &PanelResult{
		EpisodeID: pp.EpisodeID, Index: pp.Panel, Prompt: pr.Positive, Negative: pr.Negative,
		Seed: seed, Width: pr.Width, Height: pr.Height, Rating: tagged.Rating, Attempts: attempts,
	}
	if len(bad) > 0 {
		// Unsafe after the reseeds: the image is not stored or served.
		res.Status = "failed"
		res.Error = fmt.Sprintf("unsafe output after %d attempts: %v", len(attempts), bad)
	} else {
		rel := filepath.ToSlash(filepath.Join("episodes", pp.EpisodeID, fmt.Sprintf("p%02d_%d.png", pp.Panel, seed)))
		if err := writeFile(filepath.Join(w.cfg.MediaDir, rel), png); err != nil {
			return err
		}
		res.Status, res.ImagePath = "ready", rel
	}
	if len(panel.SB.Characters) > 0 {
		res.Identity = map[string]wd14.Identity{}
		var sum float64
		for _, pc := range panel.SB.Characters {
			if c, ok := ec.World.Character(pc.ID); ok {
				id := wd14.IdentityScore(tagged, c.TagPrompt)
				res.Identity[c.ID] = id
				sum += id.Recall
			}
		}
		if len(res.Identity) > 0 {
			score := sum / float64(len(res.Identity))
			res.IdentityScore = &score
		}
	}
	if err := w.store.SavePanelResult(ctx, res); err != nil {
		return err
	}
	log := w.log.With("episode", pp.EpisodeID, "panel", pp.Panel, "status", res.Status, "seed", seed, "renders", len(attempts))
	if res.IdentityScore != nil {
		log = log.With("identity", *res.IdentityScore)
	}
	log.Info("panel rendered")
	return w.maybeFinalize(ctx, pp.EpisodeID)
}

// uploadReference uploads the first IP-Adapter reference of a character in the panel.
func (w *Worker) uploadReference(ctx context.Context, wld *domain.World, p *domain.SBPanel) (string, error) {
	for _, pc := range p.Characters {
		c, ok := wld.Character(pc.ID)
		if !ok || c.IdentityLevel != "ip_adapter" || len(c.ReferenceImages) == 0 {
			continue
		}
		path := filepath.Join(w.cfg.MediaDir, filepath.FromSlash(c.ReferenceImages[0]))
		png, err := os.ReadFile(path)
		if err != nil {
			w.log.Warn("reference image missing, rendering prompt-only", "character", c.ID, "path", path)
			return "", nil
		}
		return w.comfy.Upload(ctx, png, fmt.Sprintf("webtoon_%s_%s_ref.png", wld.ID, c.ID))
	}
	return "", nil
}

func writeFile(path string, data []byte) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

// maybeFinalize applies the storyboard's state_diff and marks the episode ready once every
// panel is ready or failed. Runs under the episode lock, so only one panel job finalizes.
func (w *Worker) maybeFinalize(ctx context.Context, episodeID string) error {
	prog, err := w.store.RefreshProgress(ctx, episodeID)
	if err != nil || !prog.Done() {
		return err
	}
	return w.store.FinalizeEpisode(ctx, episodeID, func(ec *EpisodeContext, p Progress) *Finalization {
		if ec.Episode.Status != "generating" || !p.Done() {
			return nil
		}
		if p.Ready == 0 {
			return &Finalization{EpisodeStatus: "failed", Error: "all panels failed"}
		}
		sb := ec.Episode.Storyboard
		if sb == nil {
			return &Finalization{EpisodeStatus: "failed", Error: "storyboard missing"}
		}
		next := state.ApplyDiff(ec.Campaign.State, sb.StateDiffMap(), ec.Episode.Index)
		canon := state.MergeCanon(ec.World, ec.Campaign.CanonProgress, sb.CanonNodesReached.Strings())
		f := &Finalization{EpisodeStatus: "ready", StateSnapshot: next, CampaignState: next, CanonProgress: canon}
		if p.Failed > 0 {
			f.Error = fmt.Sprintf("%d of %d panels failed", p.Failed, p.Total)
		}
		w.log.Info("episode ready", "episode", episodeID, "panels", p.Total, "failed", p.Failed)
		return f
	})
}
