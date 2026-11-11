package voice

import (
	"bytes"
	"context"
	"encoding/binary"
	"encoding/json"
	"io"
	"log/slog"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/ol1n/webtoon/backend/internal/voice/receipt"
)

const workerToken = "worker-secret"

var t0 = time.Date(2026, 11, 11, 10, 0, 0, 0, time.UTC)

type env struct {
	t   *testing.T
	srv *Server
	st  *MemStore
	h   http.Handler
	now time.Time
	cfg Config
}

func quietLog() *slog.Logger { return slog.New(slog.NewTextHandler(io.Discard, nil)) }

func testVerifier(t *testing.T, c receipt.Config) ReceiptVerifier {
	t.Helper()
	if c.Mode == "" {
		c.Mode = receipt.ModeTest
	}
	v, err := receipt.New(c, quietLog())
	if err != nil {
		t.Fatal(err)
	}
	return v
}

func newEnv(t *testing.T, mut func(*Config), rv ReceiptVerifier) *env {
	t.Helper()
	e := &env{t: t, st: NewMemStore(), now: t0}
	e.cfg = Config{DataDir: t.TempDir(), DataKey: bytes.Repeat([]byte{7}, 32), WorkerToken: workerToken,
		PublicURL: "https://api.example.test", DailyLines: 50}
	if mut != nil {
		mut(&e.cfg)
	}
	if rv == nil {
		rv = testVerifier(t, receipt.Config{})
	}
	srv, err := New(e.cfg, e.st, rv, func() time.Time { return e.now }, quietLog())
	if err != nil {
		t.Fatal(err)
	}
	e.srv = srv
	mux := http.NewServeMux()
	srv.Register(mux)
	e.h = mux
	return e
}

// --- fixtures ----------------------------------------------------------------------------

func box(typ string, payload []byte) []byte {
	b := make([]byte, 8, 8+len(payload))
	binary.BigEndian.PutUint32(b, uint32(8+len(payload)))
	copy(b[4:], typ)
	return append(b, payload...)
}

const marker = "PLAINTEXT-VOICE-MARKER"

// m4a is a minimal ISO BMFF file with an mvhd of the given duration and a recognizable mdat.
func m4a(seconds float64) []byte {
	mvhd := make([]byte, 100)
	binary.BigEndian.PutUint32(mvhd[12:16], 1000)
	binary.BigEndian.PutUint32(mvhd[16:20], uint32(seconds*1000))
	out := box("ftyp", []byte("M4A \x00\x00\x00\x00M4A mp42isom"))
	out = append(out, box("mdat", []byte(strings.Repeat(marker, 20)))...)
	return append(out, box("moov", box("mvhd", mvhd))...)
}

func wav(seconds float64) []byte {
	const rate = 16000
	data := make([]byte, int(seconds*rate)*2)
	var b bytes.Buffer
	b.WriteString("RIFF")
	binary.Write(&b, binary.LittleEndian, uint32(36+len(data))) //nolint:errcheck
	b.WriteString("WAVEfmt ")
	for _, v := range []any{uint32(16), uint16(1), uint16(1), uint32(rate), uint32(rate * 2), uint16(2), uint16(16)} {
		binary.Write(&b, binary.LittleEndian, v) //nolint:errcheck
	}
	b.WriteString("data")
	binary.Write(&b, binary.LittleEndian, uint32(len(data))) //nolint:errcheck
	b.Write(data)
	return b.Bytes()
}

// --- request helpers --------------------------------------------------------------------

func (e *env) do(method, path, token string, body io.Reader, ctype string) *httptest.ResponseRecorder {
	e.t.Helper()
	r := httptest.NewRequest(method, path, body)
	r.Host = "api.local.test"
	if token != "" {
		r.Header.Set("Authorization", "Bearer "+token)
	}
	if ctype != "" {
		r.Header.Set("Content-Type", ctype)
	}
	rec := httptest.NewRecorder()
	e.h.ServeHTTP(rec, r)
	return rec
}

func (e *env) json(method, path, token string, v any) *httptest.ResponseRecorder {
	e.t.Helper()
	var body io.Reader
	if v != nil {
		b, _ := json.Marshal(v)
		body = bytes.NewReader(b)
	}
	return e.do(method, path, token, body, "application/json")
}

func decodeBody(t *testing.T, rec *httptest.ResponseRecorder) map[string]any {
	t.Helper()
	var m map[string]any
	if err := json.Unmarshal(rec.Body.Bytes(), &m); err != nil {
		t.Fatalf("body %q: %v", rec.Body.String(), err)
	}
	return m
}

