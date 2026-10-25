package pack

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"gopkg.in/yaml.v3"
)

func TestGraphDocRoundTrip(t *testing.T) {
	root, err := RepoRoot()
	if err != nil {
		t.Fatal(err)
	}
	src := filepath.Join(root, "data", "gamebooks", "sara", "graph.yaml")
	doc, err := ReadGraphDoc(src)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(string(doc), `{"schema":1,"id":"sara"`) {
		t.Errorf("key order lost: %.60s", doc)
	}
	path := filepath.Join(t.TempDir(), "graph.yaml")
	g, err := WriteGraphDoc(path, doc, []string{"n0", "end_cold"})
	if err != nil {
		t.Fatal(err)
	}
	want, _ := ReadGraph(src)
	if !reflect.DeepEqual(g.order, want.order) || !reflect.DeepEqual(g.Nodes, want.Nodes) {
		t.Error("graph changed in the round trip")
	}
	// every field survives, also those export ignores
	var a, b any
	ra, _ := os.ReadFile(src)
	rb, _ := os.ReadFile(path)
	yaml.Unmarshal(ra, &a) //nolint:errcheck
	yaml.Unmarshal(rb, &b) //nolint:errcheck
	if !reflect.DeepEqual(a, b) {
		t.Error("document changed in the round trip")
	}
}

func TestWriteGraphDocRefuses(t *testing.T) {
	path := filepath.Join(t.TempDir(), "graph.yaml")
	good := `{"id":"t","start":"a","nodes":{"a":{"ending":"good"}}}`
	if _, err := WriteGraphDoc(path, []byte(good), []string{"a"}); err != nil {
		t.Fatal(err)
	}
	for name, doc := range map[string]string{
		"drawn node removed": `{"id":"t","start":"b","nodes":{"b":{"ending":"good"}}}`,
		"dangling choice":    `{"id":"t","start":"a","nodes":{"a":{"choices":[{"id":"x","text":"X","to":"zz"}]}}}`,
		"not an object":      `[1]`,
	} {
		if _, err := WriteGraphDoc(path, []byte(doc), []string{"a"}); err == nil {
			t.Errorf("%s: want an error", name)
		}
	}
	var back map[string]any
	raw, _ := ReadGraphDoc(path)
	json.Unmarshal(raw, &back) //nolint:errcheck
	if back["start"] != "a" {
		t.Errorf("a refused write must leave the file: %s", raw)
	}
}
