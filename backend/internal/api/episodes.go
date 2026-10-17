package api

import (
	"encoding/json"
	"net/http"
	"slices"
	"strconv"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/store"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/worker"
)

type panelJSON struct {
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
}

func (s *Server) panelJSON(p dbq.Panel) panelJSON {
	out := panelJSON{Index: p.Idx, Status: p.Status, Shot: p.Shot, LocationID: p.LocationID, GapAfter: p.GapAfter,
		Bubbles: rawOr(p.Bubbles, "[]"), SFX: rawOr(p.Sfx, "[]"), Characters: rawOr(p.Characters, "[]"),
		Seed: p.Seed, IdentityScore: p.IdentityScore, Error: p.Error}
	if p.Status == "ready" && p.ImagePath != "" {
		out.ImageURL = s.mediaURL(p.ImagePath)
		out.Width, out.Height = p.Width, p.Height
	}
	return out
}

// loadEpisode returns the episode if the caller is the campaign's player or the world owner.
func (s *Server) loadEpisode(r *http.Request, id string) (dbq.Episode, dbq.Campaign, dbq.World, error) {
	e, err := s.store.Q.GetEpisode(r.Context(), id)
	if err != nil {
		return e, dbq.Campaign{}, dbq.World{}, store.ErrNotFound
	}
	c, wrow, err := s.loadCampaign(r, e.CampaignID)
	return e, c, wrow, err
}

func (s *Server) getEpisode(w http.ResponseWriter, r *http.Request) {
	e, _, _, err := s.loadEpisode(r, r.PathValue("id"))
	if err != nil {
		s.fail(w, err)
		return
	}
	panels, err := s.store.Q.ListPanels(r.Context(), e.ID)
	if err != nil {
		s.fail(w, err)
		return
	}
	ps := make([]panelJSON, 0, len(panels))
	for _, p := range panels {
		ps = append(ps, s.panelJSON(p))
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"id": e.ID, "campaign_id": e.CampaignID, "index": e.Idx, "title": e.Title, "status": e.Status,
		"panels_ready": e.PanelsReady, "panels_total": e.PanelsTotal, "credits_cost": e.CreditsCost,
		"panels": ps, "choices": rawOr(e.Choices, "[]"), "chosen": rawOr(e.Chosen, "null"),
		"warnings": rawOr(e.Warnings, "[]"), "error": e.Error,
		"created_at": e.CreatedAt, "updated_at": e.UpdatedAt,
	})
}

type panelPatch struct {
	Bubbles    []domain.Bubble `json:"bubbles"`
	Regenerate bool            `json:"regenerate"`
}

// patchPanel edits bubble text (no image regeneration needed: bubbles are an overlay)
// or enqueues a re-render of the panel with a new seed.
func (s *Server) patchPanel(w http.ResponseWriter, r *http.Request) {
	e, c, _, err := s.loadEpisode(r, r.PathValue("id"))
	if err != nil {
		s.fail(w, err)
		return
	}
	if c.PlayerID != userID(r) {
		s.fail(w, errf(http.StatusForbidden, "only the campaign's player can edit panels"))
		return
	}
	n, err := strconv.Atoi(r.PathValue("n"))
	if err != nil {
		s.fail(w, errf(http.StatusBadRequest, "panel index must be a number"))
		return
	}
	var req panelPatch
	if err := decode(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	if req.Bubbles == nil && !req.Regenerate {
		s.fail(w, errf(http.StatusBadRequest, `send {"bubbles": [...]} or {"regenerate": true}`))
		return
	}
	ctx := r.Context()
	world, err := s.store.LoadWorld(ctx, nil, c.WorldID)
	if err != nil {
		s.fail(w, err)
		return
	}
	err = s.store.Tx(ctx, func(q *dbq.Queries) error {
		p, err := q.GetPanel(ctx, dbq.GetPanelParams{EpisodeID: e.ID, Idx: int32(n)})
		if err != nil {
			return store.ErrNotFound
		}
		if req.Bubbles != nil {
			for i, b := range req.Bubbles {
				if !slices.Contains(storyboard.BubbleKinds, b.Kind) {
					return errf(http.StatusBadRequest, "bubble "+strconv.Itoa(i)+": kind must be speech|thought|shout|narration")
				}
				if b.Kind != "narration" {
					if b.SpeakerID == nil {
						return errf(http.StatusBadRequest, "bubble "+strconv.Itoa(i)+": speaker_id required")
					}
					if _, ok := world.Character(*b.SpeakerID); !ok {
						return errf(http.StatusBadRequest, "bubble "+strconv.Itoa(i)+": unknown speaker_id")
					}
				}
			}
			if err := q.UpdatePanelBubbles(ctx, dbq.UpdatePanelBubblesParams{
				EpisodeID: e.ID, Idx: int32(n), Bubbles: store.MustJSON(req.Bubbles)}); err != nil {
				return err
			}
		}
		if req.Regenerate {
			if p.Status == "pending" || p.Status == "rendering" {
				return errf(http.StatusConflict, "panel is already being rendered")
			}
			if err := q.SetPanelStatus(ctx, dbq.SetPanelStatusParams{EpisodeID: e.ID, Idx: int32(n), Status: "pending"}); err != nil {
				return err
			}
			if _, err := s.store.Enqueue(ctx, q, worker.KindPanel,
				worker.PanelPayload{EpisodeID: e.ID, Panel: n, Regenerate: true}, s.cfg.MaxAttempts); err != nil {
				return err
			}
			if _, err := q.RefreshPanelsReady(ctx, e.ID); err != nil {
				return err
			}
		}
		return nil
	})
	if err != nil {
		s.fail(w, err)
		return
	}
	if req.Regenerate {
		s.wake()
	}
	p, err := s.store.Q.GetPanel(ctx, dbq.GetPanelParams{EpisodeID: e.ID, Idx: int32(n)})
	if err != nil {
		s.fail(w, err)
		return
	}
	code := http.StatusOK
	if req.Regenerate {
		code = http.StatusAccepted
	}
	writeJSON(w, code, s.panelJSON(p))
}
