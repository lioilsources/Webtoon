// Package episodejson is the reader-facing JSON shape of an episode: GET /episodes/{id} and the
// content packs (PACK_FORMAT.md) serialise through the same functions, so the two never drift.
package episodejson

import (
	"encoding/json"

	"github.com/ol1n/webtoon/backend/internal/comfy"
	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/store"
)

// Panel is one panel of GET /episodes/{id}.
type Panel struct {
	Index         int32           `json:"index"`
	Status        string          `json:"status"`
	ImageURL      string          `json:"image_url,omitempty"`
	Width         int32           `json:"width,omitempty"`
	Height        int32           `json:"height,omitempty"`
	Shot          string          `json:"shot"`
	LocationID    string          `json:"location_id"`
	GapAfter      string          `json:"gap_after"`
	Bubbles       json.RawMessage `json:"bubbles"`
	SFX           json.RawMessage `json:"sfx"`
	Characters    json.RawMessage `json:"characters"`
	Seed          int64           `json:"seed,omitempty"`
	IdentityScore *float32        `json:"identity_score,omitempty"`
	Error         string          `json:"error,omitempty"`
	// Motion panel (PLAN-motion-panels): the loop is served next to the still, never instead of it.
	Animate         bool   `json:"animate"`
	Motion          string `json:"motion,omitempty"`
	LoopSeconds     int32  `json:"loop_seconds,omitempty"`
	VideoStatus     string `json:"video_status,omitempty"`
	VideoURL        string `json:"video_url,omitempty"`
	VideoError      string `json:"video_error,omitempty"`
	EstimateSeconds int    `json:"estimate_seconds,omitempty"` // render-time hint for the editor
	// Faces: face boxes of the image, [[x0, y0, x1, y1]] normalized; the reader keeps bubbles off them.
	Faces json.RawMessage `json:"faces,omitempty"`
}

// MediaURL turns a path relative to MEDIA_DIR (panels.image_path / video_path) into the URL the
// client loads; the API prefixes MEDIA_BASE_URL, a pack maps it to a file inside the zip.
type MediaURL func(rel string) string

// PanelJSON serialises one panel row. image_url is set only for a ready panel, video_url only for a
// ready loop of an animated panel.
func PanelJSON(p dbq.Panel, mediaURL MediaURL) Panel {
	out := Panel{Index: p.Idx, Status: p.Status, Shot: p.Shot, LocationID: p.LocationID, GapAfter: p.GapAfter,
		Bubbles: RawOr(p.Bubbles, "[]"), SFX: RawOr(p.Sfx, "[]"), Characters: RawOr(p.Characters, "[]"),
		Seed: p.Seed, IdentityScore: p.IdentityScore, Error: p.Error}
	if f := RawOr(p.Faces, "[]"); string(f) != "[]" {
		out.Faces = f
	}
	if p.Status == "ready" && p.ImagePath != "" {
		out.ImageURL = mediaURL(p.ImagePath)
		out.Width, out.Height = p.Width, p.Height
	}
	if p.Animate {
		out.Animate, out.Motion, out.LoopSeconds, out.VideoStatus, out.VideoError = true, p.Motion, p.LoopSeconds, p.VideoStatus, p.VideoError
		out.EstimateSeconds = comfy.VideoEstimateSeconds(int(p.LoopSeconds))
		if p.VideoStatus == "ready" && p.VideoPath != "" {
			out.VideoURL = mediaURL(p.VideoPath)
		}
	}
	return out
}

// EpisodeJSON is the body of GET /episodes/{id}: the episode row, its panels (as []Panel under
// "panels") and the languages the whole episode is translated into. worldLanguage is the source
// language of the world ("" = cs).
func EpisodeJSON(e dbq.Episode, panels []dbq.Panel, worldLanguage string, mediaURL MediaURL) map[string]any {
	ps := make([]Panel, 0, len(panels))
	for _, p := range panels {
		ps = append(ps, PanelJSON(p, mediaURL))
	}
	// languages = translations complete for the whole episode; the reader offers only these.
	text := store.EpisodeTextFromRows(e, panels, &domain.World{Language: worldLanguage})
	langs := text.Languages()
	if langs == nil {
		langs = []string{}
	}
	return map[string]any{
		"id": e.ID, "campaign_id": e.CampaignID, "index": e.Idx, "title": e.Title, "status": e.Status,
		"title_i18n": RawOr(e.TitleI18n, "{}"), "source_language": text.Source, "languages": langs,
		"panels_ready": e.PanelsReady, "panels_total": e.PanelsTotal, "credits_cost": e.CreditsCost,
		"panels": ps, "choices": RawOr(e.Choices, "[]"), "chosen": RawOr(e.Chosen, "null"),
		"warnings": RawOr(e.Warnings, "[]"), "error": e.Error,
		"created_at": e.CreatedAt, "updated_at": e.UpdatedAt,
	}
}

// RawOr returns raw, or def when the column is empty.
func RawOr(raw json.RawMessage, def string) json.RawMessage {
	if len(raw) == 0 {
		return json.RawMessage(def)
	}
	return raw
}
