package api

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

type fakePlayer struct{}

func (fakePlayer) Register(mux *http.ServeMux) {
	mux.HandleFunc("GET /v1/player/ping", func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(http.StatusTeapot) })
}

func TestPlayerRoutesMounted(t *testing.T) {
	for _, p := range []Registrar{fakePlayer{}, nil} {
		h := New(Config{Player: p}, nil, nil).Handler()
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, httptest.NewRequest("GET", "/v1/player/ping", nil))
		want := http.StatusTeapot
		if p == nil {
			want = http.StatusNotFound
		}
		if rec.Code != want {
			t.Fatalf("player %v: %d", p, rec.Code)
		}
	}
}
