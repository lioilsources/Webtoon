package pack

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"slices"
	"time"
)

// Catalog is catalog.json at the root of webtoon-content.
type Catalog struct {
	Schema      int            `json:"schema"`
	Version     int            `json:"version"`
	GeneratedAt string         `json:"generated_at"`
	BaseURL     string         `json:"base_url"`
	Packs       []CatalogPack  `json:"packs"`
	Stories     []CatalogStory `json:"stories"`
}

// CatalogPack is one downloadable pack.
type CatalogPack struct {
	ID        string        `json:"id"`
	Title     string        `json:"title"`
	Stories   int           `json:"stories"`
	Parts     []CatalogPart `json:"parts"`
	Free      bool          `json:"free"`
	ProductID string        `json:"product_id,omitempty"`
	Languages []string      `json:"languages"`
	Audience  string        `json:"audience"`
	Version   int           `json:"version"`
}

// CatalogPart is one zip of a pack.
type CatalogPart struct {
	Path   string `json:"path"`
	Bytes  int64  `json:"bytes"`
	SHA256 string `json:"sha256"`
}

// CatalogStory lets the library list and search a story before its pack is downloaded.
type CatalogStory struct {
	ID        string          `json:"id"`
	PackID    string          `json:"pack_id"`
	WorldID   string          `json:"world_id"`
	Title     string          `json:"title"`
	TitleI18n json.RawMessage `json:"title_i18n"`
	Cover     string          `json:"cover"`
	Episodes  int             `json:"episodes"`
	Audience  string          `json:"audience"`
}

// ReadCatalog loads catalog.json; a missing file is an empty catalog (version 0).
func ReadCatalog(path string) (*Catalog, error) {
	c := &Catalog{Schema: Schema, Packs: []CatalogPack{}, Stories: []CatalogStory{}}
	raw, err := os.ReadFile(path)
	if errors.Is(err, os.ErrNotExist) {
		return c, nil
	}
	if err != nil {
		return nil, err
	}
	if err := json.Unmarshal(raw, c); err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	if c.Schema != Schema {
		return nil, fmt.Errorf("%s: schema %d, this tool writes %d", path, c.Schema, Schema)
	}
	if c.Packs == nil {
		c.Packs = []CatalogPack{}
	}
	if c.Stories == nil {
		c.Stories = []CatalogStory{}
	}
	return c, nil
}

// Merge replaces the pack with p.ID (in place; appended when new) and its stories (removed, then
// appended), bumps the catalog version and stamps generated_at / base_url.
func (c *Catalog) Merge(p CatalogPack, stories []CatalogStory, now time.Time, baseURL string) {
	if i := slices.IndexFunc(c.Packs, func(x CatalogPack) bool { return x.ID == p.ID }); i >= 0 {
		c.Packs[i] = p
	} else {
		c.Packs = append(c.Packs, p)
	}
	c.Stories = slices.DeleteFunc(c.Stories, func(s CatalogStory) bool { return s.PackID == p.ID })
	c.Stories = append(c.Stories, stories...)
	c.Schema = Schema
	c.Version++
	c.GeneratedAt = now.UTC().Format(time.RFC3339)
	if baseURL != "" {
		c.BaseURL = baseURL
	}
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
