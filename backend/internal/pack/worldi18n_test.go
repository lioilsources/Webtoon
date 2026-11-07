package pack

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
)

func TestAssignWorldI18n(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, "data", "stories", "les")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	world := `{"id": "w_les", "title": "Les", "title_i18n": {"en": "Forest"}, "synopsis_i18n": {"en": "Trees."}}`
	if err := os.WriteFile(filepath.Join(dir, "world.json"), []byte(world), 0o644); err != nil {
		t.Fatal(err)
	}
	stories := []Story{{World: dbq.World{ID: "w_les"}}, {World: dbq.World{ID: "w_none"}}}
	if err := AssignWorldI18n(stories, root); err != nil {
		t.Fatal(err)
	}
	if stories[0].WorldTitleI18n["en"] != "Forest" || stories[0].WorldSynopsisI18n["en"] != "Trees." {
		t.Fatalf("w_les: %+v", stories[0])
	}
	if stories[1].WorldTitleI18n != nil {
		t.Fatalf("w_none got translations: %+v", stories[1])
	}

	// pack.json: present when known, left out otherwise (the app treats a missing map as empty)
	with, _ := json.Marshal(WorldJSON{ID: "w_les", TitleI18n: stories[0].WorldTitleI18n})
	without, _ := json.Marshal(WorldJSON{ID: "w_none"})
	if !strings.Contains(string(with), `"title_i18n":{"en":"Forest"}`) || strings.Contains(string(without), "i18n") {
		t.Fatalf("with=%s without=%s", with, without)
	}
}
