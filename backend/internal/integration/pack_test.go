package integration

import (
	"archive/zip"
	"context"
	"encoding/json"
	"fmt"
	"image"
	"image/png"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
	"time"

	"github.com/ol1n/webtoon/backend/internal/demo"
	"github.com/ol1n/webtoon/backend/internal/pack"
)

// TestExportPack: two imported episodes become a pack whose episode JSON is GET /episodes/{id}
// minus the dropped fields, with zip-relative media; a third failed episode cuts the story.
func TestExportPack(t *testing.T) {
	if err := pack.CheckCwebp(); err != nil {
		t.Skip(err)
	}
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
		if err := png.Encode(f, image.NewRGBA(image.Rect(0, 0, 64, 96))); err != nil {
			t.Fatal(err)
		}
		f.Close()
	}
	res, err := demo.Import(ctx, e.s, demo.Options{Storyboard: sb, PanelDir: dir, MediaDir: e.media, WorldID: "w_skyisles", PlayerID: "reader"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := demo.Import(ctx, e.s, demo.Options{Storyboard: sb, PanelDir: dir, MediaDir: e.media, CampaignID: res.CampaignID}); err != nil {
		t.Fatal(err)
	}
	// Episode 3 is queued (not ready): the story stops after episode 2.
	e.do("POST", "/campaigns/"+res.CampaignID+"/episodes", "reader", map[string]any{"choice_id": "c1"}, 202)
	// A second campaign without a ready episode is dropped.
	empty := e.do("POST", "/campaigns", "reader", map[string]any{"world_id": "w_skyisles"}, 201)["campaign"].(map[string]any)

	out := t.TempDir()
	now := time.Date(2026, 10, 23, 8, 0, 0, 0, time.UTC)
	sum, err := pack.Run(ctx, e.s.Q, pack.Options{ID: "it", Title: "IT", Version: 1, Free: true, OutDir: out, MediaDir: e.media, Now: now},
		pack.Selection{Worlds: []string{"w_skyisles"}})
	if err != nil {
		t.Fatal(err)
	}
	if len(sum.Parts) != 1 || sum.Parts[0].Stories != 1 || sum.Parts[0].Episodes != 2 || sum.Parts[0].Panels != 12 {
		t.Fatalf("summary %+v", sum.Parts)
	}
	if len(sum.Notes) != 2 || !strings.Contains(sum.Notes[0], "stops before episode 3") || !strings.Contains(sum.Notes[1], empty["id"].(string)) {
		t.Fatalf("notes %v", sum.Notes)
	}

	zr, err := zip.OpenReader(sum.Parts[0].Path)
	if err != nil {
		t.Fatal(err)
	}
	defer zr.Close()
	entries := map[string]bool{}
	var manifest pack.Manifest
	for _, f := range zr.File {
		entries[f.Name] = true
		if f.Name == "pack.json" {
			rc, _ := f.Open()
			if err := json.NewDecoder(rc).Decode(&manifest); err != nil {
				t.Fatal(err)
			}
			rc.Close()
		}
	}
	if len(manifest.Stories) != 1 || len(manifest.Episodes) != 2 || len(manifest.Worlds) != 1 || manifest.Worlds[0].ID != "w_skyisles" {
		t.Fatalf("manifest %+v", manifest)
	}
	st := manifest.Stories[0]
	if st.ID != res.CampaignID || len(st.Episodes) != 2 || st.Episodes[0] != res.EpisodeID || st.Cover != "covers/"+res.CampaignID+".webp" || !entries[st.Cover] {
		t.Fatalf("story %+v", st)
	}
	if !entries["media/"+res.EpisodeID+"/p00.webp"] || !entries["media/"+res.EpisodeID+"/p05.webp"] || len(entries) != 1+1+12 {
		t.Fatalf("entries %v", entries)
	}

	// Episode JSON == API JSON minus dropped fields, with URLs rewritten.
	api := e.do("GET", "/episodes/"+res.EpisodeID, "reader", nil, 200)
	for _, k := range []string{"error", "created_at", "updated_at"} {
		delete(api, k)
	}
	for i, p := range api["panels"].([]any) {
		pm := p.(map[string]any)
		for _, k := range []string{"seed", "identity_score", "error", "video_error", "estimate_seconds"} {
			delete(pm, k)
		}
		pm["image_url"] = fmt.Sprintf("media/%s/p%02d.webp", res.EpisodeID, i)
	}
	var got map[string]any
	raw, _ := json.Marshal(manifest.Episodes[0])
	_ = json.Unmarshal(raw, &got)
	if !reflect.DeepEqual(got, api) {
		t.Fatalf("episode\n got %v\nwant %v", got, api)
	}

	// Catalog and covers next to it.
	cat, err := pack.ReadCatalog(filepath.Join(out, "catalog.json"))
	if err != nil {
		t.Fatal(err)
	}
	if cat.Version != 1 || len(cat.Packs) != 1 || cat.Packs[0].ID != "it" || !cat.Packs[0].Free || cat.Packs[0].Audience != "teen" ||
		cat.Packs[0].Parts[0].Path != "packs/it-v1.zip" || cat.Packs[0].Parts[0].Bytes != sum.Parts[0].Bytes || len(cat.Stories) != 1 || cat.Stories[0].Episodes != 2 {
		t.Fatalf("catalog %+v", cat)
	}
	if _, err := os.Stat(filepath.Join(out, st.Cover)); err != nil {
		t.Fatal(err)
	}
	// Second run with the same version is refused (files are never overwritten).
	if _, err := pack.Run(ctx, e.s.Q, pack.Options{ID: "it", Title: "IT", Version: 1, Free: true, OutDir: out, MediaDir: e.media, Now: now},
		pack.Selection{Campaigns: []string{res.CampaignID}}); err == nil || !strings.Contains(err.Error(), "exists") {
		t.Fatalf("overwrite: %v", err)
	}
	// Starter: one zip, no catalog touched.
	starter := filepath.Join(t.TempDir(), "starter.zip")
	if _, err := pack.Run(ctx, e.s.Q, pack.Options{ID: "starter", Title: "Starter", Version: 1, Starter: starter, MediaDir: e.media, Now: now},
		pack.Selection{Campaigns: []string{res.CampaignID}}); err != nil {
		t.Fatal(err)
	}
	if _, err := os.Stat(starter); err != nil {
		t.Fatal(err)
	}
	if cat2, _ := pack.ReadCatalog(filepath.Join(out, "catalog.json")); cat2.Version != 1 {
		t.Fatal("starter must not touch the catalog")
	}
}
