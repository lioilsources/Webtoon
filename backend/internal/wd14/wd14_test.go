package wd14_test

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/upstream"
	"github.com/ol1n/webtoon/backend/internal/wd14"
)

func TestSafetyThresholds(t *testing.T) {
	cases := []struct {
		rating map[string]float64
		want   map[string]float64
	}{
		{map[string]float64{"general": 0.9, "explicit": 0.2, "questionable": 0.3}, map[string]float64{}},
		{map[string]float64{"explicit": 0.20001}, map[string]float64{"explicit": 0.2}},
		{map[string]float64{"questionable": 0.4567, "explicit": 0.5}, map[string]float64{"questionable": 0.457, "explicit": 0.5}},
	}
	for _, c := range cases {
		if got := wd14.Safety(&wd14.Tags{Rating: c.rating}); !reflect.DeepEqual(got, c.want) {
			t.Errorf("Safety(%v) = %v, want %v", c.rating, got, c.want)
		}
	}
}

func TestIdentityScore(t *testing.T) {
	tg := &wd14.Tags{General: map[string]float64{"short hair": 0.9, "green eyes": 0.35, "freckles": 0.34}}
	id := wd14.IdentityScore(tg, "short hair, green eyes, freckles")
	if id.Recall != 0.667 || !reflect.DeepEqual(id.Missing, []string{"freckles"}) {
		t.Fatalf("%+v", id)
	}
	if id := wd14.IdentityScore(tg, ""); id.Recall != 0 {
		t.Fatalf("%+v", id)
	}
}

func TestClient(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		b, _ := io.ReadAll(r.Body)
		if r.URL.Path != "/tag" || r.Header.Get("Content-Type") != "application/octet-stream" || string(b) != "PNG" {
			http.Error(w, "bad", 400)
			return
		}
		w.Write([]byte(`{"general": {"smile": 0.8}, "character": {}, "rating": {"general": 0.95}}`))
	}))
	defer srv.Close()
	tg, err := wd14.New(srv.URL).Tag(context.Background(), []byte("PNG"))
	if err != nil || tg.General["smile"] != 0.8 || tg.Rating["general"] != 0.95 {
		t.Fatalf("%+v %v", tg, err)
	}
	srv.Close()
	if _, err := wd14.New(srv.URL).Tag(context.Background(), []byte("PNG")); !upstream.IsUnavailable(err) {
		t.Fatalf("closed server must be unavailable, got %v", err)
	}
}
