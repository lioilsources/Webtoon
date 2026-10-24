package pack

import (
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"

	"gopkg.in/yaml.v3"
)

// Rules are the pack rules of rules/base/pack.yaml (part size, WebP quality, cover size, the never-exported world
// prefix, the dropped episode fields); the reasons are commented there.
type Rules struct {
	PartSize             int                         `yaml:"part_size"`
	WebPQuality          int                         `yaml:"webp_quality"`
	Cover                struct{ Width, Height int } `yaml:"cover"`
	ForbiddenWorldPrefix string                      `yaml:"forbidden_world_prefix"`
	DroppedEpisodeFields []string                    `yaml:"dropped_episode_fields"`

	// Store and catalog (catalog schema 2).
	CatalogSchema    int                  `yaml:"catalog_schema"`
	BaseURLs         BaseURLs             `yaml:"base_urls"`
	Repo             string               `yaml:"repo"`
	PackSize         int                  `yaml:"pack_size"`
	MaxPreviews      int                  `yaml:"max_previews"`
	Naming           Naming               `yaml:"naming"`
	PriceTiers       map[string]PriceTier `yaml:"price_tiers"`
	Types            []TypeRule           `yaml:"types"`
	TypeFromProfile  map[string]string    `yaml:"type_from_profile"`
	TypeFromAudience map[string]string    `yaml:"type_from_audience"`
	Bundles          []CatalogBundle      `yaml:"bundles"`
}

// Naming holds the templates of pack.yaml `naming`, filled with {type} {n} {version} {part} {id}.
type Naming struct {
	PackID          string `yaml:"pack_id"`
	ProductID       string `yaml:"product_id"`
	ReleaseTag      string `yaml:"release_tag"`
	Asset           string `yaml:"asset"`
	GamebookProduct string `yaml:"gamebook_product"`
	KitProduct      string `yaml:"kit_product"`
}

// PriceTier is a price hint (docs/store-products.md); the app shows the store's own price.
type PriceTier struct {
	USD  float64 `yaml:"usd"`
	Tier int     `yaml:"tier"`
}

// TypeRule is one pack type; only active ones (or ones a pack uses) go into catalog.json types.
type TypeRule struct {
	ID        string            `yaml:"id"`
	Active    bool              `yaml:"active"`
	Audience  string            `yaml:"audience"`
	Icon      string            `yaml:"icon"`
	TitleI18n map[string]string `yaml:"title_i18n"`
}

// Type looks a pack type up by id.
func (r Rules) Type(id string) (TypeRule, bool) {
	for _, t := range r.Types {
		if t.ID == id {
			return t, true
		}
	}
	return TypeRule{}, false
}

// Fill expands a naming template: {type} {n} {version} {part} {id}.
func Fill(tmpl string, vars map[string]string) string {
	out := tmpl
	for k, v := range vars {
		out = strings.ReplaceAll(out, "{"+k+"}", v)
	}
	return out
}

var (
	rulesOnce sync.Once
	rules     Rules
	rulesErr  error
)

// RulesPath is $WEBTOON_RULES/base/pack.yaml, else rules/base/pack.yaml in the working directory or the nearest parent
// that has one (the CLI runs from backend/, tests from backend/internal/pack).
func RulesPath() (string, error) {
	if d := os.Getenv("WEBTOON_RULES"); d != "" {
		return filepath.Join(d, "base", "pack.yaml"), nil
	}
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		p := filepath.Join(dir, "rules", "base", "pack.yaml")
		if _, err := os.Stat(p); err == nil {
			return p, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("rules/base/pack.yaml not found from the working directory up (set WEBTOON_RULES)")
		}
		dir = parent
	}
}

// LoadRules reads and validates rules/base/pack.yaml once.
func LoadRules() (Rules, error) {
	rulesOnce.Do(func() {
		p, err := RulesPath()
		if err != nil {
			rulesErr = err
			return
		}
		b, err := os.ReadFile(p)
		if err != nil {
			rulesErr = err
			return
		}
		var r Rules
		if err := yaml.Unmarshal(b, &r); err != nil {
			rulesErr = fmt.Errorf("%s: %w", p, err)
			return
		}
		if r.PartSize < 1 || r.WebPQuality < 1 || r.Cover.Width < 1 || r.Cover.Height < 1 || r.ForbiddenWorldPrefix == "" {
			rulesErr = fmt.Errorf("%s: part_size, webp_quality, cover and forbidden_world_prefix are required", p)
			return
		}
		if err := r.validateStore(); err != nil {
			rulesErr = fmt.Errorf("%s: %w", p, err)
			return
		}
		rules = r
	})
	return rules, rulesErr
}

func (r Rules) validateStore() error {
	if r.CatalogSchema != CatalogSchema {
		return fmt.Errorf("catalog_schema %d, this tool writes %d", r.CatalogSchema, CatalogSchema)
	}
	if r.BaseURLs.Pages == "" || r.BaseURLs.Releases == "" || r.Repo == "" || r.PackSize < 1 {
		return fmt.Errorf("base_urls.pages, base_urls.releases, repo and pack_size are required")
	}
	n := r.Naming
	if n.PackID == "" || n.ProductID == "" || n.ReleaseTag == "" || n.Asset == "" || n.GamebookProduct == "" || n.KitProduct == "" {
		return fmt.Errorf("naming needs pack_id, product_id, release_tag, asset, gamebook_product, kit_product")
	}
	seen := map[string]bool{}
	for _, t := range r.Types {
		if !typeIDRe.MatchString(t.ID) || seen[t.ID] {
			return fmt.Errorf("type id %q: [a-z0-9]+, unique", t.ID)
		}
		seen[t.ID] = true
		if _, ok := audienceRank[t.Audience]; !ok {
			return fmt.Errorf("type %s: audience %q", t.ID, t.Audience)
		}
	}
	for k, v := range r.TypeFromProfile {
		if !seen[v] {
			return fmt.Errorf("type_from_profile %s: unknown type %s", k, v)
		}
	}
	for k, v := range r.TypeFromAudience {
		if !seen[v] {
			return fmt.Errorf("type_from_audience %s: unknown type %s", k, v)
		}
	}
	for _, b := range r.Bundles {
		if b.ID == "" || b.ProductID == "" {
			return fmt.Errorf("bundle without id/product_id")
		}
		if _, ok := r.PriceTiers[b.PriceTier]; !ok {
			return fmt.Errorf("bundle %s: unknown price_tier %q", b.ID, b.PriceTier)
		}
		if !b.Covers.All && len(b.Covers.Types) == 0 {
			return fmt.Errorf("bundle %s covers nothing", b.ID)
		}
		for _, t := range b.Covers.Types {
			if !seen[t] {
				return fmt.Errorf("bundle %s: unknown type %s", b.ID, t)
			}
		}
	}
	for _, k := range []string{"pack", "bundle_type", "bundle_all", "gamebook", "kit"} {
		if _, ok := r.PriceTiers[k]; !ok {
			return fmt.Errorf("price_tiers.%s is required", k)
		}
	}
	return nil
}

var typeIDRe = regexp.MustCompile(`^[a-z0-9]+$`)

// RepoRoot is the directory that holds rules/ (and data/stories/).
func RepoRoot() (string, error) {
	p, err := RulesPath()
	if err != nil {
		return "", err
	}
	return filepath.Dir(filepath.Dir(filepath.Dir(p))), nil
}

// rule is LoadRules for code paths without an error return; Run calls LoadRules first, so a missing file
// fails the export cleanly before anything reaches here.
func rule() Rules {
	r, err := LoadRules()
	if err != nil {
		panic(err)
	}
	return r
}