func expect(t *testing.T, rec *httptest.ResponseRecorder, status int, code string) map[string]any {
	t.Helper()
	if rec.Code != status {
		t.Fatalf("status %d, want %d: %s", rec.Code, status, rec.Body.String())
	}
	if code == "" {
		if rec.Body.Len() == 0 {
			return nil
		}
		return decodeBody(t, rec)
	}
	m := decodeBody(t, rec)
	if m["error"] != code {
		t.Fatalf("error %v, want %s: %s", m["error"], code, rec.Body.String())
	}
	return m
}

func (e *env) device() string {
	e.t.Helper()
	m := expect(e.t, e.json("POST", "/v1/player/devices", "", map[string]string{"platform": "ios"}), 201, "")
	return m["token"].(string)
}

type form map[string]string

func (e *env) upload(token string, sample []byte, f form) *httptest.ResponseRecorder {
	e.t.Helper()
	var b bytes.Buffer
	mw := multipart.NewWriter(&b)
	for k, v := range f {
		mw.WriteField(k, v) //nolint:errcheck
	}
	if sample != nil {
		fw, _ := mw.CreateFormFile("sample", "sample.m4a")
		fw.Write(sample) //nolint:errcheck
	}
	mw.Close()
	return e.do("POST", "/v1/player/voices", token, &b, mw.FormDataContentType())
}

func okForm() form {
	return form{"consent": "true", "consent_text": "Já, Olin, souhlasím s vytvořením svého hlasu.", "receipt": "test:tx-1"}
}

func (e *env) voice(token string) string {
	e.t.Helper()
	m := expect(e.t, e.upload(token, m4a(12), okForm()), 201, "")
	return m["voice_id"].(string)
}

func (e *env) claim() (*WorkerTask, int) {
	e.t.Helper()
	r := httptest.NewRequest("POST", "/v1/worker/voice-tasks/claim", strings.NewReader(`{"worker":"w1"}`))
	r.Header.Set("Authorization", "Bearer "+workerToken)
	rec := httptest.NewRecorder()
	e.h.ServeHTTP(rec, r)
	if rec.Code == 204 {
		return nil, 204
	}
	if rec.Code != 200 {
		e.t.Fatalf("claim: %d %s", rec.Code, rec.Body.String())
	}
	var wt WorkerTask
	json.Unmarshal(rec.Body.Bytes(), &wt) //nolint:errcheck
	return &wt, 200
}

func (e *env) complete(id string, body string) *httptest.ResponseRecorder {
	return e.do("POST", "/v1/worker/voice-tasks/"+id+"/complete", workerToken, strings.NewReader(body), "application/json")
}

func (e *env) readyVoice(token string) string {
	e.t.Helper()
	id := e.voice(token)
	wt, _ := e.claim()
	if wt == nil || wt.Kind != KindVoiceCreate || wt.VoiceID != id {
		e.t.Fatalf("claim %+v", wt)
	}
	expect(e.t, e.complete(wt.TaskID, `{"worker":"w1","ok":true}`), 204, "")
	return id
}

func (e *env) putLine(voiceID, hash string) *httptest.ResponseRecorder {
	r := httptest.NewRequest("PUT", "/v1/worker/voices/"+voiceID+"/lines/"+hash, bytes.NewReader(m4a(1.5)))
	r.Header.Set("Authorization", "Bearer "+workerToken)
	r.Header.Set("X-Duration-S", "1.5")
	r.Header.Set("X-Lang", "cs")
	rec := httptest.NewRecorder()
	e.h.ServeHTTP(rec, r)
	return rec
}

func lines(n int, prefix string) map[string]any {
	var ls []map[string]string
	for i := range n {
		ls = append(ls, map[string]string{"key": prefix + string(rune('a'+i%26)) + string(rune('a'+i/26)), "text": "Věta číslo " + prefix + string(rune('A'+i%26)) + string(rune('A'+i/26)) + "."})
	}
	return map[string]any{"lang": "cs", "lines": ls}
}

// --- tests -------------------------------------------------------------------------------

func TestDeviceAuth(t *testing.T) {
	e := newEnv(t, nil, nil)
	expect(t, e.json("GET", "/v1/player/voices/00000000-0000-4000-8000-000000000000", "", nil), 401, "unauthorized")
	expect(t, e.json("GET", "/v1/player/voices/00000000-0000-4000-8000-000000000000", "nope", nil), 401, "unauthorized")
	tok := e.device()
	expect(t, e.json("GET", "/v1/player/voices/00000000-0000-4000-8000-000000000000", tok, nil), 404, "not_found")
	for _, d := range e.st.devices {
		if d.TokenHash == tok || d.TokenHash != SHA256Hex(tok) {
			t.Fatal("only the token hash is stored")
		}
	}
}

