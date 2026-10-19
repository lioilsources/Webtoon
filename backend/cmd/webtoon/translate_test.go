package main

import (
	"testing"

	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/translate"
	"github.com/ol1n/webtoon/backend/internal/worker"
)

func TestMissingLangsSkipsCompleteAndSource(t *testing.T) {
	et := &worker.EpisodeText{Status: "ready", Source: "cs", Episode: translate.Episode{
		Title:     "Ahoj",
		TitleI18n: map[string]string{"en": "Hi", "de": "Hallo"},
		Panels:    [][]domain.Bubble{{{Text: "Dobrý den", I18n: map[string]string{"en": "Hello"}}}},
	}}
	if n := missingLangs(et, []string{"cs", "en"}); n != 0 {
		t.Fatalf("en complete, cs is the source: %d", n)
	}
	if n := missingLangs(et, []string{"en", "de", "ja"}); n != 2 {
		t.Fatalf("de lacks the bubble, ja everything: %d", n)
	}
}
