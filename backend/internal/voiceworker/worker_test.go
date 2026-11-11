package voiceworker

import (
	"bytes"
	"context"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/ol1n/webtoon/backend/internal/voice"
	"github.com/ol1n/webtoon/backend/internal/voice/receipt"
)

var t0 = time.Date(2026, 11, 11, 10, 0, 0, 0, time.UTC)

func quiet() *slog.Logger { return slog.New(slog.NewTextHandler(io.Discard, nil)) }

// --- fake AiStack audio service ------------------------------------------------------------

type fakeAudio struct {
	*httptest.Server
	mu      sync.Mutex
	voices  map[string]map[string]string // id → form fields
	samples map[string][]byte
	tts     []TTSRequest
	down    bool // 503 on tts (engine not up in this profile)
	jobs    map[string]TTSRequest
	n       int
}

func newFakeAudio(t *testing.T) *fakeAudio {
	f := &fakeAudio{voices: map[string]map[string]string{}, samples: map[string][]byte{}, jobs: map[string]TTSRequest{}}
	f.Server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		f.mu.Lock()
		defer f.mu.Unlock()
		switch {
		case r.Method == "POST" && r.URL.Path == "/v1/audio/voices":
			if err := r.ParseMultipartForm(8 << 20); err != nil {
				http.Error(w, err.Error(), 400)
				return
			}
			fields := map[string]string{}
			for k, v := range r.MultipartForm.Value {
				fields[k] = v[0]
			}
			fh := r.MultipartForm.File["sample"][0]
			fd, _ := fh.Open()
			b, _ := io.ReadAll(fd)
			f.voices[fields["voice_id"]] = fields
			f.samples[fields["voice_id"]] = b
			w.WriteHeader(201)
			fmt.Fprint(w, `{}`)
		case r.Method == "DELETE" && strings.HasPrefix(r.URL.Path, "/v1/audio/voices/"):
			id := strings.TrimPrefix(r.URL.Path, "/v1/audio/voices/")
			if _, ok := f.voices[id]; !ok {
				http.Error(w, `{"detail":"neznámý hlas"}`, 404)
				return
			}
			delete(f.voices, id)
			fmt.Fprint(w, `{"status":"deleted"}`)
		case r.Method == "POST" && r.URL.Path == "/v1/audio/tts":
			var req TTSRequest
			json.NewDecoder(r.Body).Decode(&req) //nolint:errcheck
			if f.down {
				w.WriteHeader(503)
				fmt.Fprint(w, `{"detail":"chatterbox neběží"}`)
				return
			}
			f.tts = append(f.tts, req)
			f.n++
			id := fmt.Sprintf("j%d", f.n)
			f.jobs[id] = req
			w.WriteHeader(202)
			fmt.Fprintf(w, `{"job_id":%q,"status":"queued"}`, id)
		case strings.HasPrefix(r.URL.Path, "/v1/audio/jobs/") && strings.Contains(r.URL.Path, "/outputs/"):
			id := strings.Split(strings.TrimPrefix(r.URL.Path, "/v1/audio/jobs/"), "/")[0]
			fmt.Fprintf(w, "WAV:%s", f.jobs[id].Text)
		case strings.HasPrefix(r.URL.Path, "/v1/audio/jobs/"):
			id := strings.TrimPrefix(r.URL.Path, "/v1/audio/jobs/")
			fmt.Fprintf(w, `{"job_id":%q,"status":"done","outputs":[{"url":"/v1/audio/jobs/%s/outputs/out.wav","filename":"out.wav","duration":1.2}]}`, id, id)
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(f.Close)
	return f
}

// --- fake spark-broker --------------------------------------------------------------------

type fakeBroker struct {
	*httptest.Server
	mu        sync.Mutex
	submitted []map[string]any
	state     string
	polls     int // heartbeats while queued before it runs
	beats     int
	done      []map[string]any
	gone      bool // heartbeat answers 404 (orphaned)
}

func newFakeBroker(t *testing.T) *fakeBroker {
	f := &fakeBroker{}
	f.Server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		f.mu.Lock()
		defer f.mu.Unlock()
		job := func() {
			until := t0.Add(30 * time.Minute)
			json.NewEncoder(w).Encode(map[string]any{"id": "1111-1", "state": f.state, "waiting": "čeká na tts", "lease_until": until}) //nolint:errcheck
		}
		switch {
		case r.Method == "POST" && r.URL.Path == "/v1/jobs":
			var m map[string]any
			json.NewDecoder(r.Body).Decode(&m) //nolint:errcheck
			f.submitted = append(f.submitted, m)
			f.state, f.polls = "queued", 1
			w.WriteHeader(201)
			job()
		case strings.HasSuffix(r.URL.Path, "/heartbeat"):
			if f.gone {
				w.WriteHeader(404)
				fmt.Fprint(w, `{"error":"neznámá úloha"}`)
				return
			}
			f.beats++
			if f.state == "queued" {
				if f.polls--; f.polls < 0 {
					f.state = "running"
				}
			}
			job()
		case strings.HasSuffix(r.URL.Path, "/done"):
			var m map[string]any
			json.NewDecoder(r.Body).Decode(&m) //nolint:errcheck
			f.done = append(f.done, m)
			f.state = "done"
			job()
		case strings.HasSuffix(r.URL.Path, "/extend"):
			job()
		default:
			http.NotFound(w, r)
		}
	}))
	t.Cleanup(f.Close)
	return f
}

