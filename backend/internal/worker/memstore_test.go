package worker_test

import (
	"context"
	"encoding/json"
	"errors"
	"sort"
	"sync"
	"time"

	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/state"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/worker"
)

// memStore is an in-memory worker.Store with the same semantics as the Postgres one
// (job claiming by run_after, deferral without burning attempts, atomic finalize).
type memStore struct {
	mu        sync.Mutex
	now       time.Time
	jobs      []*memJob
	world     *domain.World
	styles    *domain.Styles
	campaigns map[string]*worker.Campaign
	episodes  map[string]*memEpisode
	panels    map[string][]*memPanel
	sheets    map[string]*memSheet
}

type memSheet struct {
	worker.Sheet
	Error            string
	Best             *int
	Prompt, Negative string
}

type memJob struct {
	worker.Job
	Status   string
	RunAfter time.Time
	LastErr  string
}

type memEpisode struct {
	worker.Episode
	Title       string
	Choices     []domain.Choice
	Warnings    []string
	Error       string
	Snapshot    *state.State
	PanelsReady int
}

type memPanel struct {
	worker.Panel
	Result *worker.PanelResult
	Error  string
}

var errNotFound = errors.New("not found")

func newMemStore(w *domain.World, st *domain.Styles) *memStore {
	return &memStore{now: time.Now(), world: w, styles: st,
		campaigns: map[string]*worker.Campaign{}, episodes: map[string]*memEpisode{}, panels: map[string][]*memPanel{},
		sheets: map[string]*memSheet{}}
}

func (m *memStore) advance(d time.Duration) { m.mu.Lock(); m.now = m.now.Add(d); m.mu.Unlock() }

func (m *memStore) enqueue(kind string, payload any, maxAttempts int) {
	b, _ := json.Marshal(payload)
	m.jobs = append(m.jobs, &memJob{Job: worker.Job{ID: int64(len(m.jobs) + 1), Kind: kind, Payload: b, MaxAttempts: maxAttempts},
		Status: "queued", RunAfter: m.now})
}

func (m *memStore) addCampaignWithEpisode(campID, epID, premise string, chosen *worker.Chosen) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.campaigns[campID] = &worker.Campaign{ID: campID, WorldID: m.world.ID, PlayerID: "p1", State: state.Empty(m.world), CanonProgress: []string{}}
	m.episodes[epID] = &memEpisode{Episode: worker.Episode{ID: epID, CampaignID: campID, Index: 1, Status: "queued", Premise: premise, Chosen: chosen}}
	m.enqueue(worker.KindEpisode, worker.EpisodePayload{EpisodeID: epID}, 3)
}

func (m *memStore) job(id int64) memJob {
	m.mu.Lock()
	defer m.mu.Unlock()
	return *m.jobs[id-1]
}

func (m *memStore) episode(id string) memEpisode {
	m.mu.Lock()
	defer m.mu.Unlock()
	return *m.episodes[id]
}

func (m *memStore) panel(ep string, i int) memPanel {
	m.mu.Lock()
	defer m.mu.Unlock()
	return *m.panels[ep][i]
}

func (m *memStore) ClaimJob(_ context.Context, workerID string) (*worker.Job, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	due := []*memJob{}
	for _, j := range m.jobs {
		if j.Status == "queued" && !j.RunAfter.After(m.now) {
			due = append(due, j)
		}
	}
	if len(due) == 0 {
		return nil, nil
	}
	sort.SliceStable(due, func(a, b int) bool {
		if !due[a].RunAfter.Equal(due[b].RunAfter) {
			return due[a].RunAfter.Before(due[b].RunAfter)
		}
		return due[a].ID < due[b].ID
	})
	j := due[0]
	j.Status = "running"
	j.Attempts++
	cp := j.Job
	return &cp, nil
}

func (m *memStore) setJob(id int64, fn func(j *memJob)) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	fn(m.jobs[id-1])
	return nil
}

func (m *memStore) CompleteJob(_ context.Context, id int64) error {
	return m.setJob(id, func(j *memJob) { j.Status = "done" })
}

func (m *memStore) RetryJob(_ context.Context, id int64, at time.Time, msg string) error {
	return m.setJob(id, func(j *memJob) { j.Status, j.RunAfter, j.LastErr = "queued", at, msg })
}

func (m *memStore) DeferJob(_ context.Context, id int64, at time.Time, msg string) error {
	return m.setJob(id, func(j *memJob) {
		j.Status, j.RunAfter, j.LastErr = "queued", at, msg
		j.Attempts = max(j.Attempts-1, 0)
	})
}

func (m *memStore) FailJob(_ context.Context, id int64, msg string) error {
	return m.setJob(id, func(j *memJob) { j.Status, j.LastErr = "failed", msg })
}

func (m *memStore) RequeueStaleJobs(context.Context, time.Time) (int64, error) { return 0, nil }

func (m *memStore) contextLocked(epID string) (*worker.EpisodeContext, error) {
	e, ok := m.episodes[epID]
	if !ok {
		return nil, errNotFound
	}
	c := m.campaigns[e.CampaignID]
	return &worker.EpisodeContext{Episode: e.Episode, Campaign: *c, World: m.world, Styles: m.styles}, nil
}

