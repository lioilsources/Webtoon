package trailer

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"
)

// Music renders one instrumental track with AiStack's audio service (ACE-Step, POST /v1/audio/music, the API of
// m0/music.py) and writes it to out. The service runs on SPARK: reserve it with sparkctl first (audio-music).
func Music(base, prompt string, seconds, seed int, out string) error {
	body, _ := json.Marshal(map[string]any{"prompt": prompt + ", instrumental, no vocals", "duration_s": seconds,
		"seed": seed, "instrumental": true, "loop": false, "format": "mp3", "variations": 1})
	var job struct {
		JobID   string `json:"job_id"`
		Status  string `json:"status"`
		Error   string `json:"error"`
		Outputs []struct {
			URL string `json:"url"`
		} `json:"outputs"`
	}
	if err := call("POST", base+"/v1/audio/music", body, &job); err != nil {
		return err
	}
	for deadline := time.Now().Add(10 * time.Minute); job.Status != "done" && job.Status != "error"; {
		if time.Now().After(deadline) {
			return fmt.Errorf("music job %s: no result in 10 min", job.JobID)
		}
		time.Sleep(2 * time.Second)
		if err := call("GET", base+"/v1/audio/jobs/"+job.JobID, nil, &job); err != nil {
			return err
		}
	}
	if job.Status == "error" || len(job.Outputs) == 0 {
		return fmt.Errorf("music job %s: %s", job.JobID, job.Error)
	}
	url := job.Outputs[0].URL
	if !strings.HasPrefix(url, "http") {
		url = base + url
	}
	resp, err := http.Get(url) //nolint:gosec // the audio service's own output URL
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("%s: %s", url, resp.Status)
	}
	f, err := os.Create(out)
	if err != nil {
		return err
	}
	if _, err := io.Copy(f, resp.Body); err != nil {
		f.Close()
		return err
	}
	return f.Close()
}

func call(method, url string, body []byte, v any) error {
	req, err := http.NewRequest(method, url, bytes.NewReader(body))
	if err != nil {
		return err
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := (&http.Client{Timeout: 60 * time.Second}).Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(resp.Body)
	if resp.StatusCode >= 300 {
		return fmt.Errorf("%s %s: %s: %s", method, url, resp.Status, raw)
	}
	return json.Unmarshal(raw, v)
}
