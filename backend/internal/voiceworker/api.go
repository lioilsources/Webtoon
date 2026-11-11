package voiceworker

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"

	"github.com/ol1n/webtoon/backend/internal/voice"
)

// APIClient talks to the worker API of webtoon-api on JODA (/v1/worker/*, VOICE_WORKER_TOKEN).
type APIClient struct {
	BaseURL string
	Token   string
	Worker  string // worker name, holds the task lease
	HTTP    *http.Client
}

// ErrLeaseLost: the API no longer considers this worker the task's owner (cancelled, e.g. the
// voice was deleted, or reclaimed after an expired lease).
var ErrLeaseLost = errors.New("voice task lease lost")

// HTTPError is a non-2xx response of the API.
type HTTPError struct {
	Status int
	Code   string
}

func (e *HTTPError) Error() string { return fmt.Sprintf("webtoon-api: HTTP %d %s", e.Status, e.Code) }

func (c *APIClient) do(ctx context.Context, method, path string, body io.Reader, hdr http.Header) (*http.Response, []byte, error) {
	req, err := http.NewRequestWithContext(ctx, method, strings.TrimRight(c.BaseURL, "/")+path, body)
	if err != nil {
		return nil, nil, err
	}
	for k, v := range hdr {
		req.Header[k] = v
	}
	req.Header.Set("Authorization", "Bearer "+c.Token)
	// Cloudflare rejects requests without a browser-like or explicit User-Agent (spark-gotchas).
	req.Header.Set("User-Agent", "toonfork-voice-worker/1")
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, nil, err
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(io.LimitReader(resp.Body, 16<<20))
	if err != nil {
		return resp, nil, err
	}
	if resp.StatusCode/100 != 2 {
		var e struct {
			Error string `json:"error"`
		}
		_ = json.Unmarshal(b, &e)
		if resp.StatusCode == http.StatusConflict && e.Error == "lease_lost" {
			return resp, b, ErrLeaseLost
		}
		return resp, b, &HTTPError{Status: resp.StatusCode, Code: e.Error}
	}
	return resp, b, nil
}

func (c *APIClient) postJSON(ctx context.Context, path string, v any) (*http.Response, []byte, error) {
	b, err := json.Marshal(v)
	if err != nil {
		return nil, nil, err
	}
	return c.do(ctx, http.MethodPost, path, bytes.NewReader(b), http.Header{"Content-Type": {"application/json"}})
}

// Pending returns the number of runnable tasks.
func (c *APIClient) Pending(ctx context.Context) (int, error) {
	_, b, err := c.do(ctx, http.MethodGet, "/v1/worker/voice-tasks/pending", nil, nil)
	if err != nil {
		return 0, err
	}
	var r struct {
		Pending int `json:"pending"`
	}
	return r.Pending, json.Unmarshal(b, &r)
}

// Claim takes the next task; nil when there is none.
func (c *APIClient) Claim(ctx context.Context) (*voice.WorkerTask, error) {
	resp, b, err := c.postJSON(ctx, "/v1/worker/voice-tasks/claim", map[string]string{"worker": c.Worker})
	if err != nil {
		return nil, err
	}
	if resp.StatusCode == http.StatusNoContent {
		return nil, nil
	}
	var t voice.WorkerTask
	if err := json.Unmarshal(b, &t); err != nil {
		return nil, fmt.Errorf("claim: %w", err)
	}
	return &t, nil
}

func (c *APIClient) Heartbeat(ctx context.Context, id string) error {
	_, _, err := c.postJSON(ctx, "/v1/worker/voice-tasks/"+id+"/heartbeat", map[string]string{"worker": c.Worker})
	return err
}

func (c *APIClient) Complete(ctx context.Context, id string, ok bool, msg string, retry bool) error {
	_, _, err := c.postJSON(ctx, "/v1/worker/voice-tasks/"+id+"/complete",
		map[string]any{"worker": c.Worker, "ok": ok, "error": msg, "retry": retry})
	return err
}

// Sample downloads the decrypted voice sample (kept in memory only).
func (c *APIClient) Sample(ctx context.Context, voiceID string) ([]byte, string, error) {
	resp, b, err := c.do(ctx, http.MethodGet, "/v1/worker/voices/"+voiceID+"/sample", nil, nil)
	if err != nil {
		return nil, "", err
	}
	return b, resp.Header.Get("Content-Type"), nil
}

// PutLine uploads one rendered line.
func (c *APIClient) PutLine(ctx context.Context, voiceID, hash, lang string, m4a []byte, durS float64) error {
	h := http.Header{}
	h.Set("Content-Type", "audio/mp4")
	h.Set("X-Duration-S", strconv.FormatFloat(durS, 'f', 3, 64))
	h.Set("X-Lang", lang)
	_, _, err := c.do(ctx, http.MethodPut, "/v1/worker/voices/"+voiceID+"/lines/"+hash, bytes.NewReader(m4a), h)
	return err
}
