package pack

import (
	"context"
	"errors"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
)

func mustRules(t *testing.T) Rules {
	t.Helper()
	r, err := LoadRules()
	if err != nil {
		t.Fatal(err)
	}
	return r
}

func TestStoreRules(t *testing.T) {
	r := mustRules(t)
	if r.PackSize != 50 || r.Repo != "lioilsources/webtoon-content" || r.BaseURLs.R2 != nil || r.MaxPreviews != 6 {
		t.Fatalf("store rules %+v", r)
	}
	for k, want := range map[string]float64{"pack": 0.99, "bundle_type": 2.99, "bundle_all": 6.99, "gamebook": 1.99, "kit": 3.99} {
		if r.PriceTiers[k].USD != want {
			t.Errorf("price %s = %v", k, r.PriceTiers[k].USD)
		}
	}
	langs := []string{"cs", "en", "de", "it", "fr", "pl", "pt-BR", "ja", "ko", "vi", "ru", "uk"}
	for _, ty := range r.Types {
		for _, l := range langs {
			if ty.TitleI18n[l] == "" {
				t.Errorf("type %s: no %s title", ty.ID, l)
			}
		}
	}
	for _, b := range r.Bundles {
		for _, l := range langs {
			if b.TitleI18n[l] == "" {
				t.Errorf("bundle %s: no %s title", b.ID, l)
			}
		}
	}
	if ty, _ := r.Type("harlequin"); ty.Audience != "adult" || !ty.Active {
		t.Errorf("harlequin %+v", ty)
	}
	if ty, ok := r.Type("spooky"); !ok || ty.Active {
		t.Errorf("spooky is reserved, inactive: %+v", ty)
	}
}

func TestResolveNames(t *testing.T) {
	r := mustRules(t)
	o := Options{Type: "kids", N: 2, Version: 3}
	if err := o.ResolveNames(r); err != nil {
		t.Fatal(err)
	}
	if o.ID != "kids-2" || o.ProductID != "pack_kids_2" || o.ReleaseTag != "pack-kids-2-v3" || o.Title != "Pro děti 2" {
		t.Fatalf("names %+v", o)
	}
	if o.AssetName("a") != "kids-2-a.zip" || o.AssetName("b") != "kids-2-b.zip" {
		t.Errorf("assets %s %s", o.AssetName("a"), o.AssetName("b"))
	}
	if ti := o.TitleI18n(r); ti["en"] != "Kids 2" || ti["ja"] != "キッズ 2" {
		t.Errorf("title_i18n %v", ti)
	}
	// explicit values win; free packs get no product
	o = Options{Type: "superhero", N: 1, Version: 1, ID: "hero-x", Free: true, ReleaseTag: "custom-tag"}
	if err := o.ResolveNames(r); err != nil || o.ID != "hero-x" || o.ProductID != "" || o.ReleaseTag != "custom-tag" {
		t.Fatalf("explicit %+v %v", o, err)
	}
	// hand-named pack without -n
	o = Options{ID: "romance-1", Title: "R", Version: 2}
	if err := o.ResolveNames(r); err != nil || o.ReleaseTag != "pack-romance-1-v2" || o.AssetName("a") != "romance-1-a.zip" {
		t.Fatalf("hand-named %+v %v", o, err)
	}
	for _, bad := range []Options{{N: 1, Version: 1}, {Type: "nope", N: 1, Version: 1}, {ID: "x", Version: 1, ReleaseTag: "Bad Tag"}} {
		if err := bad.ResolveNames(r); err == nil {
			t.Errorf("%+v must fail", bad)
		}
	}
}