func TestDeviceRateLimit(t *testing.T) {
	e := newEnv(t, func(c *Config) { c.DeviceRate = 2 }, nil)
	e.device()
	e.device()
	expect(t, e.json("POST", "/v1/player/devices", "", nil), 429, "rate_limited")
	e.now = e.now.Add(time.Hour)
	e.device()
}

func TestCreateVoiceValidation(t *testing.T) {
	e := newEnv(t, nil, nil)
	tok := e.device()
	f := okForm()
	f["consent"] = "false"
	expect(t, e.upload(tok, m4a(10), f), 400, "consent_required")
	f = okForm()
	delete(f, "receipt")
	expect(t, e.upload(tok, m4a(10), f), 400, "invalid_request")
	expect(t, e.upload(tok, []byte("not audio at all"), okForm()), 415, "sample_format")
	expect(t, e.upload(tok, m4a(3), okForm()), 400, "sample_invalid")
	expect(t, e.upload(tok, m4a(31), okForm()), 400, "sample_invalid")
	expect(t, e.upload(tok, bytes.Repeat([]byte{0}, MaxSampleBytes+10), okForm()), 413, "sample_too_large")
	f = okForm()
	f["receipt"] = "garbage"
	expect(t, e.upload(tok, m4a(10), f), 402, "receipt_invalid")
	expect(t, e.upload(tok, wav(6), okForm()), 201, "")
}

func TestCreateVoiceStoresEncryptedSampleAndConsent(t *testing.T) {
	e := newEnv(t, nil, nil)
	tok := e.device()
	f := okForm()
	f["consent_version"] = "2026-11"
	m := expect(t, e.upload(tok, m4a(12), f), 201, "")
	id := m["voice_id"].(string)
	if m["status"] != StatusQueued || !isUUID(id) {
		t.Fatalf("%v", m)
	}
	v := e.st.voices[id]
	raw, err := os.ReadFile(filepath.Join(e.cfg.DataDir, v.SampleFile))
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.HasPrefix(raw, []byte(boxMagic)) || bytes.Contains(raw, []byte(marker)) {
		t.Fatal("sample must be encrypted at rest")
	}
	if fi, _ := os.Stat(filepath.Join(e.cfg.DataDir, v.SampleFile)); fi.Mode().Perm() != 0o600 {
		t.Fatalf("sample mode %v", fi.Mode())
	}
	c := e.st.consents[id]
	if c.Text != f["consent_text"] || c.SHA256 != SHA256Hex(f["consent_text"]) || c.Version != "2026-11" || !c.ConsentedAt.Equal(t0) {
		t.Fatalf("consent %+v", c)
	}
	if v.ReceiptPlatform != receipt.PlatformTest || v.ReceiptOrigID != "tx-1" {
		t.Fatalf("receipt %+v", v)
	}
	// one voice per device
	expect(t, e.upload(tok, m4a(12), okForm()), 409, "voice_exists")
	got := expect(t, e.json("GET", "/v1/player/voices/"+id, tok, nil), 200, "")
	if got["status"] != StatusQueued {
		t.Fatal(got)
	}
	// another device does not see it
	expect(t, e.json("GET", "/v1/player/voices/"+id, e.device(), nil), 404, "not_found")
}

func TestReceiptFailClosed(t *testing.T) {
	// store mode without App Store / Play credentials: no voice, a clear error, no bypass
	e := newEnv(t, nil, testVerifier(t, receipt.Config{Mode: receipt.ModeStore}))
	tok := e.device()
	f := okForm()
	f["receipt"] = "eyJhbGciOiJFUzI1NiIsIng1YyI6WyJBQUFBIl19.e30.c2ln"
	expect(t, e.upload(tok, m4a(10), f), 503, "receipt_verification_unavailable")
	f["receipt"] = "test:tx-1"
	expect(t, e.upload(tok, m4a(10), f), 503, "receipt_verification_unavailable")
	if len(e.st.voices) != 0 {
		t.Fatal("no voice without a verified purchase")
	}
}

