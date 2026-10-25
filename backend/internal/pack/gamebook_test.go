package pack

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestReadGraphSara(t *testing.T) {
	root, err := RepoRoot()
	if err != nil {
		t.Fatal(err)
	}
	g, err := ReadGraph(filepath.Join(root, "data", "gamebooks", "sara", "graph.yaml"))
	if err != nil {
		t.Fatal(err)
	}
	if g.ID != "sara" || g.Start != "n0" || len(g.order) != len(g.Nodes) || g.order[0] != "n0" {
		t.Errorf("graph = %s start %s order %v", g.ID, g.Start, g.order)
	}
	if w := g.Selection().Worlds; len(w) != len(g.Nodes) || w[0] != "w_gb_sara_n0" {
		t.Errorf("selection = %v", w)
	}
}

func TestReadGraphErrors(t *testing.T) {
	cases := map[string]string{
		"unknown target": "nodes:\n  a: {choices: [{id: x, text: X, to: nope}]}\n",
		"unreachable":    "nodes:\n  a: {ending: good}\n  b: {ending: good}\n",
		"dead end":       "nodes:\n  a: {title: A}\n",
		"bad start":      "nodes:\n  b: {ending: good}\n",
	}
	for name, body := range cases {
		path := filepath.Join(t.TempDir(), "graph.yaml")
		if err := os.WriteFile(path, []byte("id: t\nstart: a\n"+body), 0o644); err != nil {
			t.Fatal(err)
		}
		if _, err := ReadGraph(path); err == nil {
			t.Errorf("%s: want an error", name)
		}
	}
}

func TestMergeGamebook(t *testing.T) {
	c := &Catalog{Gamebooks: []json.RawMessage{json.RawMessage(`{"id":"drak","status":"planned"}`)}}
	c.normalize()
	now := time.Date(2026, 10, 25, 0, 0, 0, 0, time.UTC)
	for v := 1; v <= 2; v++ {
		if err := c.MergeGamebook(CatalogGamebook{ID: "sara", Status: "ready", Version: v}, now, ""); err != nil {
			t.Fatal(err)
		}
	}
	if len(c.Gamebooks) != 2 || !strings.Contains(string(c.Gamebooks[1]), `"version":2`) || c.Version != 2 {
		t.Errorf("gamebooks = %s, version %d", c.Gamebooks, c.Version)
	}
	if len(c.Stories) != 0 {
		t.Errorf("gamebook nodes must not become library stories: %v", c.Stories)
	}
}
