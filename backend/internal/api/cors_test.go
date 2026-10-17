package api

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestCORS(t *testing.T) {
	ok := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(http.StatusTeapot) })
	s := &Server{cfg: Config{CORSOrigins: []string{"http://localhost:8096"}}}
	h := s.withCORS(ok)

	pre := httptest.NewRequest(http.MethodOptions, "/worlds", nil)
	pre.Header.Set("Origin", "http://localhost:8096")
	pre.Header.Set("Access-Control-Request-Method", "PATCH")
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, pre)
	if rec.Code != http.StatusNoContent || rec.Header().Get("Access-Control-Allow-Headers") == "" {
		t.Fatalf("preflight: %d %v", rec.Code, rec.Header())
	}

	other := httptest.NewRequest(http.MethodGet, "/worlds", nil)
	other.Header.Set("Origin", "http://evil.example")
	rec = httptest.NewRecorder()
	h.ServeHTTP(rec, other)
	if rec.Code != http.StatusTeapot || rec.Header().Get("Access-Control-Allow-Origin") != "" {
		t.Fatalf("foreign origin: %d %v", rec.Code, rec.Header())
	}

	if (&Server{}).withCORS(ok) == nil {
		t.Fatal("nil handler")
	}
}
