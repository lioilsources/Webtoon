// Package fakes provides httptest stand-ins for the Spark services: an OpenAI-compatible
// LLM, ComfyUI (/prompt, /history, /view, /upload/image, /system_stats), the WD14 tagger
// and the AiStack Image API (/v1/image/*).
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
	// CharacterTags is the tag_prompt generation reply (gen_character SYSTEM, also for locations).
	// Its repair pass maps "copper hair" to "orange hair" and drops everything else.
	CharacterTags string
	mu            sync.Mutex
	calls         map[string]int
}

const (
	KindStoryboard = "storyboard"
	KindTranslate  = "translate"
	KindRuleCheck  = "rulecheck"
	KindModeration = "moderation"
	KindTagPrompt  = "tagprompt"
	KindTagRepair  = "tagrepair"
)

var unknownTagRE = regexp.MustCompile(`'([^']*)'`)

var phraseRE = regexp.MustCompile(`(?m)^- '([^']*)': `)

func NewLLM(storyboardJSON string) *LLM {
	f := &LLM{calls: map[string]int{}, Violations: `{"violations": []}`, Blocked: "ZAKÁZÁNO",
		CharacterTags: `{"tags": ["short hair", "Orange_Hair", "copper hair", "green eyes", "brown boots", "green eyes"], "notes": "fake"}`}
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
	case strings.HasPrefix(system, "You convert a character description"), strings.HasPrefix(system, "You convert a location description"):
		if strings.HasPrefix(user, "These Danbooru tags do not exist") {
			kind = KindTagRepair
			rep := map[string][]string{}
			first := strings.SplitN(user, "\n", 2)[0]
			for _, m := range unknownTagRE.FindAllStringSubmatch(first, -1) {
				if m[1] == "copper hair" {
					rep[m[1]] = []string{"orange hair"}
				} else {
					rep[m[1]] = []string{}
				}
			}
			b, _ := json.Marshal(map[string]any{"replace": rep})
			content = string(b)
		} else {
			kind, content = KindTagPrompt, f.CharacterTags
		}
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
	Down      atomic.Bool
	unsafe    atomic.Int32
	Always    atomic.Bool // every answer explicit
	Sensitive float64     // "sensitive" rating of the safe answers (default 0.08)
	Tags      map[string]float64
	Requests  atomic.Int32
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
		sensitive := f.Sensitive
		if sensitive == 0 {
			sensitive = 0.08
		}
		rating := map[string]float64{"general": 0.9, "sensitive": sensitive, "questionable": 0.01, "explicit": 0.001}
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

// --- AiStack Image API ---------------------------------------------------------

// ImageAPI fakes llm.ol1n.com/v1/image/*: a job is done after Polls status polls (default 1),
// Closed reports every queued job as waiting_window, Fail ends jobs in error. /tag answers from
// WD14 when set. Headers of every request are kept for the auth checks.
type ImageAPI struct {
	*httptest.Server
	Closed   atomic.Bool
	Fail     atomic.Bool
	Polls    int
	WD14     *WD14
	PNGBytes []byte
	mu       sync.Mutex
	jobs     map[string]*imageJob
	byRef    map[string]string
	headers  []http.Header
	submits  int
	inputs   []string
}

type imageJob struct {
	ID       string `json:"id"`
	Status   string `json:"status"`
	Error    string `json:"error,omitempty"`
	NOutputs int    `json:"n_outputs"`
	left     int
}

func NewImageAPI() *ImageAPI {
	f := &ImageAPI{Polls: 1, PNGBytes: TinyPNG(), jobs: map[string]*imageJob{}, byRef: map[string]string{}}
	window := func() map[string]any {
		if f.Closed.Load() {
			return map[string]any{"state": "closed", "reason": "LLM profile"}
		}
		return map[string]any{"state": "open"}
	}
	view := func(j *imageJob) map[string]any {
		st := j.Status
		if st == "queued" && f.Closed.Load() {
			st = "waiting_window"
		}
		return map[string]any{"id": j.ID, "status": st, "error": j.Error, "n_outputs": j.NOutputs, "position": 0, "window": window()}
	}
	mux := http.NewServeMux()
	mux.HandleFunc("POST /v1/image/jobs", func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("X-Project") == "" {
			http.Error(w, `{"error":"missing X-Project"}`, 400)
			return
		}
		var body struct {
			Workflow  map[string]any    `json:"workflow"`
			Inputs    map[string]string `json:"inputs"`
			ClientRef string            `json:"client_ref"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil || len(body.Workflow) == 0 {
			http.Error(w, `{"error":"bad workflow"}`, 400)
			return
		}
		f.mu.Lock()
		defer f.mu.Unlock()
		if id, ok := f.byRef[body.ClientRef]; ok && body.ClientRef != "" {
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(view(f.jobs[id])) //nolint:errcheck
			return
		}
		f.submits++
		j := &imageJob{ID: fmt.Sprintf("job%d", f.submits), Status: "queued", left: f.Polls}
		f.jobs[j.ID] = j
		f.byRef[body.ClientRef] = j.ID
		for name := range body.Inputs {
			f.inputs = append(f.inputs, name)
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusAccepted)
		json.NewEncoder(w).Encode(view(j)) //nolint:errcheck
	})
	mux.HandleFunc("GET /v1/image/jobs/{id}", func(w http.ResponseWriter, r *http.Request) {
		f.mu.Lock()
		defer f.mu.Unlock()
		j, ok := f.jobs[r.PathValue("id")]
		if !ok {
			http.Error(w, `{"error":"job not found"}`, 404)
			return
		}
		if j.Status == "queued" && !f.Closed.Load() {
			if j.left--; j.left <= 0 {
				if f.Fail.Load() {
					j.Status, j.Error = "error", "ComfyUI node error"
				} else {
					j.Status, j.NOutputs = "done", 1
				}
			}
		}
		json.NewEncoder(w).Encode(view(j)) //nolint:errcheck
	})
	mux.HandleFunc("GET /v1/image/jobs/{id}/outputs/{n}", func(w http.ResponseWriter, r *http.Request) {
		f.mu.Lock()
		j, ok := f.jobs[r.PathValue("id")]
		f.mu.Unlock()
		if !ok || j.Status != "done" || r.PathValue("n") != "0" {
			http.Error(w, `{"error":"output not found"}`, 404)
			return
		}
		w.Header().Set("Content-Type", "image/png")
		w.Write(f.PNGBytes)
	})
	mux.HandleFunc("POST /v1/image/tag", func(w http.ResponseWriter, r *http.Request) {
		if f.WD14 == nil {
			http.Error(w, `{"error":"no tagger"}`, 502)
			return
		}
		resp, err := http.Post(f.WD14.URL+"/tag", r.Header.Get("Content-Type"), r.Body)
		if err != nil {
			http.Error(w, err.Error(), 502)
			return
		}
		defer resp.Body.Close()
		w.WriteHeader(resp.StatusCode)
		io.Copy(w, resp.Body) //nolint:errcheck
	})
	mux.HandleFunc("GET /v1/image/status", func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(map[string]any{"window": window(), "queued": 0, "running": false}) //nolint:errcheck
	})
	f.Server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		f.mu.Lock()
		f.headers = append(f.headers, r.Header.Clone())
		f.mu.Unlock()
		mux.ServeHTTP(w, r)
	}))
	return f
}

// Submits counts new jobs (a repeated client_ref is not a new job).
func (f *ImageAPI) Submits() int {
	f.mu.Lock()
	defer f.mu.Unlock()
	return f.submits
}

func (f *ImageAPI) Headers() []http.Header {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]http.Header(nil), f.headers...)
}

// Inputs lists the input image names sent with the jobs.
func (f *ImageAPI) Inputs() []string {
	f.mu.Lock()
	defer f.mu.Unlock()
	return append([]string(nil), f.inputs...)
}
