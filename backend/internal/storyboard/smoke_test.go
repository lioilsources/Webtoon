package storyboard_test

import (
	"context"
	"encoding/json"
	"errors"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/state"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/testutil"
)

// TestSmokeRealLLM runs ONE storyboard attempt against the real LLM (≤ 3 calls:
// storyboard, tag translation, rule check). Opt-in only:
//
//	WEBTOON_LLM_SMOKE=1 go test -run Smoke -v ./internal/storyboard/
func TestSmokeRealLLM(t *testing.T) {
	if os.Getenv("WEBTOON_LLM_SMOKE") != "1" {
		t.Skip("set WEBTOON_LLM_SMOKE=1 to call the real LLM")
	}
	url := os.Getenv("WEBTOON_LLM")
	if url == "" {
		url = "http://192.168.88.66:8080/v1"
	}
	model := os.Getenv("WEBTOON_LLM_MODEL")
	if model == "" {
		model = "openclaw-default"
	}
	c := llm.New(url, model)
	c.Retries = 0
	counting := &countingLLM{inner: c}
	w := testutil.World(t)
	gen := &storyboard.Generator{LLM: counting, Vocab: testutil.Vocab(t), Attempts: 1}
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()
	t0 := time.Now()
	sb, err := gen.Generate(ctx, w, state.Empty(w), nil, storyboard.FirstPremise(w))
	t.Logf("LLM calls: %d, took %s", counting.n, time.Since(t0).Round(time.Second))
	var se *storyboard.Error
	if errors.As(err, &se) {
		t.Logf("single attempt was not schema-valid (the worker would retry): %v", se.Log)
		return
	}
	if err != nil {
		t.Fatal(err)
	}
	t.Logf("title: %s, panels: %d, warnings: %v", sb.Title, len(sb.Panels), sb.Warnings)
	for i, p := range sb.Panels {
		var texts []string
		for _, b := range p.Bubbles {
			texts = append(texts, b.Text)
		}
		t.Logf("  %d %-13s %-9s tags=%s | %s", i, p.Shot, p.LocationID, strings.Join(p.VisualTags, ", "), strings.Join(texts, " / "))
	}
	for _, ch := range sb.Choices {
		t.Logf("  choice %s: %s", ch.Kind, ch.Text)
	}
	t.Logf("state_diff: %s", sb.StateDiff)
}

type countingLLM struct {
	inner llm.JSONCaller
	n     int
}

func (c *countingLLM) JSON(ctx context.Context, system, user string, temp float64) (json.RawMessage, error) {
	c.n++
	return c.inner.JSON(ctx, system, user, temp)
}
