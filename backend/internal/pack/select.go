package pack

import (
	"context"
	"errors"
	"fmt"
	"slices"
	"strings"

	"github.com/ol1n/webtoon/backend/internal/db/dbq"
)

// Selection names the stories of a pack: explicit campaigns, or every campaign of the given
// worlds (explicit ids and/or id prefixes). Exactly one of Campaigns and Worlds/WorldPrefixes is used.
type Selection struct {
	Campaigns     []string
	Worlds        []string
	WorldPrefixes []string
}

func (s Selection) byWorld() bool { return len(s.Worlds) > 0 || len(s.WorldPrefixes) > 0 }

// Validate checks that the selection names something and does not mix the two modes.
func (s Selection) Validate() error {
	if len(s.Campaigns) > 0 && s.byWorld() {
		return errors.New("use either -campaigns or -worlds/-world-prefix, not both")
	}
	if len(s.Campaigns) == 0 && !s.byWorld() {
		return errors.New("nothing selected: give -campaigns, -worlds or -world-prefix")
	}
	return nil
}

// checkWorld refuses the worlds that must never be published.
func checkWorld(id string) error {
	if p := rule().ForbiddenWorldPrefix; strings.HasPrefix(id, p) {
		return fmt.Errorf("world %s: ids starting with %s are never exported", id, p)
	}
	return nil
}

// MatchWorlds picks the worlds of a selection out of all: the explicit ids first, in the given
// order, then for each prefix its matches sorted by id. An unknown id is an error, a prefix
// without a match is not. Any selected w_lxf_ world is a hard error.
func MatchWorlds(all []dbq.World, sel Selection) ([]dbq.World, error) {
	byID := make(map[string]dbq.World, len(all))
	for _, w := range all {
		byID[w.ID] = w
	}
	var out []dbq.World
	seen := map[string]bool{}
	add := func(w dbq.World) error {
		if err := checkWorld(w.ID); err != nil {
			return err
		}
		if !seen[w.ID] {
			seen[w.ID] = true
			out = append(out, w)
		}
		return nil
	}
	for _, id := range sel.Worlds {
		w, ok := byID[id]
		if !ok {
			return nil, fmt.Errorf("world %s not found", id)
		}
		if err := add(w); err != nil {
			return nil, err
		}
	}
	sorted := slices.Clone(all)
	slices.SortFunc(sorted, func(a, b dbq.World) int { return strings.Compare(a.ID, b.ID) })
	for _, prefix := range sel.WorldPrefixes {
		if prefix == "" {
			return nil, errors.New("empty world prefix")
		}
		for _, w := range sorted {
			if strings.HasPrefix(w.ID, prefix) {
				if err := add(w); err != nil {
					return nil, err
				}
			}
		}
	}
	return out, nil
}

// Exportable reports whether an episode goes into a pack: ready, with an image on every panel.
func Exportable(e Episode) bool {
	if e.Row.Status != "ready" || len(e.Panels) == 0 {
		return false
	}
	for _, p := range e.Panels {
		if p.Status != "ready" || p.ImagePath == "" {
			return false
		}
	}
	return true
}

// ReadyPrefix keeps the episodes up to (not including) the first one that is not exportable;
// eps must be in idx order. A later ready episode after a gap is never exported.
func ReadyPrefix(eps []Episode) []Episode {
	for i, e := range eps {
		if !Exportable(e) {
			return eps[:i]
		}
	}
	return eps
}

// Filter cuts every story to its ready prefix and drops stories left without an episode.
// notes explain each cut (for the export summary).
func Filter(stories []Story) (kept []Story, notes []string) {
	for _, s := range stories {
		ready := ReadyPrefix(s.Episodes)
		if len(ready) == 0 {
			why := "no episode"
			if len(s.Episodes) > 0 {
				why = describe(s.Episodes[0])
			}
			notes = append(notes, fmt.Sprintf("story %s (%s) dropped: no ready episode (%s)", s.Campaign.ID, s.Campaign.Title, why))
			continue
		}
		if len(ready) < len(s.Episodes) {
			notes = append(notes, fmt.Sprintf("story %s (%s): stops before %s", s.Campaign.ID, s.Campaign.Title, describe(s.Episodes[len(ready)])))
		}
		s.Episodes = ready
		kept = append(kept, s)
	}
	return kept, notes
}

func describe(e Episode) string {
	return fmt.Sprintf("episode %d %s (status %s, panels %d/%d)", e.Row.Idx, e.Row.ID, e.Row.Status, e.Row.PanelsReady, e.Row.PanelsTotal)
}

// Load reads the selected stories with every episode and panel (unfiltered; see Filter).
func Load(ctx context.Context, q *dbq.Queries, sel Selection) ([]Story, error) {
	if err := sel.Validate(); err != nil {
		return nil, err
	}
	var out []Story
	if sel.byWorld() {
		all, err := q.ListAllWorlds(ctx)
		if err != nil {
			return nil, err
		}
		worlds, err := MatchWorlds(all, sel)
		if err != nil {
			return nil, err
		}
		for _, w := range worlds {
			camps, err := q.ListWorldCampaigns(ctx, w.ID)
			if err != nil {
				return nil, err
			}
			for _, c := range camps {
				s, err := loadStory(ctx, q, c, w)
				if err != nil {
					return nil, err
				}
				out = append(out, s)
			}
		}
		return out, nil
	}
	worlds := map[string]dbq.World{}
	for _, id := range sel.Campaigns {
		c, err := q.GetCampaign(ctx, id)
		if err != nil {
			return nil, fmt.Errorf("campaign %s: %w", id, err)
		}
		if err := checkWorld(c.WorldID); err != nil {
			return nil, err
		}
		w, ok := worlds[c.WorldID]
		if !ok {
			if w, err = q.GetWorld(ctx, c.WorldID); err != nil {
				return nil, fmt.Errorf("world %s of campaign %s: %w", c.WorldID, id, err)
			}
			worlds[c.WorldID] = w
		}
		s, err := loadStory(ctx, q, c, w)
		if err != nil {
			return nil, err
		}
		out = append(out, s)
	}
	return out, nil
}

func loadStory(ctx context.Context, q *dbq.Queries, c dbq.Campaign, w dbq.World) (Story, error) {
	s := Story{Campaign: c, World: w}
	eps, err := q.ListEpisodes(ctx, c.ID)
	if err != nil {
		return s, err
	}
	for _, e := range eps {
		panels, err := q.ListPanels(ctx, e.ID)
		if err != nil {
			return s, err
		}
		s.Episodes = append(s.Episodes, Episode{Row: e, Panels: panels})
	}
	return s, nil
}