// --- the JODA side: the real voice API over httptest -------------------------------------

type world struct {
	t      *testing.T
	api    *httptest.Server
	audio  *fakeAudio
	broker *fakeBroker
	w      *Worker
	now    time.Time
	store  *voice.MemStore
}

func box(typ string, payload []byte) []byte {
	b := make([]byte, 8, 8+len(payload))
	binary.BigEndian.PutUint32(b, uint32(8+len(payload)))
	copy(b[4:], typ)
	return append(b, payload...)
}

func m4a(seconds float64, body string) []byte {
	mvhd := make([]byte, 100)
	binary.BigEndian.PutUint32(mvhd[12:16], 1000)
	binary.BigEndian.PutUint32(mvhd[16:20], uint32(seconds*1000))
	out := box("ftyp", []byte("M4A \x00\x00\x00\x00M4A mp42isom"))
	out = append(out, box("mdat", []byte(body))...)
	return append(out, box("moov", box("mvhd", mvhd))...)
}

func newWorld(t *testing.T) *world {
	t.Helper()
	wd := &world{t: t, now: t0, store: voice.NewMemStore()}
	rv, err := receipt.New(receipt.Config{Mode: receipt.ModeTest}, quiet())
	if err != nil {
		t.Fatal(err)
	}
	srv, err := voice.New(voice.Config{DataDir: t.TempDir(), DataKey: bytes.Repeat([]byte{3}, 32), WorkerToken: "wt"},
		wd.store, rv, func() time.Time { return wd.now }, quiet())
	if err != nil {
		t.Fatal(err)
	}
	mux := http.NewServeMux()
	srv.Register(mux)
	wd.api = httptest.NewServer(mux)
	t.Cleanup(wd.api.Close)
	wd.audio = newFakeAudio(t)
	wd.broker = newFakeBroker(t)
	cfg := DefaultConfig()
	cfg.Idle, cfg.LeaseIdle, cfg.Heartbeat, cfg.Poll = time.Millisecond, time.Millisecond, time.Hour, time.Millisecond
	hc := &http.Client{Timeout: 5 * time.Second}
	wd.w = &Worker{
		API:   &APIClient{BaseURL: wd.api.URL, Token: "wt", Worker: "spark-test", HTTP: hc},
		Audio: &AudioClient{BaseURL: wd.audio.URL, HTTP: hc},
		Broker: &Broker{BaseURL: wd.broker.URL, Project: "webtoon", Session: "test", Title: "t", Services: []string{"tts"},
			Priority: 20, LeaseMin: 30, HTTP: hc, Log: quiet(), Now: func() time.Time { return wd.now }, Poll: time.Millisecond, Beat: time.Hour},
		Cfg: cfg,
		Encode: func(_ context.Context, parts []string, out string) (float64, error) {
			var body []string
			for _, p := range parts {
				b, _ := os.ReadFile(p)
				body = append(body, string(b))
			}
			return 1.25, os.WriteFile(out, m4a(1.25, strings.Join(body, "|")), 0o600)
		},
		TmpDir: t.TempDir(),
		Log:    quiet(),
		Now:    func() time.Time { return wd.now },
	}
	return wd
}

