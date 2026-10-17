// Package state is the campaign story state (§4) and the state_diff merge (port of m0/state.py).
package state

import (
	"fmt"
	"slices"

	"github.com/ol1n/webtoon/backend/internal/domain"
)

// Field order matches the prototype's dicts (it is sent to the LLM as JSON).
type State struct {
	Characters      map[string]*CharState `json:"characters"`
	CurrentLocation string                `json:"current_location"`
	OpenThreads     []string              `json:"open_threads"`
	Timeline        []TimelineEntry       `json:"timeline"`
	Facts           []string              `json:"facts"`
	Mood            string                `json:"mood"`
}

type CharState struct {
	Alive     bool              `json:"alive"`
	Location  string            `json:"location"`
	Status    string            `json:"status"`
	Relations map[string]string `json:"relations"`
	Inventory []string          `json:"inventory"`
}

type TimelineEntry struct {
	Episode int    `json:"episode"`
	Event   string `json:"event"`
}

// Empty = empty_state: every non-NPC character alive at the first allowed location.
func Empty(w *domain.World) *State {
	first := ""
	if loc := w.AllowedLocations(); len(loc) > 0 {
		first = loc[0]
	}
	s := &State{Characters: map[string]*CharState{}, CurrentLocation: first,
		OpenThreads: []string{}, Timeline: []TimelineEntry{}, Facts: []string{}}
	for _, c := range w.Characters {
		if c.Role != "npc" {
			s.Characters[c.ID] = &CharState{Alive: true, Location: first, Relations: map[string]string{}, Inventory: []string{}}
		}
	}
	return s
}

func (s *State) normalize() {
	if s.Characters == nil {
		s.Characters = map[string]*CharState{}
	}
	if s.OpenThreads == nil {
		s.OpenThreads = []string{}
	}
	if s.Timeline == nil {
		s.Timeline = []TimelineEntry{}
	}
	if s.Facts == nil {
		s.Facts = []string{}
	}
}

func (s *State) clone() *State {
	c := &State{CurrentLocation: s.CurrentLocation, Mood: s.Mood,
		OpenThreads: slices.Clone(s.OpenThreads), Timeline: slices.Clone(s.Timeline), Facts: slices.Clone(s.Facts),
		Characters: make(map[string]*CharState, len(s.Characters))}
	for id, ch := range s.Characters {
		if ch == nil {
			continue
		}
		cc := *ch
		cc.Relations = make(map[string]string, len(ch.Relations))
		for k, v := range ch.Relations {
			cc.Relations[k] = v
		}
		cc.Inventory = slices.Clone(ch.Inventory)
		c.Characters[id] = &cc
	}
	c.normalize()
	return c
}

// ApplyDiff = apply_diff: returns a new state; the input is not modified.
// diff keys: current_location, open_threads_add/remove, facts_add, timeline_add, mood.
func ApplyDiff(s *State, diff map[string]any, episodeIndex int) *State {
	out := s.clone()
	if loc := str(diff["current_location"]); loc != "" {
		out.CurrentLocation = loc
		for _, ch := range out.Characters {
			ch.Location = loc
		}
	}
	remove := strs(diff["open_threads_remove"])
	threads := out.OpenThreads[:0:0]
	for _, t := range out.OpenThreads {
		if !slices.Contains(remove, t) {
			threads = append(threads, t)
		}
	}
	for _, t := range strs(diff["open_threads_add"]) {
		if !slices.Contains(threads, t) {
			threads = append(threads, t)
		}
	}
	out.OpenThreads = threads
	for _, f := range strs(diff["facts_add"]) {
		if !slices.Contains(out.Facts, f) {
			out.Facts = append(out.Facts, f)
		}
	}
	if ev := str(diff["timeline_add"]); ev != "" {
		out.Timeline = append(out.Timeline, TimelineEntry{Episode: episodeIndex, Event: ev})
	}
	if m := str(diff["mood"]); m != "" {
		out.Mood = m
	}
	return out
}

// MergeCanon = sorted(set(progress) | set(reached)), keeping only node ids the world defines.
func MergeCanon(w *domain.World, progress, reached []string) []string {
	known := map[string]bool{}
	for _, n := range w.Canon.Nodes {
		known[n.ID] = true
	}
	out := slices.Clone(progress)
	for _, id := range reached {
		if known[id] && !slices.Contains(out, id) {
			out = append(out, id)
		}
	}
	slices.Sort(out)
	if out == nil {
		out = []string{}
	}
	return out
}

func str(v any) string {
	switch x := v.(type) {
	case nil:
		return ""
	case string:
		return x
	case []any: // e.g. timeline_add given as a list of sentences
		parts := strs(x)
		out := ""
		for i, p := range parts {
			if i > 0 {
				out += " "
			}
			out += p
		}
		return out
	default:
		return fmt.Sprint(x)
	}
}

func strs(v any) []string {
	switch x := v.(type) {
	case nil:
		return nil
	case string:
		if x == "" {
			return nil
		}
		return []string{x}
	case []string:
		return x
	case []any:
		out := make([]string, 0, len(x))
		for _, it := range x {
			if s := str(it); s != "" {
				out = append(out, s)
			}
		}
		return out
	default:
		return []string{fmt.Sprint(x)}
	}
}
