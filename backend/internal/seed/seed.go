// Package seed imports a world JSON (data/world_m0.json format) and styles.json into the database.
// Idempotent: rows are upserted by id.
package seed

import (
	"context"
	"encoding/json"
	"fmt"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/store"
)

// Styles stores the shared prompt pieces in settings('styles') and one row per preset.
func Styles(ctx context.Context, s *store.Store, raw []byte) (int, error) {
	var doc map[string]json.RawMessage
	if err := json.Unmarshal(raw, &doc); err != nil {
		return 0, fmt.Errorf("styles.json: %w", err)
	}
	var presets map[string]json.RawMessage
	if err := json.Unmarshal(doc["presets"], &presets); err != nil {
		return 0, fmt.Errorf("styles.json presets: %w", err)
	}
	common := map[string]json.RawMessage{}
	for k, v := range doc {
		if k != "presets" && k != "_note" {
			common[k] = v
		}
	}
	// Validate the shape before storing it.
	var check domain.Styles
	if err := json.Unmarshal(store.MustJSON(common), &check); err != nil {
		return 0, fmt.Errorf("styles.json: %w", err)
	}
	err := s.Tx(ctx, func(q *dbq.Queries) error {
		if err := q.UpsertSetting(ctx, dbq.UpsertSettingParams{Key: "styles", Value: store.MustJSON(common)}); err != nil {
			return err
		}
		for id, p := range presets {
			var pr domain.Preset
			if err := json.Unmarshal(p, &pr); err != nil {
				return fmt.Errorf("preset %s: %w", id, err)
			}
			if err := q.UpsertStylePreset(ctx, dbq.UpsertStylePresetParams{ID: id, Data: p}); err != nil {
				return err
			}
		}
		return nil
	})
	return len(presets), err
}

type worldFile struct {
	domain.World
	Bible       json.RawMessage `json:"bible"`
	Canon       json.RawMessage `json:"canon"`
	Permissions json.RawMessage `json:"permissions"`
}

// World upserts the world with its characters and locations. ownerID overrides the file's owner.
func World(ctx context.Context, s *store.Store, raw []byte, ownerID, visibility string) (*domain.World, error) {
	var wf worldFile
	if err := json.Unmarshal(raw, &wf); err != nil {
		return nil, fmt.Errorf("world json: %w", err)
	}
	w := &wf.World
	if w.ID == "" || w.Title == "" || w.StyleID == "" {
		return nil, fmt.Errorf("world json needs id, title, style_id")
	}
	if ownerID == "" {
		ownerID = w.OwnerID
	}
	if ownerID == "" {
		ownerID = "seed"
	}
	if visibility == "" {
		visibility = w.Visibility
	}
	if visibility == "" {
		visibility = "public"
	}
	def := func(s, d string) string {
		if s == "" {
			return d
		}
		return s
	}
	jsonOr := func(r json.RawMessage, d string) json.RawMessage {
		if len(r) == 0 {
			return json.RawMessage(d)
		}
		return r
	}
	err := s.Tx(ctx, func(q *dbq.Queries) error {
		if err := q.UpsertWorld(ctx, dbq.UpsertWorldParams{
			ID: w.ID, OwnerID: ownerID, Title: w.Title, Synopsis: w.Synopsis, Tone: w.Tone,
			Audience: def(w.Audience, "teen"), Language: def(w.Language, "cs"), StyleID: w.StyleID,
			Bible: jsonOr(wf.Bible, "{}"), Canon: jsonOr(wf.Canon, "{}"), Permissions: jsonOr(wf.Permissions, "{}"),
			Visibility: visibility,
		}); err != nil {
			return err
		}
		for i, c := range w.Characters {
			var asset *string
			if c.IdentityAsset != "" {
				asset = &c.IdentityAsset
			}
			refs := c.ReferenceImages
			if refs == nil {
				refs = []string{}
			}
			var ip json.RawMessage
			if c.IPAdapter != nil {
				ip = store.MustJSON(c.IPAdapter)
			}
			if err := q.UpsertCharacter(ctx, dbq.UpsertCharacterParams{
				WorldID: w.ID, ID: c.ID, OwnerID: ownerID, Name: c.Name, Role: def(c.Role, "npc"),
				CountTag: c.CountTag, Description: c.Description, Personality: c.Personality,
				SpeechStyle: c.SpeechStyle, TagPrompt: c.TagPrompt, ReferenceImages: store.MustJSON(refs),
				IdentityLevel: def(c.IdentityLevel, "prompt"), IdentityAsset: asset, IpAdapter: ip, Position: int32(i),
			}); err != nil {
				return fmt.Errorf("character %s: %w", c.ID, err)
			}
		}
		for i, l := range w.Locations {
			refs := l.ReferenceImages
			if refs == nil {
				refs = []string{}
			}
			if err := q.UpsertLocation(ctx, dbq.UpsertLocationParams{
				WorldID: w.ID, ID: l.ID, Name: l.Name, Description: l.Description, TagPrompt: l.TagPrompt,
				ReferenceImages: store.MustJSON(refs), Mood: l.Mood, Position: int32(i),
			}); err != nil {
				return fmt.Errorf("location %s: %w", l.ID, err)
			}
		}
		return nil
	})
	if err != nil {
		return nil, err
	}
	return w, nil
}