func (wd *world) req(method, path, token string, body io.Reader, ctype string) (int, map[string]any) {
	wd.t.Helper()
	r, _ := http.NewRequest(method, wd.api.URL+path, body)
	if token != "" {
		r.Header.Set("Authorization", "Bearer "+token)
	}
	if ctype != "" {
		r.Header.Set("Content-Type", ctype)
	}
	resp, err := http.DefaultClient.Do(r)
	if err != nil {
		wd.t.Fatal(err)
	}
	defer resp.Body.Close()
	var m map[string]any
	json.NewDecoder(resp.Body).Decode(&m) //nolint:errcheck
	return resp.StatusCode, m
}

func (wd *world) newVoice() (token, id string) {
	wd.t.Helper()
	_, m := wd.req("POST", "/v1/player/devices", "", nil, "")
	token = m["token"].(string)
	var b bytes.Buffer
	mw := multipart.NewWriter(&b)
	mw.WriteField("consent", "true")            //nolint:errcheck
	mw.WriteField("consent_text", "Souhlasím.") //nolint:errcheck
	mw.WriteField("receipt", "test:tx")         //nolint:errcheck
	fw, _ := mw.CreateFormFile("sample", "s.m4a")
	fw.Write(m4a(10, "SAMPLE-AUDIO")) //nolint:errcheck
	mw.Close()
	code, m := wd.req("POST", "/v1/player/voices", token, &b, mw.FormDataContentType())
	if code != 201 {
		wd.t.Fatalf("create voice: %d %v", code, m)
	}
	return token, m["voice_id"].(string)
}

func (wd *world) run() {
	wd.t.Helper()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	if err := wd.w.Run(ctx, true); err != nil {
		wd.t.Fatal(err)
	}
}

func TestWorkerCreatesVoiceAndLinesUnderLease(t *testing.T) {
	wd := newWorld(t)
	tok, id := wd.newVoice()
	wd.run()

	av := "toonfork-" + id
	f := wd.audio.voices[av]
	if f == nil || f["rights"] != "own" || f["source"] != "toonfork-app" || f["language"] != "cs" || f["replace"] != "true" {
		t.Fatalf("AiStack voice: %v", wd.audio.voices)
	}
	if !bytes.Equal(wd.audio.samples[av], m4a(10, "SAMPLE-AUDIO")) {
		t.Fatal("the decrypted sample reaches AiStack")
	}
	if code, m := wd.req("GET", "/v1/player/voices/"+id, tok, nil, ""); code != 200 || m["status"] != "ready" {
		t.Fatal(code, m)
	}
	if len(wd.broker.submitted) != 1 || len(wd.broker.done) != 1 {
		t.Fatalf("one lease, released: %v %v", wd.broker.submitted, wd.broker.done)
	}
	sub := wd.broker.submitted[0]
	st := sub["stages"].([]any)[0].(map[string]any)
	if sub["project"] != "webtoon" || st["mode"] != "lease" || st["services"].([]any)[0] != "tts" || sub["priority"].(float64) != 20 {
		t.Fatalf("lease request %v", sub)
	}

	body, _ := json.Marshal(map[string]any{"lang": "cs", "lines": []map[string]string{
		{"key": "a", "text": "„Ahoj,“ řekl robot. Pak odešel."}, {"key": "b", "text": "Druhá."}}})
	code, m := wd.req("POST", "/v1/player/voices/"+id+"/lines", tok, bytes.NewReader(body), "application/json")
	if code != 202 {
		t.Fatal(code, m)
	}
	job := m["job_id"].(string)
	wd.run()
	if len(wd.audio.tts) != 3 {
		t.Fatalf("two sentences + one: %+v", wd.audio.tts)
	}
	r := wd.audio.tts[0]
	if r.Text != "Ahoj, řekl robot." || r.Voice != av || r.Engine != "chatterbox" || r.Language != "cs" || r.CommercialOnly || r.Format != "wav" {
		t.Fatalf("tts request %+v", r)
	}
	code, m = wd.req("GET", "/v1/player/jobs/"+job, tok, nil, "")
	if code != 200 || m["status"] != "done" || len(m["lines"].([]any)) != 2 {
		t.Fatal(code, m)
	}
	l := m["lines"].([]any)[0].(map[string]any)
	if l["duration_s"].(float64) != 1.25 {
		t.Fatal(l)
	}
	resp, err := http.Get(wd.api.URL + l["url"].(string))
	if err != nil {
		t.Fatal(err)
	}
	got, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	if !bytes.Contains(got, []byte("WAV:Ahoj, řekl robot.|WAV:Pak odešel.")) {
		t.Fatalf("sentences joined into one line: %q", got)
	}
	if len(wd.broker.done) != 2 {
		t.Fatal("second lease released")
	}
	met := wd.broker.done[1]["metrics"].(map[string]any)["lines"].(map[string]any)
	if met["ok"].(float64) != 2 || met["failed"].(float64) != 0 {
		t.Fatalf("metrics %v", wd.broker.done[1])
	}

	// delete: the AiStack voice goes too
	if code, _ := wd.req("DELETE", "/v1/player/voices/"+id, tok, nil, ""); code != 204 {
		t.Fatal(code)
	}
	wd.run()
	if _, ok := wd.audio.voices[av]; ok {
		t.Fatal("AiStack voice deleted")
	}
	if _, err := wd.store.GetVoice(context.Background(), id); err == nil {
		t.Fatal("voice row removed")
	}
}

