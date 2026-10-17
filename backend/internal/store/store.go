// Package store is the Postgres persistence (pgx + sqlc). It implements worker.Store.
package store

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/state"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/worker"
)

var ErrNotFound = errors.New("not found")

type Store struct {
	Pool *pgxpool.Pool
	Q    *dbq.Queries
}

func New(pool *pgxpool.Pool) *Store { return &Store{Pool: pool, Q: dbq.New(pool)} }

var _ worker.Store = (*Store)(nil)

// NewID returns prefix + 12 random hex chars.
func NewID(prefix string) string {
	var b [6]byte
	_, _ = rand.Read(b[:])
	return prefix + hex.EncodeToString(b[:])
}

// Tx runs fn in a transaction.
func (s *Store) Tx(ctx context.Context, fn func(q *dbq.Queries) error) error {
	return pgx.BeginFunc(ctx, s.Pool, func(tx pgx.Tx) error { return fn(s.Q.WithTx(tx)) })
}

func notFound(err error) error {
	if errors.Is(err, pgx.ErrNoRows) {
		return ErrNotFound
	}
	return err
}

// MustJSON marshals v (nil → JSON null is avoided by callers).
func MustJSON(v any) json.RawMessage {
	b, err := json.Marshal(v)
	if err != nil {
		panic(err)
	}
	return b
}

func unmarshalOr[T any](raw json.RawMessage, def T) T {
	if len(raw) == 0 || string(raw) == "null" {
		return def
	}
	var v T
	if err := json.Unmarshal(raw, &v); err != nil {
		return def
	}
	return v
}

// --- world / styles ----------------------------------------------------------

func WorldFromRow(w dbq.World, chars []dbq.Character, locs []dbq.Location) *domain.World {
	out := &domain.World{
		ID: w.ID, OwnerID: w.OwnerID, Title: w.Title, Synopsis: w.Synopsis, Tone: w.Tone, Audience: w.Audience,
		Language: w.Language, StyleID: w.StyleID, Visibility: w.Visibility,
		Bible:       unmarshalOr(w.Bible, map[string]any{}),
		Canon:       unmarshalOr(w.Canon, domain.Canon{}),
		Permissions: unmarshalOr(w.Permissions, domain.Permissions{}),
		Characters:  []domain.Character{}, Locations: []domain.Location{},
	}
	for _, c := range chars {
		out.Characters = append(out.Characters, CharacterFromRow(c))
	}
	for _, l := range locs {
		out.Locations = append(out.Locations, LocationFromRow(l))
	}
	return out
}

func CharacterFromRow(c dbq.Character) domain.Character {
	ch := domain.Character{
		ID: c.ID, OwnerID: c.OwnerID, Name: c.Name, Role: c.Role, CountTag: c.CountTag, Description: c.Description,
		Personality: c.Personality, SpeechStyle: c.SpeechStyle, TagPrompt: c.TagPrompt,
		ReferenceImages: unmarshalOr(c.ReferenceImages, []string{}), IdentityLevel: c.IdentityLevel,
	}
	if c.IdentityAsset != nil {
		ch.IdentityAsset = *c.IdentityAsset
	}
	return ch
}

func LocationFromRow(l dbq.Location) domain.Location {
	return domain.Location{ID: l.ID, Name: l.Name, Description: l.Description, TagPrompt: l.TagPrompt,
		ReferenceImages: unmarshalOr(l.ReferenceImages, []string{}), Mood: l.Mood}
}

func (s *Store) LoadWorld(ctx context.Context, q *dbq.Queries, id string) (*domain.World, error) {
	if q == nil {
		q = s.Q
	}
	w, err := q.GetWorld(ctx, id)
	if err != nil {
		return nil, notFound(err)
	}
	chars, err := q.ListCharacters(ctx, id)
	if err != nil {
		return nil, err
	}
	locs, err := q.ListLocations(ctx, id)
	if err != nil {
		return nil, err
	}
	return WorldFromRow(w, chars, locs), nil
}

func (s *Store) LoadStyles(ctx context.Context, q *dbq.Queries) (*domain.Styles, error) {
	if q == nil {
		q = s.Q
	}
	raw, err := q.GetSetting(ctx, "styles")
	if err != nil {
		return nil, fmt.Errorf("styles not seeded: %w", notFound(err))
	}
	st := &domain.Styles{}
	if err := json.Unmarshal(raw, st); err != nil {
		return nil, err
	}
	rows, err := q.ListStylePresets(ctx)
	if err != nil {
		return nil, err
	}
	st.Presets = map[string]domain.Preset{}
	for _, r := range rows {
		var p domain.Preset
		if err := json.Unmarshal(r.Data, &p); err != nil {
			return nil, fmt.Errorf("preset %s: %w", r.ID, err)
		}
		st.Presets[r.ID] = p
	}
	return st, nil
}

// --- jobs ----------------------------------------------------------------------

