package pack

import (
	"encoding/json"
	"fmt"
	"strings"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
)

func worlds(ids ...string) []dbq.World {
	out := make([]dbq.World, 0, len(ids))
	for _, id := range ids {
		out = append(out, dbq.World{ID: id, Title: "T " + id, Audience: "adult", Language: "cs", StyleID: "s"})
	}
	return out
}

func ids(ws []dbq.World) []string {
	var out []string
	for _, w := range ws {
		out = append(out, w.ID)
	}
	return out
}

func TestMatchWorlds(t *testing.T) {
	all := worlds("w_rb_02", "w_les", "w_ra_01", "w_rb_01", "w_r_ny", "w_skyisles", "w_lxf_01")
	got, err := MatchWorlds(all, Selection{Worlds: []string{"w_skyisles", "w_les"}, WorldPrefixes: []string{"w_r_", "w_rb_", "w_ra_"}})
	if err != nil {
		t.Fatal(err)
	}
	want := "w_skyisles w_les w_r_ny w_rb_01 w_rb_02 w_ra_01"
	if strings.Join(ids(got), " ") != want {
		t.Fatalf("got %v, want %s", ids(got), want)
	}
	// duplicates collapse
	got, _ = MatchWorlds(all, Selection{Worlds: []string{"w_les"}, WorldPrefixes: []string{"w_le"}})
	if strings.Join(ids(got), " ") != "w_les" {
		t.Fatalf("got %v", ids(got))
	}
	if _, err := MatchWorlds(all, Selection{Worlds: []string{"w_nope"}}); err == nil {
		t.Error("unknown world should fail")
	}
	if _, err := MatchWorlds(all, Selection{Worlds: []string{"w_lxf_01"}}); err == nil || !strings.Contains(err.Error(), "w_lxf_") {
		t.Errorf("w_lxf_ world must be refused, got %v", err)
	}
	if _, err := MatchWorlds(all, Selection{WorldPrefixes: []string{"w_lx"}}); err == nil {
		t.Error("prefix matching a w_lxf_ world must be refused")
	}
	if _, err := MatchWorlds(all, Selection{WorldPrefixes: []string{""}}); err == nil {
		t.Error("empty prefix must be refused")
	}
	if got, _ := MatchWorlds(all, Selection{WorldPrefixes: []string{"w_zzz"}}); len(got) != 0 {
		t.Errorf("prefix without match: %v", ids(got))
	}
}

func TestSelectionValidate(t *testing.T) {
	if err := (Selection{}).Validate(); err == nil {
		t.Error("empty selection must fail")
	}
	if err := (Selection{Campaigns: []string{"cp_a"}, Worlds: []string{"w_a"}}).Validate(); err == nil {
		t.Error("mixed selection must fail")
	}
	if err := (Selection{WorldPrefixes: []string{"w_r"}}).Validate(); err != nil {
		t.Error(err)
	}
}

// ep builds a ready episode with n ready panels; the first panel is animated with a ready loop.
func ep(campaign string, idx int, n int) Episode {
	id := fmt.Sprintf("ep_%s_%d", strings.TrimPrefix(campaign, "cp_"), idx)
	e := Episode{Row: dbq.Episode{ID: id, CampaignID: campaign, Idx: int32(idx), Status: "ready", Title: "Title " + id,
		TitleI18n: json.RawMessage(`{"en":"Title en"}`), PanelsReady: int32(n), PanelsTotal: int32(n), CreditsCost: int32(n),
		Choices: json.RawMessage(`[{"id":"c1","text":"Dál","i18n":{"en":"On"}}]`), Warnings: json.RawMessage(`[]`)}}
	for i := range n {
		p := dbq.Panel{EpisodeID: id, Idx: int32(i), Status: "ready", Shot: "wide", LocationID: "l_1", GapAfter: "medium",
			ImagePath: fmt.Sprintf("episodes/%s/p%02d_1000.png", id, i), Width: 832, Height: 1216, Seed: 1000 + int64(i),
			Bubbles: json.RawMessage(`[{"kind":"narration","text":"Ahoj","i18n":{"en":"Hi"}}]`),
			Sfx:     json.RawMessage(`[]`), Characters: json.RawMessage(`[]`)}
		if i == 0 {
			p.Animate, p.Motion, p.LoopSeconds, p.VideoStatus = true, "breeze", 2, "ready"
			p.VideoPath = fmt.Sprintf("episodes/%s/p00_video_77.webp", id)
		}
		e.Panels = append(e.Panels, p)
	}
	return e
}

func TestReadyPrefix(t *testing.T) {
	a, b, c := ep("cp_x", 1, 2), ep("cp_x", 2, 2), ep("cp_x", 3, 2)
	if got := ReadyPrefix([]Episode{a, b, c}); len(got) != 3 {
		t.Fatalf("all ready: %d", len(got))
	}
	failed := b
	failed.Row.Status = "failed"
	if got := ReadyPrefix([]Episode{a, failed, c}); len(got) != 1 || got[0].Row.ID != a.Row.ID {
		t.Fatalf("stop at failed episode: %d", len(got))
	}
	noImage := b
	noImage.Panels = append([]dbq.Panel{}, b.Panels...)
	noImage.Panels[1].Status = "failed"
	noImage.Panels[1].ImagePath = ""
	if got := ReadyPrefix([]Episode{a, noImage, c}); len(got) != 1 {
		t.Fatalf("stop at panel without image: %d", len(got))
	}
	// Ready status but an empty image path (inconsistent row) also stops the story.
	odd := b
	odd.Panels = append([]dbq.Panel{}, b.Panels...)
	odd.Panels[0].ImagePath = ""
	if got := ReadyPrefix([]Episode{a, odd, c}); len(got) != 1 {
		t.Fatalf("stop at empty image_path: %d", len(got))
	}
	empty := b
	empty.Panels = nil
	if got := ReadyPrefix([]Episode{empty}); len(got) != 0 {
		t.Fatal("episode without panels is not exportable")
	}
}

func TestFilter(t *testing.T) {
	w := worlds("w_a")[0]
	full := Story{Campaign: dbq.Campaign{ID: "cp_full", Title: "Full"}, World: w, Episodes: []Episode{ep("cp_full", 1, 1), ep("cp_full", 2, 1)}}
	cut := Story{Campaign: dbq.Campaign{ID: "cp_cut", Title: "Cut"}, World: w, Episodes: []Episode{ep("cp_cut", 1, 1), ep("cp_cut", 2, 1)}}
	cut.Episodes[1].Row.Status = "generating"
	none := Story{Campaign: dbq.Campaign{ID: "cp_none", Title: "None"}, World: w, Episodes: []Episode{ep("cp_none", 1, 1)}}
	none.Episodes[0].Row.Status = "failed"
	kept, notes := Filter([]Story{full, cut, none})
	if len(kept) != 2 || kept[0].Campaign.ID != "cp_full" || len(kept[0].Episodes) != 2 || kept[1].Campaign.ID != "cp_cut" || len(kept[1].Episodes) != 1 {
		t.Fatalf("kept %+v", kept)
	}
	if len(notes) != 2 || !strings.Contains(notes[0], "cp_cut") || !strings.Contains(notes[0], "stops before episode 2") ||
		!strings.Contains(notes[1], "cp_none") || !strings.Contains(notes[1], "dropped") || !strings.Contains(notes[1], "status failed") {
		t.Fatalf("notes %v", notes)
	}
}