func TestWorkerRetriesWhenEngineIsDown(t *testing.T) {
	wd := newWorld(t)
	tok, id := wd.newVoice()
	wd.run()
	wd.audio.down = true
	body := `{"lang":"cs","lines":[{"key":"a","text":"Věta."}]}`
	_, m := wd.req("POST", "/v1/player/voices/"+id+"/lines", tok, strings.NewReader(body), "application/json")
	wd.run()
	code, st := wd.req("GET", "/v1/player/jobs/"+m["job_id"].(string), tok, nil, "")
	if code != 200 || st["status"] != "queued" {
		t.Fatalf("back in the queue: %v", st)
	}
	if n := len(wd.broker.done); n != 2 {
		t.Fatalf("the GPU is given back: %d", n)
	}
	wd.audio.down = false
	wd.now = wd.now.Add(time.Minute)
	wd.run()
	_, st = wd.req("GET", "/v1/player/jobs/"+m["job_id"].(string), tok, nil, "")
	if st["status"] != "done" {
		t.Fatal(st)
	}
}

func TestWorkerRedoesBadTakes(t *testing.T) {
	wd := newWorld(t)
	tok, id := wd.newVoice()
	wd.run()
	calls := 0
	wd.w.Measure = func(context.Context, string) (float64, float64, error) {
		calls++
		if calls == 1 {
			return 0.1, -20, nil // truncated
		}
		return 1.0, -20, nil
	}
	_, m := wd.req("POST", "/v1/player/voices/"+id+"/lines", tok, strings.NewReader(`{"lang":"cs","lines":[{"key":"a","text":"Dobrý den, pane."}]}`), "application/json")
	wd.run()
	if len(wd.audio.tts) != 2 || wd.audio.tts[0].Seed != nil || wd.audio.tts[1].Seed == nil || *wd.audio.tts[1].Seed != 1 {
		t.Fatalf("redo with a new seed: %+v", wd.audio.tts)
	}
	_, st := wd.req("GET", "/v1/player/jobs/"+m["job_id"].(string), tok, nil, "")
	if st["status"] != "done" {
		t.Fatal(st)
	}
	// a hopeless line is skipped, the job fails with the others kept
	wd.w.Measure = func(context.Context, string) (float64, float64, error) { return 1, -80, nil }
	_, m = wd.req("POST", "/v1/player/voices/"+id+"/lines", tok, strings.NewReader(`{"lang":"cs","lines":[{"key":"a","text":"Jiná věta."}]}`), "application/json")
	wd.run()
	_, st = wd.req("GET", "/v1/player/jobs/"+m["job_id"].(string), tok, nil, "")
	if st["status"] != "failed" || len(st["missing"].([]any)) != 1 {
		t.Fatal(st)
	}
}