func (s *Store) Enqueue(ctx context.Context, q *dbq.Queries, kind string, payload any, maxAttempts int) (int64, error) {
	if q == nil {
		q = s.Q
	}
	return q.EnqueueJob(ctx, dbq.EnqueueJobParams{Kind: kind, Payload: MustJSON(payload),
		MaxAttempts: int32(maxAttempts), DelaySeconds: 0})
}

func (s *Store) ClaimJob(ctx context.Context, workerID string) (*worker.Job, error) {
	j, err := s.Q.ClaimJob(ctx, workerID)
	if errors.Is(err, pgx.ErrNoRows) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	return &worker.Job{ID: j.ID, Kind: j.Kind, Payload: j.Payload, Attempts: int(j.Attempts), MaxAttempts: int(j.MaxAttempts)}, nil
}

func (s *Store) CompleteJob(ctx context.Context, id int64) error { return s.Q.CompleteJob(ctx, id) }

func (s *Store) RetryJob(ctx context.Context, id int64, at time.Time, msg string) error {
	return s.Q.RetryJob(ctx, dbq.RetryJobParams{ID: id, RunAfter: at, LastError: msg})
}

func (s *Store) DeferJob(ctx context.Context, id int64, at time.Time, msg string) error {
	return s.Q.DeferJob(ctx, dbq.DeferJobParams{ID: id, RunAfter: at, LastError: msg})
}

func (s *Store) FailJob(ctx context.Context, id int64, msg string) error {
	return s.Q.FailJob(ctx, dbq.FailJobParams{ID: id, LastError: msg})
}

func (s *Store) RequeueStaleJobs(ctx context.Context, before time.Time) (int64, error) {
	return s.Q.RequeueStaleJobs(ctx, &before)
}

// --- episodes ------------------------------------------------------------------

func EpisodeFromRow(e dbq.Episode) worker.Episode {
	ep := worker.Episode{ID: e.ID, CampaignID: e.CampaignID, Index: int(e.Idx), Status: e.Status, Premise: e.Premise,
		PanelsTotal: int(e.PanelsTotal)}
	if len(e.Chosen) > 0 && string(e.Chosen) != "null" {
		c := unmarshalOr(e.Chosen, worker.Chosen{})
		ep.Chosen = &c
	}
	if len(e.Moderation) > 0 && string(e.Moderation) != "null" {
		v := unmarshalOr(e.Moderation, storyboard.Verdict{})
		ep.Moderation = &v
	}
	if len(e.Storyboard) > 0 && string(e.Storyboard) != "null" {
		sb := &domain.Storyboard{}
		if json.Unmarshal(e.Storyboard, sb) == nil {
			ep.Storyboard = sb
		}
	}
	return ep
}

func CampaignFromRow(c dbq.Campaign, w *domain.World) worker.Campaign {
	st := unmarshalOr[*state.State](c.State, nil)
	if st == nil || st.Characters == nil {
		st = state.Empty(w)
	}
	return worker.Campaign{ID: c.ID, WorldID: c.WorldID, PlayerID: c.PlayerID, State: st,
		CanonProgress: unmarshalOr(c.CanonProgress, []string{})}
}

func (s *Store) loadContext(ctx context.Context, q *dbq.Queries, e dbq.Episode, c dbq.Campaign) (*worker.EpisodeContext, error) {
	w, err := s.LoadWorld(ctx, q, c.WorldID)
	if err != nil {
		return nil, err
	}
	st, err := s.LoadStyles(ctx, q)
	if err != nil {
		return nil, err
	}
	return &worker.EpisodeContext{Episode: EpisodeFromRow(e), Campaign: CampaignFromRow(c, w), World: w, Styles: st}, nil
}

func (s *Store) LoadEpisodeContext(ctx context.Context, episodeID string) (*worker.EpisodeContext, error) {
	e, err := s.Q.GetEpisode(ctx, episodeID)
	if err != nil {
		return nil, notFound(err)
	}
	c, err := s.Q.GetCampaign(ctx, e.CampaignID)
	if err != nil {
		return nil, notFound(err)
	}
	return s.loadContext(ctx, s.Q, e, c)
}

func (s *Store) SetEpisodeStatus(ctx context.Context, id, status, msg string) error {
	return s.Q.SetEpisodeStatus(ctx, dbq.SetEpisodeStatusParams{ID: id, Status: status, Error: msg})
}

func (s *Store) SetEpisodeModeration(ctx context.Context, id string, v storyboard.Verdict) error {
	return s.Q.SetEpisodeModeration(ctx, dbq.SetEpisodeModerationParams{ID: id, Moderation: MustJSON(v)})
}

