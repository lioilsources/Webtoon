package voice

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"slices"
	"sort"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/ol1n/webtoon/backend/internal/voice/receipt"
)

const (
	maxFieldBytes   = 8 << 10
	maxConsentRunes = 2000
	maxKeyLen       = 128
)

type voiceForm struct {
	sample                                                  []byte
	consent, consentText, consentVersion, receipt, platform string
}

// readVoiceForm reads the multipart body into memory (bounded): the plaintext sample never
// touches the disk.
func readVoiceForm(r *http.Request) (voiceForm, error) {
	var f voiceForm
	mr, err := r.MultipartReader()
	if err != nil {
		return f, apiErr(http.StatusBadRequest, "invalid_request", "expected multipart/form-data")
	}
	seenSample := false
	for {
		p, err := mr.NextPart()
		if err == io.EOF {
			break
		}
		if err != nil {
			return f, bodyErr(err)
		}
		name := p.FormName()
		switch name {
		case "sample":
			if seenSample {
				return f, apiErr(http.StatusBadRequest, "invalid_request", "sample: only one file allowed")
			}
			seenSample = true
			b, err := io.ReadAll(io.LimitReader(p, MaxSampleBytes+1))
			if err != nil {
				return f, bodyErr(err)
			}
			if len(b) > MaxSampleBytes {
				return f, apiErr(http.StatusRequestEntityTooLarge, "sample_too_large", fmt.Sprintf("sample: larger than %d bytes", MaxSampleBytes))
			}
			f.sample = b
		case "consent", "consent_text", "consent_version", "receipt", "platform":
			b, err := io.ReadAll(io.LimitReader(p, maxFieldBytes+1))
			if err != nil {
				return f, bodyErr(err)
			}
			if len(b) > maxFieldBytes {
				return f, apiErr(http.StatusBadRequest, "invalid_request", name+": too long")
			}
			v := strings.TrimSpace(string(b))
			switch name {
			case "consent":
				f.consent = v
			case "consent_text":
				f.consentText = v
			case "consent_version":
				f.consentVersion = v
			case "receipt":
				f.receipt = v
			default:
				f.platform = strings.ToLower(v)
			}
		}
		_ = p.Close()
	}
	return f, nil
}

func bodyErr(err error) error {
	var mbe *http.MaxBytesError
	if errors.As(err, &mbe) {
		return apiErr(http.StatusRequestEntityTooLarge, "sample_too_large", "request body too large")
	}
	return apiErr(http.StatusBadRequest, "invalid_request", "invalid multipart body")
}

type voiceOut struct {
	VoiceID   string `json:"voice_id"`
	Status    string `json:"status"`
	Error     string `json:"error,omitempty"`
	CreatedAt string `json:"created_at"`
}

