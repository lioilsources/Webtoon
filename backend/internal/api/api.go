// Package api is the HTTP API (WEBTOON_PLAN §7) on the Go 1.22 stdlib router.
package api

import (
	"context"
	"encoding/json"
	"errors"
	"io/fs"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/store"
	"github.com/ol1n/webtoon/backend/internal/tags"
)

// Waker is notified after a job is enqueued (the in-process worker pool).
type Waker interface{ Wake() }

type Config struct {
	MediaDir     string
	MediaBaseURL string // prefix for image URLs, default "/media"
	MaxAttempts  int
	MaxUpload    int64          // reference image upload limit, default 8 MiB
	LLM          llm.JSONCaller // tag_prompt generation (nil = 503)
	Vocab        *tags.Vocab    // WD14 vocabulary for the tag repair pass
	CORSOrigins  []string       // browser origins allowed to call the API (Flutter web); empty = no CORS headers
}

type Server struct {
	cfg   Config
	store *store.Store
	waker Waker
	log   *slog.Logger
}

func New(cfg Config, s *store.Store, waker Waker) *Server {
	if cfg.MediaBaseURL == "" {
		cfg.MediaBaseURL = "/media"
	}
	cfg.MediaBaseURL = strings.TrimRight(cfg.MediaBaseURL, "/")
	if cfg.MaxAttempts <= 0 {
		cfg.MaxAttempts = 3
	}
	if cfg.MaxUpload <= 0 {
		cfg.MaxUpload = defaultMaxUpload
	}
	return &Server{cfg: cfg, store: s, waker: waker, log: slog.Default().With("component", "api")}
}

func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /health", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "service": "webtoon"})
	})

	mux.HandleFunc("POST /worlds", s.requireUser(s.createWorld))
	mux.HandleFunc("GET /worlds", s.listWorlds)
	mux.HandleFunc("GET /worlds/{id}", s.getWorld)
	mux.HandleFunc("PATCH /worlds/{id}", s.requireUser(s.patchWorld))
	mux.HandleFunc("POST /worlds/{id}/characters", s.requireUser(s.createCharacter))
	mux.HandleFunc("POST /worlds/{id}/locations", s.requireUser(s.createLocation))
	mux.HandleFunc("GET /worlds/{id}/stats", s.requireUser(s.worldStats))

	// M3 author tools
	mux.HandleFunc("GET /style_presets", s.listStylePresets)
	mux.HandleFunc("PATCH /worlds/{id}/characters/{cid}", s.requireUser(s.patchCharacter))
	mux.HandleFunc("DELETE /worlds/{id}/characters/{cid}", s.requireUser(s.deleteCharacter))
	mux.HandleFunc("POST /worlds/{id}/characters/{cid}/tag_prompt", s.requireUser(s.characterTagPrompt))
	mux.HandleFunc("POST /worlds/{id}/characters/{cid}/sheet", s.requireUser(s.createSheet))
	mux.HandleFunc("GET /worlds/{id}/characters/{cid}/sheets", s.requireUser(s.listSheets))
	mux.HandleFunc("POST /worlds/{id}/characters/{cid}/references", s.requireUser(s.uploadCharacterReference))
	mux.HandleFunc("PATCH /worlds/{id}/locations/{lid}", s.requireUser(s.patchLocation))
	mux.HandleFunc("DELETE /worlds/{id}/locations/{lid}", s.requireUser(s.deleteLocation))
	mux.HandleFunc("POST /worlds/{id}/locations/{lid}/tag_prompt", s.requireUser(s.locationTagPrompt))
	mux.HandleFunc("POST /worlds/{id}/locations/{lid}/references", s.requireUser(s.uploadLocationReference))
	mux.HandleFunc("GET /sheets/{sid}", s.requireUser(s.getSheet))

	mux.HandleFunc("POST /campaigns", s.requireUser(s.createCampaign))
	mux.HandleFunc("GET /campaigns", s.requireUser(s.listCampaigns))
	mux.HandleFunc("GET /campaigns/{id}", s.requireUser(s.getCampaign))
	mux.HandleFunc("POST /campaigns/{id}/episodes", s.requireUser(s.createEpisode))

	mux.HandleFunc("GET /episodes/{id}", s.requireUser(s.getEpisode))
	mux.HandleFunc("PATCH /episodes/{id}/panels/{n}", s.requireUser(s.patchPanel))

	mux.HandleFunc("GET /media/{path...}", s.media)

	return s.withCORS(s.withUser(s.logRequests(mux)))
}

