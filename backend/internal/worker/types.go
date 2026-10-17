package worker

import (
	"context"
	"encoding/json"
	"time"

	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/state"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/wd14"
)

const (
	KindEpisode = "episode"
	KindPanel   = "panel"
)

type Job struct {
	ID          int64
	Kind        string
	Payload     json.RawMessage
	Attempts    int // including the current run
	MaxAttempts int
}

type EpisodePayload struct {
	EpisodeID string `json:"episode_id"`
}

type PanelPayload struct {
	EpisodeID  string `json:"episode_id"`
	Panel      int    `json:"panel"`
	Regenerate bool   `json:"regenerate,omitempty"`
}

// Chosen is what the player picked (or wrote) at the end of the previous episode.
type Chosen struct {
	ChoiceID string `json:"choice_id,omitempty"`
	Kind     string `json:"kind"`
	Text     string `json:"text"`
}

type Episode struct {
	ID          string
	CampaignID  string
	Index       int
	Status      string
	Premise     string
	Chosen      *Chosen
	Moderation  *storyboard.Verdict
	Storyboard  *domain.Storyboard
	PanelsTotal int
}

type Campaign struct {
	ID            string
	WorldID       string
	PlayerID      string
	State         *state.State
	CanonProgress []string
}

// EpisodeContext is everything a job needs to know about an episode.
type EpisodeContext struct {
	Episode  Episode
	Campaign Campaign
	World    *domain.World
	Styles   *domain.Styles
}

type Panel struct {
	EpisodeID string
	Index     int
	Status    string
	Seed      int64
	SB        domain.SBPanel // shot, location, characters, visual tags, bubbles, sfx, gap
}

type RenderAttempt struct {
	Seed   int64              `json:"seed"`
	Unsafe map[string]float64 `json:"unsafe"`
}

type PanelResult struct {
	EpisodeID     string
	Index         int
	Status        string // ready | failed
	ImagePath     string // relative to MEDIA_DIR
	Prompt        string
	Negative      string
	Seed          int64
	Width, Height int
	Rating        map[string]float64
	Identity      map[string]wd14.Identity
	IdentityScore *float64
	Attempts      []RenderAttempt
	Error         string
}

type Progress struct{ Ready, Failed, Total int }

func (p Progress) Done() bool { return p.Total > 0 && p.Ready+p.Failed >= p.Total }

// Finalization is what FinalizeEpisode persists, atomically.
type Finalization struct {
	EpisodeStatus string
	Error         string
	StateSnapshot *state.State // stored on the episode
	CampaignState *state.State // nil = campaign untouched
	CanonProgress []string
}

// Store is the persistence the worker needs. store.Store implements it on Postgres;
// tests use an in-memory implementation.
type Store interface {
	ClaimJob(ctx context.Context, workerID string) (*Job, error) // nil, nil when nothing is due
	CompleteJob(ctx context.Context, id int64) error
	RetryJob(ctx context.Context, id int64, runAfter time.Time, lastErr string) error
	DeferJob(ctx context.Context, id int64, runAfter time.Time, lastErr string) error
	FailJob(ctx context.Context, id int64, lastErr string) error
	RequeueStaleJobs(ctx context.Context, lockedBefore time.Time) (int64, error)

	LoadEpisodeContext(ctx context.Context, episodeID string) (*EpisodeContext, error)
	SetEpisodeStatus(ctx context.Context, episodeID, status, errMsg string) error
	SetEpisodeModeration(ctx context.Context, episodeID string, v storyboard.Verdict) error
	// SaveStoryboard stores the storyboard, creates the panel rows and enqueues one panel job each.
	SaveStoryboard(ctx context.Context, episodeID string, sb *domain.Storyboard, maxAttempts int) error

	GetPanel(ctx context.Context, episodeID string, idx int) (*Panel, error)
	SetPanelStatus(ctx context.Context, episodeID string, idx int, status, errMsg string) error
	SavePanelResult(ctx context.Context, r *PanelResult) error
	RefreshProgress(ctx context.Context, episodeID string) (Progress, error)
	// FinalizeEpisode locks the episode and its campaign, calls fn and persists its result
	// (fn returning nil means "nothing to do").
	FinalizeEpisode(ctx context.Context, episodeID string, fn func(ec *EpisodeContext, p Progress) *Finalization) error
}
