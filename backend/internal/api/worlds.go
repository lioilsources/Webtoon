package api

import (
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"regexp"
	"slices"
	"strings"
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
	Characters  []characterResp `json:"characters"`
	Locations   []locationResp  `json:"locations"`
	CreatedAt   time.Time       `json:"created_at"`
	UpdatedAt   time.Time       `json:"updated_at"`
}

// characterResp adds the media URLs of the reference images (reference_images are MEDIA_DIR paths).
type characterResp struct {
	domain.Character
	ReferenceURLs []string `json:"reference_urls"`
}

type locationResp struct {
	domain.Location
	ReferenceURLs []string `json:"reference_urls"`
}

func (s *Server) mediaURLs(paths []string) []string {
	out := make([]string, 0, len(paths))
	for _, p := range paths {
		out = append(out, s.mediaURL(p))
	}
	return out
}

func (s *Server) characterJSON(c domain.Character) characterResp {
	return characterResp{Character: c, ReferenceURLs: s.mediaURLs(c.ReferenceImages)}
}

func (s *Server) locationJSON(l domain.Location) locationResp {
	return locationResp{Location: l, ReferenceURLs: s.mediaURLs(l.ReferenceImages)}
}

func (s *Server) worldResponse(r *http.Request, row dbq.World) (*worldResp, error) {
	w, err := s.store.LoadWorld(r.Context(), nil, row.ID)
	if err != nil {
		return nil, err
	}
	resp := &worldResp{World: w, Bible: row.Bible, Canon: row.Canon, Permissions: row.Permissions,
		Characters: make([]characterResp, 0, len(w.Characters)), Locations: make([]locationResp, 0, len(w.Locations)),
		CreatedAt: row.CreatedAt, UpdatedAt: row.UpdatedAt}
	for _, c := range w.Characters {
		resp.Characters = append(resp.Characters, s.characterJSON(c))
	}
	for _, l := range w.Locations {
		resp.Locations = append(resp.Locations, s.locationJSON(l))
	}
	return resp, nil
}

type characterReq struct {
	ID              string                  `json:"id"`
	Name            string                  `json:"name"`
	Role            string                  `json:"role"`
	CountTag        string                  `json:"count_tag"`
	Description     string                  `json:"description"`
	Personality     string                  `json:"personality"`
	SpeechStyle     string                  `json:"speech_style"`
	TagPrompt       string                  `json:"tag_prompt"`
	ReferenceImages []string                `json:"reference_images"`
	IdentityLevel   string                  `json:"identity_level"`
	IdentityAsset   *string                 `json:"identity_asset"`
	IPAdapter       *domain.IPAdapterConfig `json:"ip_adapter"`
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

// validateWorldReq checks the fields and normalises canon (trimmed texts, ids for new nodes).
// locIDs are the world's location ids (for permissions.allowed_locations).
func (s *Server) validateWorldReq(r *http.Request, req *worldReq, locIDs []string) error {
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
		canon, err := normalizeCanon(req.Canon)
		if err != nil {
			return err
		}
		req.Canon = canon
	}
	if len(req.Permissions) > 0 {
		var p domain.Permissions
		if json.Unmarshal(req.Permissions, &p) != nil {
			return errf(http.StatusBadRequest, "invalid permissions")
		}
		for _, l := range p.AllowedLocations {
			if !slices.Contains(locIDs, l) {
				return errf(http.StatusBadRequest, "permissions.allowed_locations: unknown location "+l)
			}
		}
		if p.MaxEpisodes < 0 {
			return errf(http.StatusBadRequest, "permissions.max_episodes must be >= 0")
		}
	}
	return nil
}

// normalizeCanon validates the canon editor's ordered node list and constraints. Nodes keep
// their ids (campaign canon_progress refers to them); new nodes without an id get n1, n2, ….
// Other keys of the canon object are kept.
func normalizeCanon(raw json.RawMessage) (json.RawMessage, error) {
	bad := errf(http.StatusBadRequest, "canon must be {nodes: [{id, text}], constraints: [...]}")
	var doc map[string]json.RawMessage
	if json.Unmarshal(raw, &doc) != nil || doc == nil {
		return nil, bad
	}
	var c domain.Canon
	if json.Unmarshal(raw, &c) != nil {
		return nil, bad
	}
	seen := map[string]bool{}
	for _, n := range c.Nodes {
		if n.ID != "" {
			if seen[n.ID] {
				return nil, errf(http.StatusBadRequest, "duplicate canon node id "+n.ID)
			}
			seen[n.ID] = true
		}
	}
	nodes := make([]domain.CanonNode, 0, len(c.Nodes))
	next := 1
	for _, n := range c.Nodes {
		n.Text = strings.TrimSpace(n.Text)
		if n.Text == "" {
			return nil, errf(http.StatusBadRequest, "canon node text is required")
		}
		if n.ID == "" {
			for seen[fmt.Sprintf("n%d", next)] {
				next++
			}
			n.ID = fmt.Sprintf("n%d", next)
			seen[n.ID] = true
		} else if len(n.ID) > 64 {
			return nil, errf(http.StatusBadRequest, "canon node id too long")
		}
		nodes = append(nodes, n)
	}
	constraints := make([]any, 0, len(c.Constraints))
	for _, x := range c.Constraints {
		switch v := x.(type) {
		case string:
			if v = strings.TrimSpace(v); v != "" {
				constraints = append(constraints, v)
			}
		case nil:
		default:
			constraints = append(constraints, v)
		}
	}
	doc["nodes"] = store.MustJSON(nodes)
	doc["constraints"] = store.MustJSON(constraints)
	return store.MustJSON(doc), nil
}