func TestReceiptTestModeRefusedOnProductionHost(t *testing.T) {
	e := newEnv(t, nil, nil)
	tok := e.device()
	var b bytes.Buffer
	mw := multipart.NewWriter(&b)
	for k, v := range okForm() {
		mw.WriteField(k, v) //nolint:errcheck
	}
	fw, _ := mw.CreateFormFile("sample", "s.m4a")
	fw.Write(m4a(10)) //nolint:errcheck
	mw.Close()
	r := httptest.NewRequest("POST", "/v1/player/voices", &b)
	r.Host = "webtoon-api.ol1n.com"
	r.Header.Set("Authorization", "Bearer "+tok)
	r.Header.Set("Content-Type", mw.FormDataContentType())
	rec := httptest.NewRecorder()
	e.h.ServeHTTP(rec, r)
	expect(t, rec, 503, "receipt_verification_unavailable")

	// VOICE_PUBLIC_URL on the production host disables test mode for every request
	e2 := newEnv(t, nil, testVerifier(t, receipt.Config{PublicURL: "https://webtoon-api.ol1n.com"}))
	expect(t, e2.upload(e2.device(), m4a(10), okForm()), 503, "receipt_verification_unavailable")
}

func TestReceiptDeviceLimit(t *testing.T) {
	e := newEnv(t, nil, nil)
	e.srv.ReceiptMaxDevices = 2
	e.voice(e.device())
	e.voice(e.device())
	expect(t, e.upload(e.device(), m4a(10), okForm()), 403, "receipt_in_use")
}

func TestVoicesDisabledWithoutKey(t *testing.T) {
	e := newEnv(t, func(c *Config) { c.DataKey = nil }, nil)
	tok := e.device()
	expect(t, e.upload(tok, m4a(10), okForm()), 503, "voice_unavailable")
	expect(t, e.json("POST", "/v1/worker/voice-tasks/claim", workerToken, map[string]string{"worker": "w"}), 503, "worker_unavailable")
}

func TestWorkerAuth(t *testing.T) {
	e := newEnv(t, nil, nil)
	expect(t, e.json("GET", "/v1/worker/voice-tasks/pending", "", nil), 401, "unauthorized")
	expect(t, e.json("GET", "/v1/worker/voice-tasks/pending", e.device(), nil), 401, "unauthorized")
	m := expect(t, e.json("GET", "/v1/worker/voice-tasks/pending", workerToken, nil), 200, "")
	if m["pending"].(float64) != 0 {
		t.Fatal(m)
	}
	e2 := newEnv(t, func(c *Config) { c.WorkerToken = "" }, nil)
	expect(t, e2.json("GET", "/v1/worker/voice-tasks/pending", "", nil), 503, "worker_unavailable")
}

func TestVoiceCreateTaskAndSample(t *testing.T) {
	e := newEnv(t, nil, nil)
	tok := e.device()
	sample := m4a(12)
	expect(t, e.upload(tok, sample, okForm()), 201, "")
	wt, _ := e.claim()
	if wt.Kind != KindVoiceCreate || wt.AudioVoice != "toonfork-"+wt.VoiceID || wt.SampleExt != "m4a" {
		t.Fatalf("%+v", wt)
	}
	if _, code := e.claim(); code != 204 {
		t.Fatal("a running task is not claimed twice")
	}
	rec := e.do("GET", "/v1/worker/voices/"+wt.VoiceID+"/sample", workerToken, nil, "")
	if rec.Code != 200 || !bytes.Equal(rec.Body.Bytes(), sample) || rec.Header().Get("Content-Type") != "audio/mp4" {
		t.Fatalf("sample %d %s", rec.Code, rec.Header())
	}
	// engine down: back to the queue with a delay
	expect(t, e.complete(wt.TaskID, `{"worker":"w1","ok":false,"retry":true,"error":"audio tts: HTTP 503"}`), 204, "")
	if _, code := e.claim(); code != 204 {
		t.Fatal("retry waits")
	}
	e.now = e.now.Add(31 * time.Second)
	wt2, _ := e.claim()
	if wt2 == nil || wt2.TaskID != wt.TaskID || wt2.Attempt != 2 {
		t.Fatalf("%+v", wt2)
	}
	expect(t, e.complete(wt.TaskID, `{"worker":"other","ok":true}`), 409, "lease_lost")
	expect(t, e.complete(wt.TaskID, `{"worker":"w1","ok":false,"error":"sample too short"}`), 204, "")
	got := expect(t, e.json("GET", "/v1/player/voices/"+wt.VoiceID, tok, nil), 200, "")
	if got["status"] != StatusFailed || got["error"] != "sample too short" {
		t.Fatal(got)
	}
	expect(t, e.json("POST", "/v1/player/voices/"+wt.VoiceID+"/lines", tok, lines(1, "x")), 409, "voice_failed")
}

