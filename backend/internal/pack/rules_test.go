package pack

import (
	"reflect"
	"testing"
)

// The values the pack code had as constants before they moved to rules/base/pack.yaml.
func TestRulesMatchFormerConstants(t *testing.T) {
	r, err := LoadRules()
	if err != nil {
		t.Fatal(err)
	}
	if r.PartSize != 25 || r.WebPQuality != 85 || r.Cover.Width != 416 || r.Cover.Height != 608 || r.ForbiddenWorldPrefix != "w_lxf_" {
		t.Fatalf("rules/base/pack.yaml drifted: %+v", r)
	}
	if want := []string{"error", "created_at", "updated_at"}; !reflect.DeepEqual(r.DroppedEpisodeFields, want) {
		t.Fatalf("dropped_episode_fields %v, want %v", r.DroppedEpisodeFields, want)
	}
}
