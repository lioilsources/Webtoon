package prompt_test

import (
	"strings"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/prompt"
	"github.com/ol1n/webtoon/backend/internal/testutil"
)

type golden struct {
	Positive string `json:"positive"`
	Negative string `json:"negative"`
	Width    int    `json:"width"`
	Height   int    `json:"height"`
}

func TestBuildMatchesPrototype(t *testing.T) {
	g := testutil.Golden(t)
	var want, wantNoSFW []golden
	testutil.GoldenField(t, g, "prompts", &want)
	testutil.GoldenField(t, g, "prompts_nosfw", &wantNoSFW)
	w, st, sb := testutil.World(t), testutil.Styles(t), testutil.StoryboardEP1(t)
	for i := range sb.Panels {
		got, err := prompt.Build(&sb.Panels[i], w, st, "", true)
		if err != nil {
			t.Fatal(err)
		}
		if got.Positive != want[i].Positive {
			t.Errorf("panel %d positive\n got: %s\nwant: %s", i, got.Positive, want[i].Positive)
		}
		if got.Negative != want[i].Negative {
			t.Errorf("panel %d negative\n got: %s\nwant: %s", i, got.Negative, want[i].Negative)
		}
		if got.Width != want[i].Width || got.Height != want[i].Height {
			t.Errorf("panel %d size %dx%d, want %dx%d", i, got.Width, got.Height, want[i].Width, want[i].Height)
		}
	}
	for i := range wantNoSFW {
		got, err := prompt.Build(&sb.Panels[i], w, st, "hassaku_soft", false)
		if err != nil {
			t.Fatal(err)
		}
		if got.Positive != wantNoSFW[i].Positive || got.Negative != wantNoSFW[i].Negative {
			t.Errorf("nosfw panel %d\n got: %s | %s\nwant: %s | %s", i, got.Positive, got.Negative,
				wantNoSFW[i].Positive, wantNoSFW[i].Negative)
		}
	}
}

func TestBuildOrderAndConflicts(t *testing.T) {
	w, st := testutil.World(t), testutil.Styles(t)
	p := &domain.SBPanel{
		Shot: "medium", LocationID: "l_post",
		Characters: []domain.SBChar{{ID: "c_vesna"}},
		// "long hair" conflicts with the design (short hair) and must go; "letter" stays,
		// and the always-negative "letters" must be dropped because the scene needs a letter.
		VisualTags: []string{"1girl", "holding letter", "letter", "long hair", "orange hair", "smile"},
	}
	r, err := prompt.Build(p, w, st, "", true)
	if err != nil {
		t.Fatal(err)
	}
	pos := strings.Split(r.Positive, ", ")
	idx := func(tag string) int {
		for i, x := range pos {
			if x == tag {
				return i
			}
		}
		return -1
	}
	order := []string{"masterpiece", "1girl", "solo", "short hair", "(artist:ningen mame:0.8)", "flat color",
		"upper body", "holding letter", "indoors", "general"}
	for i := 1; i < len(order); i++ {
		if idx(order[i-1]) < 0 || idx(order[i]) < 0 || idx(order[i-1]) > idx(order[i]) {
			t.Fatalf("order broken at %q < %q in %s", order[i-1], order[i], r.Positive)
		}
	}
	if idx("long hair") >= 0 {
		t.Error("design-conflicting scene tag kept")
	}
	if idx("orange hair") < 0 {
		t.Error("design tag also present in tag_prompt must stay")
	}
	if strings.Contains(", "+r.Negative+", ", ", letters, ") {
		t.Error("negative 'letters' must be removed when 'letter' is positive")
	}
	for _, must := range []string{"text", "speech bubble", "watermark", "signature", "nsfw"} {
		if !strings.Contains(", "+r.Negative+", ", ", "+must+", ") {
			t.Errorf("negative lacks %q", must)
		}
	}
	if _, err := prompt.Build(p, w, st, "nope", true); err == nil {
		t.Error("unknown preset must fail")
	}
}

func TestCountTags(t *testing.T) {
	cases := []struct {
		chars []domain.Character
		want  string
	}{
		{nil, "no humans"},
		{[]domain.Character{{CountTag: "1girl"}}, "1girl, solo"},
		{[]domain.Character{{CountTag: "1girl"}, {CountTag: "1girl"}, {CountTag: "1boy"}}, "2girls, 1boy"},
	}
	for _, c := range cases {
		if got := strings.Join(prompt.CountTags(c.chars), ", "); got != c.want {
			t.Errorf("CountTags = %q, want %q", got, c.want)
		}
	}
}
