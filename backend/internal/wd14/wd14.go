// Package wd14 calls the WD14 tagger service and derives the SFW verdict and the
// identity score from its output (port of the checks in m0/render.py).
package wd14

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"math"
	"net/http"
	"strings"
	"time"

	"github.com/ol1n/webtoon/backend/internal/tags"
	"github.com/ol1n/webtoon/backend/internal/upstream"
)

// Unsafe holds the rating thresholds for audience-safe panels.
var Unsafe = map[string]float64{"explicit": 0.2, "questionable": 0.3}

const (
	DesignThreshold = 0.35
	MaxReseed       = 2
)

type Tags struct {
	General   map[string]float64 `json:"general"`
	Character map[string]float64 `json:"character"`
	Rating    map[string]float64 `json:"rating"`
}

type Client struct {
	URL  string
	HTTP *http.Client
}

func New(baseURL string) *Client {
	return &Client{URL: strings.TrimRight(baseURL, "/"), HTTP: &http.Client{Timeout: 120 * time.Second}}
}

// Tag POSTs PNG bytes to /tag.
func (c *Client) Tag(ctx context.Context, png []byte) (*Tags, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.URL+"/tag", bytes.NewReader(png))
	if err != nil {
		return nil, err
	}
	req.Header.Set("Content-Type", "application/octet-stream")
	resp, err := c.HTTP.Do(req)
	if err != nil {
		return nil, upstream.Unavailable("wd14", err)
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(io.LimitReader(resp.Body, 8<<20))
	if resp.StatusCode >= 300 {
		e := fmt.Errorf("POST %s/tag → %d: %.300s", c.URL, resp.StatusCode, raw)
		if upstream.StatusUnavailable(resp.StatusCode) {
			return nil, upstream.Unavailable("wd14", e)
		}
		return nil, e
	}
	var t Tags
	if err := json.Unmarshal(raw, &t); err != nil {
		return nil, fmt.Errorf("wd14 response: %w", err)
	}
	return &t, nil
}

func round3(f float64) float64 { return math.Round(f*1000) / 1000 }

// Safety returns the ratings over their threshold (empty = safe).
func Safety(t *Tags) map[string]float64 {
	bad := map[string]float64{}
	for k, lim := range Unsafe {
		if v := t.Rating[k]; v > lim {
			bad[k] = round3(v)
		}
	}
	return bad
}

type Identity struct {
	Recall  float64  `json:"recall"`
	Missing []string `json:"missing"`
}

// IdentityScore = recall of the character's design tags among WD14-detected tags.
func IdentityScore(t *Tags, tagPrompt string) Identity {
	design := tags.Split(tagPrompt)
	var hit int
	missing := []string{}
	for _, d := range design {
		if conf, ok := t.General[d]; ok && conf >= DesignThreshold {
			hit++
		} else {
			missing = append(missing, d)
		}
	}
	return Identity{Recall: round3(float64(hit) / math.Max(1, float64(len(design)))), Missing: missing}
}
