// Package demo imports a finished M0 run (storyboard JSON + rendered panel PNGs) as a ready
// episode, so the reader client can be tried without calling the LLM or ComfyUI.
package demo

import (
	"context"
	"encoding/json"
	"fmt"
	"image/png"
	"os"
	"path/filepath"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/state"
	"github.com/ol1n/webtoon/backend/internal/store"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/worker"
)

type Options struct {
	Storyboard []byte // storyboard JSON (§5.2), e.g. out/dev/storyboard_ep1.json
	PanelDir   string // directory with pNN_s<Variant>.png (+ optional meta.json from m0/render.py)
	Variant    int
	MediaDir   string // MEDIA_DIR of the API; images are copied to episodes/<ep>/pNN_<seed>.png

	// Either append to an existing campaign, or create a new one in WorldID for PlayerID.
	CampaignID        string
	WorldID           string
	PlayerID          string
	PlayerCharacterID string // default: first playable character
	Title             string // campaign title, default: world title
}

type Result struct {
	CampaignID string
	EpisodeID  string
	Index      int
	Panels     int
}

// PanelImage is one rendered panel found in the M0 output directory.
type PanelImage struct {
	Path             string
	Width, Height    int
	Seed             int64
	Prompt, Negative string
	Rating           map[string]float64
}

type metaFile struct {
	Images []struct {
		Panel    int                `json:"panel"`
		Variant  int                `json:"variant"`
		Seed     int64              `json:"seed"`
		Positive string             `json:"positive"`
		Negative string             `json:"negative"`
		Rating   map[string]float64 `json:"rating"`
	} `json:"images"`
}

// FindPanels locates pNN_s<variant>.png for each of n panels and reads their size (and, when
// meta.json is present, seed/prompt/rating). Every panel must have an image.
func FindPanels(dir string, n, variant int) ([]PanelImage, error) {
	var meta metaFile
	if raw, err := os.ReadFile(filepath.Join(dir, "meta.json")); err == nil {
		_ = json.Unmarshal(raw, &meta)
	}
	out := make([]PanelImage, n)
	for i := range n {
		p := filepath.Join(dir, fmt.Sprintf("p%02d_s%d.png", i, variant))
		f, err := os.Open(p)
		if err != nil {
			return nil, fmt.Errorf("panel %d: %w", i, err)
		}
		cfg, err := png.DecodeConfig(f)
		f.Close()
		if err != nil {
			return nil, fmt.Errorf("panel %d: %s is not a PNG: %w", i, p, err)
		}
		pi := PanelImage{Path: p, Width: cfg.Width, Height: cfg.Height, Seed: int64(1000 + i*100), Rating: map[string]float64{}}
		for _, m := range meta.Images {
			if m.Panel == i && m.Variant == variant {
				pi.Seed, pi.Prompt, pi.Negative = m.Seed, m.Positive, m.Negative
				if m.Rating != nil {
					pi.Rating = m.Rating
				}
			}
		}
		out[i] = pi
	}
	return out, nil
}

func copyFile(src, dst string) error {
	b, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	return os.WriteFile(dst, b, 0o644)
}

