package tags_test

import (
	"context"
	"encoding/json"
	"reflect"
	"strings"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/tags"
	"github.com/ol1n/webtoon/backend/internal/testutil"
)

func TestSplitNorm(t *testing.T) {
	g := testutil.Golden(t)
	var want []string
	testutil.GoldenField(t, g, "split_sample", &want)
	got := tags.Split("  Red_Hair,  green   eyes ,, ,Smile ")
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("Split = %q, want %q", got, want)
	}
	if got := tags.Split([]any{"A_b", " ", "c"}); !reflect.DeepEqual(got, []string{"a b", "c"}) {
		t.Fatalf("Split(list) = %q", got)
	}
	if got := tags.Split(nil); len(got) != 0 {
		t.Fatalf("Split(nil) = %q", got)
	}
}

func TestFilterMatchesPrototype(t *testing.T) {
	g := testutil.Golden(t)
	var sample []string
	var want [2][]string
	testutil.GoldenField(t, g, "filter_sample", &sample)
	testutil.GoldenField(t, g, "filter_result", &want)
	known, unknown := testutil.Vocab(t).Filter(sample)
	if !reflect.DeepEqual(known, want[0]) || !reflect.DeepEqual(unknown, want[1]) {
		t.Fatalf("Filter = %q / %q, want %q / %q", known, unknown, want[0], want[1])
	}
}

func TestExtraTagsKnown(t *testing.T) {
	v := testutil.Vocab(t)
	for _, tag := range []string{"masterpiece", "no humans", "over-the-shoulder shot", "1girl"} {
		if !v.Has(tag) {
			t.Errorf("%q should be known", tag)
		}
	}
}

func TestCandidatesAndTranslatePrompt(t *testing.T) {
	g := testutil.Golden(t)
	var cands map[string][]string
	var phrases []string
	var prompt string
	testutil.GoldenField(t, g, "candidates", &cands)
	testutil.GoldenField(t, g, "ep1_translate_phrases", &phrases)
	testutil.GoldenField(t, g, "ep1_translate_prompt", &prompt)
	v := testutil.Vocab(t)
	for p, want := range cands {
		if got := v.Candidates(p, 8); !reflect.DeepEqual(got, want) {
			t.Errorf("Candidates(%q) = %q, want %q", p, got, want)
		}
	}
	if got := v.TranslatePrompt(phrases); got != prompt {
		t.Fatalf("TranslatePrompt mismatch\n got: %s\nwant: %s", got, prompt)
	}
}

func TestTranslateFiltersLLMOutput(t *testing.T) {
	llm := &testutil.ScriptedLLM{Handler: func(_, user string) (string, error) {
		if !strings.Contains(user, "'glowing envelope'") {
			t.Errorf("phrase missing from prompt: %s", user)
		}
		return `{"map": {"glowing envelope": ["envelope", "glowing", "magic_glowy_thing"], "warm light": "sunlight, light rays"}}`, nil
	}}
	got, err := testutil.Vocab(t).Translate(context.Background(), llm, []string{"glowing envelope", "warm light"})
	if err != nil {
		t.Fatal(err)
	}
	want := map[string][]string{"glowing envelope": {"envelope", "glowing"}, "warm light": {"sunlight", "light rays"}}
	if !reflect.DeepEqual(got, want) {
		b, _ := json.Marshal(got)
		t.Fatalf("Translate = %s", b)
	}
	if len(llm.Calls) != 1 || llm.Calls[0].System != "You are a Danbooru tagging expert." {
		t.Fatalf("calls = %+v", llm.Calls)
	}
}

func TestDedupe(t *testing.T) {
	if got := tags.Dedupe([]string{"a", "b", "a", "c", "b"}); !reflect.DeepEqual(got, []string{"a", "b", "c"}) {
		t.Fatal(got)
	}
}
