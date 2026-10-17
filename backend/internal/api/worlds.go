package api

import (
	"encoding/json"
	"errors"
	"net/http"
	"regexp"
	"slices"
	"time"

	"github.com/jackc/pgx/v5/pgconn"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/store"
)

var (
	audiences    = []string{"kids", "teen", "adult"}
	visibilities = []string{"private", "unlisted", "public"}
	roles        = []string{"npc", "playable", "player_created"}
	idLevels     = []string{"prompt", "ip_adapter", "lora"}
	idRE         = regexp.MustCompile(`^[a-z][a-z0-9_]{0,63}$`)
)

type worldResp struct {
	*domain.World
	Bible       json.RawMessage `json:"bible"`
	Canon       json.RawMessage `json:"canon"`
	Permissions json.RawMessage `json:"permissions"`
	CreatedAt   time.Time       `json:"created_at"`
	UpdatedAt   time.Time       `json:"updated_at"`
}

func (s *Server) worldResponse(r *http.Request, row dbq.World) (*worldResp, error) {
	w, err := s.store.LoadWorld(r.Context(), nil, row.ID)
	if err != nil {
		return nil, err
	}
	return &worldResp{World: w, Bible: row.Bible, Canon: row.Canon, Permissions: row.Permissions,
		CreatedAt: row.CreatedAt, UpdatedAt: row.UpdatedAt}, nil
}

type characterReq struct {
	ID              string   `json:"id"`
	Name            string   `json:"name"`
	Role            string   `json:"role"`
	CountTag        string   `json:"count_tag"`
	Description     string   `json:"description"`
	Personality     string   `json:"personality"`
	SpeechStyle     string   `json:"speech_style"`
	TagPrompt       string   `json:"tag_prompt"`
	ReferenceImages []string `json:"reference_images"`
	IdentityLevel   string   `json:"identity_level"`
	IdentityAsset   *string  `json:"identity_asset"`
}

type locationReq struct {
	ID              string   `json:"id"`
	Name            string   `json:"name"`
	Description     string   `json:"description"`
	TagPrompt       string   `json:"tag_prompt"`
	ReferenceImages []string `json:"reference_images"`
	Mood            string   `json:"mood"`
}

type worldReq struct {
	Title       *string         `json:"title"`
	Synopsis    *string         `json:"synopsis"`
	Tone        *string         `json:"tone"`
	Audience    *string         `json:"audience"`
	Language    *string         `json:"language"`
	StyleID     *string         `json:"style_id"`
	Visibility  *string         `json:"visibility"`
	Bible       json.RawMessage `json:"bible"`
	Canon       json.RawMessage `json:"canon"`
	Permissions json.RawMessage `json:"permissions"`
	Characters  []characterReq  `json:"characters"`
	Locations   []locationReq   `json:"locations"`
}

func (s *Server) validateWorldReq(r *http.Request, req *worldReq) error {
	if req.Audience != nil && !slices.Contains(audiences, *req.Audience) {
		return errf(http.StatusBadRequest, "audience must be kids|teen|adult")
	}
	if req.Visibility != nil && !slices.Contains(visibilities, *req.Visibility) {
		return errf(http.StatusBadRequest, "visibility must be private|unlisted|public")
	}
	if req.StyleID != nil {
		st, err := s.store.LoadStyles(r.Context(), nil)
		if err == nil {
			if _, ok := st.Presets[*req.StyleID]; !ok {
				return errf(http.StatusBadRequest, "unknown style_id")
			}
		}
	}
	if len(req.Bible) > 0 {
		var m map[string]any
		if json.Unmarshal(req.Bible, &m) != nil {
			return errf(http.StatusBadRequest, "bible must be an object")
		}
	}
	if len(req.Canon) > 0 {
		var c domain.Canon
		if json.Unmarshal(req.Canon, &c) != nil {
			return errf(http.StatusBadRequest, "canon must be {nodes: [{id, text}], constraints: [...]}")
		}
	}
	if len(req.Permissions) > 0 {
		var p domain.Permissions
		if json.Unmarshal(req.Permissions, &p) != nil {
			return errf(http.StatusBadRequest, "invalid permissions")
		}
	}
	return nil
}

func deref(p *string, def string) string {
	if p == nil || *p == "" {
		return def
	}
	return *p
}

