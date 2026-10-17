// Package fakes provides httptest stand-ins for the Spark services: an OpenAI-compatible
// LLM, ComfyUI (/prompt, /history, /view, /upload/image, /system_stats) and the WD14 tagger.
// Tests never talk to the real 192.168.88.66 hosts.
package fakes

import (
	"bytes"
	"encoding/json"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"io"
	"net/http"
	"net/http/httptest"
	"regexp"
	"strings"
	"sync"
	"sync/atomic"
)

// --- LLM -----------------------------------------------------------------------

// LLM routes chat completions by system prompt to the storyboard / translate / rule-check /
// moderation handlers. Down=true answers 503 (treated as "LLM off schedule").
type LLM struct {
	*httptest.Server
	Down       atomic.Bool
	Storyboard func(user string) string // default: StoryboardJSON
	Violations string                   // rule check reply, default no violations
	Blocked    string                   // moderation blocks player text containing this
	mu         sync.Mutex
	calls      map[string]int
}

const (
	KindStoryboard = "storyboard"
	KindTranslate  = "translate"
	KindRuleCheck  = "rulecheck"
	KindModeration = "moderation"
)

var phraseRE = regexp.MustCompile(`(?m)^- '([^']*)': `)

func NewLLM(storyboardJSON string) *LLM {
	f := &LLM{calls: map[string]int{}, Violations: `{"violations": []}`, Blocked: "ZAKÁZÁNO"}
	f.Storyboard = func(string) string { return storyboardJSON }
	f.Server = httptest.NewServer(http.HandlerFunc(f.handle))
	return f
}

func (f *LLM) Calls(kind string) int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.calls[kind]
}

func (f *LLM) handle(w http.ResponseWriter, r *http.Request) {
	if f.Down.Load() {
		http.Error(w, "llm down", http.StatusServiceUnavailable)
		return
	}
	if r.URL.Path != "/v1/chat/completions" {
		http.NotFound(w, r)
		return
	}
	var req struct {
		Messages []struct{ Role, Content string } `json:"messages"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || len(req.Messages) != 2 {
		http.Error(w, "bad request", 400)
		return
	}
	system, user := req.Messages[0].Content, req.Messages[1].Content
	var kind, content string
	switch {
	case strings.HasPrefix(system, "You are the storyboard writer"):
		kind, content = KindStoryboard, f.Storyboard(user)
	case system == "You are a Danbooru tagging expert.":
		kind = KindTranslate
		m := map[string][]string{}
		for _, p := range phraseRE.FindAllStringSubmatch(user, -1) {
			m[p[1]] = []string{"sunlight"} // every phrase maps to one known tag
		}
		b, _ := json.Marshal(map[string]any{"map": m})
		content = string(b)
	case system == "You are a strict continuity editor.":
		kind, content = KindRuleCheck, f.Violations
	case strings.HasPrefix(system, "You are a content moderator"):
		kind = KindModeration
		input := user[strings.Index(user, "<<<"):]
		if f.Blocked != "" && strings.Contains(input, f.Blocked) {
			content = `{"allowed": false, "reason": "nevhodný obsah", "categories": ["violence"]}`
		} else {
			content = `{"allowed": true, "reason": "ok", "categories": []}`
		}
	default:
		http.Error(w, "unexpected system prompt", 400)
		return
	}
	f.mu.Lock()
	f.calls[kind]++
	f.mu.Unlock()
	json.NewEncoder(w).Encode(map[string]any{ //nolint:errcheck
		"choices": []any{map[string]any{"message": map[string]any{"role": "assistant", "content": content}}},
	})
}

// --- ComfyUI -------------------------------------------------------------------

type Comfy struct {
	*httptest.Server
	Down     atomic.Bool // 503 on every endpoint
	mu       sync.Mutex
	graphs   []map[string]any
	uploads  []string
	pending  map[string]int // prompt id → remaining "not done yet" polls
	seq      int
	Pings    atomic.Int32
	PNGBytes []byte
}

func NewComfy() *Comfy {
	f := &Comfy{pending: map[string]int{}, PNGBytes: TinyPNG()}
	mux := http.NewServeMux()
	mux.HandleFunc("GET /system_stats", func(w http.ResponseWriter, r *http.Request) {
		f.Pings.Add(1)
		w.Write([]byte(`{"system": {"os": "fake"}, "devices": []}`))
	})
	mux.HandleFunc("POST /prompt", func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			Prompt map[string]any `json:"prompt"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil || body.Prompt["sample"] == nil {
			http.Error(w, "bad graph", 400)
			return
		}
		f.mu.Lock()
		f.seq++
		id := fmt.Sprintf("p%d", f.seq)
		f.pending[id] = 1
		f.graphs = append(f.graphs, body.Prompt)
		f.mu.Unlock()
		json.NewEncoder(w).Encode(map[string]any{"prompt_id": id, "number": f.seq, "node_errors": map[string]any{}}) //nolint:errcheck
	})
	mux.HandleFunc("GET /history/{id}", func(w http.ResponseWriter, r *http.Request) {
		id := r.PathValue("id")
		f.mu.Lock()
		left, ok := f.pending[id]
		if ok && left > 0 {
			f.pending[id] = left - 1
		}
		f.mu.Unlock()
		if !ok || left > 0 {
			w.Write([]byte(`{}`))
			return
		}
		json.NewEncoder(w).Encode(map[string]any{id: map[string]any{ //nolint:errcheck
			"status":  map[string]any{"status_str": "success", "completed": true},
			"outputs": map[string]any{"save": map[string]any{"images": []any{map[string]any{"filename": id + ".png", "subfolder": "webtoon", "type": "output"}}}},
		}})
	})
	mux.HandleFunc("GET /view", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Query().Get("type") != "output" || r.URL.Query().Get("filename") == "" {
			http.Error(w, "bad view", 400)
			return
		}
		w.Header().Set("Content-Type", "image/png")
		w.Write(f.PNGBytes)
	})
	mux.HandleFunc("POST /upload/image", func(w http.ResponseWriter, r *http.Request) {
		file, hdr, err := r.FormFile("image")
		if err != nil {
			http.Error(w, "no image", 400)
			return
		}
		io.Copy(io.Discard, file)
		f.mu.Lock()
		f.uploads = append(f.uploads, hdr.Filename)
		f.mu.Unlock()
		json.NewEncoder(w).Encode(map[string]any{"name": hdr.Filename, "subfolder": "", "type": "input"}) //nolint:errcheck
	})
	f.Server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if f.Down.Load() {
			http.Error(w, "comfy down", http.StatusServiceUnavailable)
			return
		}
		mux.ServeHTTP(w, r)
	}))
	return f
}