// withCORS lets the Flutter web build call the API from another origin and answers preflights.
func (s *Server) withCORS(next http.Handler) http.Handler {
	if len(s.cfg.CORSOrigins) == 0 {
		return next
	}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if origin := r.Header.Get("Origin"); origin != "" && s.corsAllowed(origin) {
			h := w.Header()
			h.Set("Access-Control-Allow-Origin", origin)
			h.Add("Vary", "Origin")
			if r.Method == http.MethodOptions && r.Header.Get("Access-Control-Request-Method") != "" {
				h.Set("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
				h.Set("Access-Control-Allow-Headers", "Content-Type, X-User-ID")
				h.Set("Access-Control-Max-Age", "600")
				w.WriteHeader(http.StatusNoContent)
				return
			}
		}
		next.ServeHTTP(w, r)
	})
}

func (s *Server) corsAllowed(origin string) bool {
	for _, o := range s.cfg.CORSOrigins {
		if o == "*" || o == origin {
			return true
		}
	}
	return false
}

// --- auth stub -----------------------------------------------------------------

type ctxKey struct{}

// withUser reads X-User-ID. Placeholder for Ol1nLLM accounts: the header is trusted as-is.
func (s *Server) withUser(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if uid := strings.TrimSpace(r.Header.Get("X-User-ID")); uid != "" {
			r = r.WithContext(context.WithValue(r.Context(), ctxKey{}, uid))
		}
		next.ServeHTTP(w, r)
	})
}

func userID(r *http.Request) string {
	uid, _ := r.Context().Value(ctxKey{}).(string)
	return uid
}

func (s *Server) requireUser(h http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if userID(r) == "" {
			writeErr(w, http.StatusUnauthorized, "missing X-User-ID")
			return
		}
		h(w, r)
	}
}

type statusRecorder struct {
	http.ResponseWriter
	code int
}

func (r *statusRecorder) WriteHeader(code int) { r.code = code; r.ResponseWriter.WriteHeader(code) }

func (s *Server) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		t0 := time.Now()
		rec := &statusRecorder{ResponseWriter: w, code: http.StatusOK}
		next.ServeHTTP(rec, r)
		if r.URL.Path != "/health" && !strings.HasPrefix(r.URL.Path, "/media/") {
			s.log.Info("request", "method", r.Method, "path", r.URL.Path, "status", rec.code,
				"ms", time.Since(t0).Milliseconds(), "user", userID(r))
		}
	})
}

// --- media -----------------------------------------------------------------------

func (s *Server) media(w http.ResponseWriter, r *http.Request) {
	p := r.PathValue("path")
	fsys := os.DirFS(s.cfg.MediaDir)
	if !fs.ValidPath(p) {
		http.NotFound(w, r)
		return
	}
	st, err := fs.Stat(fsys, p)
	if err != nil || st.IsDir() {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Cache-Control", "public, max-age=86400")
	http.ServeFileFS(w, r, fsys, p)
}

func (s *Server) mediaURL(rel string) string {
	if rel == "" {
		return ""
	}
	return s.cfg.MediaBaseURL + "/" + rel
}

func (s *Server) wake() {
	if s.waker != nil {
		s.waker.Wake()
	}
}

// --- helpers ---------------------------------------------------------------------

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	enc.Encode(v) //nolint:errcheck
}

func writeErr(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}

func (s *Server) fail(w http.ResponseWriter, err error) {
	if errors.Is(err, store.ErrNotFound) {
		writeErr(w, http.StatusNotFound, "not found")
		return
	}
	var he *httpErr
	if errors.As(err, &he) {
		writeErr(w, he.code, he.msg)
		return
	}
	s.log.Error("internal error", "err", err)
	writeErr(w, http.StatusInternalServerError, "internal error")
}

type httpErr struct {
	code int
	msg  string
}

func (e *httpErr) Error() string { return e.msg }

func errf(code int, msg string) error { return &httpErr{code: code, msg: msg} }

func decode(r *http.Request, v any) error {
	dec := json.NewDecoder(http.MaxBytesReader(nil, r.Body, 1<<20))
	if err := dec.Decode(v); err != nil {
		return errf(http.StatusBadRequest, "invalid JSON body: "+err.Error())
	}
	return nil
}

func rawOr(raw json.RawMessage, def string) json.RawMessage {
	if len(raw) == 0 {
		return json.RawMessage(def)
	}
	return raw
}