func writeWorldJSON(t *testing.T, root, id, body string) {
	t.Helper()
	dir := filepath.Join(root, "data", "stories", strings.TrimPrefix(id, "w_"))
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "world.json"), []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestWorldTypeAndAssign(t *testing.T) {
	r := mustRules(t)
	root := t.TempDir()
	writeWorldJSON(t, root, "w_hero", `{"id": "w_hero", "audience": "kids", "profile": "superhero"}`)
	writeWorldJSON(t, root, "w_kid", `{"id": "w_kid", "audience": "kids"}`)
	writeWorldJSON(t, root, "w_free", `{"id": "w_free", "audience": "adult", "free": true}`)
	world := func(id, aud string) dbq.World { return dbq.World{ID: id, Audience: aud} }
	for _, c := range []struct {
		w    dbq.World
		want string
	}{
		{world("w_hero", "kids"), "superhero"},   // world.json profile
		{world("w_kid", "kids"), "kids"},         // world.json without profile → audience
		{world("w_ra_01", "adult"), "harlequin"}, // no world.json → audience
	} {
		if got, err := WorldType(c.w, root, r); err != nil || got != c.want {
			t.Errorf("%s: %q %v, want %s", c.w.ID, got, err, c.want)
		}
	}
	if _, err := WorldType(world("w_free", "adult"), root, r); err == nil {
		t.Error("free world must fail")
	}
	if _, err := WorldType(world("w_teen", "teen"), root, r); err == nil {
		t.Error("teen has no type")
	}

	st := func(w dbq.World) Story { return Story{World: w, Campaign: dbq.Campaign{ID: "cp_" + w.ID}} }
	// catalog mode: one type → the pack's type
	o := Options{OutDir: "x"}
	stories := []Story{st(world("w_kid", "kids")), st(world("w_kid2", "kids"))}
	if _, err := AssignTypes(stories, &o, root, r); err != nil || o.Type != "kids" || stories[1].Type != "kids" {
		t.Fatalf("assign %+v %v", o, err)
	}
	// mixed types without -type fail
	o = Options{OutDir: "x"}
	if _, err := AssignTypes([]Story{st(world("w_kid", "kids")), st(world("w_hero", "kids"))}, &o, root, r); err == nil {
		t.Error("mixed types need -type")
	}
	// -type overrides with a note
	o = Options{OutDir: "x", Type: "superhero"}
	stories = []Story{st(world("w_kid", "kids"))}
	notes, err := AssignTypes(stories, &o, root, r)
	if err != nil || stories[0].Type != "superhero" || len(notes) != 1 {
		t.Errorf("override %v %v %v", stories[0].Type, notes, err)
	}
	// starter: mixed and unknown are fine, a pick's type stays
	o = Options{Starter: "s.zip"}
	stories = []Story{st(world("w_kid", "kids")), st(world("w_teen", "teen")), {World: world("w_x", "kids"), Type: "superhero"}}
	if _, err := AssignTypes(stories, &o, root, r); err != nil || stories[0].Type != "kids" || stories[1].Type != "" || stories[2].Type != "superhero" {
		t.Errorf("starter %+v %v", stories, err)
	}
}

func TestGhCommand(t *testing.T) {
	got := GhCommand("lioilsources/webtoon-content", "pack-kids-1-v1", "Pro děti 1 v1",
		[]string{"/c/releases/pack-kids-1-v1/kids-1-a.zip", "/c/releases/pack-kids-1-v1/kids-1-b.zip"}, "it's 50")
	want := `gh release create 'pack-kids-1-v1' '/c/releases/pack-kids-1-v1/kids-1-a.zip' '/c/releases/pack-kids-1-v1/kids-1-b.zip' --repo 'lioilsources/webtoon-content' --title 'Pro děti 1 v1' --notes 'it'\''s 50'`
	if got != want {
		t.Errorf("got  %s\nwant %s", got, want)
	}
}

func TestCatalogPackEntry(t *testing.T) {
	var parts []Part
	for _, name := range []string{"a", "b"} {
		p := Part{Name: name}
		for i := range 4 {
			id := "cp_" + name + string(rune('0'+i))
			p.Manifest.Stories = append(p.Manifest.Stories, StoryJSON{ID: id, Cover: coverPath(id), Languages: []string{"cs"}})
		}
		p.Manifest.Worlds = []WorldJSON{{ID: "w", Audience: "kids"}}
		parts = append(parts, p)
	}
	sum := &Summary{Parts: []PartSummary{{Part: "a", Path: "/o/releases/t/kids-1-a.zip", Bytes: 10, SHA256: "x"}, {Part: "b", Path: "/o/releases/t/kids-1-b.zip", Bytes: 5, SHA256: "y"}}}
	cp := catalogPack(Options{ID: "kids-1", Type: "kids", N: 1, Title: "Pro děti 1", ProductID: "pack_kids_1", Version: 1, ReleaseTag: "t"}, parts, sum)
	if cp.Stories != 8 || cp.Bytes != 15 || cp.Cover != "covers/cp_a0.webp" || len(cp.Previews) != 6 || cp.Audience != "kids" || cp.TitleI18n["en"] != "Kids 1" {
		t.Fatalf("pack %+v", cp)
	}
	if p := cp.Parts[1]; p.Part != "b" || p.Release != "t" || p.Asset != "kids-1-b.zip" || p.Stories != 4 || p.Path != "" {
		t.Errorf("part %+v", p)
	}
}

type fakePicks struct {
	worlds map[string]dbq.World
	camps  map[string][]dbq.Campaign
}

func (f fakePicks) GetWorld(_ context.Context, id string) (dbq.World, error) {
	w, ok := f.worlds[id]
	if !ok {
		return w, errors.New("no rows")
	}
	return w, nil
}

