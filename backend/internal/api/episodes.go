package api

import (
	"encoding/json"
	"net/http"
	"slices"
	"strconv"
	"strings"

	"github.com/ol1n/webtoon/backend/internal/comfy"
	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/store"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/translate"
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
	// Motion panel (PLAN-motion-panels): the loop is served next to the still, never instead of it.
	Animate         bool   `json:"animate"`
	Motion          string `json:"motion,omitempty"`
	LoopSeconds     int32  `json:"loop_seconds,omitempty"`
	VideoStatus     string `json:"video_status,omitempty"`
	VideoURL        string `json:"video_url,omitempty"`
	VideoError      string `json:"video_error,omitempty"`
	EstimateSeconds int    `json:"estimate_seconds,omitempty"` // render-time hint for the editor
}

func (s *Server) panelJSON(p dbq.Panel) panelJSON {
	out := panelJSON{Index: p.Idx, Status: p.Status, Shot: p.Shot, LocationID: p.LocationID, GapAfter: p.GapAfter,
		Bubbles: rawOr(p.Bubbles, "[]"), SFX: rawOr(p.Sfx, "[]"), Characters: rawOr(p.Characters, "[]"),
		Seed: p.Seed, IdentityScore: p.IdentityScore, Error: p.Error}
	if p.Status == "ready" && p.ImagePath != "" {
		out.ImageURL = s.mediaURL(p.ImagePath)
		out.Width, out.Height = p.Width, p.Height
	}
	if p.Animate {
		out.Animate, out.Motion, out.LoopSeconds, out.VideoStatus, out.VideoError = true, p.Motion, p.LoopSeconds, p.VideoStatus, p.VideoError
		out.EstimateSeconds = comfy.VideoEstimateSeconds(int(p.LoopSeconds))
		if p.VideoStatus == "ready" && p.VideoPath != "" {
			out.VideoURL = s.mediaURL(p.VideoPath)
		}
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
	e, _, wrow, err := s.loadEpisode(r, r.PathValue("id"))
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
	// languages = translations complete for the whole episode; the reader offers only these.
	text := store.EpisodeTextFromRows(e, panels, &domain.World{Language: wrow.Language})
	langs := text.Languages()
	if langs == nil {
		langs = []string{}
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"id": e.ID, "campaign_id": e.CampaignID, "index": e.Idx, "title": e.Title, "status": e.Status,
		"title_i18n": rawOr(e.TitleI18n, "{}"), "source_language": text.Source, "languages": langs,
		"panels_ready": e.PanelsReady, "panels_total": e.PanelsTotal, "credits_cost": e.CreditsCost,
		"panels": ps, "choices": rawOr(e.Choices, "[]"), "chosen": rawOr(e.Chosen, "null"),
		"warnings": rawOr(e.Warnings, "[]"), "error": e.Error,
		"created_at": e.CreatedAt, "updated_at": e.UpdatedAt,
	})
}

type panelPatch struct {
	Bubbles    []domain.Bubble `json:"bubbles"`
	Regenerate bool            `json:"regenerate"`
	// Motion panel ("Rozhýbat"): any of these enqueues a loop render; animate=false makes it static.
	Animate     *bool   `json:"animate"`
	Motion      *string `json:"motion"`
	LoopSeconds *int    `json:"loop_seconds"`
	ReseedVideo bool    `json:"reseed_video"` // "Znovu": same prompt, new seed
}

