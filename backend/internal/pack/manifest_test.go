package pack

import (
	"encoding/json"
	"fmt"
	"maps"
	"reflect"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/episodejson"
)

func story(world dbq.World, n int, eps ...Episode) Story {
	id := eps[0].Row.CampaignID
	return Story{Campaign: dbq.Campaign{ID: id, WorldID: world.ID, Title: eps[0].Row.Title}, World: world, Episodes: eps}
}

func roundTrip(t *testing.T, v any) map[string]any {
	t.Helper()
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatal(err)
	}
	var m map[string]any
	if err := json.Unmarshal(b, &m); err != nil {
		t.Fatal(err)
	}
	return m
}

// TestEpisodeShape: a pack episode is GET /episodes/{id} (internal/episodejson, the API's own
// serialiser) minus the dropped fields, with URLs relative to the zip root.
func TestEpisodeShape(t *testing.T) {
	w := worlds("w_a")[0]
	e := ep("cp_a", 1, 3)
	e.Panels[1].IdentityScore = ptr(float32(0.9))
	e.Panels[2].Animate, e.Panels[2].VideoStatus, e.Panels[2].VideoError = true, "failed", "boom"
	parts, err := Plan(Options{ID: "p", Title: "P", Version: 1, MediaDir: "/m", Now: time.Unix(0, 0)}, []Story{story(w, 1, e)})
	if err != nil {
		t.Fatal(err)
	}
	got := roundTrip(t, parts[0].Manifest.Episodes[0])

	api := roundTrip(t, episodejson.EpisodeJSON(e.Row, e.Panels, w.Language, func(rel string) string { return "/media/" + rel }))
	for _, k := range rule().DroppedEpisodeFields {
		if _, ok := api[k]; !ok {
			t.Fatalf("API shape lost %q; update PACK_FORMAT.md and droppedEpisodeFields", k)
		}
		delete(api, k)
	}
	if !slices.Equal(slices.Sorted(maps.Keys(got)), slices.Sorted(maps.Keys(api))) {
		t.Fatalf("episode keys\n got %v\nwant %v", slices.Sorted(maps.Keys(got)), slices.Sorted(maps.Keys(api)))
	}
	apiPanels := api["panels"].([]any)
	gotPanels := got["panels"].([]any)
	dropped := []string{"seed", "identity_score", "error", "video_error", "estimate_seconds"}
	for i := range apiPanels {
		ap, gp := apiPanels[i].(map[string]any), gotPanels[i].(map[string]any)
		for _, k := range dropped {
			delete(ap, k)
			if _, ok := gp[k]; ok {
				t.Errorf("panel %d still has %q", i, k)
			}
		}
		ap["image_url"] = fmt.Sprintf("media/%s/p%02d.webp", e.Row.ID, i)
		if _, ok := ap["video_url"]; ok {
			ap["video_url"] = fmt.Sprintf("media/%s/p%02d_loop.webp", e.Row.ID, i)
		}
		if !reflect.DeepEqual(ap, gp) {
			t.Errorf("panel %d\n got %v\nwant %v", i, gp, ap)
		}
	}
	delete(api, "panels")
	delete(got, "panels")
	if !reflect.DeepEqual(api, got) {
		t.Errorf("episode\n got %v\nwant %v", got, api)
	}
	// Panel 2: animated but the loop failed → no video_url, and the error is not shipped.
	if _, ok := gotPanels[2].(map[string]any)["video_url"]; ok {
		t.Error("failed loop must not have video_url")
	}
	if parts[0].Loops != 1 || parts[0].Panels != 3 {
		t.Errorf("loops %d panels %d", parts[0].Loops, parts[0].Panels)
	}
}

func ptr[T any](v T) *T { return &v }

func TestPlanStoriesWorldsFiles(t *testing.T) {
	wa, wb := worlds("w_a", "w_b")[0], worlds("w_a", "w_b")[1]
	wb.Audience = "kids"
	e1, e2 := ep("cp_a", 1, 2), ep("cp_a", 2, 1)
	e2.Row.TitleI18n = json.RawMessage(`{"en":"Two"}`)
	// Episode 2 lacks German: the story's languages are the intersection, source language first.
	e1.Row.TitleI18n = json.RawMessage(`{"en":"One","de":"Eins"}`)
	for i := range e1.Panels {
		e1.Panels[i].Bubbles = json.RawMessage(`[{"kind":"narration","text":"Ahoj","i18n":{"en":"Hi","de":"Hallo"}}]`)
	}
	e1.Row.Choices = json.RawMessage(`[{"id":"c1","text":"Dál","i18n":{"en":"On","de":"Weiter"}}]`)
	sa := story(wa, 2, e1, e2)
	sb := story(wb, 1, ep("cp_b", 1, 1))
	sb.Campaign.Title = "Different title" // not the first episode's title → no title_i18n
	parts, err := Plan(Options{ID: "p", Title: "P", Version: 2, MediaDir: "/m", Now: time.Unix(0, 0)}, []Story{sa, sb})
	if err != nil {
		t.Fatal(err)
	}
	m := parts[0].Manifest
	if m.Schema != 1 || m.ID != "p" || m.Version != 2 || m.Part != "" || m.GeneratedAt != "1970-01-01T00:00:00Z" {
		t.Fatalf("manifest %+v", m)
	}
	if len(m.Worlds) != 2 || m.Worlds[0].ID != "w_a" || m.Worlds[1].Audience != "kids" {
		t.Fatalf("worlds %+v", m.Worlds)
	}
	s0, s1 := m.Stories[0], m.Stories[1]
	if s0.ID != "cp_a" || s0.WorldID != "w_a" || s0.Cover != "covers/cp_a.webp" || !slices.Equal(s0.Episodes, []string{e1.Row.ID, e2.Row.ID}) {
		t.Fatalf("story 0 %+v", s0)
	}
	if string(s0.TitleI18n) != `{"en":"One","de":"Eins"}` || !slices.Equal(s0.Languages, []string{"cs", "en"}) {
		t.Fatalf("story 0 i18n %s langs %v", s0.TitleI18n, s0.Languages)
	}
	if string(s1.TitleI18n) != "{}" || s1.Title != "Different title" || !slices.Equal(s1.Languages, []string{"cs", "en"}) {
		t.Fatalf("story 1 %+v", s1)
	}
	if len(m.Episodes) != 3 {
		t.Fatalf("episodes %d", len(m.Episodes))
	}
	// Files: covers first (story order), then media in episode / panel order; loops next to their still.
	var paths []string
	for _, f := range parts[0].Files {
		paths = append(paths, f.Path)
	}
	want := []string{"covers/cp_a.webp", "covers/cp_b.webp",
		"media/ep_a_1/p00.webp", "media/ep_a_1/p00_loop.webp", "media/ep_a_1/p01.webp",
		"media/ep_a_2/p00.webp", "media/ep_a_2/p00_loop.webp",
		"media/ep_b_1/p00.webp", "media/ep_b_1/p00_loop.webp"}
	if !slices.Equal(paths, want) {
		t.Fatalf("files\n got %v\nwant %v", paths, want)
	}
	if f := parts[0].Files[0]; f.Kind != kindCover || f.Src != "/m/episodes/ep_a_1/p00_1000.png" {
		t.Fatalf("cover file %+v", f)
	}
	if f := parts[0].Files[3]; f.Kind != kindCopy || f.Src != "/m/episodes/ep_a_1/p00_video_77.webp" {
		t.Fatalf("loop file %+v", f)
	}
}