// Import inserts the storyboard as a ready episode with ready panels and applies its state_diff
// to the campaign, exactly as the worker would after rendering. No jobs are enqueued.
func Import(ctx context.Context, s *store.Store, o Options) (*Result, error) {
	sb := &domain.Storyboard{}
	if err := json.Unmarshal(o.Storyboard, sb); err != nil {
		return nil, fmt.Errorf("storyboard: %w", err)
	}
	if len(sb.Panels) == 0 {
		return nil, fmt.Errorf("storyboard has no panels")
	}
	// Translations made before rendering (webtoon translate -storyboard): bubbles[].i18n and
	// choices[].i18n travel in the domain types, the title's sit next to it.
	var extra struct {
		TitleI18n map[string]string `json:"title_i18n"`
	}
	_ = json.Unmarshal(o.Storyboard, &extra)
	worker.AssignChoiceIDs(sb.Choices)
	images, err := FindPanels(o.PanelDir, len(sb.Panels), o.Variant)
	if err != nil {
		return nil, err
	}

	res := &Result{Panels: len(sb.Panels)}
	var mediaDir string
	err = s.Tx(ctx, func(q *dbq.Queries) error {
		var camp dbq.Campaign
		var world *domain.World
		next := 1
		if o.CampaignID != "" {
			c, err := q.GetCampaignForUpdate(ctx, o.CampaignID)
			if err != nil {
				return fmt.Errorf("campaign %s: %w", o.CampaignID, store.ErrNotFound)
			}
			camp = c
			if world, err = s.LoadWorld(ctx, q, c.WorldID); err != nil {
				return err
			}
			eps, err := q.ListEpisodes(ctx, c.ID)
			if err != nil {
				return err
			}
			for _, e := range eps {
				if e.Status == "queued" || e.Status == "generating" {
					return fmt.Errorf("campaign %s has episode %s still %s", c.ID, e.ID, e.Status)
				}
				next = int(e.Idx) + 1
			}
		} else {
			if o.PlayerID == "" {
				return fmt.Errorf("player id is required for a new campaign")
			}
			var err error
			if world, err = s.LoadWorld(ctx, q, o.WorldID); err != nil {
				return fmt.Errorf("world %q: %w", o.WorldID, err)
			}
			pc := o.PlayerCharacterID
			if pc == "" {
				for _, c := range world.Characters {
					if c.Role == "playable" {
						pc = c.ID
						break
					}
				}
			} else if _, ok := world.Character(pc); !ok {
				return fmt.Errorf("unknown character %q", pc)
			}
			var pcPtr *string
			if pc != "" {
				pcPtr = &pc
			}
			title := o.Title
			if title == "" {
				title = world.Title
			}
			camp, err = q.CreateCampaign(ctx, dbq.CreateCampaignParams{
				ID: store.NewID("cp_"), WorldID: world.ID, PlayerID: o.PlayerID, Title: title, PlayerCharacterID: pcPtr,
				State: store.MustJSON(state.Empty(world)), CanonProgress: json.RawMessage("[]"),
			})
			if err != nil {
				return err
			}
		}

		premise := storyboard.FirstPremise(world)
		if next > 1 {
			premise = "(imported demo episode)"
		}
		e, err := q.CreateEpisode(ctx, dbq.CreateEpisodeParams{
			ID: store.NewID("ep_"), CampaignID: camp.ID, Idx: int32(next), Premise: premise,
		})
		if err != nil {
			return err
		}
		warnings := sb.Warnings
		if warnings == nil {
			warnings = []string{}
		}
		if err := q.SaveStoryboard(ctx, dbq.SaveStoryboardParams{
			ID: e.ID, Title: sb.Title, Storyboard: store.MustJSON(sb), Choices: store.MustJSON(sb.Choices),
			StateDiff: store.MustJSON(sb.StateDiffMap()), Warnings: store.MustJSON(warnings),
			PanelsTotal: int32(len(sb.Panels)), CreditsCost: int32(len(sb.Panels)),
		}); err != nil {
			return err
		}
		if len(extra.TitleI18n) > 0 {
			if err := q.SetEpisodeI18n(ctx, dbq.SetEpisodeI18nParams{
				ID: e.ID, TitleI18n: store.MustJSON(extra.TitleI18n), Choices: store.MustJSON(sb.Choices),
			}); err != nil {
				return err
			}
		}
		mediaDir = filepath.Join(o.MediaDir, "episodes", e.ID)
		for i, p := range sb.Panels {
			if err := q.InsertPanel(ctx, dbq.InsertPanelParams{
				EpisodeID: e.ID, Idx: int32(i), Shot: p.Shot, LocationID: p.LocationID, GapAfter: p.GapAfter,
				Bubbles: store.MustJSON(nonNil(p.Bubbles)), Sfx: store.MustJSON(nonNil(p.SFX)),
				Characters: store.MustJSON(nonNil(p.Characters)), VisualTags: store.MustJSON(nonNil(p.VisualTags)),
				Animate: p.Animate, Motion: p.Motion, LoopSeconds: int32(storyboard.LoopSecondsOr(p.LoopSeconds)),
				VideoStatus: map[bool]string{true: "pending"}[p.Animate],
			}); err != nil {
				return err
			}
			img := images[i]
			rel := filepath.ToSlash(filepath.Join("episodes", e.ID, fmt.Sprintf("p%02d_%d.png", i, img.Seed)))
			if err := copyFile(img.Path, filepath.Join(o.MediaDir, filepath.FromSlash(rel))); err != nil {
				return err
			}
			if err := q.SavePanelResult(ctx, dbq.SavePanelResultParams{
				EpisodeID: e.ID, Idx: int32(i), Status: "ready", ImagePath: rel, Prompt: img.Prompt, Negative: img.Negative,
				Seed: img.Seed, Width: int32(img.Width), Height: int32(img.Height), Rating: store.MustJSON(img.Rating),
				Attempts: json.RawMessage("[]"),
			}); err != nil {
				return err
			}
		}
		if _, err := q.RefreshPanelsReady(ctx, e.ID); err != nil {
			return err
		}
		cur := store.CampaignFromRow(camp, world)
		st := state.ApplyDiff(cur.State, sb.StateDiffMap(), next)
		canon := state.MergeCanon(world, cur.CanonProgress, sb.CanonNodesReached.Strings())
		if err := q.UpdateCampaignState(ctx, dbq.UpdateCampaignStateParams{
			ID: camp.ID, State: store.MustJSON(st), CanonProgress: store.MustJSON(canon),
		}); err != nil {
			return err
		}
		if err := q.FinishEpisode(ctx, dbq.FinishEpisodeParams{ID: e.ID, Status: "ready", StateSnapshot: store.MustJSON(st)}); err != nil {
			return err
		}
		res.CampaignID, res.EpisodeID, res.Index = camp.ID, e.ID, next
		return nil
	})
	if err != nil {
		if mediaDir != "" {
			_ = os.RemoveAll(mediaDir)
		}
		return nil, err
	}
	return res, nil
}

func nonNil[T any](v []T) []T {
	if v == nil {
		return []T{}
	}
	return v
}