func TestExpiredTaskLeaseIsReclaimed(t *testing.T) {
	e := newEnv(t, nil, nil)
	e.voice(e.device())
	wt, _ := e.claim()
	expect(t, e.do("POST", "/v1/worker/voice-tasks/"+wt.TaskID+"/heartbeat", workerToken, strings.NewReader(`{"worker":"w1"}`), ""), 204, "")
	e.now = e.now.Add(11 * time.Minute)
	wt2, _ := e.claim()
	if wt2 == nil || wt2.TaskID != wt.TaskID {
		t.Fatal("expired lease must be reclaimed")
	}
}

func TestLinesValidation(t *testing.T) {
	e := newEnv(t, nil, nil)
	tok := e.device()
	id := e.voice(tok)
	path := "/v1/player/voices/" + id + "/lines"
	expect(t, e.json("POST", path, tok, lines(1, "a")), 409, "voice_not_ready")
	wt, _ := e.claim()
	expect(t, e.complete(wt.TaskID, `{"worker":"w1","ok":true}`), 204, "")

	expect(t, e.json("POST", path, tok, lines(201, "a")), 400, "too_many_lines")
	expect(t, e.json("POST", path, tok, map[string]any{"lang": "cs", "lines": []any{}}), 400, "invalid_request")
	expect(t, e.json("POST", path, tok, map[string]any{"lang": "de", "lines": []map[string]string{{"key": "a", "text": "Hallo"}}}), 400, "unsupported_lang")
	expect(t, e.json("POST", path, tok, map[string]any{"lang": "cs", "lines": []map[string]string{{"key": "a", "text": strings.Repeat("á", 301)}}}), 400, "line_too_long")
	expect(t, e.json("POST", path, tok, map[string]any{"lang": "cs", "lines": []map[string]string{{"key": "a", "text": strings.Repeat("á", 300)}}}), 202, "")
	expect(t, e.json("POST", path, tok, map[string]any{"lang": "cs", "lines": []map[string]string{{"key": "a", "text": "x"}, {"key": "a", "text": "y"}}}), 400, "invalid_request")
	expect(t, e.json("POST", path, tok, map[string]any{"lang": "cs", "lines": []map[string]string{{"key": "a", "text": "  "}}}), 400, "invalid_request")
	expect(t, e.json("POST", path, e.device(), lines(1, "a")), 404, "not_found")
}

