// Package comfy is a minimal ComfyUI API client plus the parametrised SDXL workflow
// (optionally with IP-Adapter). Port of m0/comfy.py.
//
// This code never starts ComfyUI. When it is not reachable (outside the Spark window
// 07–13) every call returns upstream.Unavailable and the worker backs off.
package comfy

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"strings"
	"time"

	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/upstream"
)

type Client struct {
	URL          string
	HTTP         *http.Client
	PollInterval time.Duration // prototype: 1.5 s
	Timeout      time.Duration // prototype: 900 s
}

func New(baseURL string) *Client {
	return &Client{
		URL: strings.TrimRight(baseURL, "/"), HTTP: &http.Client{Timeout: 120 * time.Second},
		PollInterval: 1500 * time.Millisecond, Timeout: 900 * time.Second,
	}
}

type Graph map[string]any

func node(class string, inputs map[string]any) map[string]any {
	return map[string]any{"class_type": class, "inputs": inputs}
}

// Workflow builds the API-format graph. refImage = file name already uploaded to ComfyUI input/.
func Workflow(positive, negative string, width, height int, seed int64, p domain.Preset, prefix, refImage string, ipWeight float64) Graph {
	sample := map[string]any{
		"model": []any{"ckpt", 0}, "positive": []any{"pos", 0}, "negative": []any{"neg", 0}, "latent_image": []any{"latent", 0},
		"seed": seed, "steps": p.Steps, "cfg": p.CFG,
		"sampler_name": p.Sampler, "scheduler": p.Scheduler, "denoise": 1.0,
	}
	g := Graph{
		"ckpt":   node("CheckpointLoaderSimple", map[string]any{"ckpt_name": p.Checkpoint}),
		"pos":    node("CLIPTextEncode", map[string]any{"text": positive, "clip": []any{"ckpt", 1}}),
		"neg":    node("CLIPTextEncode", map[string]any{"text": negative, "clip": []any{"ckpt", 1}}),
		"latent": node("EmptyLatentImage", map[string]any{"width": width, "height": height, "batch_size": 1}),
		"sample": node("KSampler", sample),
		"decode": node("VAEDecode", map[string]any{"samples": []any{"sample", 0}, "vae": []any{"ckpt", 2}}),
		"save":   node("SaveImage", map[string]any{"images": []any{"decode", 0}, "filename_prefix": prefix}),
	}
	if p.Prediction == "v" {
		g["vpred"] = node("ModelSamplingDiscrete", map[string]any{"model": []any{"ckpt", 0}, "sampling": "v_prediction", "zsnr": true})
		sample["model"] = []any{"vpred", 0}
	}
	if refImage != "" {
		base := sample["model"]
		g["ipload"] = node("IPAdapterUnifiedLoader", map[string]any{"model": base, "preset": "PLUS (high strength)"})
		g["refimg"] = node("LoadImage", map[string]any{"image": refImage})
		g["ipapply"] = node("IPAdapterAdvanced", map[string]any{
			"model": []any{"ipload", 0}, "ipadapter": []any{"ipload", 1}, "image": []any{"refimg", 0},
			"weight": ipWeight, "weight_type": "linear", "combine_embeds": "concat",
			"start_at": 0.0, "end_at": 0.8, "embeds_scaling": "V only"})
		sample["model"] = []any{"ipapply", 0}
	}
	return g
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
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, upstream.Unavailable("comfyui", err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(io.LimitReader(resp.Body, 64<<20))
	if err != nil {
		return nil, upstream.Unavailable("comfyui", err)
	}
	if resp.StatusCode >= 300 {
		e := fmt.Errorf("%s %s → %d: %s", method, path, resp.StatusCode, truncate(raw, 500))
		if upstream.StatusUnavailable(resp.StatusCode) {
			return nil, upstream.Unavailable("comfyui", e)
		}
		return nil, e
	}
	return raw, nil
}

// Ping checks /system_stats (5 s timeout). Returns upstream.Unavailable when down.
func (c *Client) Ping(ctx context.Context) error {
	raw, err := c.do(ctx, http.MethodGet, "/system_stats", nil, "", 5*time.Second)
	if err != nil {
		if upstream.IsUnavailable(err) {
			return err
		}
		return upstream.Unavailable("comfyui", err)
	}
	var v map[string]any
	if err := json.Unmarshal(raw, &v); err != nil {
		return upstream.Unavailable("comfyui", fmt.Errorf("system_stats: %w", err))
	}
	return nil
}

// Upload puts PNG bytes into ComfyUI's input folder; returns the name to reference in LoadImage.
func (c *Client) Upload(ctx context.Context, png []byte, name string) (string, error) {
	var buf bytes.Buffer
	mw := multipart.NewWriter(&buf)
	fw, err := mw.CreateFormFile("image", name)
	if err != nil {
		return "", err
	}
	fw.Write(png)                      //nolint:errcheck
	mw.WriteField("overwrite", "true") //nolint:errcheck
	mw.Close()
	raw, err := c.do(ctx, http.MethodPost, "/upload/image", &buf, mw.FormDataContentType(), 0)
	if err != nil {
		return "", err
	}
	var res struct {
		Name      string `json:"name"`
		Subfolder string `json:"subfolder"`
	}
	if err := json.Unmarshal(raw, &res); err != nil {
		return "", fmt.Errorf("upload response: %w", err)
	}
	if res.Subfolder != "" {
		return res.Subfolder + "/" + res.Name, nil
	}
	return res.Name, nil
}

// Run queues the graph, waits for it and returns the output PNGs.
func (c *Client) Run(ctx context.Context, g Graph) ([][]byte, error) {
	body, _ := json.Marshal(map[string]any{"prompt": g, "client_id": newHex()})
	raw, err := c.do(ctx, http.MethodPost, "/prompt", bytes.NewReader(body), "application/json", 0)
	if err != nil {
		return nil, err
	}
	var queued struct {
		PromptID   string          `json:"prompt_id"`
		NodeErrors json.RawMessage `json:"node_errors"`
	}
	if err := json.Unmarshal(raw, &queued); err != nil {
		return nil, fmt.Errorf("queue response: %s", truncate(raw, 300))
	}
	if len(queued.NodeErrors) > 2 && string(queued.NodeErrors) != "null" { // more than "{}"
		return nil, fmt.Errorf("node_errors: %s", truncate(queued.NodeErrors, 600))
	}
	if queued.PromptID == "" {
		return nil, fmt.Errorf("no prompt_id: %s", truncate(raw, 300))
	}
	deadline := time.Now().Add(c.Timeout)
	for time.Now().Before(deadline) {
		raw, err := c.do(ctx, http.MethodGet, "/history/"+queued.PromptID, nil, "", 0)
		if err != nil {
			return nil, err
		}
		var hist map[string]struct {
			Status struct {
				StatusStr string          `json:"status_str"`
				Messages  json.RawMessage `json:"messages"`
			} `json:"status"`
			Outputs map[string]struct {
				Images []struct {
					Filename  string `json:"filename"`
					Subfolder string `json:"subfolder"`
					Type      string `json:"type"`
				} `json:"images"`
			} `json:"outputs"`
		}
		if err := json.Unmarshal(raw, &hist); err != nil {
			return nil, fmt.Errorf("history: %w", err)
		}
		if entry, ok := hist[queued.PromptID]; ok {
			if entry.Status.StatusStr == "error" {
				return nil, fmt.Errorf("ComfyUI error: %s", truncate(entry.Status.Messages, 800))
			}
			var images [][]byte
			for _, out := range entry.Outputs {
				for _, im := range out.Images {
					q := url.Values{"filename": {im.Filename}, "subfolder": {im.Subfolder}, "type": {im.Type}}
					png, err := c.do(ctx, http.MethodGet, "/view?"+q.Encode(), nil, "", 0)
					if err != nil {
						return nil, err
					}
					images = append(images, png)
				}
			}
			if len(images) == 0 {
				return nil, fmt.Errorf("prompt %s finished without images", queued.PromptID)
			}
			return images, nil
		}
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(c.PollInterval):
		}
	}
	return nil, fmt.Errorf("prompt %s not finished in %s", queued.PromptID, c.Timeout)
}

func newHex() string {
	var b [16]byte
	_, _ = rand.Read(b[:])
	return hex.EncodeToString(b[:])
}

func truncate(b []byte, n int) string {
	if len(b) > n {
		return string(b[:n]) + "..."
	}
	return string(b)
}
