package api

// M3 author (DM) tools: character / location library edits, LLM tag_prompt generation,
// character reference sheets, reference image upload, style preset list.

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"image"
	_ "image/jpeg" // DecodeConfig of uploaded references
	_ "image/png"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"slices"
	"sort"
	"strings"
	"time"

	"github.com/jackc/pgx/v5"

	"github.com/ol1n/webtoon/backend/internal/chargen"
	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/store"
	"github.com/ol1n/webtoon/backend/internal/tags"
	"github.com/ol1n/webtoon/backend/internal/upstream"
	"github.com/ol1n/webtoon/backend/internal/worker"
)

const (
	defaultMaxUpload = 8 << 20
	maxSheetSeeds    = 8
)

// normTagPrompt normalises an edited tag_prompt: booru spelling, no blanks, no duplicates.
func normTagPrompt(s string) string {
	return strings.Join(tags.Dedupe(tags.Split(s)), ", ")
}

// --- ownership -------------------------------------------------------------------

// ownedWorld loads the world and requires the caller to own it.
func (s *Server) ownedWorld(r *http.Request, msg string) (dbq.World, error) {
	row, err := s.loadWorldRow(r, r.PathValue("id"))
	if err != nil {
		return row, err
	}
	if row.OwnerID != userID(r) {
		return row, errf(http.StatusForbidden, msg)
	}
	return row, nil
}

// editableCharacter: the world owner edits any character; a player only their own
// player_created one.
func (s *Server) editableCharacter(r *http.Request) (dbq.World, dbq.Character, bool, error) {
	row, err := s.loadWorldRow(r, r.PathValue("id"))
	if err != nil {
		return row, dbq.Character{}, false, err
	}
	c, err := s.store.Q.GetCharacter(r.Context(), dbq.GetCharacterParams{WorldID: row.ID, ID: r.PathValue("cid")})
	if err != nil {
		return row, c, false, notFoundErr(err)
	}
	uid := userID(r)
	isOwner := row.OwnerID == uid
	if !isOwner && !(c.Role == "player_created" && c.OwnerID == uid) {
		return row, c, false, errf(http.StatusForbidden, "only the world owner can edit it")
	}
	return row, c, isOwner, nil
}

func (s *Server) ownedLocation(r *http.Request) (dbq.World, dbq.Location, error) {
	row, err := s.ownedWorld(r, "only the world owner can edit it")
	if err != nil {
		return row, dbq.Location{}, err
	}
	l, err := s.store.Q.GetLocation(r.Context(), dbq.GetLocationParams{WorldID: row.ID, ID: r.PathValue("lid")})
	return row, l, notFoundErr(err)
}

func notFoundErr(err error) error {
	if errors.Is(err, pgx.ErrNoRows) {
		return store.ErrNotFound
	}
	return err
}

// checkReferenceList: a PATCH may reorder or remove reference images, never add foreign paths.
func checkReferenceList(next []string, current json.RawMessage) error {
	var cur []string
	_ = json.Unmarshal(current, &cur)
	seen := map[string]bool{}
	for _, p := range next {
		if !slices.Contains(cur, p) {
			return errf(http.StatusBadRequest, "reference_images may only reorder or remove existing images (upload new ones)")
		}
		if seen[p] {
			return errf(http.StatusBadRequest, "duplicate reference image "+p)
		}
		seen[p] = true
	}
	return nil
}

// --- characters ----------------------------------------------------------------------

type characterPatch struct {
	Name            *string         `json:"name"`
	Role            *string         `json:"role"`
	CountTag        *string         `json:"count_tag"`
	Description     *string         `json:"description"`
	Personality     *string         `json:"personality"`
	SpeechStyle     *string         `json:"speech_style"`
	TagPrompt       *string         `json:"tag_prompt"`
	ReferenceImages *[]string       `json:"reference_images"`
	IdentityLevel   *string         `json:"identity_level"`
	IdentityAsset   json.RawMessage `json:"identity_asset"` // absent = keep, null = clear
	IPAdapter       json.RawMessage `json:"ip_adapter"`     // absent = keep, null = clear
}