func TestLinesFlowCacheAndSignedURLs(t *testing.T) {
	e := newEnv(t, nil, nil)
	tok := e.device()
	id := e.readyVoice(tok)
	path := "/v1/player/voices/" + id + "/lines"
	req := map[string]any{"lang": "cs", "lines": []map[string]string{
		{"key": "p1", "text": "Ahoj,   světe!"}, {"key": "p2", "text": "Druhá věta."}, {"key": "p3", "text": "Ahoj, světe!"}}}
	m := expect(t, e.json("POST", path, tok, req), 202, "")
	job := m["job_id"].(string)
	if m["status"] != TaskQueued {
		t.Fatal(m)
	}
	// the same request while it waits: the same job, no extra quota
	m2 := expect(t, e.json("POST", path, tok, req), 202, "")
	if m2["job_id"] != job || e.st.quota[[2]string{e.st.voices[id].DeviceID, "2026-11-11"}] != 2 {
		t.Fatalf("idempotent: %v quota %v", m2, e.st.quota)
	}
	st := expect(t, e.json("GET", "/v1/player/jobs/"+job, tok, nil), 200, "")
	if st["status"] != TaskQueued || st["done"].(float64) != 0 || st["total"].(float64) != 3 {
		t.Fatal(st)
	}
	wt, _ := e.claim()
	if wt.Kind != KindLines || len(wt.Lines) != 2 || wt.Lang != "cs" {
		t.Fatalf("one worker line per unique text: %+v", wt)
	}
	if wt.Lines[0].Text != "Ahoj, světe!" || wt.Lines[0].Hash != LineHash(id, "cs", "Ahoj, světe!") {
		t.Fatalf("%+v", wt.Lines[0])
	}
	expect(t, e.putLine(id, wt.Lines[0].Hash), 204, "")
	// partial result while running
	st = expect(t, e.json("GET", "/v1/player/jobs/"+job, tok, nil), 200, "")
	if st["status"] != TaskRunning || st["done"].(float64) != 2 {
		t.Fatal(st)
	}
	expect(t, e.putLine(id, wt.Lines[1].Hash), 204, "")
	expect(t, e.complete(wt.TaskID, `{"worker":"w1","ok":true}`), 204, "")
	st = expect(t, e.json("GET", "/v1/player/jobs/"+job, tok, nil), 200, "")
	ls := st["lines"].([]any)
	if st["status"] != TaskDone || len(ls) != 3 || len(st["missing"].([]any)) != 0 {
		t.Fatal(st)
	}
	l1, l3 := ls[0].(map[string]any), ls[2].(map[string]any)
	if l1["key"] != "p1" || l1["url"] != l3["url"] || l1["duration_s"].(float64) != 1.5 {
		t.Fatalf("same text, same URL: %v %v", l1, l3)
	}
	u, _ := url.Parse(l1["url"].(string))
	if u.Host != "api.example.test" {
		t.Fatal(u)
	}
	rec := e.do("GET", u.RequestURI(), "", nil, "")
	if rec.Code != 200 || !bytes.Equal(rec.Body.Bytes(), m4a(1.5)) || rec.Header().Get("Content-Type") != "audio/mp4" {
		t.Fatalf("line %d", rec.Code)
	}
	raw, _ := os.ReadFile(filepath.Join(e.cfg.DataDir, linePath(id, wt.Lines[0].Hash)))
	if bytes.Contains(raw, []byte(marker)) {
		t.Fatal("lines are encrypted at rest")
	}
	// tampered or expired URL
	q := u.Query()
	q.Set("sig", strings.Repeat("0", 32))
	expect(t, e.do("GET", u.Path+"?"+q.Encode(), "", nil, ""), 403, "url_expired")
	e.now = e.now.Add(76 * time.Minute)
	expect(t, e.do("GET", u.RequestURI(), "", nil, ""), 403, "url_expired")

	// cached lines: a new request is done at once and costs no quota
	e.now = t0.Add(5 * time.Minute)
	m3 := expect(t, e.json("POST", path, tok, map[string]any{"lang": "cs", "lines": []map[string]string{{"key": "other", "text": "Druhá   věta."}}}), 202, "")
	if m3["status"] != TaskDone {
		t.Fatal(m3)
	}
	st = expect(t, e.json("GET", "/v1/player/jobs/"+m3["job_id"].(string), tok, nil), 200, "")
	if ls[1].(map[string]any)["url"] != st["lines"].([]any)[0].(map[string]any)["url"] {
		t.Fatal("same line, same URL within the bucket")
	}
	// another device cannot read the job
	expect(t, e.json("GET", "/v1/player/jobs/"+job, e.device(), nil), 404, "not_found")
}

func TestLinesPartialFailure(t *testing.T) {
	e := newEnv(t, nil, nil)
	tok := e.device()
	id := e.readyVoice(tok)
	m := expect(t, e.json("POST", "/v1/player/voices/"+id+"/lines", tok, lines(2, "f")), 202, "")
	wt, _ := e.claim()
	expect(t, e.putLine(id, wt.Lines[0].Hash), 204, "")
	expect(t, e.complete(wt.TaskID, `{"worker":"w1","ok":false,"error":"1 of 2 lines failed"}`), 204, "")
	st := expect(t, e.json("GET", "/v1/player/jobs/"+m["job_id"].(string), tok, nil), 200, "")
	if st["status"] != TaskFailed || len(st["lines"].([]any)) != 1 || len(st["missing"].([]any)) != 1 || st["error"] == nil {
		t.Fatal(st)
	}
}

func TestDailyQuota(t *testing.T) {
	e := newEnv(t, func(c *Config) { c.DailyLines = 5 }, nil)
	tok := e.device()
	id := e.readyVoice(tok)
	path := "/v1/player/voices/" + id + "/lines"
	expect(t, e.json("POST", path, tok, lines(3, "a")), 202, "")
	m := expect(t, e.json("POST", path, tok, lines(3, "b")), 429, "quota_exceeded")
	if m["used"].(float64) != 3 || m["limit"].(float64) != 5 || m["resets_at"] != "2026-11-12T00:00:00Z" {
		t.Fatal(m)
	}
	expect(t, e.json("POST", path, tok, lines(2, "c")), 202, "")
	expect(t, e.json("POST", path, tok, lines(1, "d")), 429, "quota_exceeded")
	e.now = e.now.Add(24 * time.Hour)
	expect(t, e.json("POST", path, tok, lines(5, "e")), 202, "")
}

