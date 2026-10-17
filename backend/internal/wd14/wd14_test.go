package wd14_test

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"reflect"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/testutil"
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
	id := wd14.IdentityScore(tg, "short hair, green eyes, freckles", "")
	if id.Recall != 0.667 || !reflect.DeepEqual(id.Missing, []string{"freckles"}) {
		t.Fatalf("%+v", id)
	}
	if id := wd14.IdentityScore(tg, "", ""); id.Recall != 0 {
		t.Fatalf("%+v", id)
	}
	// Out-of-frame tags do not count: boots are not in a medium shot, the skirt not in a close-up.
	tg = &wd14.Tags{General: map[string]float64{"short hair": 0.9}}
	if id := wd14.IdentityScore(tg, "short hair, red skirt, brown boots", "close-up"); id.Recall != 1 || len(id.Missing) != 0 {
		t.Fatalf("close-up %+v", id)
	}
	if id := wd14.IdentityScore(tg, "short hair, red skirt, brown boots", "medium"); id.Recall != 0.5 ||
		!reflect.DeepEqual(id.Missing, []string{"red skirt"}) {
		t.Fatalf("medium %+v", id)
	}
}

// TestIdentityMatchesPrototype compares with render.identity on the M0 character for every shot.
func TestIdentityMatchesPrototype(t *testing.T) {
	g := testutil.Golden(t)
	var cases []struct {
		Shot    string             `json:"shot"`
		General map[string]float64 `json:"general"`
		Want    wd14.Identity      `json:"identity"`
	}
	testutil.GoldenField(t, g, "identity", &cases)
	if len(cases) == 0 {
		t.Fatal("no golden identity cases")
	}
	w := testutil.World(t)
	for _, c := range cases {
		got := wd14.IdentityScore(&wd14.Tags{General: c.General}, w.Characters[0].TagPrompt, c.Shot)
		if got.Recall != c.Want.Recall || !reflect.DeepEqual(got.Missing, c.Want.Missing) {
			t.Errorf("shot %q: got %+v, want %+v", c.Shot, got, c.Want)
		}
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
