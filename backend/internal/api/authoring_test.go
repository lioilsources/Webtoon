package api

import (
	"bytes"
	"encoding/json"
	"errors"
	"mime/multipart"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/fakes"
)

func code(err error) int {
	var he *httpErr
	if errors.As(err, &he) {
		return he.code
	}
	return 0
}

func TestNormalizeCanon(t *testing.T) {
	raw := json.RawMessage(`{"nodes": [{"text": "a"}, {"id": "n1", "text": " b "}, {"text": "c"}], "constraints": [" x ", "", null, {"k": 1}], "extra": true}`)
	out, err := normalizeCanon(raw)
	if err != nil {
		t.Fatal(err)
	}
	var got struct {
		Nodes       []domain.CanonNode `json:"nodes"`
		Constraints []any              `json:"constraints"`
		Extra       bool               `json:"extra"`
	}
	json.Unmarshal(out, &got) //nolint:errcheck
	// "n1" is taken by the second node, so the new ones get n2, n3 — order is preserved.
	if len(got.Nodes) != 3 || got.Nodes[0].ID != "n2" || got.Nodes[1].ID != "n1" || got.Nodes[1].Text != "b" || got.Nodes[2].ID != "n3" {
		t.Fatalf("nodes %+v", got.Nodes)
	}
	if len(got.Constraints) != 2 || got.Constraints[0] != "x" || !got.Extra {
		t.Fatalf("constraints %+v extra %v", got.Constraints, got.Extra)
	}
	for _, bad := range []string{`[]`, `{"nodes": [{"id": "a", "text": "x"}, {"id": "a", "text": "y"}]}`, `{"nodes": [{"text": ""}]}`, `{"nodes": "x"}`} {
		if _, err := normalizeCanon(json.RawMessage(bad)); code(err) != 400 {
			t.Errorf("%s: %v", bad, err)
		}
	}
}

func TestReferenceListAndTags(t *testing.T) {
	cur := json.RawMessage(`["a.png", "b.png"]`)
	if err := checkReferenceList([]string{"b.png"}, cur); err != nil {
		t.Fatal(err)
	}
	if err := checkReferenceList([]string{"b.png", "a.png"}, cur); err != nil {
		t.Fatal(err)
	}
	if code(checkReferenceList([]string{"../etc/passwd"}, cur)) != 400 || code(checkReferenceList([]string{"a.png", "a.png"}, cur)) != 400 {
		t.Fatal("foreign or duplicate paths must be rejected")
	}
	if got := normTagPrompt(" Red_Hair, red hair,, (smile:1.2) ,BLUE   eyes"); got != "red hair, (smile:1.2), blue eyes" {
		t.Fatalf("normTagPrompt %q", got)
	}
	if validateIPAdapter(nil) != nil || validateIPAdapter(&domain.IPAdapterConfig{Preset: "PLUS FACE (portraits)", Weight: 0.4, EndAt: 1}) != nil {
		t.Fatal("valid ip adapter rejected")
	}
	for _, ip := range []domain.IPAdapterConfig{{Preset: "x"}, {Weight: -1}, {Weight: 2.5}, {EndAt: 1.5}} {
		if code(validateIPAdapter(&ip)) != 400 {
			t.Errorf("%+v accepted", ip)
		}
	}
}

func uploadReq(t *testing.T, field string, data []byte) *http.Request {
	var buf bytes.Buffer
	mw := multipart.NewWriter(&buf)
	mw.WriteField("note", "x") //nolint:errcheck
	fw, _ := mw.CreateFormFile(field, "f")
	fw.Write(data) //nolint:errcheck
	mw.Close()
	r := httptest.NewRequest("POST", "/", &buf)
	r.Header.Set("Content-Type", mw.FormDataContentType())
	return r
}

func TestReadUpload(t *testing.T) {
	s := New(Config{MaxUpload: 1 << 10}, nil, nil)
	data, ext, err := s.readUpload(httptest.NewRecorder(), uploadReq(t, "file", fakes.TinyPNG()))
	if err != nil || ext != ".png" || !bytes.Equal(data, fakes.TinyPNG()) {
		t.Fatalf("png: %v %q", err, ext)
	}
	// JPEG magic but not a decodable image, plain text, missing field, too large, not multipart.
	cases := map[string]struct {
		r    *http.Request
		code int
	}{
		"fake jpeg": {uploadReq(t, "file", []byte("\xff\xd8\xff\xe0garbage")), 400},
		"text":      {uploadReq(t, "file", []byte("hello")), 400},
		"no field":  {uploadReq(t, "other", fakes.TinyPNG()), 400},
		"too large": {uploadReq(t, "file", append(fakes.TinyPNG(), make([]byte, 2<<10)...)), 413},
		"json":      {httptest.NewRequest("POST", "/", bytes.NewReader([]byte("{}"))), 400},
	}
	for name, c := range cases {
		if _, _, err := s.readUpload(httptest.NewRecorder(), c.r); code(err) != c.code {
			t.Errorf("%s: %v", name, err)
		}
	}
}