func (s *Store) SaveStoryboard(ctx context.Context, episodeID string, sb *domain.Storyboard, maxAttempts int) error {
	warnings := sb.Warnings
	if warnings == nil {
		warnings = []string{}
	}
	diff := sb.StateDiffMap()
	return s.Tx(ctx, func(q *dbq.Queries) error {
		if err := q.SaveStoryboard(ctx, dbq.SaveStoryboardParams{
			ID: episodeID, Title: sb.Title, Storyboard: MustJSON(sb), Choices: MustJSON(sb.Choices),
			StateDiff: MustJSON(diff), Warnings: MustJSON(warnings),
			PanelsTotal: int32(len(sb.Panels)), CreditsCost: int32(len(sb.Panels)),
		}); err != nil {
			return err
		}
		for i, p := range sb.Panels {
			if err := q.InsertPanel(ctx, dbq.InsertPanelParams{
				EpisodeID: episodeID, Idx: int32(i), Shot: p.Shot, LocationID: p.LocationID, GapAfter: p.GapAfter,
				Bubbles: MustJSON(p.Bubbles), Sfx: MustJSON(p.SFX), Characters: MustJSON(p.Characters),
				VisualTags: MustJSON(p.VisualTags),
			}); err != nil {
				return err
			}
			if _, err := s.Enqueue(ctx, q, worker.KindPanel, worker.PanelPayload{EpisodeID: episodeID, Panel: i}, maxAttempts); err != nil {
				return err
			}
		}
		return nil
	})
}

// --- panels ----------------------------------------------------------------------

func PanelFromRow(p dbq.Panel) *worker.Panel {
	return &worker.Panel{
		EpisodeID: p.EpisodeID, Index: int(p.Idx), Status: p.Status, Seed: p.Seed,
		SB: domain.SBPanel{
			Shot: p.Shot, LocationID: p.LocationID, GapAfter: p.GapAfter,
			Characters: unmarshalOr(p.Characters, []domain.SBChar{}),
			Bubbles:    unmarshalOr(p.Bubbles, []domain.Bubble{}),
			SFX:        unmarshalOr(p.Sfx, []domain.SFX{}),
			VisualTags: unmarshalOr(p.VisualTags, []string{}),
		},
	}
}

func (s *Store) GetPanel(ctx context.Context, episodeID string, idx int) (*worker.Panel, error) {
	p, err := s.Q.GetPanel(ctx, dbq.GetPanelParams{EpisodeID: episodeID, Idx: int32(idx)})
	if err != nil {
		return nil, notFound(err)
	}
	return PanelFromRow(p), nil
}

func (s *Store) SetPanelStatus(ctx context.Context, episodeID string, idx int, status, msg string) error {
	return s.Q.SetPanelStatus(ctx, dbq.SetPanelStatusParams{EpisodeID: episodeID, Idx: int32(idx), Status: status, Error: msg})
}

func (s *Store) SavePanelResult(ctx context.Context, r *worker.PanelResult) error {
	var identity json.RawMessage
	if r.Identity != nil {
		identity = MustJSON(r.Identity)
	}
	var score *float32
	if r.IdentityScore != nil {
		f := float32(*r.IdentityScore)
		score = &f
	}
	return s.Q.SavePanelResult(ctx, dbq.SavePanelResultParams{
		EpisodeID: r.EpisodeID, Idx: int32(r.Index), Status: r.Status, ImagePath: r.ImagePath,
		Prompt: r.Prompt, Negative: r.Negative, Seed: r.Seed, Width: int32(r.Width), Height: int32(r.Height),
		Rating: MustJSON(r.Rating), Identity: identity, IdentityScore: score, Attempts: MustJSON(r.Attempts), Error: r.Error,
	})
}

func (s *Store) RefreshProgress(ctx context.Context, episodeID string) (worker.Progress, error) {
	if _, err := s.Q.RefreshPanelsReady(ctx, episodeID); err != nil {
		return worker.Progress{}, notFound(err)
	}
	p, err := s.Q.PanelProgress(ctx, episodeID)
	if err != nil {
		return worker.Progress{}, err
	}
	return worker.Progress{Ready: int(p.Ready), Failed: int(p.Failed), Total: int(p.Total)}, nil
}

func (s *Store) FinalizeEpisode(ctx context.Context, episodeID string, fn func(*worker.EpisodeContext, worker.Progress) *worker.Finalization) error {
	return s.Tx(ctx, func(q *dbq.Queries) error {
		e, err := q.GetEpisodeForUpdate(ctx, episodeID)
		if err != nil {
			return notFound(err)
		}
		c, err := q.GetCampaignForUpdate(ctx, e.CampaignID)
		if err != nil {
			return notFound(err)
		}
		ec, err := s.loadContext(ctx, q, e, c)
		if err != nil {
			return err
		}
		pr, err := q.PanelProgress(ctx, episodeID)
		if err != nil {
			return err
		}
		f := fn(ec, worker.Progress{Ready: int(pr.Ready), Failed: int(pr.Failed), Total: int(pr.Total)})
		if f == nil {
			return nil
		}
		if f.CampaignState != nil {
			if err := q.UpdateCampaignState(ctx, dbq.UpdateCampaignStateParams{
				ID: c.ID, State: MustJSON(f.CampaignState), CanonProgress: MustJSON(f.CanonProgress),
			}); err != nil {
				return err
			}
		}
		var snap json.RawMessage
		if f.StateSnapshot != nil {
			snap = MustJSON(f.StateSnapshot)
		}
		return q.FinishEpisode(ctx, dbq.FinishEpisodeParams{ID: episodeID, Status: f.EpisodeStatus, StateSnapshot: snap, Error: f.Error})
	})
}
