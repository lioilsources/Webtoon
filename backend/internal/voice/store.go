package voice

import (
	"context"
	"slices"
	"sort"
	"sync"
	"time"
)

// Store persists devices, voices, consents, lines, quotas and worker tasks. PGStore is the
// production implementation (tables from migration 000007); MemStore backs the unit tests.
type Store interface {
	CreateDevice(ctx context.Context, d Device) error
	// DeviceByTokenHash finds a device and bumps last_seen_at (at most once an hour).
	DeviceByTokenHash(ctx context.Context, hash string, now time.Time) (Device, error)
	DeleteDevice(ctx context.Context, id string) error

	// ActiveVoiceByDevice returns the device's voice that is not being deleted, or nil.
	ActiveVoiceByDevice(ctx context.Context, deviceID string) (*Voice, error)
	// ReceiptDevices counts devices other than deviceID with an active voice bought with this purchase.
	ReceiptDevices(ctx context.Context, platform, origID, deviceID string) (int, error)
	// CreateVoice stores the voice, its consent record and its voice_create task in one go;
	// ErrVoiceExists when the device already has an active voice.
	CreateVoice(ctx context.Context, v Voice, c Consent, t Task) error
	GetVoice(ctx context.Context, id string) (Voice, error)
	TouchVoice(ctx context.Context, id string, now time.Time) error
	// SetVoiceStatus changes queued/ready/failed; ErrNotFound for a voice being deleted.
	SetVoiceStatus(ctx context.Context, id, status, msg string, now time.Time) error
	// BeginDeleteVoice marks the voice deleting, detaches it from its device, cancels its open
	// tasks, drops its line rows, closes the consent record and queues t (voice_delete).
	BeginDeleteVoice(ctx context.Context, id, reason string, now time.Time, t Task) error
	// FinishDeleteVoice removes the voice row once the AiStack voice is gone.
	FinishDeleteVoice(ctx context.Context, id string) error
	GetConsent(ctx context.Context, voiceID string) (Consent, error)
	StaleVoices(ctx context.Context, before time.Time) ([]string, error)
	// StaleDevices lists devices unseen since before that have no active voice.
	StaleDevices(ctx context.Context, before time.Time) ([]string, error)
	// Cleanup drops consent records of voices deleted before consentsBefore, finished tasks
	// older than tasksBefore and quota rows before quotaDay (YYYY-MM-DD).
	Cleanup(ctx context.Context, consentsBefore, tasksBefore time.Time, quotaDay string) error

	Lines(ctx context.Context, voiceID string, hashes []string) (map[string]Line, error)
	PutLine(ctx context.Context, l Line) error
	// AddQuota adds n lines to the device's count for day unless that would exceed limit.
	AddQuota(ctx context.Context, deviceID, day string, n, limit int) (used int, ok bool, err error)

	// OpenLineTask returns a queued or running lines task of the voice with this idem key, or nil.
	OpenLineTask(ctx context.Context, voiceID, idemKey string) (*Task, error)
	CreateTask(ctx context.Context, t Task) error
	GetTask(ctx context.Context, id string) (Task, error)
	PendingTasks(ctx context.Context, now time.Time) (int, error)
	// ClaimTask takes the next runnable task (queued and due, or running with an expired lease).
	ClaimTask(ctx context.Context, worker string, now, leaseUntil time.Time) (*Task, error)
	HeartbeatTask(ctx context.Context, id, worker string, now, leaseUntil time.Time) error
	// FinishTask sets the final status of a running task held by worker; status queued puts it
	// back with runAfter. ErrLeaseLost when the worker no longer holds it.
	FinishTask(ctx context.Context, id, worker, status, msg string, runAfter, now time.Time) error
}

// MemStore is an in-memory Store for tests.
type MemStore struct {
	mu       sync.Mutex
	devices  map[string]Device
	voices   map[string]Voice
	consents map[string]Consent
	lines    map[string]map[string]Line
	quota    map[[2]string]int
	tasks    map[string]Task
}

func NewMemStore() *MemStore {
	return &MemStore{devices: map[string]Device{}, voices: map[string]Voice{}, consents: map[string]Consent{},
		lines: map[string]map[string]Line{}, quota: map[[2]string]int{}, tasks: map[string]Task{}}
}

var _ Store = (*MemStore)(nil)

func (m *MemStore) CreateDevice(_ context.Context, d Device) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.devices[d.ID] = d
	return nil
}

