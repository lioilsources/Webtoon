package pack

import (
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"gopkg.in/yaml.v3"
)

// Rules are the pack rules of rules/pack.yaml (part size, WebP quality, cover size, the never-exported world
// prefix, the dropped episode fields); the reasons are commented there.
type Rules struct {
	PartSize             int                         `yaml:"part_size"`
	WebPQuality          int                         `yaml:"webp_quality"`
	Cover                struct{ Width, Height int } `yaml:"cover"`
	ForbiddenWorldPrefix string                      `yaml:"forbidden_world_prefix"`
	DroppedEpisodeFields []string                    `yaml:"dropped_episode_fields"`
}

var (
	rulesOnce sync.Once
	rules     Rules
	rulesErr  error
)

// RulesPath is $WEBTOON_RULES/pack.yaml, else rules/pack.yaml in the working directory or the nearest parent
// that has one (the CLI runs from backend/, tests from backend/internal/pack).
func RulesPath() (string, error) {
	if d := os.Getenv("WEBTOON_RULES"); d != "" {
		return filepath.Join(d, "pack.yaml"), nil
	}
	dir, err := os.Getwd()
	if err != nil {
		return "", err
	}
	for {
		p := filepath.Join(dir, "rules", "pack.yaml")
		if _, err := os.Stat(p); err == nil {
			return p, nil
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			return "", fmt.Errorf("rules/pack.yaml not found from the working directory up (set WEBTOON_RULES)")
		}
		dir = parent
	}
}

// LoadRules reads and validates rules/pack.yaml once.
func LoadRules() (Rules, error) {
	rulesOnce.Do(func() {
		p, err := RulesPath()
		if err != nil {
			rulesErr = err
			return
		}
		b, err := os.ReadFile(p)
		if err != nil {
			rulesErr = err
			return
		}
		var r Rules
		if err := yaml.Unmarshal(b, &r); err != nil {
			rulesErr = fmt.Errorf("%s: %w", p, err)
			return
		}
		if r.PartSize < 1 || r.WebPQuality < 1 || r.Cover.Width < 1 || r.Cover.Height < 1 || r.ForbiddenWorldPrefix == "" {
			rulesErr = fmt.Errorf("%s: part_size, webp_quality, cover and forbidden_world_prefix are required", p)
			return
		}
		rules = r
	})
	return rules, rulesErr
}

// rule is LoadRules for code paths without an error return; Run calls LoadRules first, so a missing file
// fails the export cleanly before anything reaches here.
func rule() Rules {
	r, err := LoadRules()
	if err != nil {
		panic(err)
	}
	return r
}
