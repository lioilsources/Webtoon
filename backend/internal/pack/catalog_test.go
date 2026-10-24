package pack

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

const pagesURL = "https://lioilsources.github.io/webtoon-content/"

func TestCatalogMerge(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "catalog.json")
	c, err := ReadCatalog(path)
	if err != nil || c.Version != 0 || len(c.Packs) != 0 || c.Schema != CatalogSchema {
		t.Fatalf("missing catalog: %+v %v", c, err)
	}
	now := time.Date(2026, 10, 23, 8, 0, 0, 0, time.UTC)
	c.Merge(CatalogPack{ID: "harlequin-1", Type: "harlequin", N: 1, Title: "Romantika 1", Stories: 1, ProductID: "pack_harlequin_1", Version: 1,
		Parts: []CatalogPart{{Part: "a", Release: "pack-harlequin-1-v1", Asset: "harlequin-1-a.zip", Bytes: 10, SHA256: "aa", Stories: 1}}, Languages: []string{"cs"}, Audience: "adult"},
		[]CatalogStory{{ID: "cp_1", PackID: "harlequin-1", Type: "harlequin", WorldID: "w_rb_01", Title: "One", TitleI18n: json.RawMessage(`{}`), Cover: "covers/cp_1.webp", Episodes: 1, Audience: "adult"}},
		now, "")
	c.Merge(CatalogPack{ID: "kids-1", Type: "kids", Title: "Kids", Stories: 1, Free: true, Version: 1, Parts: []CatalogPart{}, Languages: []string{"cs"}, Audience: "kids"},
		[]CatalogStory{{ID: "cp_k", PackID: "kids-1", Type: "kids", WorldID: "w_les", Title: "K", TitleI18n: json.RawMessage(`{}`), Cover: "covers/cp_k.webp", Episodes: 2, Audience: "kids"}},
		now, "")
	if err := WriteCatalog(path, c); err != nil {
		t.Fatal(err)
	}
	c, err = ReadCatalog(path)
	if err != nil {
		t.Fatal(err)
	}
	if c.Version != 2 || c.BaseURLs.Pages != pagesURL || c.BaseURLs.R2 != nil || c.GeneratedAt != "2026-10-23T08:00:00Z" || len(c.Packs) != 2 || len(c.Stories) != 2 {
		t.Fatalf("catalog %+v", c)
	}
	raw, _ := os.ReadFile(path)
	var generic map[string]any
	_ = json.Unmarshal(raw, &generic)
	if generic["schema"] != float64(2) {
		t.Errorf("schema %v", generic["schema"])
	}
	if _, ok := generic["base_url"]; ok {
		t.Error("schema 2 writes base_urls, not base_url")
	}
	urls := generic["base_urls"].(map[string]any)
	if v, ok := urls["r2"]; !ok || v != nil {
		t.Errorf("r2 must be written as null: %v", urls)
	}
	packs := generic["packs"].([]any)
	if _, ok := packs[0].(map[string]any)["product_id"]; !ok {
		t.Error("paid pack needs product_id")
	}
	if _, ok := packs[1].(map[string]any)["product_id"]; ok || packs[1].(map[string]any)["free"] != true {
		t.Error("free pack has no product_id")
	}
	part := packs[0].(map[string]any)["parts"].([]any)[0].(map[string]any)
	if part["release"] != "pack-harlequin-1-v1" || part["asset"] != "harlequin-1-a.zip" || part["part"] != "a" {
		t.Errorf("part %v", part)
	}
	if _, ok := part["path"]; ok {
		t.Error("a release part has no path")
	}
	// types: the three active ones; bundles from pack.yaml with covers {types} / "all"
	var typeIDs []string
	for _, ty := range c.Types {
		typeIDs = append(typeIDs, ty.ID)
	}
	if strings.Join(typeIDs, " ") != "kids harlequin superhero" {
		t.Errorf("types %v", typeIDs)
	}
	bundles := generic["bundles"].([]any)
	if len(bundles) != 4 {
		t.Fatalf("bundles %v", bundles)
	}
	last := bundles[3].(map[string]any)
	if last["id"] != "bundle_all" || last["covers"] != "all" || last["price_tier"] != "bundle_all" {
		t.Errorf("bundle_all %v", last)
	}
	first := bundles[0].(map[string]any)["covers"].(map[string]any)["types"].([]any)
	if len(first) != 1 || first[0] != "kids" {
		t.Errorf("bundle_kids covers %v", first)
	}
	if g, ok := generic["gamebooks"].([]any); !ok || len(g) != 0 {
		t.Errorf("gamebooks %v", generic["gamebooks"])
	}

	// Re-export of harlequin-1 v2 replaces the pack in place and its stories.
	c.Merge(CatalogPack{ID: "harlequin-1", Type: "harlequin", Title: "Romantika 1", Stories: 2, ProductID: "pack_harlequin_1", Version: 2,
		Parts: []CatalogPart{{Part: "a", Release: "pack-harlequin-1-v2", Asset: "harlequin-1-a.zip", Bytes: 20, SHA256: "bb"}}, Languages: []string{"cs", "en"}, Audience: "adult"},
		[]CatalogStory{
			{ID: "cp_1", PackID: "harlequin-1", Title: "One", Episodes: 2},
			{ID: "cp_2", PackID: "harlequin-1", Title: "Two", Episodes: 1},
		}, now.Add(time.Hour), "https://example.org/")
	if c.Version != 3 || c.GeneratedAt != "2026-10-23T09:00:00Z" || c.BaseURLs.Pages != "https://example.org/" {
		t.Fatalf("version %d at %s, pages %s", c.Version, c.GeneratedAt, c.BaseURLs.Pages)
	}
	if len(c.Packs) != 2 || c.Packs[0].ID != "harlequin-1" || c.Packs[0].Version != 2 || c.Packs[0].Parts[0].Release != "pack-harlequin-1-v2" || c.Packs[1].ID != "kids-1" {
		t.Fatalf("packs %+v", c.Packs)
	}
	if len(c.Stories) != 3 || c.Stories[0].ID != "cp_k" || c.Stories[1].ID != "cp_1" || c.Stories[1].Episodes != 2 || c.Stories[2].ID != "cp_2" {
		t.Fatalf("stories %+v", c.Stories)
	}

	if err := os.WriteFile(path, []byte(`{"schema": 3}`), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := ReadCatalog(path); err == nil {
		t.Error("unknown schema must be refused")
	}
}