func (m *memStore) LoadEpisodeContext(_ context.Context, epID string) (*worker.EpisodeContext, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.contextLocked(epID)
}

func (m *memStore) SetEpisodeStatus(_ context.Context, id, status, msg string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	e := m.episodes[id]
	e.Status, e.Error = status, msg
	return nil
}

func (m *memStore) SetEpisodeModeration(_ context.Context, id string, v storyboard.Verdict) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.episodes[id].Moderation = &v
	return nil
}

func (m *memStore) SaveStoryboard(_ context.Context, id string, sb *domain.Storyboard, maxAttempts int) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	e := m.episodes[id]
	e.Storyboard, e.Title, e.Choices, e.Warnings = sb, sb.Title, sb.Choices, sb.Warnings
	e.PanelsTotal, e.Status, e.Error, e.PanelsReady = len(sb.Panels), "generating", "", 0
	m.panels[id] = nil
	for i, p := range sb.Panels {
		m.panels[id] = append(m.panels[id], &memPanel{Panel: worker.Panel{EpisodeID: id, Index: i, Status: "pending", SB: p}})
		m.enqueue(worker.KindPanel, worker.PanelPayload{EpisodeID: id, Panel: i}, maxAttempts)
	}
	return nil
}

func (m *memStore) GetPanel(_ context.Context, ep string, i int) (*worker.Panel, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	ps := m.panels[ep]
	if i < 0 || i >= len(ps) {
		return nil, errNotFound
	}
	cp := ps[i].Panel
	return &cp, nil
}

func (m *memStore) SetPanelStatus(_ context.Context, ep string, i int, status, msg string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	p := m.panels[ep][i]
	p.Status, p.Error = status, msg
	return nil
}

func (m *memStore) SavePanelResult(_ context.Context, r *worker.PanelResult) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	p := m.panels[r.EpisodeID][r.Index]
	p.Status, p.Seed, p.Result, p.Error = r.Status, r.Seed, r, r.Error
	return nil
}

func (m *memStore) progressLocked(ep string) worker.Progress {
	var pr worker.Progress
	for _, p := range m.panels[ep] {
		pr.Total++
		switch p.Status {
		case "ready":
			pr.Ready++
		case "failed":
			pr.Failed++
		}
	}
	return pr
}

func (m *memStore) RefreshProgress(_ context.Context, ep string) (worker.Progress, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	pr := m.progressLocked(ep)
	m.episodes[ep].PanelsReady = pr.Ready
	return pr, nil
}

func (m *memStore) FinalizeEpisode(_ context.Context, ep string, fn func(*worker.EpisodeContext, worker.Progress) *worker.Finalization) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	ec, err := m.contextLocked(ep)
	if err != nil {
		return err
	}
	f := fn(ec, m.progressLocked(ep))
	if f == nil {
		return nil
	}
	e := m.episodes[ep]
	if f.CampaignState != nil {
		c := m.campaigns[e.CampaignID]
		c.State, c.CanonProgress = f.CampaignState, f.CanonProgress
	}
	e.Status, e.Error, e.Snapshot = f.EpisodeStatus, f.Error, f.StateSnapshot
	return nil
}

func (m *memStore) addSheet(id, charID string, seeds int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.sheets[id] = &memSheet{Sheet: worker.Sheet{ID: id, WorldID: m.world.ID, CharacterID: charID, Status: "queued", Seeds: seeds}}
	m.enqueue(worker.KindSheet, worker.SheetPayload{SheetID: id}, 3)
}

func (m *memStore) sheet(id string) memSheet {
	m.mu.Lock()
	defer m.mu.Unlock()
	return *m.sheets[id]
}

func (m *memStore) LoadSheetContext(_ context.Context, id string) (*worker.SheetContext, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	sh, ok := m.sheets[id]
	if !ok {
		return nil, errNotFound
	}
	cp := sh.Sheet
	cp.Images = append([]worker.SheetImage(nil), sh.Images...)
	return &worker.SheetContext{Sheet: cp, World: m.world, Styles: m.styles}, nil
}

func (m *memStore) SetSheetStatus(_ context.Context, id, status, msg string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.sheets[id].Status, m.sheets[id].Error = status, msg
	return nil
}

func (m *memStore) SetSheetPrompt(_ context.Context, id, pos, neg string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.sheets[id].Prompt, m.sheets[id].Negative = pos, neg
	return nil
}

func (m *memStore) AddSheetImage(_ context.Context, id string, img worker.SheetImage) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.sheets[id].Images = append(m.sheets[id].Images, img)
	return nil
}

func (m *memStore) FinishSheet(_ context.Context, id, status string, best *int, msg string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	sh := m.sheets[id]
	sh.Status, sh.Best, sh.Error = status, best, msg
	if best != nil {
		for i := range m.world.Characters {
			if m.world.Characters[i].ID == sh.CharacterID {
				m.world.Characters[i].ReferenceImages = append(m.world.Characters[i].ReferenceImages, sh.Images[*best].Path)
			}
		}
	}
	return nil
}
