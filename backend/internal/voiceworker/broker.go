package voiceworker

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"strings"
	"sync"
	"time"
)

// Broker is a minimal client of spark-broker (AiStack services/spark-broker, :8100), the same
// calls as `sparkctl lease` / `hb` / `extend` / `done`: the worker holds a lease of the `tts`
// service only while the JODA queue has work, and returns it when the queue is empty.
type Broker struct {
	BaseURL  string
	Token    string // SPARK_BROKER_TOKEN, optional
	Project  string // webtoon
	Session  string
	Title    string
	Services []string
	Priority int
	LeaseMin int
	HTTP     *http.Client
	Log      *slog.Logger
	Now      func() time.Time
	Poll     time.Duration // how often to look at a queued lease
	Beat     time.Duration // heartbeat interval while held (broker orphans after 10 min)
}

type brokerJob struct {
	ID         string     `json:"id"`
	State      string     `json:"state"` // queued | running | draining | done | failed | cancelled | orphaned
	Waiting    string     `json:"waiting"`
	LeaseUntil *time.Time `json:"lease_until"`
	Error      string     `json:"error"`
}

func (j *brokerJob) final() bool {
	switch j.State {
	case "done", "failed", "cancelled", "orphaned":
		return true
	}
	return false
}

// BrokerError is a non-2xx answer of the broker.
type BrokerError struct {
	Status int
	Msg    string
}

func (e *BrokerError) Error() string {
	return fmt.Sprintf("spark-broker: HTTP %d: %s", e.Status, e.Msg)
}

func (b *Broker) do(ctx context.Context, method, path string, body any) (*brokerJob, error) {
	var rd io.Reader
	if body != nil {
		bb, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		rd = bytes.NewReader(bb)
	}
	req, err := http.NewRequestWithContext(ctx, method, strings.TrimRight(b.BaseURL, "/")+path, rd)
	if err != nil {
		return nil, err
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if b.Token != "" {
		req.Header.Set("Authorization", "Bearer "+b.Token)
	}
	resp, err := b.HTTP.Do(req)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()
	rb, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if resp.StatusCode/100 != 2 {
		var e struct {
			Error string `json:"error"`
		}
		_ = json.Unmarshal(rb, &e)
		return nil, &BrokerError{Status: resp.StatusCode, Msg: e.Error}
	}
	var j brokerJob
	if err := json.Unmarshal(rb, &j); err != nil {
		return nil, fmt.Errorf("spark-broker: %w", err)
	}
	return &j, nil
}

// Acquire submits a lease and waits until the broker reports it running.
func (b *Broker) Acquire(ctx context.Context) (*Lease, error) {
	notify := false // a summary per lease would flood Telegram; errors are reported anyway
	j, err := b.do(ctx, http.MethodPost, "/v1/jobs", map[string]any{
		"project": b.Project, "session": b.Session, "title": b.Title, "priority": b.Priority, "notify": notify,
		"stages": []map[string]any{{"name": "voices", "services": b.Services, "mode": "lease",
			"lease_min": b.LeaseMin, "estimate_min": b.LeaseMin}},
	})
	if err != nil {
		return nil, fmt.Errorf("lease: %w", err)
	}
	b.Log.Info("broker lease queued", "job", j.ID, "services", b.Services)
	lastWait := ""
	for j.State != "running" {
		if j.final() || j.State == "draining" {
			return nil, fmt.Errorf("lease %s ended before it started: %s %s", j.ID, j.State, j.Error)
		}
		if j.Waiting != lastWait {
			b.Log.Info("broker lease waiting", "job", j.ID, "why", j.Waiting)
			lastWait = j.Waiting
		}
		select {
		case <-ctx.Done():
			b.cancel(j.ID)
			return nil, ctx.Err()
		case <-time.After(b.Poll):
		}
		nj, err := b.do(ctx, http.MethodPost, "/v1/jobs/"+j.ID+"/heartbeat", nil)
		if err != nil {
			var be *BrokerError
			if errors.As(err, &be) && be.Status/100 == 4 {
				return nil, fmt.Errorf("lease %s: %w", j.ID, err)
			}
			b.Log.Warn("broker unreachable while waiting", "job", j.ID, "err", err)
			continue
		}
		j = nj
	}
	b.Log.Info("broker lease running", "job", j.ID)
	l := &Lease{b: b, id: j.ID, until: j.LeaseUntil, done: make(chan struct{})}
	l.ctx, l.cancelCtx = context.WithCancel(context.Background())
	go l.keep()
	return l, nil
}

func (b *Broker) cancel(id string) {
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_, _ = b.do(ctx, http.MethodDelete, "/v1/jobs/"+id, nil)
}

// Lease is a running broker lease. Usable turns false when the broker wants the GPU back
// (draining, an extension refused); Ctx is cancelled when the lease is gone.
type Lease struct {
	b         *Broker
	id        string
	ctx       context.Context
	cancelCtx context.CancelFunc
	done      chan struct{}

	mu       sync.Mutex
	until    *time.Time
	draining bool
	metrics  map[string]map[string]int
}

// Ctx is cancelled when the broker ends the lease (expired, orphaned, cancelled).
func (l *Lease) Ctx() context.Context { return l.ctx }

func (l *Lease) ID() string { return l.id }

// Usable reports whether new tasks may be started under this lease.
func (l *Lease) Usable() bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	return !l.draining && l.ctx.Err() == nil
}