func (s *Server) createVoice(w http.ResponseWriter, r *http.Request, d Device) {
	if s.box == nil {
		s.fail(w, r, errUnavailable)
		return
	}
	r.Body = http.MaxBytesReader(w, r.Body, MaxSampleBytes+64<<10)
	f, err := readVoiceForm(r)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	var problems []string
	if f.consent != "true" {
		s.fail(w, r, apiErr(http.StatusBadRequest, "consent_required", "consent must be true"))
		return
	}
	if f.consentText == "" || utf8.RuneCountInString(f.consentText) > maxConsentRunes {
		problems = append(problems, fmt.Sprintf("consent_text: required, at most %d characters", maxConsentRunes))
	}
	if len(f.consentVersion) > 32 {
		problems = append(problems, "consent_version: at most 32 characters")
	}
	if f.receipt == "" {
		problems = append(problems, "receipt: required")
	}
	if f.platform != "" && f.platform != receipt.PlatformIOS && f.platform != receipt.PlatformAndroid {
		problems = append(problems, "platform: ios or android")
	}
	if len(f.sample) == 0 {
		problems = append(problems, "sample: required")
	}
	if len(problems) > 0 {
		s.fail(w, r, apiErr(http.StatusBadRequest, "invalid_request", strings.Join(problems, "; ")))
		return
	}
	ext, ok := SniffAudio(f.sample)
	if !ok {
		s.fail(w, r, apiErr(http.StatusUnsupportedMediaType, "sample_format", "sample: must be m4a (AAC) or wav"))
		return
	}
	dur, err := AudioDuration(ext, f.sample)
	if err != nil {
		s.fail(w, r, apiErr(http.StatusBadRequest, "sample_invalid", "sample: unreadable audio"))
		return
	}
	if dur < MinSampleS-sampleTolerance || dur > MaxSampleS+sampleTolerance {
		s.fail(w, r, apiErr(http.StatusBadRequest, "sample_invalid", fmt.Sprintf("sample: %.1f s, must be 5–30 s", dur)))
		return
	}
	if v, err := s.store.ActiveVoiceByDevice(r.Context(), d.ID); err != nil {
		s.fail(w, r, err)
		return
	} else if v != nil {
		s.fail(w, r, apiErr(http.StatusConflict, "voice_exists", "this device already has a voice; delete it first"))
		return
	}

	plat := f.platform
	if plat == "" {
		plat = d.Platform
	}
	p, err := s.rv.Verify(r.Context(), plat, f.receipt, r.Host)
	switch {
	case errors.Is(err, receipt.ErrUnavailable):
		s.log.Warn("voice receipt not verifiable", "device", d.ID, "err", err)
		s.fail(w, r, apiErr(http.StatusServiceUnavailable, "receipt_verification_unavailable",
			"the purchase cannot be verified on this server right now"))
		return
	case errors.Is(err, receipt.ErrInvalid):
		s.log.Info("voice receipt rejected", "device", d.ID, "err", err)
		s.fail(w, r, apiErr(http.StatusPaymentRequired, "receipt_invalid", strings.TrimPrefix(err.Error(), "receipt_invalid: ")))
		return
	case err != nil:
		s.fail(w, r, err)
		return
	}
	if n, err := s.store.ReceiptDevices(r.Context(), p.Platform, p.OriginalID, d.ID); err != nil {
		s.fail(w, r, err)
		return
	} else if s.ReceiptMaxDevices > 0 && n >= s.ReceiptMaxDevices {
		s.fail(w, r, apiErr(http.StatusForbidden, "receipt_in_use",
			fmt.Sprintf("this purchase already has a voice on %d devices", n)))
		return
	}

	now := s.now()
	id := newUUID()
	rel := samplePath(id, ext)
	if err := s.box.Write(rel, f.sample); err != nil {
		s.fail(w, r, err)
		return
	}
	version := f.consentVersion
	if version == "" {
		version = s.cfg.ConsentVersion
	}
	v := Voice{ID: id, DeviceID: d.ID, Status: StatusQueued, SampleFile: rel, SampleExt: ext, SampleBytes: len(f.sample),
		SampleDurationS: dur, ReceiptPlatform: p.Platform, ReceiptOrigID: p.OriginalID, ReceiptTxID: p.TransactionID,
		CreatedAt: now, UpdatedAt: now, LastUsedAt: now}
	c := Consent{VoiceID: id, DeviceID: d.ID, Text: f.consentText, SHA256: SHA256Hex(f.consentText), Version: version, ConsentedAt: now}
	t := Task{ID: "vt_" + randHex(8), Kind: KindVoiceCreate, VoiceID: id, DeviceID: d.ID, Priority: 5, Status: TaskQueued,
		RunAfter: now, CreatedAt: now, UpdatedAt: now}
	if err := s.store.CreateVoice(r.Context(), v, c, t); err != nil {
		_ = removeVoiceDir(s.cfg.DataDir, id)
		if errors.Is(err, ErrVoiceExists) {
			s.fail(w, r, apiErr(http.StatusConflict, "voice_exists", "this device already has a voice; delete it first"))
			return
		}
		s.fail(w, r, err)
		return
	}
	s.log.Info("voice created", "voice", id, "device", d.ID, "bytes", len(f.sample), "ext", ext,
		"duration_s", fmt.Sprintf("%.1f", dur), "receipt", p.Platform, "env", p.Environment)
	w.Header().Set("Location", "/v1/player/voices/"+id)
	writeJSON(w, http.StatusCreated, voiceOut{VoiceID: id, Status: v.Status, CreatedAt: fmtTime(now)})
}

// ownVoice returns the device's voice; a foreign, unknown or deleted voice is ErrNotFound.
func (s *Server) ownVoice(r *http.Request, d Device) (Voice, error) {
	id := r.PathValue("id")
	if !isUUID(id) {
		return Voice{}, ErrNotFound
	}
	v, err := s.store.GetVoice(r.Context(), id)
	if err != nil {
		return v, err
	}
	if v.DeviceID != d.ID || v.Status == StatusDeleting {
		return Voice{}, ErrNotFound
	}
	return v, nil
}

func (s *Server) getVoice(w http.ResponseWriter, r *http.Request, d Device) {
	v, err := s.ownVoice(r, d)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	_ = s.store.TouchVoice(r.Context(), v.ID, s.now())
	writeJSON(w, http.StatusOK, voiceOut{VoiceID: v.ID, Status: v.Status, Error: v.Error, CreatedAt: fmtTime(v.CreatedAt)})
}