func (f fakePicks) GetCampaign(_ context.Context, id string) (dbq.Campaign, error) {
	for _, cs := range f.camps {
		for _, c := range cs {
			if c.ID == id {
				return c, nil
			}
		}
	}
	return dbq.Campaign{}, errors.New("no rows")
}

func (f fakePicks) ListWorldCampaigns(_ context.Context, id string) ([]dbq.Campaign, error) {
	return f.camps[id], nil
}

func TestStarterShowcasePicks(t *testing.T) {
	r := mustRules(t)
	root, err := RepoRoot()
	if err != nil {
		t.Fatal(err)
	}
	pf, err := ReadPicks(filepath.Join(root, "data", "starter_showcase.yaml"), r)
	if err != nil {
		t.Fatal(err)
	}
	if pf.Pack.ID != "starter" || pf.Pack.Version != 2 || len(pf.Picks) != 15 {
		t.Fatalf("pick file %+v", pf.Pack)
	}
	count, styles := map[string]int{}, map[string]bool{}
	for _, p := range pf.Picks {
		count[p.Type]++
		if styles[p.Style] {
			t.Errorf("style %s used twice (one story per style)", p.Style)
		}
		styles[p.Style] = true
		if p.Type != "harlequin" && (p.From == "" || p.World != p.From+"__"+p.Style) {
			t.Errorf("%s: a restyled pick is <from>__<style>", p.World)
		}
	}
	if count["kids"] != 5 || count["superhero"] != 5 || count["harlequin"] != 5 || pf.Picks[0].Type != "kids" {
		t.Errorf("counts %v", count)
	}
}

func TestReadAndResolvePicks(t *testing.T) {
	r := mustRules(t)
	dir := t.TempDir()
	write := func(body string) string {
		p := filepath.Join(dir, "p.yaml")
		if err := os.WriteFile(p, []byte(body), 0o644); err != nil {
			t.Fatal(err)
		}
		return p
	}
	for _, bad := range []string{
		"picks: []",
		"picks: [{world: w_a, type: kids}]",
		"picks: [{world: w_a, type: nope, style: s}]",
		"picks: [{world: w_a, type: kids, style: s}, {world: w_a, type: kids, style: t}]",
		"picks: [{world: w_lxf_a, type: kids, style: s}]",
	} {
		if _, err := ReadPicks(write(bad), r); err == nil {
			t.Errorf("%s must fail", bad)
		}
	}
	q := fakePicks{
		worlds: map[string]dbq.World{"w_a": {ID: "w_a", StyleID: "ink_wash"}, "w_b": {ID: "w_b", StyleID: "clean_webtoon_noartist"}},
		camps:  map[string][]dbq.Campaign{"w_a": {{ID: "cp_first", WorldID: "w_a"}, {ID: "cp_second", WorldID: "w_a"}}, "w_c": {{ID: "cp_c", WorldID: "w_c"}}},
	}
	ctx := context.Background()
	if _, c, err := ResolvePick(ctx, q, Pick{World: "w_a", Style: "ink_wash"}); err != nil || c.ID != "cp_first" {
		t.Errorf("first campaign: %v %v", c.ID, err)
	}
	if _, c, err := ResolvePick(ctx, q, Pick{World: "w_a", Style: "ink_wash", Campaign: "cp_second"}); err != nil || c.ID != "cp_second" {
		t.Errorf("campaign override: %v %v", c.ID, err)
	}
	if _, _, err := ResolvePick(ctx, q, Pick{World: "w_a", Style: "ink_wash", Campaign: "cp_c"}); err == nil {
		t.Error("a campaign of another world must fail")
	}
	if _, _, err := ResolvePick(ctx, q, Pick{World: "w_b", Style: "pixar_3d"}); err == nil || !strings.Contains(err.Error(), "m0/restyle.sh w_b:pixar_3d") {
		t.Errorf("style mismatch must name restyle.sh: %v", err)
	}
	if _, _, err := ResolvePick(ctx, q, Pick{World: "w_b__pixar_3d", From: "w_b", Style: "pixar_3d"}); err == nil || !strings.Contains(err.Error(), "restyle.sh w_b:pixar_3d") {
		t.Errorf("missing restyled world must name restyle.sh: %v", err)
	}
	if _, _, err := ResolvePick(ctx, q, Pick{World: "w_a", Style: "ink_wash", Campaign: "cp_nope"}); err == nil {
		t.Error("unknown campaign must fail")
	}
	q.worlds["w_d"] = dbq.World{ID: "w_d", StyleID: "s"}
	if _, _, err := ResolvePick(ctx, q, Pick{World: "w_d", Style: "s"}); err == nil {
		t.Error("world without campaign must fail")
	}
	if err := (Selection{Picks: []Pick{{World: "w_a"}}, Worlds: []string{"w_b"}}).Validate(); err == nil {
		t.Error("picks are exclusive")
	}
}