func TestPlanRejects(t *testing.T) {
	w := worlds("w_a")[0]
	ok := []Story{story(w, 1, ep("cp_a", 1, 1))}
	for _, o := range []Options{
		{ID: "Bad_ID", Title: "t", Version: 1},
		{ID: "ok", Title: "", Version: 1},
		{ID: "ok", Title: "t", Version: 0},
	} {
		if _, err := Plan(o, ok); err == nil {
			t.Errorf("options %+v accepted", o)
		}
	}
	if _, err := Plan(Options{ID: "ok", Title: "t", Version: 1}, nil); err == nil {
		t.Error("no stories accepted")
	}
	bad := story(w, 1, ep("cp_a", 1, 1))
	bad.Episodes[0].Row.Status = "failed"
	if _, err := Plan(Options{ID: "ok", Title: "t", Version: 1}, []Story{bad}); err == nil || !strings.Contains(err.Error(), "not exportable") {
		t.Errorf("unfiltered story accepted: %v", err)
	}
}

func TestSplitParts(t *testing.T) {
	w := worlds("w_a")[0]
	var stories []Story
	for i := range 60 {
		stories = append(stories, story(w, 1, ep(fmt.Sprintf("cp_%02d", i), 1, 1)))
	}
	parts, err := Plan(Options{ID: "big", Title: "Big", Version: 1, Now: time.Unix(0, 0)}, stories)
	if err != nil {
		t.Fatal(err)
	}
	if len(parts) != 3 {
		t.Fatalf("parts %d", len(parts))
	}
	for i, want := range []struct {
		name string
		n    int
	}{{"a", 25}, {"b", 25}, {"c", 10}} {
		p := parts[i]
		if p.Name != want.name || p.Manifest.Part != want.name || len(p.Stories) != want.n || len(p.Manifest.Stories) != want.n ||
			len(p.Manifest.Episodes) != want.n || p.Manifest.ID != "big" {
			t.Errorf("part %d: %s %d stories %d episodes", i, p.Name, len(p.Manifest.Stories), len(p.Manifest.Episodes))
		}
		if p.Manifest.Stories[0].ID != fmt.Sprintf("cp_%02d", i*25) {
			t.Errorf("part %d starts with %s", i, p.Manifest.Stories[0].ID)
		}
		// Each part is self-contained: only its own episodes and worlds.
		for _, s := range p.Manifest.Stories {
			if !slices.ContainsFunc(p.Manifest.Episodes, func(e map[string]any) bool { return e["id"] == s.Episodes[0] }) {
				t.Errorf("part %s misses episode of %s", p.Name, s.ID)
			}
		}
	}
	// 25 stories fit in one unnamed zip; the starter is never split.
	if parts, _ := Plan(Options{ID: "p", Title: "P", Version: 1}, stories[:25]); len(parts) != 1 || parts[0].Name != "" || parts[0].Manifest.Part != "" {
		t.Errorf("25 stories: %d parts, name %q", len(parts), parts[0].Name)
	}
	if parts, _ := Plan(Options{ID: "starter", Title: "S", Version: 1, Starter: "x.zip"}, stories); len(parts) != 1 || len(parts[0].Stories) != 60 {
		t.Errorf("starter must not be split: %d parts", len(parts))
	}
	// Worlds list only the worlds used in the part.
	wb := worlds("w_b")[0]
	mixed := append(slices.Clone(stories[:25]), story(wb, 1, ep("cp_bb", 1, 1)))
	parts, _ = Plan(Options{ID: "p", Title: "P", Version: 1}, mixed)
	if len(parts) != 2 || len(parts[0].Manifest.Worlds) != 1 || parts[1].Manifest.Worlds[0].ID != "w_b" || len(parts[1].Manifest.Worlds) != 1 {
		t.Errorf("worlds per part: %+v / %+v", parts[0].Manifest.Worlds, parts[1].Manifest.Worlds)
	}
}
