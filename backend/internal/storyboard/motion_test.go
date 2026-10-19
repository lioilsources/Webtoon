package storyboard

import (
	"strings"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/domain"
)

func TestCheckMotion(t *testing.T) {
	ok := []string{
		"her hair moves in the sea breeze, she slowly turns her head, static camera",
		"gentle rain on the window, candle flickers, static camera",
	}
	for _, m := range ok {
		if err := CheckMotion(m); err != nil {
			t.Errorf("%q: %v", m, err)
		}
	}
	bad := map[string]string{
		"": "empty",
		"she slowly removes her coat, static camera": "banned",
		"they kiss under the lantern":                "banned",
		"he lies on the bed and smiles":              "banned",
		strings.Repeat("wind ", 16):                  "words",
	}
	for m, why := range bad {
		if err := CheckMotion(m); err == nil {
			t.Errorf("%q should fail (%s)", m, why)
		}
	}
	if LoopSecondsOr(0) != 2 || LoopSecondsOr(7) != 3 || LoopSecondsOr(1) != 1 {
		t.Fatal("LoopSecondsOr")
	}
}

func TestNormalizeMotionCapsAndFences(t *testing.T) {
	one := []domain.SBChar{{ID: "a"}}
	two := []domain.SBChar{{ID: "a"}, {ID: "b"}}
	sb := &domain.Storyboard{Panels: []domain.SBPanel{
		{Shot: "establishing", Animate: true, Motion: "waves roll in, static camera"},
		{Shot: "medium", Characters: two, Animate: true, Motion: "they look at each other, static camera"},
		{Shot: "medium", Characters: one, Animate: true, Motion: "she unbuttons her coat"},
		{Shot: "medium", Characters: one, Animate: true, Motion: "her hair moves in the wind, static camera", LoopSeconds: 9},
		{Shot: "medium", Characters: one, Animate: true, Motion: "she raises her glass and smiles, static camera"},
		{Shot: "wide", Animate: false, Motion: "stale text"},
	}}
	warns := normalizeMotion(sb)
	got := []bool{}
	for _, p := range sb.Panels {
		got = append(got, p.Animate)
	}
	want := []bool{true, false, false, true, false, false}
	for i := range want {
		if got[i] != want[i] {
			t.Fatalf("animate flags %v, want %v (warnings %v)", got, want, warns)
		}
	}
	if sb.Panels[3].LoopSeconds != 3 || sb.Panels[0].LoopSeconds != DefaultLoopSeconds {
		t.Fatalf("loop seconds %d / %d", sb.Panels[3].LoopSeconds, sb.Panels[0].LoopSeconds)
	}
	if sb.Panels[5].Motion != "" || sb.Panels[1].Motion != "" {
		t.Fatal("dropped loops must clear their motion prompt")
	}
	if len(warns) != 3 {
		t.Fatalf("warnings %v", warns)
	}
}