var countTagValues = []string{"", "1girl", "1boy"}

// validateIPAdapter checks the optional IP-Adapter settings (zero = default).
func validateIPAdapter(ip *domain.IPAdapterConfig) error {
	if ip == nil {
		return nil
	}
	if ip.Preset != "" && !slices.Contains(domain.IPAdapterPresets, ip.Preset) {
		return errf(http.StatusBadRequest, "ip_adapter.preset must be one of: "+strings.Join(domain.IPAdapterPresets, ", "))
	}
	if ip.Weight < 0 || ip.Weight > 2 {
		return errf(http.StatusBadRequest, "ip_adapter.weight must be within 0..2")
	}
	if ip.EndAt < 0 || ip.EndAt > 1 {
		return errf(http.StatusBadRequest, "ip_adapter.end_at must be within 0..1")
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
	var locIDs []string
	for _, l := range req.Locations {
		locIDs = append(locIDs, l.ID)
	}
	if err := s.validateWorldReq(r, &req, locIDs); err != nil {
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
	onlyOwn := r.URL.Query().Get("owner") == "me"
	if onlyOwn && userID(r) == "" {
		s.fail(w, errf(http.StatusUnauthorized, "missing X-User-ID"))
		return
	}
	rows, err := s.store.Q.ListWorlds(r.Context(), dbq.ListWorldsParams{Viewer: userID(r), Visibility: vis, OnlyOwn: onlyOwn})
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
	locs, err := s.store.Q.ListLocations(r.Context(), row.ID)
	if err != nil {
		s.fail(w, err)
		return
	}
	var locIDs []string
	for _, l := range locs {
		locIDs = append(locIDs, l.ID)
	}
	if err := s.validateWorldReq(r, &req, locIDs); err != nil {
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
	if !slices.Contains(countTagValues, c.CountTag) {
		return dbq.Character{}, errf(http.StatusBadRequest, "count_tag must be 1girl|1boy or empty")
	}
	if err := validateIPAdapter(c.IPAdapter); err != nil {
		return dbq.Character{}, err
	}
	var ip json.RawMessage
	if c.IPAdapter != nil {
		ip = store.MustJSON(c.IPAdapter)
	}
	if c.ReferenceImages == nil {
		c.ReferenceImages = []string{}
	}
	row, err := q.CreateCharacter(r.Context(), dbq.CreateCharacterParams{
		WorldID: worldID, ID: c.ID, OwnerID: ownerID, Name: c.Name, Role: c.Role, CountTag: c.CountTag,
		Description: c.Description, Personality: c.Personality, SpeechStyle: c.SpeechStyle, TagPrompt: normTagPrompt(c.TagPrompt),
		ReferenceImages: store.MustJSON(c.ReferenceImages), IdentityLevel: c.IdentityLevel, IdentityAsset: c.IdentityAsset,
		IpAdapter: ip,
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
		WorldID: worldID, ID: l.ID, Name: l.Name, Description: l.Description, TagPrompt: normTagPrompt(l.TagPrompt),
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
	writeJSON(w, http.StatusCreated, s.characterJSON(store.CharacterFromRow(c)))
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
	writeJSON(w, http.StatusCreated, s.locationJSON(store.LocationFromRow(l)))
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
	stopped, err := s.store.Q.StoppedAt(ctx, row.ID)
	if err != nil {
		s.fail(w, err)
		return
	}
	stoppedOut := make([]map[string]int, 0, len(stopped))
	for _, st := range stopped {
		stoppedOut = append(stoppedOut, map[string]int{"episode": int(st.Episode), "campaigns": int(st.Campaigns)})
	}
	perEp, err := s.store.Q.ChoicesByEpisode(ctx, row.ID)
	if err != nil {
		s.fail(w, err)
		return
	}
	type epChoices struct {
		Episode int            `json:"episode"`
		Total   int            `json:"total"`
		Choices map[string]int `json:"choices"`
	}
	perEpOut := []*epChoices{}
	for _, c := range perEp {
		if len(perEpOut) == 0 || perEpOut[len(perEpOut)-1].Episode != int(c.Episode) {
			perEpOut = append(perEpOut, &epChoices{Episode: int(c.Episode), Choices: map[string]int{}})
		}
		cur := perEpOut[len(perEpOut)-1]
		cur.Choices[c.ChoiceID] += int(c.N)
		cur.Total += int(c.N)
	}
	pcs, err := s.store.Q.PlayerCreatedCharacters(ctx, row.ID)
	if err != nil {
		s.fail(w, err)
		return
	}
	pcOut := make([]map[string]any, 0, len(pcs))
	for _, c := range pcs {
		pcOut = append(pcOut, map[string]any{"id": c.ID, "name": c.Name, "owner_id": c.OwnerID,
			"description": c.Description, "created_at": c.CreatedAt})
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
		"campaign_depth":     depthOut,   // how many episodes campaigns got to
		"canon_reached":      canonOut,   // canon node id → campaigns that reached it
		"stopped_at":         stoppedOut, // last episode index per campaign (0 = no episode yet)
		"choices_by_episode": perEpOut,   // choice made at the end of episode i (c1/c2/c3/free)
		"player_created":     pcOut,
	})
}
