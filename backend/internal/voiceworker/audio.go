package voiceworker

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"strings"
)

// AudioClient talks to the AiStack audio service (services/audio, port 8093 on Spark), ported from
// Hajánek forge/internal/worker/audio.go. Routes and shapes mirror app/main.py and app/schemas.py:
//
//	POST   /v1/audio/voices        multipart voice_id, sample, rights, source, language, replace → 201
//	DELETE /v1/audio/voices/{id}   → 200 | 404
//	POST   /v1/audio/tts           TtsRequest → 202 {job_id}; 503 engine down; 403 license
//	GET    /v1/audio/jobs/{id}     → {status: queued|running|done|error, error, outputs[{url, filename, duration}]}
//
// Errors are FastAPI {"detail": "..."}.
type AudioClient struct {
	BaseURL string
	Key     string // optional AUDIO_API_KEY (Bearer)
	HTTP    *http.Client
}

// AudioError is a non-2xx response of the audio service.
type AudioError struct {
	Op     string
	Status int
	Detail string
}

func (e *AudioError) Error() string {
	return fmt.Sprintf("audio %s: HTTP %d: %s", e.Op, e.Status, e.Detail)
}

// TTSRequest mirrors schemas.TtsRequest (the fields the worker uses).
type TTSRequest struct {
	Text           string  `json:"text"`
	Language       string  `json:"language"`
	Voice          string  `json:"voice"`
	Engine         string  `json:"engine"`
	CommercialOnly bool    `json:"commercial_only"`
	Speed          float64 `json:"speed"`
	Seed           *int    `json:"seed,omitempty"`
	Format         string  `json:"format"`
}

type audioJob struct {
	JobID   string `json:"job_id"`
	Status  string `json:"status"`
	Error   string `json:"error"`
	Outputs []struct {
		URL      string  `json:"url"`
		Filename string  `json:"filename"`
		Duration float64 `json:"duration"`
	} `json:"outputs"`
}

func (a *AudioClient) do(ctx context.Context, op, method, path string, body io.Reader, ctype string) (int, []byte, error) {
	u := path
	if !strings.HasPrefix(path, "http://") && !strings.HasPrefix(path, "https://") {
		u = strings.TrimRight(a.BaseURL, "/") + path
	}
	req, err := http.NewRequestWithContext(ctx, method, u, body)
	if err != nil {
		return 0, nil, err
	}
	if ctype != "" {
		req.Header.Set("Content-Type", ctype)
	}
	if a.Key != "" {
		req.Header.Set("Authorization", "Bearer "+a.Key)
	}
	resp, err := a.HTTP.Do(req)
	if err != nil {
		return 0, nil, err
	}
	defer resp.Body.Close()
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return resp.StatusCode, nil, err
	}
	if resp.StatusCode/100 != 2 {
		return resp.StatusCode, b, &AudioError{Op: op, Status: resp.StatusCode, Detail: detail(b)}
	}
	return resp.StatusCode, b, nil
}

func detail(b []byte) string {
	var d struct {
		Detail any `json:"detail"`
	}
	if json.Unmarshal(b, &d) == nil && d.Detail != nil {
		if s, ok := d.Detail.(string); ok {
			return s
		}
		j, _ := json.Marshal(d.Detail)
		return string(j)
	}
	s := strings.TrimSpace(string(b))
	if len(s) > 300 {
		s = s[:300]
	}
	return s
}

// CreateVoice uploads the cloning sample (replace=true: a retried task is idempotent).
func (a *AudioClient) CreateVoice(ctx context.Context, voiceID string, sample []byte, filename, language, source string) error {
	var buf bytes.Buffer
	mw := multipart.NewWriter(&buf)
	for _, kv := range [][2]string{
		{"voice_id", voiceID}, {"rights", "own"}, {"source", source}, {"language", language}, {"replace", "true"},
	} {
		if err := mw.WriteField(kv[0], kv[1]); err != nil {
			return err
		}
	}
	fw, err := mw.CreateFormFile("sample", filename)
	if err != nil {
		return err
	}
	if _, err := fw.Write(sample); err != nil {
		return err
	}
	if err := mw.Close(); err != nil {
		return err
	}
	_, _, err = a.do(ctx, "voices", http.MethodPost, "/v1/audio/voices", &buf, mw.FormDataContentType())
	return err
}

// DeleteVoice removes a stored voice; an unknown voice (404) is not an error.
func (a *AudioClient) DeleteVoice(ctx context.Context, voiceID string) (bool, error) {
	status, _, err := a.do(ctx, "voices delete", http.MethodDelete, "/v1/audio/voices/"+url.PathEscape(voiceID), nil, "")
	if status == http.StatusNotFound {
		return false, nil
	}
	return err == nil, err
}

// SubmitTTS enqueues a TTS job and returns its id.
func (a *AudioClient) SubmitTTS(ctx context.Context, r TTSRequest) (string, error) {
	b, err := json.Marshal(r)
	if err != nil {
		return "", err
	}
	_, rb, err := a.do(ctx, "tts", http.MethodPost, "/v1/audio/tts", bytes.NewReader(b), "application/json")
	if err != nil {
		return "", err
	}
	var acc audioJob
	if err := json.Unmarshal(rb, &acc); err != nil {
		return "", fmt.Errorf("audio tts: %w", err)
	}
	if acc.JobID == "" {
		return "", fmt.Errorf("audio tts: no job_id in response")
	}
	return acc.JobID, nil
}

func (a *AudioClient) job(ctx context.Context, id string) (*audioJob, error) {
	_, b, err := a.do(ctx, "jobs", http.MethodGet, "/v1/audio/jobs/"+url.PathEscape(id), nil, "")
	if err != nil {
		return nil, err
	}
	var st audioJob
	if err := json.Unmarshal(b, &st); err != nil {
		return nil, fmt.Errorf("audio job: %w", err)
	}
	return &st, nil
}

// Download saves an output URL (relative to BaseURL or absolute) to dst.
func (a *AudioClient) Download(ctx context.Context, outURL, dst string) error {
	_, b, err := a.do(ctx, "output", http.MethodGet, outURL, nil, "")
	if err != nil {
		return err
	}
	return os.WriteFile(dst, b, 0o600)
}