// A schema 1 catalog is read and upgraded: base_url → base_urls.pages, type from audience, legacy part paths kept.
func TestCatalogSchema1Upgrade(t *testing.T) {
	path := filepath.Join(t.TempDir(), "catalog.json")
	v1 := `{"schema": 1, "version": 3, "generated_at": "2026-10-20T00:00:00Z", "base_url": "https://old.example/",
	  "packs": [{"id": "romance-1", "title": "Romance I", "stories": 1, "free": false, "product_id": "pack_romance_1",
	             "parts": [{"path": "packs/romance-1-v1-a.zip", "bytes": 5, "sha256": "cc"}],
	             "languages": ["cs"], "audience": "adult", "version": 1}],
	  "stories": [{"id": "cp_1", "pack_id": "romance-1", "world_id": "w_r", "title": "One", "title_i18n": {},
	               "cover": "covers/cp_1.webp", "episodes": 1, "audience": "adult"},
	              {"id": "cp_k", "pack_id": "romance-1", "world_id": "w_k", "title": "K", "title_i18n": {},
	               "cover": "covers/cp_k.webp", "episodes": 1, "audience": "kids"}]}`
	if err := os.WriteFile(path, []byte(v1), 0o644); err != nil {
		t.Fatal(err)
	}
	c, err := ReadCatalog(path)
	if err != nil {
		t.Fatal(err)
	}
	if c.Schema != 2 || c.BaseURLs.Pages != "https://old.example/" || c.BaseURL != "" || c.Version != 3 {
		t.Fatalf("upgrade %+v", c)
	}
	if c.Packs[0].Type != "harlequin" || c.Stories[0].Type != "harlequin" || c.Stories[1].Type != "kids" {
		t.Errorf("types %s %s %s", c.Packs[0].Type, c.Stories[0].Type, c.Stories[1].Type)
	}
	if c.Packs[0].Parts[0].Path != "packs/romance-1-v1-a.zip" {
		t.Errorf("legacy part %+v", c.Packs[0].Parts[0])
	}
	if len(c.Bundles) != 0 || len(c.Types) != 0 {
		t.Error("schema 1 has no types/bundles until rules are applied")
	}
}

// catalog-bundles: base_urls, types and bundles come from pack.yaml, packs/stories/gamebooks stay, version bumps.
func TestRefreshCatalog(t *testing.T) {
	path := filepath.Join(t.TempDir(), "catalog.json")
	start := `{"schema": 2, "version": 5, "generated_at": "x", "base_urls": {"pages": "p", "releases": "r", "r2": "https://r2/"},
	  "types": [{"id": "old", "title_i18n": {}, "audience": "kids", "icon": "x"}],
	  "packs": [{"id": "animals-1", "type": "animals", "title": "A", "free": true, "version": 1, "stories": 0, "bytes": 0,
	             "audience": "kids", "languages": [], "parts": []}],
	  "bundles": [{"id": "bundle_old", "product_id": "bundle_old", "price_tier": "x", "title_i18n": {}, "covers": "all"}],
	  "gamebooks": [{"id": "drak", "product_id": "gamebook_drak", "kit_product_id": "kit_drak", "status": "planned"}],
	  "stories": []}`
	if err := os.WriteFile(path, []byte(start), 0o644); err != nil {
		t.Fatal(err)
	}
	now := time.Date(2026, 10, 24, 0, 0, 0, 0, time.UTC)
	c, err := RefreshCatalog(path, "", now)
	if err != nil {
		t.Fatal(err)
	}
	if c.Version != 6 || c.GeneratedAt != "2026-10-24T00:00:00Z" || c.BaseURLs.Pages != pagesURL || c.BaseURLs.R2 != nil ||
		!strings.Contains(c.BaseURLs.Releases, "/releases/download/") {
		t.Fatalf("refresh %+v", c)
	}
	var ids []string
	for _, ty := range c.Types {
		ids = append(ids, ty.ID)
	}
	// animals is inactive but a pack uses it, so it is listed (pack.yaml order)
	if strings.Join(ids, " ") != "kids harlequin superhero animals" {
		t.Errorf("types %v", ids)
	}
	if len(c.Bundles) != 4 || c.Bundles[0].ID != "bundle_kids" || !c.Bundles[3].Covers.All || c.Bundles[0].TitleI18n["en"] == "" {
		t.Errorf("bundles %+v", c.Bundles)
	}
	if len(c.Gamebooks) != 1 || !strings.Contains(string(c.Gamebooks[0]), "kit_drak") || len(c.Packs) != 1 {
		t.Errorf("gamebooks/packs must stay: %s %d", c.Gamebooks, len(c.Packs))
	}
	back, err := ReadCatalog(path)
	if err != nil || back.Version != 6 {
		t.Fatalf("written: %v %v", back, err)
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
