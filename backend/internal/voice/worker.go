package voice

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"time"
)

// Worker API (VOICE_WORKER_TOKEN). The Spark worker (internal/voiceworker) polls pending,
// takes a broker lease for `tts` only when there is work, then claims tasks one by one.

// WorkerTask is what claim hands to the worker.
type WorkerTask struct {
	TaskID     string       `json:"task_id"`
	Kind       string       `json:"kind"`
	VoiceID    string       `json:"voice_id"`
	AudioVoice string       `json:"audio_voice"`
	Lang       string       `json:"lang,omitempty"`
	SampleExt  string       `json:"sample_ext,omitempty"`
	Lines      []WorkerLine `json:"lines,omitempty"` // only lines not yet cached, one per hash
	Attempt    int          `json:"attempt"`
}

type WorkerLine struct {
	Hash string `json:"hash"`
	Text string `json:"text"`
}

func (s *Server) pendingTasks(w http.ResponseWriter, r *http.Request) {
	n, err := s.store.PendingTasks(r.Context(), s.now())
	if err != nil {
		s.fail(w, r, err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]int{"pending": n})
}

type workerReq struct {
	Worker string `json:"worker"`
	OK     bool   `json:"ok"`
	Error  string `json:"error"`
	Retry  bool   `json:"retry"`
}

func decodeWorker(w http.ResponseWriter, r *http.Request) (workerReq, error) {
	var req workerReq
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 64<<10)).Decode(&req); err != nil {
		return req, apiErr(http.StatusBadRequest, "invalid_request", "invalid JSON body")
	}
	if req.Worker == "" || len(req.Worker) > 64 {
		return req, apiErr(http.StatusBadRequest, "invalid_request", "worker: required")
	}
	return req, nil
}

