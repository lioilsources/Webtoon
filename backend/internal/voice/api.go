package voice

import (
	"context"
	"crypto/rand"
	"crypto/subtle"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"log/slog"
	"net/http"
	"strings"
	"time"

	"github.com/ol1n/webtoon/backend/internal/voice/receipt"
)

// ReceiptVerifier checks the voice_clone purchase (receipt.Verifier in production).
type ReceiptVerifier interface {
	Verify(ctx context.Context, platform, rcpt, host string) (receipt.Purchase, error)
}

// Server serves /v1/player/* (app, device token) and /v1/worker/* (Spark worker, worker token).
type Server struct {
	cfg     Config
	store   Store
	box     *Box // nil without VOICE_DATA_KEY: voice endpoints answer 503
	rv      ReceiptVerifier
	limiter *RateLimiter
	now     func() time.Time
	log     *slog.Logger

	// ReceiptMaxDevices limits how many devices one purchase may give a voice at the same time.
	ReceiptMaxDevices int
}

// New builds the server. now == nil uses time.Now.
func New(cfg Config, st Store, rv ReceiptVerifier, now func() time.Time, log *slog.Logger) (*Server, error) {
	cfg = cfg.withDefaults()
	if now == nil {
		now = time.Now
	}
	if log == nil {
		log = slog.Default()
	}
	box, err := NewBox(cfg.DataKey, cfg.DataDir)
	if err != nil {
		return nil, err
	}
	if box == nil {
		log.Warn("VOICE_DATA_KEY is not set: player voice endpoints answer 503 voice_unavailable")
	}
	return &Server{cfg: cfg, store: st, box: box, rv: rv, now: now, log: log.With("component", "voice"),
		limiter: NewRateLimiter(cfg.DeviceRate, time.Hour, now), ReceiptMaxDevices: 3}, nil
}

// Register adds the routes to mux.
func (s *Server) Register(mux *http.ServeMux) {
	mux.HandleFunc("POST /v1/player/devices", s.registerDevice)
	mux.Handle("DELETE /v1/player/devices/me", s.device(s.deleteDevice))
	mux.Handle("POST /v1/player/voices", s.device(s.createVoice))
	mux.Handle("GET /v1/player/voices/{id}", s.device(s.getVoice))
	mux.Handle("DELETE /v1/player/voices/{id}", s.device(s.deleteVoiceHandler))
	mux.Handle("POST /v1/player/voices/{id}/lines", s.device(s.createLines))
	mux.Handle("GET /v1/player/jobs/{id}", s.device(s.getJob))
	mux.HandleFunc("GET /v1/player/lines/{voice}/{file}", s.serveLine)

	mux.Handle("GET /v1/worker/voice-tasks/pending", s.worker(s.pendingTasks))
	mux.Handle("POST /v1/worker/voice-tasks/claim", s.worker(s.claimTask))
	mux.Handle("POST /v1/worker/voice-tasks/{id}/heartbeat", s.worker(s.heartbeatTask))
	mux.Handle("POST /v1/worker/voice-tasks/{id}/complete", s.worker(s.completeTask))
	mux.Handle("GET /v1/worker/voices/{id}/sample", s.worker(s.workerSample))
	mux.Handle("PUT /v1/worker/voices/{id}/lines/{hash}", s.worker(s.workerPutLine))
}

// --- errors ----------------------------------------------------------------------------

// apiError is the JSON error of the player and worker API: {"error": code, "message": text}.
type apiError struct {
	status int
	code   string
	msg    string
	extra  map[string]any
}

func (e *apiError) Error() string { return e.code + ": " + e.msg }

func apiErr(status int, code, msg string) *apiError {
	return &apiError{status: status, code: code, msg: msg}
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	w.WriteHeader(status)
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	enc.Encode(v) //nolint:errcheck
}

func (s *Server) fail(w http.ResponseWriter, r *http.Request, err error) {
	var ae *apiError
	switch {
	case errors.As(err, &ae):
		body := map[string]any{"error": ae.code, "message": ae.msg}
		for k, v := range ae.extra {
			body[k] = v
		}
		writeJSON(w, ae.status, body)
	case errors.Is(err, ErrNotFound):
		writeJSON(w, http.StatusNotFound, map[string]any{"error": "not_found", "message": "not found"})
	default:
		s.log.Error("internal error", "method", r.Method, "path", r.URL.Path, "err", err)
		writeJSON(w, http.StatusInternalServerError, map[string]any{"error": "internal", "message": "internal error"})
	}
}

var errUnavailable = apiErr(http.StatusServiceUnavailable, "voice_unavailable", "voice cloning is not configured on this server")

// --- auth ------------------------------------------------------------------------------

type deviceHandler func(w http.ResponseWriter, r *http.Request, d Device)

// device authenticates `Authorization: Bearer <device token>`.
func (s *Server) device(next deviceHandler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		token, ok := strings.CutPrefix(r.Header.Get("Authorization"), "Bearer ")
		if ok && token != "" {
			d, err := s.store.DeviceByTokenHash(r.Context(), SHA256Hex(token), s.now())
			switch {
			case err == nil:
				next(w, r, d)
				return
			case !errors.Is(err, ErrNotFound):
				s.fail(w, r, err)
				return
			}
		}
		w.Header().Set("WWW-Authenticate", `Bearer realm="toonfork"`)
		s.fail(w, r, apiErr(http.StatusUnauthorized, "unauthorized", "missing or unknown device token"))
	})
}

