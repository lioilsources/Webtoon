package pack

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"slices"
	"time"

	"gopkg.in/yaml.v3"
)

// CatalogSchema is the catalog.json schema this tool writes (PACK_FORMAT.md); schema 1 is still read.
const CatalogSchema = 2

// Catalog is catalog.json at the root of webtoon-content (schema 2).
type Catalog struct {
	Schema      int    `json:"schema"`
	Version     int    `json:"version"`
	GeneratedAt string `json:"generated_at"`
	// BaseURL is schema 1's only URL (= base_urls.pages); read, never written.
	BaseURL   string            `json:"base_url,omitempty"`
	BaseURLs  BaseURLs          `json:"base_urls"`
	Types     []CatalogType     `json:"types"`
	Packs     []CatalogPack     `json:"packs"`
	Bundles   []CatalogBundle   `json:"bundles"`
	Gamebooks []json.RawMessage `json:"gamebooks"` // STUB: kept as written by hand until the gamebook format exists
	Stories   []CatalogStory    `json:"stories"`
}

// BaseURLs are the hosts the app composes URLs from: Pages (catalog, covers), Releases (zips), R2 (zips, when set).
type BaseURLs struct {
	Pages    string  `json:"pages" yaml:"pages"`
	Releases string  `json:"releases" yaml:"releases"`
	R2       *string `json:"r2" yaml:"r2"`
}

// CatalogType is one pack type (rules/base/pack.yaml types).
type CatalogType struct {
	ID        string            `json:"id"`
	TitleI18n map[string]string `json:"title_i18n"`
	Audience  string            `json:"audience"`
	Icon      string            `json:"icon"`
}

// CatalogPack is one downloadable pack.
type CatalogPack struct {
	ID        string            `json:"id"`
	Type      string            `json:"type"`
	N         int               `json:"n,omitempty"`
	Title     string            `json:"title"`
	TitleI18n map[string]string `json:"title_i18n,omitempty"`
	ProductID string            `json:"product_id,omitempty"`
	Free      bool              `json:"free"`
	Version   int               `json:"version"`
	Stories   int               `json:"stories"`
	Bytes     int64             `json:"bytes"`
	Audience  string            `json:"audience"`
	Languages []string          `json:"languages"`
	Cover     string            `json:"cover,omitempty"`
	Previews  []string          `json:"previews,omitempty"`
	Parts     []CatalogPart     `json:"parts"`
}

// CatalogPart is one zip of a pack: a GitHub release asset (schema 2) or a Pages path (schema 1, legacy).
type CatalogPart struct {
	Part    string `json:"part,omitempty"`
	Release string `json:"release,omitempty"`
	Asset   string `json:"asset,omitempty"`
	Path    string `json:"path,omitempty"`
	Bytes   int64  `json:"bytes"`
	SHA256  string `json:"sha256"`
	Stories int    `json:"stories,omitempty"`
}

// CatalogBundle is one bundle product; it unlocks every pack (current and future) of the covered types.
type CatalogBundle struct {
	ID        string            `json:"id" yaml:"id"`
	ProductID string            `json:"product_id" yaml:"product_id"`
	PriceTier string            `json:"price_tier" yaml:"price_tier"`
	TitleI18n map[string]string `json:"title_i18n" yaml:"title_i18n"`
	Covers    Covers            `json:"covers" yaml:"covers"`
}

// Covers is a bundle's `covers`: {"types": [...]} or the string "all".
type Covers struct {
	All   bool
	Types []string
}

func (c Covers) MarshalJSON() ([]byte, error) {
	if c.All {
		return json.Marshal("all")
	}
	return json.Marshal(map[string][]string{"types": c.Types})
}

func (c *Covers) UnmarshalJSON(b []byte) error {
	var s string
	if json.Unmarshal(b, &s) == nil {
		if s != "all" {
			return fmt.Errorf(`covers: %q, want "all" or {"types": [...]}`, s)
		}
		*c = Covers{All: true}
		return nil
	}
	var m struct{ Types []string }
	if err := json.Unmarshal(b, &m); err != nil {
		return err
	}
	*c = Covers{Types: m.Types}
	return nil
}

func (c *Covers) UnmarshalYAML(n *yaml.Node) error {
	if n.Kind == yaml.ScalarNode {
		if n.Value != "all" {
			return fmt.Errorf(`covers: %q, want all or {types: [...]}`, n.Value)
		}
		*c = Covers{All: true}
		return nil
	}
	var m struct {
		Types []string `yaml:"types"`
	}
	if err := n.Decode(&m); err != nil {
		return err
	}
	*c = Covers{Types: m.Types}
	return nil
}

// CatalogStory lets the library and the store list a story before its pack is downloaded.
type CatalogStory struct {
	ID        string          `json:"id"`
	PackID    string          `json:"pack_id"`
	Type      string          `json:"type"`
	WorldID   string          `json:"world_id"`
	Title     string          `json:"title"`
	TitleI18n json.RawMessage `json:"title_i18n"`
	Cover     string          `json:"cover"`
	Episodes  int             `json:"episodes"`
	Audience  string          `json:"audience"`
}