func (s *Server) claimTask(w http.ResponseWriter, r *http.Request) {
	req, err := decodeWorker(w, r)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	ctx := r.Context()
	for range 50 { // skip tasks that turn out to have nothing to do
		now := s.now()
		t, err := s.store.ClaimTask(ctx, req.Worker, now, now.Add(s.cfg.TaskLease))
		if err != nil {
			s.fail(w, r, err)
			return
		}
		if t == nil {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		finish := func(status, msg string) error {
			return s.store.FinishTask(ctx, t.ID, req.Worker, status, msg, now, now)
		}
		if t.Attempts > s.cfg.MaxTaskAttempts {
			msg := fmt.Sprintf("gave up after %d attempts: %s", t.Attempts-1, t.Error)
			if err := finish(TaskFailed, trunc(msg, 500)); err != nil {
				s.fail(w, r, err)
				return
			}
			if t.Kind == KindVoiceCreate {
				_ = s.store.SetVoiceStatus(ctx, t.VoiceID, StatusFailed, "voice service unavailable, try again later", now)
			}
			s.log.Warn("voice task failed for good", "task", t.ID, "kind", t.Kind, "attempts", t.Attempts-1)
			continue
		}
		wt := WorkerTask{TaskID: t.ID, Kind: t.Kind, VoiceID: t.VoiceID, AudioVoice: AudioVoiceID(s.cfg.AudioPrefix, t.VoiceID),
			Lang: t.Lang, Attempt: t.Attempts}
		if t.Kind != KindVoiceDelete {
			v, err := s.store.GetVoice(ctx, t.VoiceID)
			if errors.Is(err, ErrNotFound) || err == nil && v.Status == StatusDeleting {
				if err := finish(TaskCancelled, "voice deleted"); err != nil {
					s.fail(w, r, err)
					return
				}
				continue
			}
			if err != nil {
				s.fail(w, r, err)
				return
			}
			if t.Kind == KindVoiceCreate {
				wt.SampleExt = v.SampleExt
			} else {
				if v.Status != StatusReady {
					if err := finish(TaskFailed, "voice is not ready"); err != nil {
						s.fail(w, r, err)
						return
					}
					continue
				}
				hashes := uniqueHashes(t.Lines)
				have, err := s.store.Lines(ctx, t.VoiceID, hashes)
				if err != nil {
					s.fail(w, r, err)
					return
				}
				seen := map[string]bool{}
				for _, l := range t.Lines {
					if _, ok := have[l.Hash]; !ok && !seen[l.Hash] {
						seen[l.Hash] = true
						wt.Lines = append(wt.Lines, WorkerLine{Hash: l.Hash, Text: l.Text})
					}
				}
				if len(wt.Lines) == 0 {
					if err := finish(TaskDone, ""); err != nil {
						s.fail(w, r, err)
						return
					}
					continue
				}
			}
		}
		writeJSON(w, http.StatusOK, wt)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (s *Server) heartbeatTask(w http.ResponseWriter, r *http.Request) {
	req, err := decodeWorker(w, r)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	now := s.now()
	if err := s.store.HeartbeatTask(r.Context(), r.PathValue("id"), req.Worker, now, now.Add(s.cfg.TaskLease)); err != nil {
		s.workerFail(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (s *Server) workerFail(w http.ResponseWriter, r *http.Request, err error) {
	if errors.Is(err, ErrLeaseLost) {
		s.fail(w, r, apiErr(http.StatusConflict, "lease_lost", "the task is not held by this worker (cancelled, reclaimed or finished)"))
		return
	}
	s.fail(w, r, err)
}

// retryDelay grows from 30 s to 10 min with the attempts (engine down, preempted lease, …).
func retryDelay(attempt int) time.Duration {
	d := 30 * time.Second
	for i := 1; i < attempt && d < 10*time.Minute; i++ {
		d *= 2
	}
	return min(d, 10*time.Minute)
}

func (s *Server) completeTask(w http.ResponseWriter, r *http.Request) {
	req, err := decodeWorker(w, r)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	ctx := r.Context()
	id := r.PathValue("id")
	t, err := s.store.GetTask(ctx, id)
	if err != nil {
		s.workerFail(w, r, ErrLeaseLost)
		return
	}
	now := s.now()
	msg := trunc(req.Error, 500)
	switch {
	case req.OK:
		if err := s.store.FinishTask(ctx, id, req.Worker, TaskDone, "", now, now); err != nil {
			s.workerFail(w, r, err)
			return
		}
		switch t.Kind {
		case KindVoiceCreate:
			if err := s.store.SetVoiceStatus(ctx, t.VoiceID, StatusReady, "", now); err != nil && !errors.Is(err, ErrNotFound) {
				s.fail(w, r, err)
				return
			}
		case KindVoiceDelete:
			if err := s.store.FinishDeleteVoice(ctx, t.VoiceID); err != nil {
				s.fail(w, r, err)
				return
			}
		}
	case req.Retry:
		if err := s.store.FinishTask(ctx, id, req.Worker, TaskQueued, msg, now.Add(retryDelay(t.Attempts)), now); err != nil {
			s.workerFail(w, r, err)
			return
		}
	default:
		if err := s.store.FinishTask(ctx, id, req.Worker, TaskFailed, msg, now, now); err != nil {
			s.workerFail(w, r, err)
			return
		}
		switch t.Kind {
		case KindVoiceCreate:
			if err := s.store.SetVoiceStatus(ctx, t.VoiceID, StatusFailed, trunc(msg, 300), now); err != nil && !errors.Is(err, ErrNotFound) {
				s.fail(w, r, err)
				return
			}
		case KindVoiceDelete:
			s.log.Error("AiStack voice not deleted; the row stays 'deleting' for a manual check", "voice", t.VoiceID, "err", msg)
		}
	}
	s.log.Info("voice task", "task", id, "kind", t.Kind, "ok", req.OK, "retry", req.Retry, "attempt", t.Attempts)
	w.WriteHeader(http.StatusNoContent)
}

// workerSample hands the decrypted sample to the worker, which uploads it to AiStack.
func (s *Server) workerSample(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	if !isUUID(id) {
		s.fail(w, r, ErrNotFound)
		return
	}
	v, err := s.store.GetVoice(r.Context(), id)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	if v.Status == StatusDeleting || v.SampleFile == "" {
		s.fail(w, r, apiErr(http.StatusConflict, "voice_deleting", "the voice is being deleted"))
		return
	}
	b, err := s.box.Read(v.SampleFile)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	ct := "audio/mp4"
	if v.SampleExt == "wav" {
		ct = "audio/wav"
	}
	w.Header().Set("Content-Type", ct)
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Length", strconv.Itoa(len(b)))
	_, _ = w.Write(b)
}

// workerPutLine stores one rendered line (m4a, X-Duration-S, X-Lang).
func (s *Server) workerPutLine(w http.ResponseWriter, r *http.Request) {
	id, hash := r.PathValue("id"), r.PathValue("hash")
	if !isUUID(id) || !isHash(hash) {
		s.fail(w, r, apiErr(http.StatusBadRequest, "invalid_request", "bad voice id or hash"))
		return
	}
	dur, err := strconv.ParseFloat(r.Header.Get("X-Duration-S"), 64)
	if err != nil || dur <= 0 || dur > 120 {
		s.fail(w, r, apiErr(http.StatusBadRequest, "invalid_request", "X-Duration-S: seconds, 0–120"))
		return
	}
	lang := r.Header.Get("X-Lang")
	if lang == "" || len(lang) > 16 {
		s.fail(w, r, apiErr(http.StatusBadRequest, "invalid_request", "X-Lang: required"))
		return
	}
	b, err := io.ReadAll(http.MaxBytesReader(w, r.Body, MaxLineBytes))
	if err != nil {
		s.fail(w, r, apiErr(http.StatusRequestEntityTooLarge, "invalid_request", fmt.Sprintf("line: at most %d bytes", MaxLineBytes)))
		return
	}
	if ext, ok := SniffAudio(b); !ok || ext != "m4a" {
		s.fail(w, r, apiErr(http.StatusUnsupportedMediaType, "invalid_request", "line: must be m4a"))
		return
	}
	rel := linePath(id, hash)
	if err := s.box.Write(rel, b); err != nil {
		s.fail(w, r, err)
		return
	}
	l := Line{VoiceID: id, Hash: hash, Lang: lang, File: rel, Bytes: len(b), DurationS: dur, CreatedAt: s.now()}
	if err := s.store.PutLine(r.Context(), l); err != nil {
		_ = removeFile(s.cfg.DataDir, rel)
		if errors.Is(err, ErrNotFound) {
			s.fail(w, r, apiErr(http.StatusConflict, "voice_deleting", "the voice is being deleted"))
			return
		}
		s.fail(w, r, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
