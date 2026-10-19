package worker_test

import (
	"context"
	"strings"
	"testing"
	"time"

	"github.com/ol1n/webtoon/backend/internal/fakes"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/testutil"
	"github.com/ol1n/webtoon/backend/internal/translate"
	"github.com/ol1n/webtoon/backend/internal/worker"
)

func readyEpisode(t *testing.T, langs ...string) *harness {
	t.Helper()
	h := newHarness(t, func(c *worker.Config) { c.Langs = langs })
	h.store.addCampaignWithEpisode("cp1", "ep1", storyboard.FirstPremise(testutil.World(t)), nil)
	h.drain()
	if ep := h.store.episode("ep1"); ep.Status != "ready" {
		t.Fatalf("episode not ready: %s %s", ep.Status, ep.Error)
	}
	return h
}

func TestReadyEpisodeIsTranslated(t *testing.T) {
	h := readyEpisode(t, "en", "de", "cs") // cs is the source and is skipped
	if n := h.llm.Calls(fakes.KindBubbles); n != 2 {
		t.Fatalf("expected one translation call per target (en, de), got %d", n)
	}
	ep := h.store.episode("ep1")
	if !strings.HasPrefix(ep.TitleI18n["en"], "[English] ") || !strings.HasPrefix(ep.TitleI18n["de"], "[German] ") {
		t.Fatalf("title i18n %v", ep.TitleI18n)
	}
	if _, ok := ep.TitleI18n["cs"]; ok {
		t.Fatal("source language must not be translated")
	}
	for _, c := range ep.Choices {
		if c.Text != "" && c.I18n["en"] != "[English] "+c.Text {
			t.Fatalf("choice %s i18n %v", c.ID, c.I18n)
		}
	}
	bubbles := 0
	for i := range 6 {
		for _, b := range h.store.panel("ep1", i).SB.Bubbles {
			bubbles++
			if b.I18n["de"] != "[German] "+b.Text {
				t.Fatalf("panel %d bubble %q i18n %v", i, b.Text, b.I18n)
			}
		}
	}
	if bubbles == 0 {
		t.Fatal("golden storyboard has no bubbles")
	}
}

func TestTranslationSkipsCompleteLanguages(t *testing.T) {
	h := readyEpisode(t, "en")
	if h.llm.Calls(fakes.KindBubbles) != 1 {
		t.Fatalf("calls %d", h.llm.Calls(fakes.KindBubbles))
	}
	done, err := h.w.TranslateEpisode(context.Background(), worker.TranslatePayload{EpisodeID: "ep1", Langs: []string{"en", "fr"}})
	if err != nil {
		t.Fatal(err)
	}
	if strings.Join(done, ",") != "fr" || h.llm.Calls(fakes.KindBubbles) != 2 {
		t.Fatalf("expected only fr to be translated, got %v (calls %d)", done, h.llm.Calls(fakes.KindBubbles))
	}
	done, err = h.w.TranslateEpisode(context.Background(), worker.TranslatePayload{EpisodeID: "ep1", Langs: []string{"en"}, Force: true})
	if err != nil || strings.Join(done, ",") != "en" {
		t.Fatalf("force: %v %v", done, err)
	}
}

func TestTranslationWaitsForLLM(t *testing.T) {
	h := newHarness(t, func(c *worker.Config) { c.Langs = []string{"en"} })
	h.store.addCampaignWithEpisode("cp1", "ep1", storyboard.FirstPremise(testutil.World(t)), nil)
	h.step() // storyboard while the LLM is up
	for range 6 {
		h.step()
	}
	h.llm.Down.Store(true)
	h.step() // translation job: LLM off schedule → deferred, attempt not burned
	j := h.store.jobs[len(h.store.jobs)-1]
	if j.Kind != worker.KindTranslate || j.Status != "queued" || !j.RunAfter.After(h.store.now) {
		t.Fatalf("translate job %s status=%s run_after=%v", j.Kind, j.Status, j.RunAfter)
	}
	h.llm.Down.Store(false)
	h.store.advance(6 * time.Minute)
	h.drain()
	if ep := h.store.episode("ep1"); ep.TitleI18n["en"] == "" {
		t.Fatal("translation did not resume after the LLM came back")
	}
}

func TestIncompleteTranslationRetries(t *testing.T) {
	h := newHarness(t, func(c *worker.Config) { c.Langs = []string{"en"} })
	h.llm.DropID = translate.BubbleID(1, 0)
	h.store.addCampaignWithEpisode("cp1", "ep1", storyboard.FirstPremise(testutil.World(t)), nil)
	h.drain()
	j := h.store.jobs[len(h.store.jobs)-1]
	if j.Kind != worker.KindTranslate || j.Status != "queued" || !strings.Contains(j.LastErr, "no translation for [p1b0]") {
		t.Fatalf("expected a retry of the incomplete translation, got %s %s %q", j.Kind, j.Status, j.LastErr)
	}
	if ep := h.store.episode("ep1"); len(ep.TitleI18n) != 0 {
		t.Fatal("an incomplete reply must store nothing")
	}
}