func (m *MemStore) DeviceByTokenHash(_ context.Context, hash string, now time.Time) (Device, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for id, d := range m.devices {
		if d.TokenHash == hash {
			if now.Sub(d.LastSeenAt) >= time.Hour {
				d.LastSeenAt = now
				m.devices[id] = d
			}
			return d, nil
		}
	}
	return Device{}, ErrNotFound
}

func (m *MemStore) DeleteDevice(_ context.Context, id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.devices, id)
	for k := range m.quota {
		if k[0] == id {
			delete(m.quota, k)
		}
	}
	for vid, v := range m.voices {
		if v.DeviceID == id {
			v.DeviceID = ""
			m.voices[vid] = v
		}
	}
	return nil
}

func (m *MemStore) activeVoice(deviceID string) *Voice {
	for _, v := range m.voices {
		if v.DeviceID == deviceID && v.Status != StatusDeleting {
			return &v
		}
	}
	return nil
}

func (m *MemStore) ActiveVoiceByDevice(_ context.Context, deviceID string) (*Voice, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	return m.activeVoice(deviceID), nil
}

func (m *MemStore) ReceiptDevices(_ context.Context, platform, origID, deviceID string) (int, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	seen := map[string]bool{}
	for _, v := range m.voices {
		if v.Status != StatusDeleting && v.DeviceID != "" && v.DeviceID != deviceID &&
			v.ReceiptPlatform == platform && v.ReceiptOrigID == origID {
			seen[v.DeviceID] = true
		}
	}
	return len(seen), nil
}

func (m *MemStore) CreateVoice(_ context.Context, v Voice, c Consent, t Task) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if m.activeVoice(v.DeviceID) != nil {
		return ErrVoiceExists
	}
	m.voices[v.ID] = v
	m.consents[v.ID] = c
	m.tasks[t.ID] = t
	return nil
}

func (m *MemStore) GetVoice(_ context.Context, id string) (Voice, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	v, ok := m.voices[id]
	if !ok {
		return Voice{}, ErrNotFound
	}
	return v, nil
}

func (m *MemStore) TouchVoice(_ context.Context, id string, now time.Time) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if v, ok := m.voices[id]; ok && v.Status != StatusDeleting {
		v.LastUsedAt = now
		m.voices[id] = v
	}
	return nil
}

func (m *MemStore) SetVoiceStatus(_ context.Context, id, status, msg string, now time.Time) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	v, ok := m.voices[id]
	if !ok || v.Status == StatusDeleting {
		return ErrNotFound
	}
	v.Status, v.Error, v.UpdatedAt = status, msg, now
	m.voices[id] = v
	return nil
}

func (m *MemStore) BeginDeleteVoice(_ context.Context, id, reason string, now time.Time, t Task) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	v, ok := m.voices[id]
	if !ok || v.Status == StatusDeleting {
		return ErrNotFound
	}
	v.Status, v.DeviceID, v.SampleFile, v.UpdatedAt = StatusDeleting, "", "", now
	m.voices[id] = v
	delete(m.lines, id)
	for tid, ot := range m.tasks {
		if ot.VoiceID == id && (ot.Status == TaskQueued || ot.Status == TaskRunning) {
			ot.Status, ot.Error, ot.UpdatedAt, ot.FinishedAt = TaskCancelled, "voice deleted", now, &now
			m.tasks[tid] = ot
		}
	}
	if c, ok := m.consents[id]; ok {
		c.DeletedAt, c.DeleteReason = &now, reason
		m.consents[id] = c
	}
	m.tasks[t.ID] = t
	return nil
}

func (m *MemStore) FinishDeleteVoice(_ context.Context, id string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	delete(m.voices, id)
	delete(m.lines, id)
	return nil
}

func (m *MemStore) GetConsent(_ context.Context, voiceID string) (Consent, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	c, ok := m.consents[voiceID]
	if !ok {
		return Consent{}, ErrNotFound
	}
	return c, nil
}

func (m *MemStore) StaleVoices(_ context.Context, before time.Time) ([]string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	var out []string
	for id, v := range m.voices {
		if v.Status != StatusDeleting && v.LastUsedAt.Before(before) {
			out = append(out, id)
		}
	}
	sort.Strings(out)
	return out, nil
}

func (m *MemStore) StaleDevices(_ context.Context, before time.Time) ([]string, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	var out []string
	for id, d := range m.devices {
		if d.LastSeenAt.Before(before) && m.activeVoice(id) == nil {
			out = append(out, id)
		}
	}
	sort.Strings(out)
	return out, nil
}

