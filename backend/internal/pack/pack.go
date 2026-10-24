// Package pack builds offline content packs (PACK_FORMAT.md) from Postgres + MEDIA_DIR:
// a zip with pack.json, WebP panels/loops and story covers, plus the catalog.json of the
// webtoon-content repo. `webtoon export-pack` is the CLI around Run.
package pack

import (
	"encoding/json"
	"regexp"
	"time"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
)

// Part size, WebP quality, cover size, the forbidden world prefix and the dropped episode fields are rules:
// rules/base/pack.yaml (rules.go).
// Schema is the pack.json schema (catalog.json has its own, CatalogSchema). Base URLs, naming, types and bundles
// of the catalog are in rules/base/pack.yaml too.
const Schema = 1

var packIDRe = regexp.MustCompile(`^[a-z0-9-]+$`)

// Options of one export.
type Options struct {
	ID        string // pack id, [a-z0-9-]
	Title     string
	Version   int    // ≥ 1; part of the zip file name (files are never overwritten in webtoon-content)
	ProductID string // store product of a paid pack (catalog mode)
	Free      bool   // free pack: no product (catalog mode)
	BaseURL   string // catalog base_urls.pages override; default rules base_urls.pages
	MediaDir  string // MEDIA_DIR of the backend (PNG panels, WebP loops)

	// Type is the pack type (rules types); default: the selected worlds' type (WorldType). N is the pack number
	// of the type: with it the id, product and release tag come from rules naming (unless given).
	Type       string
	N          int
	ReleaseTag string // GitHub release of the zips; default from rules naming

	OutDir  string // catalog mode: writes releases/<tag>/<asset>, covers/, catalog.json under it
	Starter string // starter mode: writes this one zip (no parts, no catalog)

	Workers int       // cwebp processes in flight; default runtime.NumCPU()
	Force   bool      // overwrite an existing zip (the format says: new version = new name)
	Now     time.Time // generated_at and zip entry times; default time.Now()
}

// Story is one campaign with the episodes it contributes (Filter keeps the ready prefix only).
type Story struct {
	Campaign dbq.Campaign
	World    dbq.World
	Episodes []Episode
	Type     string // pack type of the story (pick, -type or WorldType); "" when unknown
}

// Episode is one episode row with its panels in idx order.
type Episode struct {
	Row    dbq.Episode
	Panels []dbq.Panel
}

// Manifest is pack.json.
type Manifest struct {
	Schema      int              `json:"schema"`
	ID          string           `json:"id"`
	Title       string           `json:"title"`
	Version     int              `json:"version"`
	Part        string           `json:"part,omitempty"`
	GeneratedAt string           `json:"generated_at"`
	Worlds      []WorldJSON      `json:"worlds"`
	Stories     []StoryJSON      `json:"stories"`
	Episodes    []map[string]any `json:"episodes"`
}

// WorldJSON is a world as the reader needs it (no bible, no canon, no permissions).
type WorldJSON struct {
	ID       string `json:"id"`
	Title    string `json:"title"`
	Synopsis string `json:"synopsis"`
	Tone     string `json:"tone"`
	Audience string `json:"audience"`
	Language string `json:"language"`
	StyleID  string `json:"style_id"`
	Type     string `json:"type,omitempty"`
}

// StoryJSON is one story (= campaign) of pack.json.
type StoryJSON struct {
	ID        string          `json:"id"`
	WorldID   string          `json:"world_id"`
	Title     string          `json:"title"`
	TitleI18n json.RawMessage `json:"title_i18n"`
	Episodes  []string        `json:"episodes"`
	Cover     string          `json:"cover"`
	Languages []string        `json:"languages"`
	Type      string          `json:"type,omitempty"`
}

// Summary is what Run reports.
type Summary struct {
	Parts []PartSummary
	Notes []string // stories dropped or cut short, in selection order
	// Catalog mode only.
	CatalogPath    string
	CatalogVersion int
	ReleaseTag     string
	GhCommand      string // `gh release create …` uploading the zips (printed, never run)
}

// PartSummary describes one written zip.
type PartSummary struct {
	Part     string // "" when the pack has a single zip
	Path     string
	Stories  int
	Episodes int
	Panels   int
	Loops    int
	Bytes    int64
	SHA256   string
}
