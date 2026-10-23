package pack

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func TestCatalogMerge(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "catalog.json")
	c, err := ReadCatalog(path)
	if err != nil || c.Version != 0 || len(c.Packs) != 0 {
		t.Fatalf("missing catalog: %+v %v", c, err)
	}
	now := time.Date(2026, 10, 23, 8, 0, 0, 0, time.UTC)
	c.Merge(CatalogPack{ID: "romance-1", Title: "Romance I", Stories: 1, ProductID: "pack_romance_1", Version: 1,
		Parts: []CatalogPart{{Path: "packs/romance-1-v1.zip", Bytes: 10, SHA256: "aa"}}, Languages: []string{"cs"}, Audience: "adult"},
		[]CatalogStory{{ID: "cp_1", PackID: "romance-1", WorldID: "w_rb_01", Title: "One", TitleI18n: json.RawMessage(`{}`), Cover: "covers/cp_1.webp", Episodes: 1, Audience: "adult"}},
		now, DefaultBaseURL)
	c.Merge(CatalogPack{ID: "kids-1", Title: "Kids", Stories: 1, Free: true, Version: 1, Parts: []CatalogPart{}, Languages: []string{"cs"}, Audience: "kids"},
		[]CatalogStory{{ID: "cp_k", PackID: "kids-1", WorldID: "w_les", Title: "K", TitleI18n: json.RawMessage(`{}`), Cover: "covers/cp_k.webp", Episodes: 2, Audience: "kids"}},
		now, "")
	if err := WriteCatalog(path, c); err != nil {
		t.Fatal(err)
	}
	c, err = ReadCatalog(path)
	if err != nil {
		t.Fatal(err)
	}
	if c.Version != 2 || c.BaseURL != DefaultBaseURL || c.GeneratedAt != "2026-10-23T08:00:00Z" || len(c.Packs) != 2 || len(c.Stories) != 2 {
		t.Fatalf("catalog %+v", c)
	}
	raw, _ := os.ReadFile(path)
	var generic map[string]any
	_ = json.Unmarshal(raw, &generic)
	packs := generic["packs"].([]any)
	if _, ok := packs[0].(map[string]any)["product_id"]; !ok {
		t.Error("paid pack needs product_id")
	}
	if _, ok := packs[1].(map[string]any)["product_id"]; ok || packs[1].(map[string]any)["free"] != true {
		t.Error("free pack has no product_id")
	}

	// Re-export of romance-1 v2 with two stories replaces the pack in place and its stories.
	c.Merge(CatalogPack{ID: "romance-1", Title: "Romance I", Stories: 2, ProductID: "pack_romance_1", Version: 2,
		Parts: []CatalogPart{{Path: "packs/romance-1-v2.zip", Bytes: 20, SHA256: "bb"}}, Languages: []string{"cs", "en"}, Audience: "adult"},
		[]CatalogStory{
			{ID: "cp_1", PackID: "romance-1", Title: "One", Episodes: 2},
			{ID: "cp_2", PackID: "romance-1", Title: "Two", Episodes: 1},
		}, now.Add(time.Hour), "")
	if c.Version != 3 || c.GeneratedAt != "2026-10-23T09:00:00Z" {
		t.Fatalf("version %d at %s", c.Version, c.GeneratedAt)
	}
	if len(c.Packs) != 2 || c.Packs[0].ID != "romance-1" || c.Packs[0].Version != 2 || c.Packs[0].Parts[0].Path != "packs/romance-1-v2.zip" || c.Packs[1].ID != "kids-1" {
		t.Fatalf("packs %+v", c.Packs)
	}
	if len(c.Stories) != 3 || c.Stories[0].ID != "cp_k" || c.Stories[1].ID != "cp_1" || c.Stories[1].Episodes != 2 || c.Stories[2].ID != "cp_2" {
		t.Fatalf("stories %+v", c.Stories)
	}

	if err := os.WriteFile(path, []byte(`{"schema": 2}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := ReadCatalog(path); err == nil {
		t.Error("foreign schema must be refused")
	}
}

func TestPackAudienceAndLanguages(t *testing.T) {
	parts := []Part{
		{Manifest: Manifest{Worlds: []WorldJSON{{ID: "a", Audience: "kids"}, {ID: "b", Audience: "teen"}},
			Stories: []StoryJSON{{Languages: []string{"cs", "en"}}, {Languages: []string{"cs", "de"}}}}},
		{Manifest: Manifest{Worlds: []WorldJSON{{ID: "c", Audience: "adult"}}, Stories: []StoryJSON{{Languages: []string{"cs"}}}}},
	}
	if got := packAudience(parts); got != "adult" {
		t.Errorf("audience %q", got)
	}
	if got := packLanguages(parts); len(got) != 3 || got[0] != "cs" || got[1] != "en" || got[2] != "de" {
		t.Errorf("languages %v", got)
	}
	if got := packAudience(parts[:1]); got != "teen" {
		t.Errorf("audience %q", got)
	}
}
