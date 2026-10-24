package pack

import (
	"context"
	"errors"
	"fmt"
	"os"

	"gopkg.in/yaml.v3"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
)

// PickFile is a starter selection (data/starter_showcase.yaml): explicit worlds, one story each, in library order.
type PickFile struct {
	Pack struct {
		ID      string `yaml:"id"`
		Title   string `yaml:"title"`
		Version int    `yaml:"version"`
	} `yaml:"pack"`
	Picks []Pick `yaml:"picks"`
}

// Pick is one starter story: the world (its first campaign unless Campaign is given), its pack type and the style
// it must be drawn in. From documents the world a restyled copy (m0/restyle.sh) was made from.
type Pick struct {
	World    string `yaml:"world"`
	Type     string `yaml:"type"`
	Style    string `yaml:"style"`
	From     string `yaml:"from"`
	Campaign string `yaml:"campaign"`
}

// ReadPicks parses and validates a pick file against the rules (known types, no duplicate or free worlds).
func ReadPicks(path string, r Rules) (*PickFile, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var pf PickFile
	if err := yaml.Unmarshal(raw, &pf); err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	if len(pf.Picks) == 0 {
		return nil, fmt.Errorf("%s: no picks", path)
	}
	seen := map[string]bool{}
	for i, p := range pf.Picks {
		if p.World == "" || p.Type == "" || p.Style == "" {
			return nil, fmt.Errorf("%s: pick %d needs world, type and style", path, i+1)
		}
		if _, ok := r.Type(p.Type); !ok {
			return nil, fmt.Errorf("%s: pick %s: unknown type %s", path, p.World, p.Type)
		}
		if seen[p.World] {
			return nil, fmt.Errorf("%s: world %s picked twice", path, p.World)
		}
		seen[p.World] = true
		if err := checkWorld(p.World); err != nil {
			return nil, err
		}
	}
	return &pf, nil
}

// pickStore is the part of dbq.Queries the picks need (a fake in tests).
type pickStore interface {
	GetWorld(ctx context.Context, id string) (dbq.World, error)
	GetCampaign(ctx context.Context, id string) (dbq.Campaign, error)
	ListWorldCampaigns(ctx context.Context, worldID string) ([]dbq.Campaign, error)
}

// ResolvePick finds the world and campaign of one pick and checks the world is drawn in the pick's style.
func ResolvePick(ctx context.Context, q pickStore, p Pick) (dbq.World, dbq.Campaign, error) {
	w, err := q.GetWorld(ctx, p.World)
	if err != nil {
		hint := ""
		if p.From != "" {
			hint = fmt.Sprintf(" (a restyled copy of %s: run m0/restyle.sh %s:%s first)", p.From, p.From, p.Style)
		}
		return w, dbq.Campaign{}, fmt.Errorf("pick %s: world not found%s: %w", p.World, hint, err)
	}
	if w.StyleID != p.Style {
		from := p.From
		if from == "" {
			from = p.World
		}
		return w, dbq.Campaign{}, fmt.Errorf("pick %s: world is drawn in %s, the pick wants %s: re-render it with m0/restyle.sh %s:%s",
			p.World, w.StyleID, p.Style, from, p.Style)
	}
	if p.Campaign != "" {
		c, err := q.GetCampaign(ctx, p.Campaign)
		if err != nil {
			return w, c, fmt.Errorf("pick %s: campaign %s: %w", p.World, p.Campaign, err)
		}
		if c.WorldID != w.ID {
			return w, c, fmt.Errorf("pick %s: campaign %s belongs to %s", p.World, p.Campaign, c.WorldID)
		}
		return w, c, nil
	}
	camps, err := q.ListWorldCampaigns(ctx, w.ID) // created_at, id order
	if err != nil {
		return w, dbq.Campaign{}, err
	}
	if len(camps) == 0 {
		return w, dbq.Campaign{}, fmt.Errorf("pick %s: the world has no campaign (import it first)", p.World)
	}
	return w, camps[0], nil
}

// loadPicks reads the stories of a pick file, one per pick, in file order, typed by the pick.
func loadPicks(ctx context.Context, q *dbq.Queries, picks []Pick) ([]Story, error) {
	if len(picks) == 0 {
		return nil, errors.New("no picks")
	}
	var out []Story
	for _, p := range picks {
		w, c, err := ResolvePick(ctx, q, p)
		if err != nil {
			return nil, err
		}
		s, err := loadStory(ctx, q, c, w)
		if err != nil {
			return nil, err
		}
		s.Type = p.Type
		out = append(out, s)
	}
	return out, nil
}