func (s *Server) patchCharacter(w http.ResponseWriter, r *http.Request) {
	row, c, isOwner, err := s.editableCharacter(r)
	if err != nil {
		s.fail(w, err)
		return
	}
	var req characterPatch
	if err := decode(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	p := dbq.UpdateCharacterParams{WorldID: row.ID, ID: c.ID, Name: req.Name, CountTag: req.CountTag,
		Description: req.Description, Personality: req.Personality, SpeechStyle: req.SpeechStyle}
	if req.Name != nil && strings.TrimSpace(*req.Name) == "" {
		s.fail(w, errf(http.StatusBadRequest, "character name is required"))
		return
	}
	if req.Role != nil && *req.Role != c.Role {
		if !isOwner {
			s.fail(w, errf(http.StatusForbidden, "only the world owner can change roles"))
			return
		}
		if !slices.Contains(roles, *req.Role) {
			s.fail(w, errf(http.StatusBadRequest, "role must be npc|playable|player_created"))
			return
		}
		p.Role = req.Role
	}
	if req.CountTag != nil && !slices.Contains(countTagValues, *req.CountTag) {
		s.fail(w, errf(http.StatusBadRequest, "count_tag must be 1girl|1boy or empty"))
		return
	}
	if req.TagPrompt != nil {
		tp := normTagPrompt(*req.TagPrompt)
		p.TagPrompt = &tp
	}
	if req.ReferenceImages != nil {
		if err := checkReferenceList(*req.ReferenceImages, c.ReferenceImages); err != nil {
			s.fail(w, err)
			return
		}
		p.ReferenceImages = store.MustJSON(*req.ReferenceImages)
	}
	if req.IdentityLevel != nil {
		if !slices.Contains(idLevels, *req.IdentityLevel) {
			s.fail(w, errf(http.StatusBadRequest, "identity_level must be prompt|ip_adapter|lora"))
			return
		}
		p.IdentityLevel = req.IdentityLevel
	}
	if len(req.IdentityAsset) > 0 {
		p.SetIdentityAsset = true
		var a *string
		if json.Unmarshal(req.IdentityAsset, &a) != nil {
			s.fail(w, errf(http.StatusBadRequest, "identity_asset must be a string or null"))
			return
		}
		p.IdentityAsset = a
	}
	if len(req.IPAdapter) > 0 {
		p.SetIpAdapter = true
		var ip *domain.IPAdapterConfig
		if json.Unmarshal(req.IPAdapter, &ip) != nil {
			s.fail(w, errf(http.StatusBadRequest, "ip_adapter must be {preset, weight, end_at} or null"))
			return
		}
		if err := validateIPAdapter(ip); err != nil {
			s.fail(w, err)
			return
		}
		if ip != nil {
			p.IpAdapter = store.MustJSON(ip)
		}
	}
	out, err := s.store.Q.UpdateCharacter(r.Context(), p)
	if err != nil {
		s.fail(w, notFoundErr(err))
		return
	}
	writeJSON(w, http.StatusOK, s.characterJSON(store.CharacterFromRow(out)))
}

func (s *Server) deleteCharacter(w http.ResponseWriter, r *http.Request) {
	row, c, _, err := s.editableCharacter(r)
	if err != nil {
		s.fail(w, err)
		return
	}
	n, err := s.store.Q.CountPlayerCharacterCampaigns(r.Context(), dbq.CountPlayerCharacterCampaignsParams{
		WorldID: row.ID, PlayerCharacterID: &c.ID})
	if err != nil {
		s.fail(w, err)
		return
	}
	if n > 0 {
		s.fail(w, errf(http.StatusConflict, "character is the player character of a campaign"))
		return
	}
	if _, err := s.store.Q.DeleteCharacter(r.Context(), dbq.DeleteCharacterParams{WorldID: row.ID, ID: c.ID}); err != nil {
		s.fail(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// --- locations ---------------------------------------------------------------------

type locationPatch struct {
	Name            *string   `json:"name"`
	Description     *string   `json:"description"`
	TagPrompt       *string   `json:"tag_prompt"`
	ReferenceImages *[]string `json:"reference_images"`
	Mood            *string   `json:"mood"`
}

func (s *Server) patchLocation(w http.ResponseWriter, r *http.Request) {
	row, l, err := s.ownedLocation(r)
	if err != nil {
		s.fail(w, err)
		return
	}
	var req locationPatch
	if err := decode(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	if req.Name != nil && strings.TrimSpace(*req.Name) == "" {
		s.fail(w, errf(http.StatusBadRequest, "location name is required"))
		return
	}
	p := dbq.UpdateLocationParams{WorldID: row.ID, ID: l.ID, Name: req.Name, Description: req.Description, Mood: req.Mood}
	if req.TagPrompt != nil {
		tp := normTagPrompt(*req.TagPrompt)
		p.TagPrompt = &tp
	}
	if req.ReferenceImages != nil {
		if err := checkReferenceList(*req.ReferenceImages, l.ReferenceImages); err != nil {
			s.fail(w, err)
			return
		}
		p.ReferenceImages = store.MustJSON(*req.ReferenceImages)
	}
	out, err := s.store.Q.UpdateLocation(r.Context(), p)
	if err != nil {
		s.fail(w, notFoundErr(err))
		return
	}
	writeJSON(w, http.StatusOK, s.locationJSON(store.LocationFromRow(out)))
}

// deleteLocation also drops it from permissions.allowed_locations.
func (s *Server) deleteLocation(w http.ResponseWriter, r *http.Request) {
	row, l, err := s.ownedLocation(r)
	if err != nil {
		s.fail(w, err)
		return
	}
	err = s.store.Tx(r.Context(), func(q *dbq.Queries) error {
		if _, err := q.DeleteLocation(r.Context(), dbq.DeleteLocationParams{WorldID: row.ID, ID: l.ID}); err != nil {
			return err
		}
		var perms map[string]any
		if json.Unmarshal(row.Permissions, &perms) != nil || perms == nil {
			return nil
		}
		allowed, ok := perms["allowed_locations"].([]any)
		if !ok {
			return nil
		}
		kept := []any{}
		for _, a := range allowed {
			if a != l.ID {
				kept = append(kept, a)
			}
		}
		if len(kept) == len(allowed) {
			return nil
		}
		perms["allowed_locations"] = kept
		return q.SetWorldPermissions(r.Context(), dbq.SetWorldPermissionsParams{ID: row.ID, Permissions: store.MustJSON(perms)})
	})
	if err != nil {
		s.fail(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

// --- tag_prompt generation (m0/gen_character.py) ------------------------------------------

type tagPromptReq struct {
	Name        *string `json:"name"`
	Description *string `json:"description"`
}

func (s *Server) generateTags(w http.ResponseWriter, r *http.Request, system, name, description string) {
	var req tagPromptReq
	if err := decodeOptional(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	if req.Name != nil && *req.Name != "" {
		name = *req.Name
	}
	if req.Description != nil {
		description = *req.Description
	}
	if strings.TrimSpace(description) == "" {
		s.fail(w, errf(http.StatusBadRequest, "description is required to generate tags"))
		return
	}
	if s.cfg.LLM == nil || s.cfg.Vocab == nil {
		s.fail(w, errf(http.StatusServiceUnavailable, "llm unavailable: not configured"))
		return
	}
	res, err := chargen.Generate(r.Context(), s.cfg.LLM, s.cfg.Vocab, system, name, description)
	if err != nil {
		if upstream.IsUnavailable(err) {
			s.fail(w, errf(http.StatusServiceUnavailable, "llm unavailable: "+err.Error()))
			return
		}
		s.log.Error("tag generation", "err", err)
		s.fail(w, errf(http.StatusBadGateway, "tag generation failed: "+err.Error()))
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{
		"tags": res.Tags, "tag_prompt": res.TagPrompt(), "dropped": res.Dropped, "unknown": nonNil(res.Unknown),
		"replaced": res.Replaced, "notes": res.Notes,
	})
}

// decodeOptional is decode for bodies that may be empty.
func decodeOptional(r *http.Request, v any) error {
	if r.Body == nil || r.ContentLength == 0 {
		return nil
	}
	dec := json.NewDecoder(http.MaxBytesReader(nil, r.Body, 1<<20))
	if err := dec.Decode(v); err != nil && err != io.EOF {
		return errf(http.StatusBadRequest, "invalid JSON body: "+err.Error())
	}
	return nil
}

func nonNil(l []string) []string {
	if l == nil {
		return []string{}
	}
	return l
}

func (s *Server) characterTagPrompt(w http.ResponseWriter, r *http.Request) {
	_, c, _, err := s.editableCharacter(r)
	if err != nil {
		s.fail(w, err)
		return
	}
	s.generateTags(w, r, chargen.CharacterSystem, c.Name, c.Description)
}

func (s *Server) locationTagPrompt(w http.ResponseWriter, r *http.Request) {
	_, l, err := s.ownedLocation(r)
	if err != nil {
		s.fail(w, err)
		return
	}
	s.generateTags(w, r, chargen.LocationSystem, l.Name, l.Description)
}

// --- character sheets (m0/render.py --sheet) ----------------------------------------------

type sheetImageJSON struct {
	Seed     int64              `json:"seed"`
	ImageURL *string            `json:"image_url"`
	Path     string             `json:"path,omitempty"`
	Status   string             `json:"status"`
	Recall   float64            `json:"recall"`
	Missing  []string           `json:"missing"`
	Unsafe   map[string]float64 `json:"unsafe,omitempty"`
}

func (s *Server) sheetJSON(r dbq.CharacterSheet) map[string]any {
	sh := store.SheetFromRow(r)
	images := make([]sheetImageJSON, 0, len(sh.Images))
	for _, im := range sh.Images {
		j := sheetImageJSON{Seed: im.Seed, Path: im.Path, Status: im.Status, Recall: im.Recall, Missing: nonNil(im.Missing), Unsafe: im.Unsafe}
		if im.Path != "" {
			u := s.mediaURL(im.Path)
			j.ImageURL = &u
		}
		images = append(images, j)
	}
	out := map[string]any{
		"id": r.ID, "world_id": r.WorldID, "character_id": r.CharacterID, "status": r.Status, "error": r.Error,
		"seeds": r.Seeds, "done": len(images), "images": images, "best": nil, "best_image_url": nil,
		"prompt": r.Prompt, "negative": r.Negative, "created_at": r.CreatedAt, "updated_at": r.UpdatedAt,
	}
	if r.Best != nil && int(*r.Best) < len(images) {
		out["best"] = *r.Best
		out["best_image_url"] = images[*r.Best].ImageURL
	}
	return out
}

type sheetReq struct {
	Seeds int `json:"seeds"`
}

func (s *Server) createSheet(w http.ResponseWriter, r *http.Request) {
	row, c, _, err := s.editableCharacter(r)
	if err != nil {
		s.fail(w, err)
		return
	}
	var req sheetReq
	if err := decodeOptional(r, &req); err != nil {
		s.fail(w, err)
		return
	}
	if req.Seeds == 0 {
		req.Seeds = worker.DefaultSheetSeeds
	}
	if req.Seeds < 1 || req.Seeds > maxSheetSeeds {
		s.fail(w, errf(http.StatusBadRequest, fmt.Sprintf("seeds must be within 1..%d", maxSheetSeeds)))
		return
	}
	if strings.TrimSpace(c.TagPrompt) == "" {
		s.fail(w, errf(http.StatusBadRequest, "character has no tag_prompt"))
		return
	}
	var sheet dbq.CharacterSheet
	err = s.store.Tx(r.Context(), func(q *dbq.Queries) error {
		existing, err := q.ListSheets(r.Context(), dbq.ListSheetsParams{WorldID: row.ID, CharacterID: c.ID})
		if err != nil {
			return err
		}
		for _, e := range existing {
			if e.Status == "queued" || e.Status == "rendering" {
				return errf(http.StatusConflict, "a sheet is already being rendered")
			}
		}
		sheet, err = q.CreateSheet(r.Context(), dbq.CreateSheetParams{ID: store.NewID("sh_"), WorldID: row.ID,
			CharacterID: c.ID, RequestedBy: userID(r), Seeds: int32(req.Seeds)})
		if err != nil {
			return err
		}
		_, err = s.store.Enqueue(r.Context(), q, worker.KindSheet, worker.SheetPayload{SheetID: sheet.ID}, s.cfg.MaxAttempts)
		return err
	})
	if err != nil {
		s.fail(w, err)
		return
	}
	s.wake()
	writeJSON(w, http.StatusAccepted, s.sheetJSON(sheet))
}

func (s *Server) listSheets(w http.ResponseWriter, r *http.Request) {
	row, c, _, err := s.editableCharacter(r)
	if err != nil {
		s.fail(w, err)
		return
	}
	rows, err := s.store.Q.ListSheets(r.Context(), dbq.ListSheetsParams{WorldID: row.ID, CharacterID: c.ID})
	if err != nil {
		s.fail(w, err)
		return
	}
	out := make([]map[string]any, 0, len(rows))
	for _, sh := range rows {
		out = append(out, s.sheetJSON(sh))
	}
	writeJSON(w, http.StatusOK, map[string]any{"sheets": out})
}

// getSheet: the world owner or whoever requested the sheet.
func (s *Server) getSheet(w http.ResponseWriter, r *http.Request) {
	sh, err := s.store.Q.GetSheet(r.Context(), r.PathValue("sid"))
	if err != nil {
		s.fail(w, notFoundErr(err))
		return
	}
	wrow, err := s.store.Q.GetWorld(r.Context(), sh.WorldID)
	if err != nil || (wrow.OwnerID != userID(r) && sh.RequestedBy != userID(r)) {
		s.fail(w, store.ErrNotFound)
		return
	}
	writeJSON(w, http.StatusOK, s.sheetJSON(sh))
}

// --- reference image upload ---------------------------------------------------------------

// readUpload reads the multipart "file" field: PNG or JPEG, at most MaxUpload bytes.
// Returns the bytes and the extension to store it under.
func (s *Server) readUpload(w http.ResponseWriter, r *http.Request) ([]byte, string, error) {
	limit := s.cfg.MaxUpload
	tooLarge := errf(http.StatusRequestEntityTooLarge, fmt.Sprintf("file too large (max %d MiB)", limit>>20))
	r.Body = http.MaxBytesReader(w, r.Body, limit+1<<20) // + multipart overhead
	mr, err := r.MultipartReader()
	if err != nil {
		return nil, "", errf(http.StatusBadRequest, "expected multipart/form-data with a \"file\" field")
	}
	for {
		part, err := mr.NextPart()
		if err == io.EOF {
			return nil, "", errf(http.StatusBadRequest, "missing \"file\" field")
		}
		if err != nil {
			var mbe *http.MaxBytesError
			if errors.As(err, &mbe) {
				return nil, "", tooLarge
			}
			return nil, "", errf(http.StatusBadRequest, "invalid multipart body: "+err.Error())
		}
		if part.FormName() != "file" {
			continue
		}
		data, err := io.ReadAll(io.LimitReader(part, limit+1))
		if err != nil {
			var mbe *http.MaxBytesError
			if errors.As(err, &mbe) {
				return nil, "", tooLarge
			}
			return nil, "", errf(http.StatusBadRequest, "upload: "+err.Error())
		}
		if int64(len(data)) > limit {
			return nil, "", tooLarge
		}
		var ext string
		switch http.DetectContentType(data) {
		case "image/png":
			ext = ".png"
		case "image/jpeg":
			ext = ".jpg"
		default:
			return nil, "", errf(http.StatusBadRequest, "file must be a PNG or JPEG image")
		}
		if _, _, err := image.DecodeConfig(bytes.NewReader(data)); err != nil {
			return nil, "", errf(http.StatusBadRequest, "file must be a PNG or JPEG image")
		}
		return data, ext, nil
	}
}

func (s *Server) saveMedia(rel string, data []byte) error {
	path := filepath.Join(s.cfg.MediaDir, filepath.FromSlash(rel))
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

func refName(ext string) string {
	return fmt.Sprintf("ref_%s_%s%s", time.Now().UTC().Format("20060102T150405"), store.NewID(""), ext)
}

func (s *Server) uploadCharacterReference(w http.ResponseWriter, r *http.Request) {
	row, c, _, err := s.editableCharacter(r)
	if err != nil {
		s.fail(w, err)
		return
	}
	data, ext, err := s.readUpload(w, r)
	if err != nil {
		s.fail(w, err)
		return
	}
	rel := filepath.ToSlash(filepath.Join("characters", row.ID, c.ID, refName(ext)))
	if err := s.saveMedia(rel, data); err != nil {
		s.fail(w, err)
		return
	}
	if err := s.store.Q.AppendCharacterReference(r.Context(), dbq.AppendCharacterReferenceParams{WorldID: row.ID, ID: c.ID, Path: rel}); err != nil {
		s.fail(w, err)
		return
	}
	out, err := s.store.Q.GetCharacter(r.Context(), dbq.GetCharacterParams{WorldID: row.ID, ID: c.ID})
	if err != nil {
		s.fail(w, notFoundErr(err))
		return
	}
	writeJSON(w, http.StatusCreated, s.characterJSON(store.CharacterFromRow(out)))
}

func (s *Server) uploadLocationReference(w http.ResponseWriter, r *http.Request) {
	row, l, err := s.ownedLocation(r)
	if err != nil {
		s.fail(w, err)
		return
	}
	data, ext, err := s.readUpload(w, r)
	if err != nil {
		s.fail(w, err)
		return
	}
	rel := filepath.ToSlash(filepath.Join("locations", row.ID, l.ID, refName(ext)))
	if err := s.saveMedia(rel, data); err != nil {
		s.fail(w, err)
		return
	}
	if err := s.store.Q.AppendLocationReference(r.Context(), dbq.AppendLocationReferenceParams{WorldID: row.ID, ID: l.ID, Path: rel}); err != nil {
		s.fail(w, err)
		return
	}
	out, err := s.store.Q.GetLocation(r.Context(), dbq.GetLocationParams{WorldID: row.ID, ID: l.ID})
	if err != nil {
		s.fail(w, notFoundErr(err))
		return
	}
	writeJSON(w, http.StatusCreated, s.locationJSON(store.LocationFromRow(out)))
}

// --- style presets ---------------------------------------------------------------------------

// listStylePresets is the style picker: presets with their tags and an optional preview image
// (MEDIA_DIR/styles/<id>.png|.jpg).
func (s *Server) listStylePresets(w http.ResponseWriter, r *http.Request) {
	st, err := s.store.LoadStyles(r.Context(), nil)
	if err != nil {
		s.fail(w, err)
		return
	}
	ids := make([]string, 0, len(st.Presets))
	for id := range st.Presets {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	out := make([]map[string]any, 0, len(ids))
	for _, id := range ids {
		p := st.Presets[id]
		var preview *string
		for _, ext := range []string{".png", ".jpg", ".webp"} {
			rel := "styles/" + id + ext
			if fi, err := os.Stat(filepath.Join(s.cfg.MediaDir, filepath.FromSlash(rel))); err == nil && !fi.IsDir() {
				u := s.mediaURL(rel)
				preview = &u
				break
			}
		}
		out = append(out, map[string]any{
			"id": id, "checkpoint": p.Checkpoint, "prediction": p.Prediction,
			"artist_tags": nonNil(p.ArtistTags), "aesthetic_tags": nonNil(p.AestheticTags),
			"sampler": p.Sampler, "scheduler": p.Scheduler, "steps": p.Steps, "cfg": p.CFG, "preview_url": preview,
		})
	}
	writeJSON(w, http.StatusOK, map[string]any{"presets": out})
}