// ReadCatalog loads catalog.json (schema 1 or 2, upgraded to 2 in memory); a missing file is an empty catalog
// (version 0).
func ReadCatalog(path string) (*Catalog, error) {
	c := &Catalog{Schema: CatalogSchema}
	raw, err := os.ReadFile(path)
	if err != nil && !errors.Is(err, os.ErrNotExist) {
		return nil, err
	}
	if err == nil {
		if err := json.Unmarshal(raw, c); err != nil {
			return nil, fmt.Errorf("%s: %w", path, err)
		}
	}
	switch c.Schema {
	case 1:
		c.upgrade1()
	case CatalogSchema:
	default:
		return nil, fmt.Errorf("%s: schema %d, this tool reads 1 and %d", path, c.Schema, CatalogSchema)
	}
	c.normalize()
	return c, nil
}

// upgrade1 moves a schema 1 catalog to 2: base_url → base_urls.pages, type from audience (type_from_audience).
// Part paths stay as they are (the app still resolves them against pages).
func (c *Catalog) upgrade1() {
	r := rule()
	c.Schema = CatalogSchema
	if c.BaseURL != "" {
		c.BaseURLs.Pages = c.BaseURL
	}
	c.BaseURL = ""
	for i := range c.Packs {
		if c.Packs[i].Type == "" {
			c.Packs[i].Type = r.TypeFromAudience[c.Packs[i].Audience]
		}
	}
	for i := range c.Stories {
		if c.Stories[i].Type == "" {
			c.Stories[i].Type = r.TypeFromAudience[c.Stories[i].Audience]
		}
	}
}

func (c *Catalog) normalize() {
	if c.Types == nil {
		c.Types = []CatalogType{}
	}
	if c.Packs == nil {
		c.Packs = []CatalogPack{}
	}
	if c.Bundles == nil {
		c.Bundles = []CatalogBundle{}
	}
	if c.Gamebooks == nil {
		c.Gamebooks = []json.RawMessage{}
	}
	if c.Stories == nil {
		c.Stories = []CatalogStory{}
	}
}

// Merge replaces the pack with p.ID (in place; appended when new) and its stories (removed, then
// appended), refreshes base_urls/types/bundles from the rules, bumps the catalog version and stamps
// generated_at; pagesURL (non-empty) overrides base_urls.pages.
func (c *Catalog) Merge(p CatalogPack, stories []CatalogStory, now time.Time, pagesURL string) {
	if i := slices.IndexFunc(c.Packs, func(x CatalogPack) bool { return x.ID == p.ID }); i >= 0 {
		c.Packs[i] = p
	} else {
		c.Packs = append(c.Packs, p)
	}
	c.Stories = slices.DeleteFunc(c.Stories, func(s CatalogStory) bool { return s.PackID == p.ID })
	c.Stories = append(c.Stories, stories...)
	c.ApplyRules(rule(), pagesURL)
	c.Touch(now)
}

// ApplyRules rewrites base_urls, types and bundles from rules/base/pack.yaml (`webtoon catalog-bundles`, and every
// export). types = the active ones plus any type a pack uses, in pack.yaml order. Gamebooks are left as they are.
// pagesURL (non-empty) overrides base_urls.pages.
func (c *Catalog) ApplyRules(r Rules, pagesURL string) {
	c.Schema = CatalogSchema
	c.BaseURL = ""
	c.BaseURLs = r.BaseURLs
	if pagesURL != "" {
		c.BaseURLs.Pages = pagesURL
	}
	used := map[string]bool{}
	for _, p := range c.Packs {
		used[p.Type] = true
	}
	c.Types = []CatalogType{}
	for _, t := range r.Types {
		if t.Active || used[t.ID] {
			c.Types = append(c.Types, CatalogType{ID: t.ID, TitleI18n: t.TitleI18n, Audience: t.Audience, Icon: t.Icon})
		}
	}
	c.Bundles = slices.Clone(r.Bundles)
	c.normalize()
}

// Touch bumps the version and stamps generated_at.
func (c *Catalog) Touch(now time.Time) {
	c.Version++
	c.GeneratedAt = now.UTC().Format(time.RFC3339)
}

// RefreshCatalog is `webtoon catalog-bundles`: catalog.json at path gets base_urls, types and bundles from
// pack.yaml and a new version. Needs no database.
func RefreshCatalog(path, pagesURL string, now time.Time) (*Catalog, error) {
	r, err := LoadRules()
	if err != nil {
		return nil, err
	}
	c, err := ReadCatalog(path)
	if err != nil {
		return nil, err
	}
	c.ApplyRules(r, pagesURL)
	c.Touch(now)
	return c, WriteCatalog(path, c)
}

// WriteCatalog writes catalog.json (indented: it lives in a git repo).
func WriteCatalog(path string, c *Catalog) error {
	b, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(b, '\n'), 0o644)
}

// audienceRank orders audiences; a pack mixing worlds is labelled with the most restrictive one.
var audienceRank = map[string]int{"kids": 0, "teen": 1, "adult": 2}

func packAudience(parts []Part) string {
	best := ""
	for _, p := range parts {
		for _, w := range p.Manifest.Worlds {
			if best == "" || audienceRank[w.Audience] > audienceRank[best] {
				best = w.Audience
			}
		}
	}
	return best
}

// packLanguages is the union of the story languages, in the order first seen.
func packLanguages(parts []Part) []string {
	out := []string{}
	for _, p := range parts {
		for _, s := range p.Manifest.Stories {
			for _, l := range s.Languages {
				if !slices.Contains(out, l) {
					out = append(out, l)
				}
			}
		}
	}
	return out
}
