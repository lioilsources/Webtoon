package api

import (
	"encoding/json"
	"net/http"
	"slices"
	"strconv"
	"strings"
	"time"
	"unicode/utf8"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/state"
	"github.com/ol1n/webtoon/backend/internal/store"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/worker"
)

const maxFreeText = 500

type campaignReq struct {
	WorldID           string `json:"world_id"`
	PlayerCharacterID string `json:"player_character_id"`
	Title             string `json:"title"`
	Start             *bool  `json:"start"` // default true: enqueue the first episode right away
}

func (s *Server) createCampaign(w http.ResponseWriter, r *http.Request) {
	var req campaignReq
	if err := decode(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	wrow, err := s.loadWorldRow(r, req.WorldID)
	if err != nil {
		s.fail(w, err)
		return
	}
	world, err := s.store.LoadWorld(r.Context(), nil, wrow.ID)
	if err != nil {
		s.fail(w, err)
		return
	}
	uid := userID(r)
	pc := req.PlayerCharacterID
	if pc == "" {
		for _, c := range world.Characters {
			if c.Role == "playable" {
				pc = c.ID
				break
			}
		}
	} else {
		c, ok := world.Character(pc)
		switch {
		case !ok:
			s.fail(w, errf(http.StatusBadRequest, "unknown player_character_id"))
			return
		case c.Role == "npc", c.Role == "player_created" && c.OwnerID != uid:
			s.fail(w, errf(http.StatusForbidden, "that character is not playable for you"))
			return
		}
	}
	var pcPtr *string
	if pc != "" {
		pcPtr = &pc
	}
	title := req.Title
	if title == "" {
		title = world.Title
	}
	start := req.Start == nil || *req.Start

	var camp dbq.Campaign
	var ep *dbq.Episode
	err = s.store.Tx(r.Context(), func(q *dbq.Queries) error {
		var err error
		camp, err = q.CreateCampaign(r.Context(), dbq.CreateCampaignParams{
			ID: store.NewID("cp_"), WorldID: world.ID, PlayerID: uid, Title: title, PlayerCharacterID: pcPtr,
			State: store.MustJSON(state.Empty(world)), CanonProgress: json.RawMessage("[]"),
		})
		if err != nil {
			return err
		}
		if start {
			e, err := s.enqueueEpisode(r, q, camp.ID, 1, storyboard.FirstPremise(world), nil)
			if err != nil {
				return err
			}
			ep = &e
		}
		return nil
	})
	if err != nil {
		s.fail(w, err)
		return
	}
	s.wake()
	resp := map[string]any{"campaign": s.campaignJSON(camp, nil)}
	if ep != nil {
		resp["first_episode_id"] = ep.ID
	}
	writeJSON(w, http.StatusCreated, resp)
}

func (s *Server) enqueueEpisode(r *http.Request, q *dbq.Queries, campaignID string, idx int, premise string, chosen *worker.Chosen) (dbq.Episode, error) {
	var chosenRaw json.RawMessage
	if chosen != nil {
		chosenRaw = store.MustJSON(chosen)
	}
	e, err := q.CreateEpisode(r.Context(), dbq.CreateEpisodeParams{
		ID: store.NewID("ep_"), CampaignID: campaignID, Idx: int32(idx), Premise: premise, Chosen: chosenRaw,
	})
	if err != nil {
		return e, err
	}
	_, err = s.store.Enqueue(r.Context(), q, worker.KindEpisode, worker.EpisodePayload{EpisodeID: e.ID}, s.cfg.MaxAttempts)
	return e, err
}

type episodeSummary struct {
	ID          string          `json:"id"`
	Index       int32           `json:"index"`
	Title       string          `json:"title"`
	TitleI18n   json.RawMessage `json:"title_i18n"`
	Status      string          `json:"status"`
	PanelsReady int32           `json:"panels_ready"`
	PanelsTotal int32           `json:"panels_total"`
	Chosen      json.RawMessage `json:"chosen"`
	CreatedAt   time.Time       `json:"created_at"`
}

func (s *Server) campaignJSON(c dbq.Campaign, eps []dbq.Episode) map[string]any {
	out := map[string]any{
		"id": c.ID, "world_id": c.WorldID, "player_id": c.PlayerID, "title": c.Title, "status": c.Status,
		"player_character_id": c.PlayerCharacterID, "state": c.State, "canon_progress": c.CanonProgress,
		"branch_parent_episode_id": c.BranchParentEpisodeID, "created_at": c.CreatedAt, "updated_at": c.UpdatedAt,
	}
	if eps != nil {
		list := make([]episodeSummary, 0, len(eps))
		for _, e := range eps {
			list = append(list, episodeSummary{e.ID, e.Idx, e.Title, rawOr(e.TitleI18n, "{}"), e.Status, e.PanelsReady, e.PanelsTotal,
				rawOr(e.Chosen, "null"), e.CreatedAt})
		}
		out["episodes"] = list
	}
	return out
}

// listCampaigns lists the caller's own campaigns (newest activity first), optionally for one world.
func (s *Server) listCampaigns(w http.ResponseWriter, r *http.Request) {
	rows, err := s.store.Q.ListPlayerCampaigns(r.Context(), userID(r))
	if err != nil {
		s.fail(w, err)
		return
	}
	world := r.URL.Query().Get("world_id")
	out := make([]map[string]any, 0, len(rows))
	for _, c := range rows {
		if world != "" && c.WorldID != world {
			continue
		}
		out = append(out, map[string]any{"id": c.ID, "world_id": c.WorldID, "world_title": c.WorldTitle,
			"title": c.Title, "status": c.Status, "player_character_id": c.PlayerCharacterID,
			"episodes": c.Episodes, "last_episode_status": c.LastStatus, "last_activity": c.LastActivity,
			"created_at": c.CreatedAt, "updated_at": c.UpdatedAt})
	}
	writeJSON(w, http.StatusOK, map[string]any{"campaigns": out})
}

// loadCampaign returns the campaign if the caller is its player or the world owner.
func (s *Server) loadCampaign(r *http.Request, id string) (dbq.Campaign, dbq.World, error) {
	c, err := s.store.Q.GetCampaign(r.Context(), id)
	if err != nil {
		return c, dbq.World{}, store.ErrNotFound
	}
	wrow, err := s.store.Q.GetWorld(r.Context(), c.WorldID)
	if err != nil {
		return c, wrow, store.ErrNotFound
	}
	uid := userID(r)
	if c.PlayerID != uid && wrow.OwnerID != uid {
		return c, wrow, store.ErrNotFound
	}
	return c, wrow, nil
}

func (s *Server) getCampaign(w http.ResponseWriter, r *http.Request) {
	c, _, err := s.loadCampaign(r, r.PathValue("id"))
	if err != nil {
		s.fail(w, err)
		return
	}
	eps, err := s.store.Q.ListEpisodes(r.Context(), c.ID)
	if err != nil {
		s.fail(w, err)
		return
	}
	writeJSON(w, http.StatusOK, s.campaignJSON(c, eps))
}

type episodeReq struct {
	ChoiceID string `json:"choice_id"`
	FreeText string `json:"free_text"`
}

// createEpisode continues the campaign from its last ready episode with a closed choice or free text.
// Free text is moderated by the worker before generation.
func (s *Server) createEpisode(w http.ResponseWriter, r *http.Request) {
	c, _, err := s.loadCampaign(r, r.PathValue("id"))
	if err != nil {
		s.fail(w, err)
		return
	}
	if c.PlayerID != userID(r) {
		s.fail(w, errf(http.StatusForbidden, "only the campaign's player can continue it"))
		return
	}
	var req episodeReq
	if r.ContentLength != 0 {
		if err := decode(r, &req); err != nil {
			s.fail(w, err)
			return
		}
	}
	req.FreeText = strings.TrimSpace(req.FreeText)
	if req.ChoiceID != "" && req.FreeText != "" {
		s.fail(w, errf(http.StatusBadRequest, "send either choice_id or free_text"))
		return
	}
	if utf8.RuneCountInString(req.FreeText) > maxFreeText {
		s.fail(w, errf(http.StatusBadRequest, "free_text longer than "+strconv.Itoa(maxFreeText)+" characters"))
		return
	}
	world, err := s.store.LoadWorld(r.Context(), nil, c.WorldID)
	if err != nil {
		s.fail(w, err)
		return
	}

	var ep dbq.Episode
	err = s.store.Tx(r.Context(), func(q *dbq.Queries) error {
		if _, err := q.GetCampaignForUpdate(r.Context(), c.ID); err != nil { // serialise concurrent posts
			return err
		}
		eps, err := q.ListEpisodes(r.Context(), c.ID)
		if err != nil {
			return err
		}
		var lastReady *dbq.Episode
		for i := range eps {
			switch eps[i].Status {
			case "queued", "generating":
				return errf(http.StatusConflict, "an episode is still being generated")
			case "ready":
				lastReady = &eps[i]
			}
		}
		next := len(eps) + 1
		if len(eps) > 0 {
			next = int(eps[len(eps)-1].Idx) + 1
		}
		if m := world.Permissions.MaxEpisodes; m > 0 && next > m {
			return errf(http.StatusConflict, "campaign reached max_episodes of this world")
		}
		if lastReady == nil {
			// First episode (or every earlier attempt failed): start from the world's canon/synopsis.
			ep, err = s.enqueueEpisode(r, q, c.ID, next, storyboard.FirstPremise(world), nil)
			return err
		}
		chosen, err := pickChoice(lastReady, req)
		if err != nil {
			return err
		}
		var prev domain.Storyboard
		_ = json.Unmarshal(lastReady.Storyboard, &prev)
		ep, err = s.enqueueEpisode(r, q, c.ID, next, storyboard.ContinuationPremise(&prev, chosen.Text), chosen)
		return err
	})
	if err != nil {
		s.fail(w, err)
		return
	}
	s.wake()
	writeJSON(w, http.StatusAccepted, map[string]any{"episode_id": ep.ID, "index": ep.Idx, "status": ep.Status})
}

func pickChoice(prev *dbq.Episode, req episodeReq) (*worker.Chosen, error) {
	var choices []domain.Choice
	_ = json.Unmarshal(prev.Choices, &choices)
	if req.FreeText != "" {
		if !slices.ContainsFunc(choices, func(c domain.Choice) bool { return c.Kind == "free" }) {
			return nil, errf(http.StatusBadRequest, "the previous episode does not offer a free choice")
		}
		return &worker.Chosen{ChoiceID: "free", Kind: "free", Text: req.FreeText}, nil
	}
	if req.ChoiceID == "" {
		return nil, errf(http.StatusBadRequest, "choice_id or free_text is required")
	}
	for _, c := range choices {
		if c.ID == req.ChoiceID {
			if c.Kind == "free" {
				return nil, errf(http.StatusBadRequest, "the free choice needs free_text")
			}
			return &worker.Chosen{ChoiceID: c.ID, Kind: c.Kind, Text: c.Text}, nil
		}
	}
	return nil, errf(http.StatusBadRequest, "unknown choice_id")
}