func TestWorkerWithoutWorkTakesNoLease(t *testing.T) {
	wd := newWorld(t)
	wd.run()
	if len(wd.broker.submitted) != 0 {
		t.Fatal("no lease for an empty queue")
	}
}

func TestLeaseLostCancelsTask(t *testing.T) {
	wd := newWorld(t)
	wd.newVoice()
	wd.w.Broker.(*Broker).Beat = time.Millisecond
	l, err := wd.w.Broker.Acquire(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	wd.broker.mu.Lock()
	wd.broker.gone = true // the broker forgot the lease (orphaned, restarted)
	wd.broker.mu.Unlock()
	select {
	case <-l.Ctx().Done():
	case <-time.After(5 * time.Second):
		t.Fatal("lease context not cancelled")
	}
	if l.Usable() {
		t.Fatal("lost lease is not usable")
	}
	l.Release("")
}

func TestSentences(t *testing.T) {
	got := sentences(ttsText("„Ahoj!“ Řekl. Nahoru… a dolů. 3. května přišel."))
	want := []string{"Ahoj!", "Řekl.", "Nahoru… a dolů. 3. května přišel."}
	if strings.Join(got, "|") != strings.Join(want, "|") {
		t.Fatalf("%q", got)
	}
}

func TestRetryable(t *testing.T) {
	cases := map[error]bool{
		&AudioError{Status: 503}: true, &AudioError{Status: 429}: true, &AudioError{Status: 403}: false,
		&AudioError{Status: 422}: false, &HTTPError{Status: 502}: true, &HTTPError{Status: 409}: false,
		ErrLeaseLost: true, context.Canceled: true,
	}
	for err, want := range cases {
		if retryable(err) != want {
			t.Errorf("%v: %v", err, !want)
		}
	}
}

// TestEncodeLine runs the real ffmpeg chain when ffmpeg is installed (the worker image has it).
func TestEncodeLine(t *testing.T) {
	if _, err := exec.LookPath("ffmpeg"); err != nil {
		t.Skip("ffmpeg not installed")
	}
	dir := t.TempDir()
	in := filepath.Join(dir, "in.wav")
	// 0.5 s silence, 1.5 s tone at -30 dBFS-ish, 0.7 s silence
	if _, err := ffmpeg(context.Background(), "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=0.5",
		"-f", "lavfi", "-i", "sine=f=440:r=24000:d=1.5", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=0.7",
		"-filter_complex", "[1:a]volume=0.05[t];[0:a][t][2:a]concat=n=3:v=0:a=1", in); err != nil {
		t.Fatal(err)
	}
	out := filepath.Join(dir, "out.m4a")
	o := DefaultConfig().Encode
	d, err := EncodeLine(context.Background(), []string{in}, out, o)
	if err != nil {
		t.Fatal(err)
	}
	if d < 1.4 || d > 1.75 {
		t.Fatalf("silence trimmed: %.2f s", d)
	}
	l, err := Loudness(context.Background(), out)
	if err != nil || l < -17.5 || l > -14.5 {
		t.Fatalf("loudnorm -16 LUFS: %.1f %v", l, err)
	}
	b, _ := os.ReadFile(out)
	if len(b) < 12 || string(b[4:8]) != "ftyp" {
		t.Fatal("m4a container")
	}
	silent := filepath.Join(dir, "silent.wav")
	ffmpeg(context.Background(), "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono:d=1", silent) //nolint:errcheck
	if _, err := EncodeLine(context.Background(), []string{silent}, filepath.Join(dir, "s.m4a"), o); err == nil {
		t.Fatal("silence is rejected")
	}
}