func TestDeleteVoice(t *testing.T) {
	e := newEnv(t, nil, nil)
	tok := e.device()
	id := e.readyVoice(tok)
	m := expect(t, e.json("POST", "/v1/player/voices/"+id+"/lines", tok, lines(2, "z")), 202, "")
	wt, _ := e.claim()
	expect(t, e.putLine(id, wt.Lines[0].Hash), 204, "")
	st := expect(t, e.json("GET", "/v1/player/jobs/"+m["job_id"].(string), tok, nil), 200, "")
	lineURL, _ := url.Parse(st["lines"].([]any)[0].(map[string]any)["url"].(string))

	expect(t, e.json("DELETE", "/v1/player/voices/"+id, e.device(), nil), 404, "not_found")
	expect(t, e.json("DELETE", "/v1/player/voices/"+id, tok, nil), 204, "")
	if _, err := os.Stat(filepath.Join(e.cfg.DataDir, "voices", id)); !os.IsNotExist(err) {
		t.Fatal("sample and lines must be gone at once")
	}
	expect(t, e.json("GET", "/v1/player/voices/"+id, tok, nil), 404, "not_found")
	expect(t, e.json("GET", "/v1/player/jobs/"+m["job_id"].(string), tok, nil), 404, "not_found")
	expect(t, e.do("GET", lineURL.RequestURI(), "", nil, ""), 404, "not_found")
	expect(t, e.do("GET", "/v1/worker/voices/"+id+"/sample", workerToken, nil, ""), 409, "voice_deleting")
	// the running lines task is cancelled: the worker loses its lease
	expect(t, e.do("POST", "/v1/worker/voice-tasks/"+wt.TaskID+"/heartbeat", workerToken, strings.NewReader(`{"worker":"w1"}`), ""), 409, "lease_lost")
	expect(t, e.putLine(id, wt.Lines[1].Hash), 409, "voice_deleting")
	// the device may record a new voice right away
	expect(t, e.upload(tok, m4a(10), okForm()), 201, "")

	del, _ := e.claim()
	if del.Kind != KindVoiceDelete || del.VoiceID != id || del.AudioVoice != "toonfork-"+id {
		t.Fatalf("delete first (priority): %+v", del)
	}
	expect(t, e.complete(del.TaskID, `{"worker":"w1","ok":true}`), 204, "")
	if _, ok := e.st.voices[id]; ok {
		t.Fatal("row removed after the AiStack delete")
	}
	c := e.st.consents[id]
	if c.DeletedAt == nil || c.DeleteReason != "user" || c.Text == "" {
		t.Fatalf("consent record stays as proof: %+v", c)
	}
}

func TestDeleteDevice(t *testing.T) {
	e := newEnv(t, nil, nil)
	tok := e.device()
	id := e.voice(tok)
	expect(t, e.json("DELETE", "/v1/player/devices/me", tok, nil), 204, "")
	expect(t, e.json("GET", "/v1/player/voices/"+id, tok, nil), 401, "unauthorized")
	if e.st.voices[id].Status != StatusDeleting || e.st.consents[id].DeleteReason != "device_deleted" {
		t.Fatal("device deletion deletes the voice")
	}
}

func TestPurgeInactive(t *testing.T) {
	e := newEnv(t, nil, nil)
	tok := e.device()
	id := e.readyVoice(tok)
	idle := e.device() // never records a voice
	_ = idle
	e.now = t0.Add(179 * 24 * time.Hour)
	expect(t, e.json("GET", "/v1/player/voices/"+id, tok, nil), 200, "") // use keeps it
	if err := e.srv.Purge(context.Background()); err != nil {
		t.Fatal(err)
	}
	if e.st.voices[id].Status != StatusReady || len(e.st.devices) != 2 {
		t.Fatal("nothing is stale yet")
	}
	e.now = e.now.Add(181 * 24 * time.Hour)
	// a stray directory of a vanished voice is swept too
	stray := filepath.Join(e.cfg.DataDir, "voices", "11111111-1111-4111-8111-111111111111")
	os.MkdirAll(stray, 0o700) //nolint:errcheck
	if err := e.srv.Purge(context.Background()); err != nil {
		t.Fatal(err)
	}
	if e.st.voices[id].Status != StatusDeleting || e.st.consents[id].DeleteReason != "inactive" {
		t.Fatalf("inactive voice deleted: %+v", e.st.voices[id])
	}
	if _, err := os.Stat(filepath.Join(e.cfg.DataDir, "voices", id)); !os.IsNotExist(err) {
		t.Fatal("files removed")
	}
	if _, err := os.Stat(stray); !os.IsNotExist(err) {
		t.Fatal("stray dir swept")
	}
	if len(e.st.devices) != 0 {
		t.Fatalf("stale devices removed: %v", e.st.devices)
	}
	del, _ := e.claim()
	if del == nil || del.Kind != KindVoiceDelete {
		t.Fatal("AiStack delete queued")
	}
	e.now = e.now.Add(366 * 24 * time.Hour)
	if err := e.srv.Purge(context.Background()); err != nil {
		t.Fatal(err)
	}
	if _, ok := e.st.consents[id]; ok {
		t.Fatal("consent record dropped after its retention")
	}
}