func (r panelPatch) touchesMotion() bool {
	return r.Animate != nil || r.Motion != nil || r.LoopSeconds != nil || r.ReseedVideo
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
	if req.Bubbles == nil && !req.Regenerate && !req.touchesMotion() {
		s.fail(w, errf(http.StatusBadRequest, `send {"bubbles": [...]}, {"regenerate": true} or {"animate": true, "motion": "...", "loop_seconds": 2}`))
		return
	}
	ctx := r.Context()
	world, err := s.store.LoadWorld(ctx, nil, c.WorldID)
	if err != nil {
		s.fail(w, err)
		return
	}
	retranslate, videoJob := false, false
	err = s.store.Tx(ctx, func(q *dbq.Queries) error {
		p, err := q.GetPanelForUpdate(ctx, dbq.GetPanelForUpdateParams{EpisodeID: e.ID, Idx: int32(n)})
		if err != nil {
			return store.ErrNotFound
		}
		if req.touchesMotion() {
			animate := p.Animate
			if req.Animate != nil {
				animate = *req.Animate
			}
			motion, loop := p.Motion, int(p.LoopSeconds)
			if req.Motion != nil {
				motion = strings.TrimSpace(*req.Motion)
			}
			if req.LoopSeconds != nil {
				if *req.LoopSeconds < 1 || *req.LoopSeconds > 3 {
					return errf(http.StatusBadRequest, "loop_seconds must be 1, 2 or 3")
				}
				loop = *req.LoopSeconds
			}
			loop = storyboard.LoopSecondsOr(loop)
			if animate {
				if err := storyboard.CheckMotion(motion); err != nil {
					return errf(http.StatusBadRequest, err.Error())
				}
				if !p.Animate {
					if cnt, err := q.CountAnimatedPanels(ctx, e.ID); err != nil {
						return err
					} else if int(cnt) >= storyboard.MaxAnimatedPanels {
						return errf(http.StatusConflict, "at most "+strconv.Itoa(storyboard.MaxAnimatedPanels)+" animated panels per episode")
					}
				}
			}
			changed := animate != p.Animate || motion != p.Motion || loop != int(p.LoopSeconds) || req.ReseedVideo
			if changed {
				status := ""
				if animate {
					if p.VideoStatus == "rendering" {
						return errf(http.StatusConflict, "the loop is being rendered")
					}
					status = "pending"
				}
				if err := q.SetPanelMotion(ctx, dbq.SetPanelMotionParams{EpisodeID: e.ID, Idx: int32(n),
					Animate: animate, Motion: motion, LoopSeconds: int32(loop), VideoStatus: status}); err != nil {
					return err
				}
				// The loop needs the still; before it exists the panel job enqueues the loop itself.
				if animate && p.Status == "ready" {
					if _, err := s.store.Enqueue(ctx, q, worker.KindPanelVideo,
						worker.PanelVideoPayload{EpisodeID: e.ID, Panel: n, Reseed: req.ReseedVideo}, s.cfg.MaxAttempts); err != nil {
						return err
					}
					videoJob = true
				}
			}
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
			// The editor changes originals only: unchanged texts keep their translations,
			// changed ones lose them and the episode is queued for translation again.
			old := []domain.Bubble{}
			_ = json.Unmarshal(p.Bubbles, &old)
			retranslate = translate.KeepI18n(old, req.Bubbles) && len(s.cfg.Langs) > 0 && e.Status == "ready"
			if err := q.UpdatePanelBubbles(ctx, dbq.UpdatePanelBubblesParams{
				EpisodeID: e.ID, Idx: int32(n), Bubbles: store.MustJSON(req.Bubbles)}); err != nil {
				return err
			}
			if retranslate {
				if _, err := s.store.Enqueue(ctx, q, worker.KindTranslate,
					worker.TranslatePayload{EpisodeID: e.ID}, s.cfg.MaxAttempts); err != nil {
					return err
				}
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
	if req.Regenerate || retranslate || videoJob {
		s.wake()
	}
	p, err := s.store.Q.GetPanel(ctx, dbq.GetPanelParams{EpisodeID: e.ID, Idx: int32(n)})
	if err != nil {
		s.fail(w, err)
		return
	}
	code := http.StatusOK
	if req.Regenerate || videoJob {
		code = http.StatusAccepted
	}
	writeJSON(w, code, s.panelJSON(p))
}