func (s *Server) deleteVoiceHandler(w http.ResponseWriter, r *http.Request, d Device) {
	v, err := s.ownVoice(r, d)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	if err := s.DeleteVoice(r.Context(), v.ID, "user"); err != nil {
		s.fail(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

type linesReq struct {
	Lang  string `json:"lang"`
	Lines []struct {
		Key  string `json:"key"`
		Text string `json:"text"`
	} `json:"lines"`
}

func (s *Server) createLines(w http.ResponseWriter, r *http.Request, d Device) {
	if s.box == nil {
		s.fail(w, r, errUnavailable)
		return
	}
	v, err := s.ownVoice(r, d)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	switch v.Status {
	case StatusQueued:
		s.fail(w, r, apiErr(http.StatusConflict, "voice_not_ready", "the voice is still being prepared"))
		return
	case StatusFailed:
		s.fail(w, r, apiErr(http.StatusConflict, "voice_failed", "the voice could not be created: "+v.Error))
		return
	}
	var req linesReq
	dec := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20))
	if err := dec.Decode(&req); err != nil {
		s.fail(w, r, apiErr(http.StatusBadRequest, "invalid_request", "invalid JSON body"))
		return
	}
	req.Lang = strings.ToLower(strings.TrimSpace(req.Lang))
	if !slices.Contains(s.cfg.Langs, req.Lang) {
		s.fail(w, r, apiErr(http.StatusBadRequest, "unsupported_lang",
			fmt.Sprintf("lang %q: the voice speaks %s", req.Lang, strings.Join(s.cfg.Langs, ", "))))
		return
	}
	if len(req.Lines) == 0 {
		s.fail(w, r, apiErr(http.StatusBadRequest, "invalid_request", "lines: at least one"))
		return
	}
	if len(req.Lines) > s.cfg.MaxLines {
		s.fail(w, r, apiErr(http.StatusBadRequest, "too_many_lines", fmt.Sprintf("lines: at most %d per request", s.cfg.MaxLines)))
		return
	}
	lines := make([]TaskLine, 0, len(req.Lines))
	keys := map[string]bool{}
	for i, l := range req.Lines {
		k := strings.TrimSpace(l.Key)
		if k == "" || len(k) > maxKeyLen || keys[k] {
			s.fail(w, r, apiErr(http.StatusBadRequest, "invalid_request",
				fmt.Sprintf("lines[%d].key: required, unique, at most %d bytes", i, maxKeyLen)))
			return
		}
		keys[k] = true
		t := NormalizeText(l.Text)
		if t == "" {
			s.fail(w, r, apiErr(http.StatusBadRequest, "invalid_request", fmt.Sprintf("lines[%d].text: required", i)))
			return
		}
		if utf8.RuneCountInString(t) > s.cfg.MaxChars {
			s.fail(w, r, apiErr(http.StatusBadRequest, "line_too_long",
				fmt.Sprintf("lines[%d] (%s): at most %d characters", i, k, s.cfg.MaxChars)))
			return
		}
		lines = append(lines, TaskLine{Key: k, Text: t, Hash: LineHash(v.ID, req.Lang, t)})
	}
	idem := idemKey(req.Lang, lines)
	now := s.now()
	_ = s.store.TouchVoice(r.Context(), v.ID, now)
	if t, err := s.store.OpenLineTask(r.Context(), v.ID, idem); err != nil {
		s.fail(w, r, err)
		return
	} else if t != nil {
		writeJSON(w, http.StatusAccepted, map[string]any{"job_id": t.ID, "status": t.Status})
		return
	}
	hashes := uniqueHashes(lines)
	have, err := s.store.Lines(r.Context(), v.ID, hashes)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	missing := len(hashes) - len(have)
	used, ok, err := s.store.AddQuota(r.Context(), d.ID, day(now), missing, s.cfg.DailyLines)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	if !ok {
		ae := apiErr(http.StatusTooManyRequests, "quota_exceeded",
			fmt.Sprintf("daily limit of %d new lines reached (%d used, %d asked)", s.cfg.DailyLines, used, missing))
		ae.extra = map[string]any{"limit": s.cfg.DailyLines, "used": used, "requested": missing,
			"resets_at": fmtTime(now.UTC().Truncate(24 * time.Hour).Add(24 * time.Hour))}
		s.fail(w, r, ae)
		return
	}
	t := Task{ID: "vt_" + randHex(8), Kind: KindLines, VoiceID: v.ID, DeviceID: d.ID, Lang: req.Lang, Lines: lines,
		IdemKey: idem, Status: TaskQueued, RunAfter: now, CreatedAt: now, UpdatedAt: now}
	if missing == 0 {
		t.Status, t.FinishedAt = TaskDone, &now // everything is cached
	}
	if err := s.store.CreateTask(r.Context(), t); err != nil {
		s.fail(w, r, err)
		return
	}
	s.log.Info("voice lines", "voice", v.ID, "job", t.ID, "lines", len(lines), "new", missing)
	writeJSON(w, http.StatusAccepted, map[string]any{"job_id": t.ID, "status": t.Status})
}

func uniqueHashes(lines []TaskLine) []string {
	seen := map[string]bool{}
	var out []string
	for _, l := range lines {
		if !seen[l.Hash] {
			seen[l.Hash] = true
			out = append(out, l.Hash)
		}
	}
	return out
}

func idemKey(lang string, lines []TaskLine) string {
	parts := make([]string, len(lines))
	for i, l := range lines {
		parts[i] = l.Key + "\x1f" + l.Hash
	}
	sort.Strings(parts)
	return SHA256Hex(lang + "\n" + strings.Join(parts, "\n"))
}

type lineOut struct {
	Key       string  `json:"key"`
	URL       string  `json:"url"`
	DurationS float64 `json:"duration_s"`
}

func (s *Server) getJob(w http.ResponseWriter, r *http.Request, d Device) {
	if s.box == nil {
		s.fail(w, r, errUnavailable)
		return
	}
	t, err := s.store.GetTask(r.Context(), r.PathValue("id"))
	if err != nil {
		s.fail(w, r, err)
		return
	}
	if t.Kind != KindLines || t.DeviceID != d.ID {
		s.fail(w, r, ErrNotFound)
		return
	}
	v, err := s.store.GetVoice(r.Context(), t.VoiceID)
	if err != nil || v.Status == StatusDeleting || v.DeviceID != d.ID {
		s.fail(w, r, ErrNotFound)
		return
	}
	now := s.now()
	_ = s.store.TouchVoice(r.Context(), v.ID, now)
	have, err := s.store.Lines(r.Context(), v.ID, uniqueHashes(t.Lines))
	if err != nil {
		s.fail(w, r, err)
		return
	}
	out := []lineOut{}
	var missing []string
	for _, l := range t.Lines {
		if c, ok := have[l.Hash]; ok {
			out = append(out, lineOut{Key: l.Key, URL: s.voiceURL(s.box.LineURL(v.ID, l.Hash, now, s.cfg.URLTTL)), DurationS: round3(c.DurationS)})
		} else {
			missing = append(missing, l.Key)
		}
	}
	status := t.Status
	if status == TaskRunning && t.LeaseUntil != nil && t.LeaseUntil.Before(now) {
		status = TaskQueued // the worker went away; the task is waiting for the next one
	}
	body := map[string]any{"job_id": t.ID, "status": status, "lang": t.Lang, "done": len(out), "total": len(t.Lines), "lines": out}
	if t.Error != "" && status == TaskFailed {
		body["error"] = t.Error
	}
	if status == TaskFailed || status == TaskDone {
		if missing == nil {
			missing = []string{}
		}
		body["missing"] = missing // lines the app reads with the system voice
	}
	writeJSON(w, http.StatusOK, body)
}

func round3(f float64) float64 { return float64(int64(f*1000+0.5)) / 1000 }

// serveLine serves a rendered line by signed URL (no bearer: players and share sheets fetch it plainly).
func (s *Server) serveLine(w http.ResponseWriter, r *http.Request) {
	if s.box == nil {
		s.fail(w, r, errUnavailable)
		return
	}
	voiceID := r.PathValue("voice")
	hash, ok := strings.CutSuffix(r.PathValue("file"), ".m4a")
	q := r.URL.Query()
	if !ok || !isUUID(voiceID) || !isHash(hash) || !s.box.CheckLineURL(voiceID, hash, q.Get("exp"), q.Get("sig"), s.now()) {
		s.fail(w, r, apiErr(http.StatusForbidden, "url_expired", "the line URL is invalid or expired; ask the job again"))
		return
	}
	v, err := s.store.GetVoice(r.Context(), voiceID)
	if err != nil || v.Status == StatusDeleting {
		s.fail(w, r, ErrNotFound)
		return
	}
	have, err := s.store.Lines(r.Context(), voiceID, []string{hash})
	if err != nil {
		s.fail(w, r, err)
		return
	}
	l, ok := have[hash]
	if !ok {
		s.fail(w, r, ErrNotFound)
		return
	}
	b, err := s.box.Read(l.File)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	w.Header().Set("Content-Type", "audio/mp4")
	w.Header().Set("Cache-Control", "private, max-age=3600")
	http.ServeContent(w, r, hash+".m4a", l.CreatedAt, bytes.NewReader(b))
}
