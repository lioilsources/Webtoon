package llm_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"

	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/upstream"
)

func TestExtractJSON(t *testing.T) {
	cases := map[string]string{
		`{"a": 1}`:                          `{"a": 1}`,
		"Sure!\n```json\n{\"a\": 2}\n```\n": `{"a": 2}`,
		`prefix {"a": {"b": 3}} suffix`:     `{"a": {"b": 3}}`,
	}
	for in, want := range cases {
		got, err := llm.ExtractJSON(in)
		if err != nil || string(got) != want {
			t.Errorf("ExtractJSON(%q) = %s, %v", in, got, err)
		}
	}
	if _, err := llm.ExtractJSON("no json here"); err == nil {
		t.Error("expected error")
	}
}

func reply(content string) []byte {
	b, _ := json.Marshal(map[string]any{"choices": []any{map[string]any{"message": map[string]any{"content": content}}}})
	return b
}

func TestClientRetriesInvalidJSON(t *testing.T) {
	var n atomic.Int32
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var req map[string]any
		json.NewDecoder(r.Body).Decode(&req)
		if r.URL.Path != "/v1/chat/completions" || req["model"] != "m" ||
			req["response_format"].(map[string]any)["type"] != "json_object" {
			http.Error(w, "bad request", 400)
			return
		}
		if n.Add(1) == 1 {
			w.Write(reply("not json"))
			return
		}
		w.Write(reply(`{"ok": true}`))
	}))
	defer srv.Close()
	c := llm.New(srv.URL+"/v1", "m")
	c.RetryWait = time.Millisecond
	raw, err := c.JSON(context.Background(), "sys", "user", 0.5)
	if err != nil || string(raw) != `{"ok": true}` || n.Load() != 2 {
		t.Fatalf("raw=%s err=%v calls=%d", raw, err, n.Load())
	}
}

func TestClientUnavailable(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "upstream down", http.StatusBadGateway)
	}))
	c := llm.New(srv.URL, "m")
	if _, err := c.JSON(context.Background(), "s", "u", 0); !upstream.IsUnavailable(err) {
		t.Fatalf("502 must be unavailable: %v", err)
	}
	srv.Close()
	if _, err := c.JSON(context.Background(), "s", "u", 0); !upstream.IsUnavailable(err) {
		t.Fatalf("connection refused must be unavailable: %v", err)
	}
	litellm := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, `{"error":{"message":"litellm.InternalServerError: OpenAIException - Connection error.No fallback model group found"}}`, http.StatusInternalServerError)
	}))
	defer litellm.Close()
	if _, err := llm.New(litellm.URL, "m").JSON(context.Background(), "s", "u", 0); !upstream.IsUnavailable(err) {
		t.Fatalf("LiteLLM 500 connection error must be unavailable: %v", err)
	}
	bad := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "bad", http.StatusBadRequest)
	}))
	defer bad.Close()
	if _, err := llm.New(bad.URL, "m").JSON(context.Background(), "s", "u", 0); err == nil || upstream.IsUnavailable(err) {
		t.Fatalf("400 is a real error: %v", err)
	}
}