// worker authenticates the Spark worker with VOICE_WORKER_TOKEN.
func (s *Server) worker(next http.HandlerFunc) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if s.cfg.WorkerToken == "" || s.box == nil {
			s.fail(w, r, apiErr(http.StatusServiceUnavailable, "worker_unavailable", "voice worker API is not configured"))
			return
		}
		got := []byte(r.Header.Get("Authorization"))
		want := []byte("Bearer " + s.cfg.WorkerToken)
		if subtle.ConstantTimeCompare(got, want) != 1 {
			s.fail(w, r, apiErr(http.StatusUnauthorized, "unauthorized", "bad worker token"))
			return
		}
		next(w, r)
	})
}

func randHex(n int) string {
	b := make([]byte, n)
	_, _ = rand.Read(b)
	return hex.EncodeToString(b)
}

// newUUID returns a random (v4) UUID.
func newUUID() string {
	b := make([]byte, 16)
	_, _ = rand.Read(b)
	b[6] = b[6]&0x0f | 0x40
	b[8] = b[8]&0x3f | 0x80
	h := hex.EncodeToString(b)
	return h[0:8] + "-" + h[8:12] + "-" + h[12:16] + "-" + h[16:20] + "-" + h[20:32]
}

func isUUID(s string) bool {
	if len(s) != 36 {
		return false
	}
	for i, c := range s {
		switch i {
		case 8, 13, 18, 23:
			if c != '-' {
				return false
			}
		default:
			if !(c >= '0' && c <= '9' || c >= 'a' && c <= 'f') {
				return false
			}
		}
	}
	return true
}

func isHash(s string) bool {
	if len(s) != 64 {
		return false
	}
	_, err := hex.DecodeString(s)
	return err == nil && strings.ToLower(s) == s
}

// --- devices ---------------------------------------------------------------------------

func (s *Server) registerDevice(w http.ResponseWriter, r *http.Request) {
	if !s.limiter.Allow(clientIP(r)) {
		w.Header().Set("Retry-After", "600")
		s.fail(w, r, apiErr(http.StatusTooManyRequests, "rate_limited", "too many registrations, try later"))
		return
	}
	var body struct {
		Platform string `json:"platform"`
	}
	if r.ContentLength > 0 {
		_ = json.NewDecoder(http.MaxBytesReader(w, r.Body, 4<<10)).Decode(&body)
	}
	plat := strings.ToLower(strings.TrimSpace(body.Platform))
	if plat != "ios" && plat != "android" {
		plat = ""
	}
	tb := make([]byte, 32)
	if _, err := rand.Read(tb); err != nil {
		s.fail(w, r, err)
		return
	}
	token := base64.RawURLEncoding.EncodeToString(tb)
	now := s.now()
	d := Device{ID: "dev_" + randHex(8), TokenHash: SHA256Hex(token), Platform: plat, CreatedAt: now, LastSeenAt: now}
	if err := s.store.CreateDevice(r.Context(), d); err != nil {
		s.fail(w, r, err)
		return
	}
	writeJSON(w, http.StatusCreated, map[string]string{"device_id": d.ID, "token": token})
}

func (s *Server) deleteDevice(w http.ResponseWriter, r *http.Request, d Device) {
	v, err := s.store.ActiveVoiceByDevice(r.Context(), d.ID)
	if err != nil {
		s.fail(w, r, err)
		return
	}
	if v != nil {
		if err := s.DeleteVoice(r.Context(), v.ID, "device_deleted"); err != nil {
			s.fail(w, r, err)
			return
		}
	}
	if err := s.store.DeleteDevice(r.Context(), d.ID); err != nil {
		s.fail(w, r, err)
		return
	}
	s.log.Info("device deleted", "device", d.ID)
	w.WriteHeader(http.StatusNoContent)
}

// DeleteVoice removes the sample and the lines at once and queues the AiStack deletion.
// The database goes first, so the worker cannot fetch the sample any more; leftover files
// (a failed remove) are swept by Purge.
func (s *Server) DeleteVoice(ctx context.Context, id, reason string) error {
	now := s.now()
	t := Task{ID: "vt_" + randHex(8), Kind: KindVoiceDelete, VoiceID: id, Priority: 10, Status: TaskQueued,
		RunAfter: now, CreatedAt: now, UpdatedAt: now}
	if err := s.store.BeginDeleteVoice(ctx, id, reason, now, t); err != nil {
		return err
	}
	if err := removeVoiceDir(s.cfg.DataDir, id); err != nil {
		s.log.Error("voice files not removed, Purge retries", "voice", id, "err", err)
	}
	s.log.Info("voice deleted", "voice", id, "reason", reason)
	return nil
}

func (s *Server) voiceURL(path string) string { return s.cfg.PublicURL + path }

func fmtTime(t time.Time) string { return t.UTC().Format(time.RFC3339) }

func day(t time.Time) string { return t.UTC().Format("2006-01-02") }

func trunc(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n]
}
