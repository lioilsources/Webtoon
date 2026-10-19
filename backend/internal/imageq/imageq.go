// Package imageq is the client of the AiStack Image API (llm.ol1n.com/v1/image/*): a shared
// ComfyUI job queue on Spark with the WD14 tagger behind it. It offers the same calls the worker
// uses from comfy.Client and wd14.Client, so the backend can run outside the home LAN.
//
// The queue keeps a job across the comfy window: a job submitted outside it waits there
// (waiting_window). Run then returns upstream.Unavailable, the worker backs off, and the retry
// re-attaches to the same job through its client_ref instead of queueing a second one.
package imageq

import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/ol1n/webtoon/backend/internal/comfy"
	"github.com/ol1n/webtoon/backend/internal/upstream"
	"github.com/ol1n/webtoon/backend/internal/wd14"
)

const service = "image-api"

type Client struct {
	URL          string // base, e.g. https://llm.ol1n.com (paths /v1/image/* are appended)
	AccessID     string // CF-Access-Client-Id
	AccessSecret string // CF-Access-Client-Secret
	Project      string // X-Project
	HTTP         *http.Client
	PollInterval time.Duration
	Timeout      time.Duration // how long Run waits for a queued/running job before backing off

	mu     sync.Mutex
	inputs map[string][]byte // "uploaded" reference images, sent with the job that loads them
}

func New(baseURL, accessID, accessSecret string) *Client {
	return &Client{
		URL: strings.TrimRight(baseURL, "/"), AccessID: accessID, AccessSecret: accessSecret, Project: "webtoon",
		HTTP: &http.Client{Timeout: 120 * time.Second}, PollInterval: 1500 * time.Millisecond, Timeout: 900 * time.Second,
		inputs: map[string][]byte{},
	}
}

// Window is the comfy window as the queue reports it (state open/closed/busy/hot/cpu).
type Window struct {
	State  string `json:"state"`
	Reason string `json:"reason"`
}

type job struct {
	ID       string `json:"id"`
	Status   string `json:"status"`
	Error    string `json:"error"`
	Position int    `json:"position"`
	NOutputs int    `json:"n_outputs"`
	Window   Window `json:"window"`
}

func (c *Client) do(ctx context.Context, method, path string, body io.Reader, contentType string, timeout time.Duration) ([]byte, error) {
	if timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, timeout)
		defer cancel()
	}
	req, err := http.NewRequestWithContext(ctx, method, c.URL+path, body)
	if err != nil {
		return nil, err
	}
	if contentType != "" {
		req.Header.Set("Content-Type", contentType)
	}
	req.Header.Set("X-Project", c.Project)
	if c.AccessID != "" {
		req.Header.Set("CF-Access-Client-Id", c.AccessID)
		req.Header.Set("CF-Access-Client-Secret", c.AccessSecret)
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, upstream.Unavailable(service, err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(io.LimitReader(resp.Body, 64<<20))
	if err != nil {
		return nil, upstream.Unavailable(service, err)
	}
	if resp.StatusCode >= 300 {
		e := fmt.Errorf("%s %s → %d: %s", method, path, resp.StatusCode, truncate(raw, 500))
		// 52x: Cloudflare cannot reach the tunnel (Spark rebooting, cloudflared restarting).
		if upstream.StatusUnavailable(resp.StatusCode) || (resp.StatusCode >= 520 && resp.StatusCode <= 530) {
			return nil, upstream.Unavailable(service, e)
		}
		return nil, e
	}
	return raw, nil
}

// Ping checks /v1/image/status: Unavailable unless the comfy window is open, so the worker
// waits as it does when the LAN ComfyUI is down.
func (c *Client) Ping(ctx context.Context) error {
	raw, err := c.do(ctx, http.MethodGet, "/v1/image/status", nil, "", 5*time.Second)
	if err != nil {
		if upstream.IsUnavailable(err) {
			return err
		}
		return upstream.Unavailable(service, err)
	}
	var st struct {
		Window Window `json:"window"`
	}
	if err := json.Unmarshal(raw, &st); err != nil {
		return upstream.Unavailable(service, fmt.Errorf("status: %w", err))
	}
	if st.Window.State != "open" {
		return upstream.Unavailable(service, fmt.Errorf("comfy window %s: %s", st.Window.State, st.Window.Reason))
	}
	return nil
}

var badName = regexp.MustCompile(`[^A-Za-z0-9._-]`)

// Upload keeps the PNG for the next jobs that load it: the Image API takes input images
// with the job (base64), not through a separate upload. Returns the LoadImage name.
func (c *Client) Upload(_ context.Context, png []byte, name string) (string, error) {
	name = strings.TrimLeft(badName.ReplaceAllString(name, "_"), "._-")
	if name == "" || len(name) > 128 {
		return "", fmt.Errorf("bad input name %q", name)
	}
	c.mu.Lock()
	c.inputs[name] = png
	c.mu.Unlock()
	return name, nil
}

// Run submits the graph, waits for it and returns the output PNGs. The client_ref is a hash of
// the graph and its inputs, so a retry after a back-off finds the job it queued before.
func (c *Client) Run(ctx context.Context, g comfy.Graph) ([][]byte, error) {
	inputs, err := c.inputsFor(g)
	if err != nil {
		return nil, err
	}
	b64 := map[string]string{}
	for name, b := range inputs {
		b64[name] = base64.StdEncoding.EncodeToString(b)
	}
	ref, err := clientRef(g, inputs)
	if err != nil {
		return nil, err
	}
	body, err := json.Marshal(map[string]any{"workflow": g, "inputs": b64, "client_ref": ref})
	if err != nil {
		return nil, err
	}
	raw, err := c.do(ctx, http.MethodPost, "/v1/image/jobs", bytes.NewReader(body), "application/json", 0)
	if err != nil {
		return nil, err
	}
	var j job
	if err := json.Unmarshal(raw, &j); err != nil || j.ID == "" {
		return nil, fmt.Errorf("submit response: %s", truncate(raw, 300))
	}
	deadline := time.Now().Add(c.Timeout)
	for {
		switch j.Status {
		case "done":
			return c.outputs(ctx, j)
		case "error":
			return nil, fmt.Errorf("image job %s failed: %s", j.ID, j.Error)
		case "cancelled":
			return nil, fmt.Errorf("image job %s was cancelled", j.ID)
		case "waiting_window":
			return nil, upstream.Unavailable(service, fmt.Errorf("job %s waits for the comfy window (%s: %s)", j.ID, j.Window.State, j.Window.Reason))
		}
		if !time.Now().Before(deadline) {
			// Still queued behind other projects or running: the job stays, the retry re-attaches.
			return nil, upstream.Unavailable(service, fmt.Errorf("job %s still %s after %s", j.ID, j.Status, c.Timeout))
		}
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(c.PollInterval):
		}
		raw, err := c.do(ctx, http.MethodGet, "/v1/image/jobs/"+j.ID, nil, "", 0)
		if err != nil {
			return nil, err
		}
		if err := json.Unmarshal(raw, &j); err != nil {
			return nil, fmt.Errorf("job status: %w", err)
		}
	}
}

