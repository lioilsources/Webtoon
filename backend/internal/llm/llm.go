// Package llm is a minimal OpenAI-compatible chat client (LiteLLM / vLLM on Spark) in JSON mode.
package llm

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"regexp"
	"strings"
	"time"

	"github.com/ol1n/webtoon/backend/internal/upstream"
)

// JSONCaller is what the pipeline needs from an LLM; tests substitute fakes.
type JSONCaller interface {
	JSON(ctx context.Context, system, user string, temperature float64) (json.RawMessage, error)
}

// SchemaCaller is a JSONCaller that can also force a JSON schema (vLLM guided decoding).
// Callers type-assert for it and fall back to JSON when the client cannot.
type SchemaCaller interface {
	JSONSchema(ctx context.Context, system, user string, temperature float64, name string, schema json.RawMessage) (json.RawMessage, error)
}

type Client struct {
	URL       string // base, e.g. http://192.168.88.66:8080/v1
	Model     string
	MaxTokens int
	Retries   int // extra attempts when the reply is not valid JSON (prototype: 2)
	HTTP      *http.Client
	RetryWait time.Duration
	// Cloudflare Access service token, when the LLM sits behind Access (llm.ol1n.com).
	AccessID, AccessSecret string
}

func New(url, model string) *Client {
	return &Client{
		URL: strings.TrimRight(url, "/"), Model: model, MaxTokens: 6000, Retries: 2,
		HTTP: &http.Client{Timeout: 300 * time.Second}, RetryWait: time.Second,
	}
}

var fenceRE = regexp.MustCompile("(?s)```(?:json)?\\s*(.*?)```")

// ExtractJSON mirrors common._extract_json: strip a ``` fence, take the outermost {...}.
func ExtractJSON(text string) (json.RawMessage, error) {
	text = strings.TrimSpace(text)
	if m := fenceRE.FindStringSubmatch(text); m != nil {
		text = m[1]
	}
	start := strings.Index(text, "{")
	end := strings.LastIndex(text, "}")
	if start < 0 || end < start {
		return nil, errors.New("no JSON object in reply")
	}
	raw := json.RawMessage(text[start : end+1])
	var probe map[string]any
	if err := json.Unmarshal(raw, &probe); err != nil {
		return nil, err
	}
	return raw, nil
}

type chatReq struct {
	Model          string         `json:"model"`
	Messages       []chatMsg      `json:"messages"`
	ResponseFormat any            `json:"response_format"`
	Temperature    float64        `json:"temperature"`
	MaxTokens      int            `json:"max_tokens"`
	TemplateKwargs map[string]any `json:"chat_template_kwargs,omitempty"`
}

type chatMsg struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// JSON runs one chat completion in JSON mode and returns the parsed object.
// Transport errors and 502/503/504 are reported as upstream.Unavailable.
func (c *Client) JSON(ctx context.Context, system, user string, temperature float64) (json.RawMessage, error) {
	return c.call(ctx, system, user, temperature, map[string]string{"type": "json_object"}, nil)
}

// JSONSchema is JSON with a forced schema (response_format json_schema, strict) and thinking
// switched off: qwen3 behind LiteLLM otherwise spends minutes reasoning before short structured answers.
func (c *Client) JSONSchema(ctx context.Context, system, user string, temperature float64, name string, schema json.RawMessage) (json.RawMessage, error) {
	rf := map[string]any{"type": "json_schema", "json_schema": map[string]any{"name": name, "schema": schema, "strict": true}}
	return c.call(ctx, system, user, temperature, rf, map[string]any{"enable_thinking": false})
}

func (c *Client) call(ctx context.Context, system, user string, temperature float64, format any, kwargs map[string]any) (json.RawMessage, error) {
	var last error
	for attempt := 0; attempt <= c.Retries; attempt++ {
		content, err := c.complete(ctx, system, user, temperature, format, kwargs)
		if err != nil {
			return nil, err
		}
		raw, err := ExtractJSON(content)
		if err == nil {
			return raw, nil
		}
		last = err
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-time.After(c.RetryWait):
		}
	}
	return nil, fmt.Errorf("LLM did not return valid JSON: %w", last)
}

func (c *Client) complete(ctx context.Context, system, user string, temperature float64, format any, kwargs map[string]any) (string, error) {
	body, _ := json.Marshal(chatReq{
		Model: c.Model,
		Messages: []chatMsg{
			{Role: "system", Content: system},
			{Role: "user", Content: user},
		},
		ResponseFormat: format,
		Temperature:    temperature,
		MaxTokens:      c.MaxTokens,
		TemplateKwargs: kwargs,
	})
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.URL+"/chat/completions", bytes.NewReader(body))
	if err != nil {
		return "", err
	}
	req.Header.Set("Content-Type", "application/json")
	if c.AccessID != "" {
		req.Header.Set("CF-Access-Client-Id", c.AccessID)
		req.Header.Set("CF-Access-Client-Secret", c.AccessSecret)
	}
	resp, err := c.HTTP.Do(req)
	if err != nil {
		if ctx.Err() != nil {
			return "", ctx.Err()
		}
		return "", upstream.Unavailable("llm", err)
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(io.LimitReader(resp.Body, 8<<20))
	if err != nil {
		return "", upstream.Unavailable("llm", err)
	}
	if resp.StatusCode >= 300 {
		e := fmt.Errorf("POST %s/chat/completions → %d: %s", c.URL, resp.StatusCode, truncate(raw, 500))
		if upstream.StatusUnavailable(resp.StatusCode) || backendDown(resp.StatusCode, raw) {
			return "", upstream.Unavailable("llm", e)
		}
		return "", e
	}
	var out struct {
		Choices []struct {
			Message struct {
				Content *string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}
	if err := json.Unmarshal(raw, &out); err != nil {
		return "", fmt.Errorf("LLM response: %w", err)
	}
	if len(out.Choices) == 0 {
		return "", fmt.Errorf("LLM response without choices: %s", truncate(raw, 300))
	}
	if out.Choices[0].Message.Content == nil {
		return "", nil
	}
	return *out.Choices[0].Message.Content, nil
}

func truncate(b []byte, n int) string {
	if len(b) > n {
		return string(b[:n]) + "..."
	}
	return string(b)
}

// backendDown: LiteLLM keeps answering while the model behind it is off schedule, and reports
// that as a 500 "Connection error" (no fallback). Treat it like a 502 so jobs wait, not fail.
func backendDown(code int, body []byte) bool {
	if code != http.StatusInternalServerError {
		return false
	}
	b := string(body)
	return strings.Contains(b, "Connection error") || strings.Contains(b, "No fallback model group") ||
		strings.Contains(b, "APIConnectionError")
}