// Count adds to the metrics reported with done ({"lines": {"ok": n, "failed": m}}).
func (l *Lease) Count(name string, ok bool) {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.metrics == nil {
		l.metrics = map[string]map[string]int{}
	}
	if l.metrics[name] == nil {
		l.metrics[name] = map[string]int{"ok": 0, "failed": 0}
	}
	if ok {
		l.metrics[name]["ok"]++
	} else {
		l.metrics[name]["failed"]++
	}
}

func (l *Lease) keep() {
	t := time.NewTicker(l.b.Beat)
	defer t.Stop()
	for {
		select {
		case <-l.done:
			return
		case <-t.C:
		}
		ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
		j, err := l.b.do(ctx, http.MethodPost, "/v1/jobs/"+l.id+"/heartbeat", nil)
		cancel()
		if err != nil {
			var be *BrokerError
			if errors.As(err, &be) && be.Status/100 == 4 {
				l.b.Log.Warn("broker lease lost", "job", l.id, "err", err)
				l.cancelCtx()
				return
			}
			l.b.Log.Warn("broker heartbeat failed", "job", l.id, "err", err)
			continue
		}
		if j.final() {
			l.b.Log.Warn("broker lease ended", "job", l.id, "state", j.State)
			l.cancelCtx()
			return
		}
		l.mu.Lock()
		l.until = j.LeaseUntil
		if j.State == "draining" && !l.draining {
			l.draining = true
			l.b.Log.Info("broker wants the GPU back, finishing the current task", "job", l.id)
		}
		near := l.until != nil && l.until.Sub(l.b.Now()) < 10*time.Minute
		l.mu.Unlock()
		if near && !l.draining {
			ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
			_, err := l.b.do(ctx, http.MethodPost, fmt.Sprintf("/v1/jobs/%s/extend?minutes=%d", l.id, l.b.LeaseMin), nil)
			cancel()
			if err != nil {
				// Someone with higher priority waits for another profile: let them have it.
				l.mu.Lock()
				l.draining = true
				l.mu.Unlock()
				l.b.Log.Info("broker lease not extended, releasing after the current task", "job", l.id, "err", err)
			}
		}
	}
}

// Release reports done (with metrics, or the error) and stops the heartbeat.
func (l *Lease) Release(errMsg string) {
	select {
	case <-l.done:
		return
	default:
		close(l.done)
	}
	defer l.cancelCtx()
	if l.ctx.Err() != nil {
		return // the broker already ended it
	}
	l.mu.Lock()
	m := l.metrics
	l.mu.Unlock()
	body := map[string]any{}
	if errMsg != "" {
		body["error"] = errMsg
	} else if len(m) > 0 {
		body["metrics"] = m
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	if _, err := l.b.do(ctx, http.MethodPost, "/v1/jobs/"+l.id+"/done", body); err != nil {
		l.b.Log.Warn("broker done failed", "job", l.id, "err", err)
		return
	}
	l.b.Log.Info("broker lease released", "job", l.id, "metrics", m)
}
