package state_test

import (
	"encoding/json"
	"reflect"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/state"
	"github.com/ol1n/webtoon/backend/internal/testutil"
)

// asGeneric round-trips through JSON so typed and golden values compare structurally.
func asGeneric(t *testing.T, v any) any {
	t.Helper()
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatal(err)
	}
	var out any
	if err := json.Unmarshal(b, &out); err != nil {
		t.Fatal(err)
	}
	return out
}

func TestMergeMatchesPrototype(t *testing.T) {
	g := testutil.Golden(t)
	w := testutil.World(t)
	var wantEmpty, want1, want2 any
	var diff1, diff2 map[string]any
	testutil.GoldenField(t, g, "empty_state", &wantEmpty)
	testutil.GoldenField(t, g, "state_after_ep1", &want1)
	testutil.GoldenField(t, g, "state_after_2", &want2)
	testutil.GoldenField(t, g, "ep1_state_diff", &diff1)
	testutil.GoldenField(t, g, "diff2", &diff2)

	s0 := state.Empty(w)
	if got := asGeneric(t, s0); !reflect.DeepEqual(got, wantEmpty) {
		t.Fatalf("empty state\n got %v\nwant %v", got, wantEmpty)
	}
	s1 := state.ApplyDiff(s0, diff1, 1)
	if got := asGeneric(t, s1); !reflect.DeepEqual(got, want1) {
		t.Fatalf("after ep1\n got %v\nwant %v", got, want1)
	}
	// Deliberate deviation: the prototype's list comprehension checks against the old list, so a
	// fact repeated inside one facts_add ("f1", "f1") was added twice. The port de-duplicates.
	w2 := want2.(map[string]any)
	facts := w2["facts"].([]any)
	w2["facts"] = facts[:len(facts)-1]
	s2 := state.ApplyDiff(s1, diff2, 2)
	if got := asGeneric(t, s2); !reflect.DeepEqual(got, want2) {
		t.Fatalf("after 2\n got %v\nwant %v", got, want2)
	}
	// ApplyDiff must not mutate its input.
	if got := asGeneric(t, s0); !reflect.DeepEqual(got, wantEmpty) {
		t.Fatal("input state mutated")
	}
}

func TestApplyDiffLenient(t *testing.T) {
	s := state.Empty(testutil.World(t))
	out := state.ApplyDiff(s, map[string]any{
		"open_threads_add": "one thread", // string instead of list
		"facts_add":        []any{"f", nil, 3.0},
		"timeline_add":     []any{"a", "b"},
		"unknown_key":      true,
	}, 4)
	if !reflect.DeepEqual(out.OpenThreads, []string{"one thread"}) {
		t.Errorf("threads %q", out.OpenThreads)
	}
	if !reflect.DeepEqual(out.Facts, []string{"f", "3"}) {
		t.Errorf("facts %q", out.Facts)
	}
	if len(out.Timeline) != 1 || out.Timeline[0].Event != "a b" || out.Timeline[0].Episode != 4 {
		t.Errorf("timeline %+v", out.Timeline)
	}
	if out.CurrentLocation != "l_post" {
		t.Errorf("location changed: %s", out.CurrentLocation)
	}
}

func TestMergeCanon(t *testing.T) {
	w := testutil.World(t)
	got := state.MergeCanon(w, []string{}, []string{"c1", "c1", "bogus"})
	if !reflect.DeepEqual(got, []string{"c1"}) {
		t.Fatalf("got %q", got)
	}
	if got := state.MergeCanon(w, nil, nil); got == nil || len(got) != 0 {
		t.Fatalf("got %#v", got)
	}
}
