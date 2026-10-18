package chargen_test

import (
	"context"
	"encoding/json"
	"errors"
	"reflect"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/chargen"
	"github.com/ol1n/webtoon/backend/internal/testutil"
	"github.com/ol1n/webtoon/backend/internal/upstream"
)

type call struct {
	System      string  `json:"system"`
	User        string  `json:"user"`
	Temperature float64 `json:"temperature"`
}

// scripted answers from a list and records system/user/temperature.
type scripted struct {
	replies []json.RawMessage
	calls   []call
}

func (s *scripted) JSON(_ context.Context, system, user string, temp float64) (json.RawMessage, error) {
	s.calls = append(s.calls, call{system, user, temp})
	if len(s.calls) > len(s.replies) {
		return nil, errors.New("unexpected call")
	}
	return s.replies[len(s.calls)-1], nil
}

func TestGenerateMatchesPrototype(t *testing.T) {
	g := testutil.Golden(t)
	var system string
	testutil.GoldenField(t, g, "gen_character_system", &system)
	if system != chargen.CharacterSystem {
		t.Fatalf("system prompt differs\n got: %q\nwant: %q", chargen.CharacterSystem, system)
	}
	for _, sc := range []string{"gen_character", "gen_character2"} {
		var replies []json.RawMessage
		var want struct {
			Known   []string `json:"known"`
			Unknown []string `json:"unknown"`
		}
		var wantCalls []call
		testutil.GoldenField(t, g, sc+"_replies", &replies)
		testutil.GoldenField(t, g, sc+"_result", &want)
		testutil.GoldenField(t, g, sc+"_calls", &wantCalls)
		llm := &scripted{replies: replies}
		res, err := chargen.Generate(context.Background(), llm, testutil.Vocab(t), chargen.CharacterSystem,
			"Vesna", "Mladá kurýrka s krátkými zrzavými vlasy.")
		if err != nil {
			t.Fatal(err)
		}
		if !reflect.DeepEqual(res.Tags, want.Known) || !reflect.DeepEqual(res.Unknown, want.Unknown) {
			t.Errorf("%s: got %v / %v, want %v / %v", sc, res.Tags, res.Unknown, want.Known, want.Unknown)
		}
		if !reflect.DeepEqual(llm.calls, wantCalls) {
			t.Errorf("%s calls differ\n got: %+v\nwant: %+v", sc, llm.calls, wantCalls)
		}
	}
}

func TestDroppedAndReplaced(t *testing.T) {
	llm := &scripted{replies: []json.RawMessage{
		json.RawMessage(`{"tags": "short hair, copper hair, brown boots, green eyes", "notes": "ok"}`),
		json.RawMessage(`{"replace": {"copper hair": ["orange hair"], "brown boots": ["qqq unknown"]}}`),
		json.RawMessage(`{"tags": ["short hair", "orange hair", "green eyes"]}`),
	}}
	res, err := chargen.Generate(context.Background(), llm, testutil.Vocab(t), chargen.CharacterSystem, "A", "b")
	if err != nil {
		t.Fatal(err)
	}
	// Attempt 1 keeps "qqq unknown" as unknown, attempt 2 is clean and wins.
	if res.TagPrompt() != "short hair, orange hair, green eyes" || len(res.Unknown) != 0 || len(llm.calls) != 3 {
		t.Fatalf("%+v (%d calls)", res, len(llm.calls))
	}

	llm = &scripted{replies: []json.RawMessage{
		json.RawMessage(`{"tags": ["short hair", "copper hair", "brown boots"], "notes": "n1"}`),
		json.RawMessage(`{"replace": {"copper hair": ["orange hair"]}}`),
	}}
	res, _ = chargen.Generate(context.Background(), llm, testutil.Vocab(t), chargen.LocationSystem, "A", "b")
	if res.TagPrompt() != "short hair, orange hair" || !reflect.DeepEqual(res.Dropped, []string{"brown boots"}) ||
		!reflect.DeepEqual(res.Replaced, map[string][]string{"copper hair": {"orange hair"}}) || res.Notes != "n1" {
		t.Fatalf("%+v", res)
	}
}

type down struct{}

func (down) JSON(context.Context, string, string, float64) (json.RawMessage, error) {
	return nil, upstream.Unavailable("llm", errors.New("503"))
}

func TestLLMDown(t *testing.T) {
	if _, err := chargen.Generate(context.Background(), down{}, testutil.Vocab(t), chargen.CharacterSystem, "A", "b"); !upstream.IsUnavailable(err) {
		t.Fatalf("got %v", err)
	}
}

func TestSystemFor(t *testing.T) {
	if chargen.SystemFor("1girl") != chargen.CharacterSystem || chargen.SystemFor("1boy") != chargen.CharacterSystem {
		t.Fatal("humans keep the prototype prompt")
	}
	if chargen.SystemFor("") != chargen.CreatureSystem {
		t.Fatal("no count tag = pet/creature prompt")
	}
}