func TestRetentionIsConfigurable(t *testing.T) {
	e := newEnv(t, func(c *Config) { c.Retention = 30 * 24 * time.Hour }, nil)
	id := e.voice(e.device())
	e.now = t0.Add(31 * 24 * time.Hour)
	if err := e.srv.Purge(context.Background()); err != nil {
		t.Fatal(err)
	}
	if e.st.voices[id].Status != StatusDeleting {
		t.Fatal("30-day retention")
	}
}

func TestLineHashNormalization(t *testing.T) {
	a := LineHash("v", "cs", "  Ahoj\n  světe ")
	if a != LineHash("v", "cs", "Ahoj světe") || a != LineHash("v", "cs", "Ahoj světu"[:0]+"Ahoj světe") {
		t.Fatal("whitespace and NFC")
	}
	if NormalizeText("ě") != "ě" {
		t.Fatal("NFC")
	}
	if a == LineHash("v", "en", "Ahoj světe") || a == LineHash("w", "cs", "Ahoj světe") {
		t.Fatal("voice and lang are part of the key")
	}
}

func TestAudioDuration(t *testing.T) {
	if d, err := AudioDuration("m4a", m4a(12.5)); err != nil || d != 12.5 {
		t.Fatal(d, err)
	}
	if d, err := AudioDuration("wav", wav(6)); err != nil || d != 6 {
		t.Fatal(d, err)
	}
	// mvhd version 1 (64-bit times)
	mvhd := make([]byte, 112)
	mvhd[0] = 1
	binary.BigEndian.PutUint32(mvhd[20:24], 48000)
	binary.BigEndian.PutUint64(mvhd[24:32], 48000*7)
	f := append(box("ftyp", []byte("M4A ")), box("moov", box("mvhd", mvhd))...)
	if d, err := AudioDuration("m4a", f); err != nil || d != 7 {
		t.Fatal(d, err)
	}
	if _, err := AudioDuration("m4a", box("ftyp", []byte("M4A "))); err == nil {
		t.Fatal("no moov")
	}
	if _, err := AudioDuration("m4a", []byte{0, 0, 0, 99, 'f', 't', 'y', 'p'}); err == nil {
		t.Fatal("truncated box")
	}
}

func TestBoxBindsPath(t *testing.T) {
	dir := t.TempDir()
	b, _ := NewBox(bytes.Repeat([]byte{1}, 32), dir)
	if err := b.Write("voices/a/sample.m4a.enc", []byte("secret")); err != nil {
		t.Fatal(err)
	}
	got, err := b.Read("voices/a/sample.m4a.enc")
	if err != nil || string(got) != "secret" {
		t.Fatal(got, err)
	}
	os.MkdirAll(filepath.Join(dir, "voices/b"), 0o700)                                                      //nolint:errcheck
	os.Rename(filepath.Join(dir, "voices/a/sample.m4a.enc"), filepath.Join(dir, "voices/b/sample.m4a.enc")) //nolint:errcheck
	if _, err := b.Read("voices/b/sample.m4a.enc"); err == nil {
		t.Fatal("a file moved to another voice must not decrypt")
	}
	other, _ := NewBox(bytes.Repeat([]byte{2}, 32), dir)
	b.Write("x.enc", []byte("secret")) //nolint:errcheck
	if _, err := other.Read("x.enc"); err == nil {
		t.Fatal("wrong key")
	}
}

func TestConfigFromEnvRejectsBadKey(t *testing.T) {
	t.Setenv("VOICE_DATA_KEY", "abc")
	if _, err := ConfigFromEnv(); err == nil || strings.Contains(err.Error(), "abc") {
		t.Fatalf("bad key is an error that never echoes the value: %v", err)
	}
	t.Setenv("VOICE_DATA_KEY", strings.Repeat("ab", 32))
	t.Setenv("VOICE_RETENTION_DAYS", "90")
	c, err := ConfigFromEnv()
	if err != nil || len(c.DataKey) != 32 || c.Retention != 90*24*time.Hour || c.DailyLines != 300 || c.MaxLines != 200 || c.MaxChars != 300 {
		t.Fatalf("%+v %v", c, err)
	}
}