func (m *MemStore) Cleanup(_ context.Context, consentsBefore, tasksBefore time.Time, quotaDay string) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	for id, c := range m.consents {
		if c.DeletedAt != nil && c.DeletedAt.Before(consentsBefore) {
			delete(m.consents, id)
		}
	}
	for id, t := range m.tasks {
		if t.FinishedAt != nil && t.FinishedAt.Before(tasksBefore) {
			delete(m.tasks, id)
		}
	}
	for k := range m.quota {
		if k[1] < quotaDay {
			delete(m.quota, k)
		}
	}
	return nil
}

func (m *MemStore) Lines(_ context.Context, voiceID string, hashes []string) (map[string]Line, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	out := map[string]Line{}
	for _, h := range hashes {
		if l, ok := m.lines[voiceID][h]; ok {
			out[h] = l
		}
	}
	return out, nil
}

func (m *MemStore) PutLine(_ context.Context, l Line) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	v, ok := m.voices[l.VoiceID]
	if !ok || v.Status == StatusDeleting {
		return ErrNotFound
	}
	if m.lines[l.VoiceID] == nil {
		m.lines[l.VoiceID] = map[string]Line{}
	}
	m.lines[l.VoiceID][l.Hash] = l
	return nil
}

func (m *MemStore) AddQuota(_ context.Context, deviceID, day string, n, limit int) (int, bool, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	k := [2]string{deviceID, day}
	if m.quota[k]+n > limit {
		return m.quota[k], false, nil
	}
	m.quota[k] += n
	return m.quota[k], true, nil
}

func (m *MemStore) OpenLineTask(_ context.Context, voiceID, idemKey string) (*Task, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	for _, t := range m.tasks {
		if t.Kind == KindLines && t.VoiceID == voiceID && t.IdemKey == idemKey &&
			(t.Status == TaskQueued || t.Status == TaskRunning) {
			return &t, nil
		}
	}
	return nil, nil
}

func (m *MemStore) CreateTask(_ context.Context, t Task) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.tasks[t.ID] = t
	return nil
}

func (m *MemStore) GetTask(_ context.Context, id string) (Task, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	t, ok := m.tasks[id]
	if !ok {
		return Task{}, ErrNotFound
	}
	return t, nil
}

func runnable(t Task, now time.Time) bool {
	return (t.Status == TaskQueued && !t.RunAfter.After(now)) ||
		(t.Status == TaskRunning && t.LeaseUntil != nil && t.LeaseUntil.Before(now))
}

func (m *MemStore) PendingTasks(_ context.Context, now time.Time) (int, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	n := 0
	for _, t := range m.tasks {
		if runnable(t, now) {
			n++
		}
	}
	return n, nil
}

func (m *MemStore) ClaimTask(_ context.Context, worker string, now, leaseUntil time.Time) (*Task, error) {
	m.mu.Lock()
	defer m.mu.Unlock()
	var cand []Task
	for _, t := range m.tasks {
		if runnable(t, now) {
			cand = append(cand, t)
		}
	}
	if len(cand) == 0 {
		return nil, nil
	}
	slices.SortFunc(cand, func(a, b Task) int {
		if a.Priority != b.Priority {
			return b.Priority - a.Priority
		}
		if c := a.CreatedAt.Compare(b.CreatedAt); c != 0 {
			return c
		}
		return compareStr(a.ID, b.ID)
	})
	t := cand[0]
	t.Status, t.Worker, t.LeaseUntil, t.UpdatedAt = TaskRunning, worker, &leaseUntil, now
	t.Attempts++
	m.tasks[t.ID] = t
	return &t, nil
}

func compareStr(a, b string) int {
	switch {
	case a < b:
		return -1
	case a > b:
		return 1
	}
	return 0
}

func (m *MemStore) HeartbeatTask(_ context.Context, id, worker string, now, leaseUntil time.Time) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	t, ok := m.tasks[id]
	if !ok || t.Status != TaskRunning || t.Worker != worker {
		return ErrLeaseLost
	}
	t.LeaseUntil, t.UpdatedAt = &leaseUntil, now
	m.tasks[id] = t
	return nil
}

func (m *MemStore) FinishTask(_ context.Context, id, worker, status, msg string, runAfter, now time.Time) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	t, ok := m.tasks[id]
	if !ok || t.Status != TaskRunning || t.Worker != worker {
		return ErrLeaseLost
	}
	t.Status, t.Error, t.UpdatedAt, t.LeaseUntil = status, msg, now, nil
	if status == TaskQueued {
		t.RunAfter, t.Worker = runAfter, ""
	} else {
		t.FinishedAt = &now
	}
	m.tasks[id] = t
	return nil
}
