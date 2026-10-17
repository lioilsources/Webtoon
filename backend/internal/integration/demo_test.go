package integration

import (
	"context"
	"fmt"
	"image"
	"image/png"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/demo"
)

// TestImportDemo: an imported M0 run is a ready episode the API serves like a rendered one,
// and the campaign can be continued from its choices.
func TestImportDemo(t *testing.T) {
	e := setup(t)
	ctx := context.Background()
	sb, err := os.ReadFile("../testdata/storyboard_ep1.json")
	if err != nil {
		t.Fatal(err)
	}
	dir := t.TempDir()
	for i := range 6 {
		f, err := os.Create(filepath.Join(dir, fmt.Sprintf("p%02d_s0.png", i)))
		if err != nil {
			t.Fatal(err)
		}
		if err := png.Encode(f, image.NewRGBA(image.Rect(0, 0, 832, 1216))); err != nil {
			t.Fatal(err)
		}
		f.Close()
	}
	res, err := demo.Import(ctx, e.s, demo.Options{Storyboard: sb, PanelDir: dir, MediaDir: e.media,
		WorldID: "w_skyisles", PlayerID: "reader"})
	if err != nil {
		t.Fatal(err)
	}
	if res.Index != 1 || res.Panels != 6 {
		t.Fatalf("result %+v", res)
	}

	ep := e.do("GET", "/episodes/"+res.EpisodeID, "reader", nil, 200)
	if ep["status"] != "ready" || ep["panels_ready"].(float64) != 6 || ep["credits_cost"].(float64) != 6 {
		t.Fatalf("episode %v", ep)
	}
	p0 := ep["panels"].([]any)[0].(map[string]any)
	url, _ := p0["image_url"].(string)
	if !strings.HasPrefix(url, "/media/episodes/"+res.EpisodeID+"/p00_") || p0["width"].(float64) != 832 {
		t.Fatalf("panel 0 %v", p0)
	}
	if _, err := os.Stat(filepath.Join(e.media, strings.TrimPrefix(url, "/media/"))); err != nil {
		t.Fatal(err)
	}
	choices := ep["choices"].([]any)
	if choices[0].(map[string]any)["id"] != "c1" || choices[len(choices)-1].(map[string]any)["id"] != "free" {
		t.Fatalf("choices %v", choices)
	}

	list := e.do("GET", "/campaigns", "reader", nil, 200)["campaigns"].([]any)
	if len(list) != 1 || list[0].(map[string]any)["id"] != res.CampaignID ||
		list[0].(map[string]any)["world_title"] == "" || list[0].(map[string]any)["last_episode_status"] != "ready" {
		t.Fatalf("campaigns %v", list)
	}
	if n := len(e.do("GET", "/campaigns", "someone-else", nil, 200)["campaigns"].([]any)); n != 0 {
		t.Fatalf("other player sees %d campaigns", n)
	}
	camp := e.do("GET", "/campaigns/"+res.CampaignID, "reader", nil, 200)
	if st := camp["state"].(map[string]any); st["current_location"] != "l_cliff" {
		t.Fatalf("state_diff not applied: %v", st)
	}

	// Second import appends episode 2 to the same campaign.
	res2, err := demo.Import(ctx, e.s, demo.Options{Storyboard: sb, PanelDir: dir, MediaDir: e.media, CampaignID: res.CampaignID})
	if err != nil || res2.Index != 2 {
		t.Fatalf("append: %+v %v", res2, err)
	}
	// The player continues with a closed choice (director is accepted and ignored for now).
	next := e.do("POST", "/campaigns/"+res.CampaignID+"/episodes", "reader",
		map[string]any{"choice_id": "c2", "director": map[string]any{"location_id": "l_market"}}, 202)
	if next["index"].(float64) != 3 {
		t.Fatalf("next %v", next)
	}
	if _, err := demo.Import(ctx, e.s, demo.Options{Storyboard: sb, PanelDir: dir, MediaDir: e.media, CampaignID: res.CampaignID}); err == nil {
		t.Fatal("import into a campaign with a queued episode should fail")
	}
}