func (c *Client) outputs(ctx context.Context, j job) ([][]byte, error) {
	if j.NOutputs == 0 {
		return nil, fmt.Errorf("image job %s finished without outputs", j.ID)
	}
	images := make([][]byte, 0, j.NOutputs)
	for n := 0; n < j.NOutputs; n++ {
		png, err := c.do(ctx, http.MethodGet, fmt.Sprintf("/v1/image/jobs/%s/outputs/%d", j.ID, n), nil, "", 0)
		if err != nil {
			return nil, err
		}
		images = append(images, png)
	}
	return images, nil
}

// inputsFor returns the uploaded images the graph's LoadImage nodes reference.
func (c *Client) inputsFor(g comfy.Graph) (map[string][]byte, error) {
	c.mu.Lock()
	defer c.mu.Unlock()
	out := map[string][]byte{}
	for id, n := range g {
		node, _ := n.(map[string]any)
		if node["class_type"] != "LoadImage" {
			continue
		}
		in, _ := node["inputs"].(map[string]any)
		name, _ := in["image"].(string)
		b, ok := c.inputs[name]
		if !ok {
			return nil, fmt.Errorf("node %s loads %q, which was not uploaded", id, name)
		}
		out[name] = b
	}
	return out, nil
}

func clientRef(g comfy.Graph, inputs map[string][]byte) (string, error) {
	h := sha256.New()
	if err := json.NewEncoder(h).Encode(g); err != nil { // map keys are sorted: stable per graph
		return "", err
	}
	names := make([]string, 0, len(inputs))
	for name := range inputs {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		h.Write([]byte(name))
		h.Write(inputs[name])
	}
	return "webtoon-" + hex.EncodeToString(h.Sum(nil))[:40], nil
}

// Tag runs the WD14 tagger through /v1/image/tag (same body and answer as the host's /tag).
func (c *Client) Tag(ctx context.Context, png []byte) (*wd14.Tags, error) {
	raw, err := c.do(ctx, http.MethodPost, "/v1/image/tag", bytes.NewReader(png), "application/octet-stream", 0)
	if err != nil {
		return nil, err
	}
	var t wd14.Tags
	if err := json.Unmarshal(raw, &t); err != nil {
		return nil, fmt.Errorf("wd14 response: %w", err)
	}
	return &t, nil
}

func truncate(b []byte, n int) string {
	if len(b) > n {
		return string(b[:n]) + "..."
	}
	return string(b)
}
