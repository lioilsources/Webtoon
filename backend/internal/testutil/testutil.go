// Package testutil loads the M0 fixtures and golden outputs of the Python prototype
// (internal/testdata/golden_m0.json, produced by running m0/*.py pure functions).
package testutil

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"sync"
	"testing"

	"github.com/ol1n/webtoon/backend/data"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/tags"
)

func dir() string {
	_, f, _, _ := runtime.Caller(0)
	return filepath.Join(filepath.Dir(f), "..", "testdata")
}

func World(t testing.TB) *domain.World {
	t.Helper()
	w := &domain.World{}
	if err := json.Unmarshal(data.WorldM0, w); err != nil {
		t.Fatal(err)
	}
	return w
}

func Styles(t testing.TB) *domain.Styles {
	t.Helper()
	s := &domain.Styles{}
	if err := json.Unmarshal(data.Styles, s); err != nil {
		t.Fatal(err)
	}
	return s
}

var (
	vocabOnce sync.Once
	vocab     *tags.Vocab
)

func Vocab(t testing.TB) *tags.Vocab {
	t.Helper()
	vocabOnce.Do(func() {
		v, err := tags.LoadVocab(data.WD14Tags)
		if err != nil {
			panic(err)
		}
		vocab = v
	})
	return vocab
}

// Golden returns golden_m0.json as raw fields.
func Golden(t testing.TB) map[string]json.RawMessage {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join(dir(), "golden_m0.json"))
	if err != nil {
		t.Fatal(err)
	}
	g := map[string]json.RawMessage{}
	if err := json.Unmarshal(raw, &g); err != nil {
		t.Fatal(err)
	}
	return g
}

// GoldenField decodes one golden field into v.
func GoldenField(t testing.TB, g map[string]json.RawMessage, key string, v any) {
	t.Helper()
	raw, ok := g[key]
	if !ok {
		t.Fatalf("golden key %q missing", key)
	}
	if err := json.Unmarshal(raw, v); err != nil {
		t.Fatalf("golden %s: %v", key, err)
	}
}

// StoryboardEP1 is out/dev/storyboard_ep1.json from the M0 run (validated, with visual_tags).
func StoryboardEP1(t testing.TB) *domain.Storyboard {
	t.Helper()
	raw, err := os.ReadFile(filepath.Join(dir(), "storyboard_ep1.json"))
	if err != nil {
		t.Fatal(err)
	}
	sb := &domain.Storyboard{}
	if err := json.Unmarshal(raw, sb); err != nil {
		t.Fatal(err)
	}
	return sb
}

// ScriptedLLM answers JSON calls from a queue of handlers; it records every call.
type ScriptedLLM struct {
	mu      sync.Mutex
	Handler func(system, user string) (string, error)
	Calls   []Call
}

type Call struct{ System, User string }

func (s *ScriptedLLM) JSON(_ context.Context, system, user string, _ float64) (json.RawMessage, error) {
	s.mu.Lock()
	s.Calls = append(s.Calls, Call{system, user})
	s.mu.Unlock()
	out, err := s.Handler(system, user)
	if err != nil {
		return nil, err
	}
	return json.RawMessage(out), nil
}