func (s *Server) createWorld(w http.ResponseWriter, r *http.Request) {
	var req worldReq
	if err := decode(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	if deref(req.Title, "") == "" || deref(req.StyleID, "") == "" {
		s.fail(w, errf(http.StatusBadRequest, "title and style_id are required"))
		return
	}
	if err := s.validateWorldReq(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	uid := userID(r)
	var row dbq.World
	err := s.store.Tx(r.Context(), func(q *dbq.Queries) error {
		var err error
		row, err = q.CreateWorld(r.Context(), dbq.CreateWorldParams{
			ID: store.NewID("w_"), OwnerID: uid, Title: *req.Title, Synopsis: deref(req.Synopsis, ""),
			Tone: deref(req.Tone, ""), Audience: deref(req.Audience, "teen"), Language: deref(req.Language, "cs"),
			StyleID: *req.StyleID, Bible: rawOr(req.Bible, "{}"), Canon: rawOr(req.Canon, "{}"),
			Permissions: rawOr(req.Permissions, "{}"), Visibility: deref(req.Visibility, "private"),
		})
		if err != nil {
			return err
		}
		for _, c := range req.Characters {
			if _, err := insertCharacter(r, q, row.ID, uid, c, true); err != nil {
				return err
			}
		}
		for _, l := range req.Locations {
			if _, err := insertLocation(r, q, row.ID, l); err != nil {
				return err
			}
		}
		return nil
	})
	if err != nil {
		s.fail(w, err)
		return
	}
	resp, err := s.worldResponse(r, row)
	if err != nil {
		s.fail(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, resp)
}

func (s *Server) listWorlds(w http.ResponseWriter, r *http.Request) {
	var vis *string
	if v := r.URL.Query().Get("visibility"); v != "" {
		vis = &v
	}
	rows, err := s.store.Q.ListWorlds(r.Context(), dbq.ListWorldsParams{Viewer: userID(r), Visibility: vis})
	if err != nil {
		s.fail(w, err)
		return
	}
	out := make([]map[string]any, 0, len(rows))
	for _, row := range rows {
		out = append(out, map[string]any{"id": row.ID, "owner_id": row.OwnerID, "title": row.Title,
			"synopsis": row.Synopsis, "tone": row.Tone, "audience": row.Audience, "language": row.Language,
			"style_id": row.StyleID, "visibility": row.Visibility, "created_at": row.CreatedAt})
	}
	writeJSON(w, http.StatusOK, map[string]any{"worlds": out})
}

// loadWorldRow returns the world if the caller may see it (public/unlisted, or owner).
func (s *Server) loadWorldRow(r *http.Request, id string) (dbq.World, error) {
	row, err := s.store.Q.GetWorld(r.Context(), id)
	if err != nil {
		return row, store.ErrNotFound
	}
	if row.Visibility == "private" && row.OwnerID != userID(r) {
		return row, store.ErrNotFound
	}
	return row, nil
}

func (s *Server) getWorld(w http.ResponseWriter, r *http.Request) {
	row, err := s.loadWorldRow(r, r.PathValue("id"))
	if err != nil {
		s.fail(w, err)
		return
	}
	resp, err := s.worldResponse(r, row)
	if err != nil {
		s.fail(w, err)
		return
	}
	writeJSON(w, http.StatusOK, resp)
}

func (s *Server) patchWorld(w http.ResponseWriter, r *http.Request) {
	row, err := s.loadWorldRow(r, r.PathValue("id"))
	if err != nil {
		s.fail(w, err)
		return
	}
	if row.OwnerID != userID(r) {
		s.fail(w, errf(http.StatusForbidden, "only the world owner can edit it"))
		return
	}
	var req worldReq
	if err := decode(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	if req.Characters != nil || req.Locations != nil {
		s.fail(w, errf(http.StatusBadRequest, "use POST /worlds/{id}/characters|locations"))
		return
	}
	if err := s.validateWorldReq(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	row, err = s.store.Q.UpdateWorld(r.Context(), dbq.UpdateWorldParams{
		ID: row.ID, Title: req.Title, Synopsis: req.Synopsis, Tone: req.Tone, Audience: req.Audience,
		Language: req.Language, StyleID: req.StyleID, Visibility: req.Visibility,
		Bible: req.Bible, Canon: req.Canon, Permissions: req.Permissions,
	})
	if err != nil {
		s.fail(w, err)
		return
	}
	resp, err := s.worldResponse(r, row)
	if err != nil {
		s.fail(w, err)
		return
	}
	writeJSON(w, http.StatusOK, resp)
}

func conflict(err error, what string) error {
	var pe *pgconn.PgError
	if errors.As(err, &pe) && pe.Code == "23505" {
		return errf(http.StatusConflict, what+" id already exists in this world")
	}
	return err
}

func insertCharacter(r *http.Request, q *dbq.Queries, worldID, ownerID string, c characterReq, isOwner bool) (dbq.Character, error) {
	if c.Name == "" {
		return dbq.Character{}, errf(http.StatusBadRequest, "character name is required")
	}
	if c.ID == "" {
		c.ID = store.NewID("c_")
	} else if !idRE.MatchString(c.ID) {
		return dbq.Character{}, errf(http.StatusBadRequest, "character id must match "+idRE.String())
	}
	if c.Role == "" {
		c.Role = "npc"
	}
	if !isOwner {
		c.Role = "player_created"
	}
	if !slices.Contains(roles, c.Role) {
		return dbq.Character{}, errf(http.StatusBadRequest, "role must be npc|playable|player_created")
	}
	if c.IdentityLevel == "" {
		c.IdentityLevel = "prompt"
	}
	if !slices.Contains(idLevels, c.IdentityLevel) {
		return dbq.Character{}, errf(http.StatusBadRequest, "identity_level must be prompt|ip_adapter|lora")
	}
	if c.ReferenceImages == nil {
		c.ReferenceImages = []string{}
	}
	row, err := q.CreateCharacter(r.Context(), dbq.CreateCharacterParams{
		WorldID: worldID, ID: c.ID, OwnerID: ownerID, Name: c.Name, Role: c.Role, CountTag: c.CountTag,
		Description: c.Description, Personality: c.Personality, SpeechStyle: c.SpeechStyle, TagPrompt: c.TagPrompt,
		ReferenceImages: store.MustJSON(c.ReferenceImages), IdentityLevel: c.IdentityLevel, IdentityAsset: c.IdentityAsset,
	})
	return row, conflict(err, "character")
}

func insertLocation(r *http.Request, q *dbq.Queries, worldID string, l locationReq) (dbq.Location, error) {
	if l.Name == "" {
		return dbq.Location{}, errf(http.StatusBadRequest, "location name is required")
	}
	if l.ID == "" {
		l.ID = store.NewID("l_")
	} else if !idRE.MatchString(l.ID) {
		return dbq.Location{}, errf(http.StatusBadRequest, "location id must match "+idRE.String())
	}
	if l.ReferenceImages == nil {
		l.ReferenceImages = []string{}
	}
	row, err := q.CreateLocation(r.Context(), dbq.CreateLocationParams{
		WorldID: worldID, ID: l.ID, Name: l.Name, Description: l.Description, TagPrompt: l.TagPrompt,
		ReferenceImages: store.MustJSON(l.ReferenceImages), Mood: l.Mood,
	})
	return row, conflict(err, "location")
}

// createCharacter: the owner adds any character; other players only player_created ones,
// and only when permissions.can_create_character allows it.
func (s *Server) createCharacter(w http.ResponseWriter, r *http.Request) {
	row, err := s.loadWorldRow(r, r.PathValue("id"))
	if err != nil {
		s.fail(w, err)
		return
	}
	uid := userID(r)
	isOwner := row.OwnerID == uid
	if !isOwner {
		var p domain.Permissions
		_ = json.Unmarshal(row.Permissions, &p)
		if !p.CanCreateCharacter {
			s.fail(w, errf(http.StatusForbidden, "this world does not allow player-created characters"))
			return
		}
	}
	var req characterReq
	if err := decode(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	c, err := insertCharacter(r, s.store.Q, row.ID, uid, req, isOwner)
	if err != nil {
		s.fail(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, store.CharacterFromRow(c))
}

func (s *Server) createLocation(w http.ResponseWriter, r *http.Request) {
	row, err := s.loadWorldRow(r, r.PathValue("id"))
	if err != nil {
		s.fail(w, err)
		return
	}
	if row.OwnerID != userID(r) {
		s.fail(w, errf(http.StatusForbidden, "only the world owner can add locations"))
		return
	}
	var req locationReq
	if err := decode(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	l, err := insertLocation(r, s.store.Q, row.ID, req)
	if err != nil {
		s.fail(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, store.LocationFromRow(l))
}

// worldStats is the author dashboard: counts, where campaigns are, choice distribution.
func (s *Server) worldStats(w http.ResponseWriter, r *http.Request) {
	row, err := s.loadWorldRow(r, r.PathValue("id"))
	if err != nil {
		s.fail(w, err)
		return
	}
	if row.OwnerID != userID(r) {
		s.fail(w, errf(http.StatusForbidden, "only the world owner can see stats"))
		return
	}
	ctx := r.Context()
	counts, err := s.store.Q.WorldCounts(ctx, row.ID)
	if err != nil {
		s.fail(w, err)
		return
	}
	dist, err := s.store.Q.ChoiceDistribution(ctx, row.ID)
	if err != nil {
		s.fail(w, err)
		return
	}
	depths, err := s.store.Q.CampaignDepths(ctx, row.ID)
	if err != nil {
		s.fail(w, err)
		return
	}
	canon, err := s.store.Q.CanonReached(ctx, row.ID)
	if err != nil {
		s.fail(w, err)
		return
	}
	byKind := map[string]int{}
	byChoice := map[string]int{}
	for _, d := range dist {
		byKind[d.Kind] += int(d.N)
		if d.ChoiceID != "" {
			byChoice[d.ChoiceID] += int(d.N)
		}
	}
	depthOut := make([]map[string]int, 0, len(depths))
	for _, d := range depths {
		depthOut = append(depthOut, map[string]int{"episodes": int(d.Depth), "campaigns": int(d.Campaigns)})
	}
	canonOut := map[string]int{}
	for _, c := range canon {
		canonOut[c.NodeID] = int(c.Campaigns)
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"world_id":                  row.ID,
		"campaigns":                 counts.Campaigns,
		"players":                   counts.Players,
		"episodes":                  counts.Episodes,
		"episodes_ready":            counts.EpisodesReady,
		"episodes_failed":           counts.EpisodesFailed,
		"panels_ready":              counts.PanelsReady,
		"player_created_characters": counts.PlayerCreatedCharacters,
		"choices": map[string]any{
			"by_kind":   byKind,   // closed vs free
			"by_choice": byChoice, // c1/c2/c3/free — position of the picked option
		},
		"campaign_depth": depthOut, // how many episodes campaigns got to (where players stopped)
		"canon_reached":  canonOut,
	})
}