func (f *Comfy) Graphs() []map[string]any {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]map[string]any(nil), f.graphs...)
}

func (f *Comfy) Uploads() []string {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]string(nil), f.uploads...)
}

// --- WD14 ------------------------------------------------------------------------

// WD14 answers /tag. Unsafe(n) makes the next n answers explicit.
type WD14 struct {
	*httptest.Server
	Down     atomic.Bool
	unsafe   atomic.Int32
	Always   atomic.Bool // every answer explicit
	Tags     map[string]float64
	Requests atomic.Int32
}

func NewWD14(general map[string]float64) *WD14 {
	f := &WD14{Tags: general}
	f.Server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if f.Down.Load() {
			http.Error(w, "wd14 down", http.StatusServiceUnavailable)
			return
		}
		body, _ := io.ReadAll(r.Body)
		if r.URL.Path != "/tag" || !bytes.HasPrefix(body, []byte("\x89PNG")) {
			http.Error(w, "bad", 400)
			return
		}
		f.Requests.Add(1)
		rating := map[string]float64{"general": 0.9, "sensitive": 0.08, "questionable": 0.01, "explicit": 0.001}
		if f.Always.Load() || f.unsafe.Add(-1) >= 0 {
			rating = map[string]float64{"general": 0.01, "sensitive": 0.1, "questionable": 0.2, "explicit": 0.9}
		}
		json.NewEncoder(w).Encode(map[string]any{"general": f.Tags, "character": map[string]float64{}, "rating": rating}) //nolint:errcheck
	}))
	return f
}

func (f *WD14) Unsafe(n int) { f.unsafe.Store(int32(n)) }

// TinyPNG is a valid 2x2 PNG.
func TinyPNG() []byte {
	img := image.NewRGBA(image.Rect(0, 0, 2, 2))
	img.Set(0, 0, color.RGBA{255, 0, 0, 255})
	var buf bytes.Buffer
	png.Encode(&buf, img) //nolint:errcheck
	return buf.Bytes()
}
