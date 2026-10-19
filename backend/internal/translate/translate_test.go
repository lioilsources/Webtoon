package translate_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/fakes"
	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/translate"
)

func sp(s string) *string { return &s }

func episode() *translate.Episode {
	return &translate.Episode{
		Title: "Santorini",
		Panels: [][]domain.Bubble{
			{{Text: "Santorini. Terasa.", Kind: "narration"}},
			{{SpeakerID: sp("elena"), Text: "Já jsem jen malá.", Kind: "thought"}, {SpeakerID: sp("nikos"), Text: "Nedá se přehlédnout.", Kind: "speech"}},
			{},
		},
		Choices: []domain.Choice{{ID: "c1", Kind: "closed", Text: "Zůstat"}, {ID: "free", Kind: "free", Text: "Nebo napiš…"}},
		Names:   map[string]string{"elena": "Elena", "nikos": "Nikos"},
	}
}

func TestRunRoundTrip(t *testing.T) {
	f := fakes.NewLLM("{}")
	defer f.Close()
	c := llm.New(f.URL+"/v1", "m")
	c.RetryWait = time.Millisecond
	e := episode()
	got, err := translate.Run(context.Background(), c, "cs", "en", e.Items())
	if err != nil {
		t.Fatal(err)
	}
	r := e.Collect("en", got)
	if r.Title == nil || r.Title.Dst != "[English] Santorini" || r.Bubbles[1][1].Dst != "[English] Nedá se přehlédnout." || r.Choices[1].Src != "Nebo napiš…" {
		t.Fatalf("collect %+v", r)
	}
	translate.ApplyBubbles(e.Panels[1], "en", r.Bubbles[1])
	translate.ApplyChoices(e.Choices, "en", r.Choices)
	e.TitleI18n = map[string]string{"en": r.Title.Dst}
	if e.Complete("en") {
		t.Fatal("panel 0 was not applied yet")
	}
	translate.ApplyBubbles(e.Panels[0], "en", r.Bubbles[0])
	if !e.Complete("en") || strings.Join(e.Languages(), ",") != "en" {
		t.Fatalf("languages %v", e.Languages())
	}
}

func TestRunSendsSchemaWithoutThinking(t *testing.T) {
	var body map[string]any
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewDecoder(r.Body).Decode(&body)                                                               //nolint:errcheck
		json.NewEncoder(w).Encode(map[string]any{"choices": []any{map[string]any{"message": map[string]any{ //nolint:errcheck
			"content": `{"translations": [{"id": "title", "text": "Hi"}]}`}}}})
	}))
	defer srv.Close()
	_, err := translate.Run(context.Background(), llm.New(srv.URL, "m"), "cs", "pt-BR", []translate.Item{{ID: "title", Kind: "title", Text: "Ahoj"}})
	if err != nil {
		t.Fatal(err)
	}
	rf, _ := body["response_format"].(map[string]any)
	kw, _ := body["chat_template_kwargs"].(map[string]any)
	if rf["type"] != "json_schema" || kw["enable_thinking"] != false || body["temperature"] != 0.0 {
		t.Fatalf("request %v", body)
	}
	msgs, _ := body["messages"].([]any)
	user := msgs[1].(map[string]any)["content"].(string)
	if !strings.Contains(user, "from Czech into Brazilian Portuguese") {
		t.Fatalf("prompt languages: %s", user[:80])
	}
}

func TestMissingIDIsAnError(t *testing.T) {
	f := fakes.NewLLM("{}")
	defer f.Close()
	f.DropID = "c0"
	_, err := translate.Run(context.Background(), llm.New(f.URL+"/v1", "m"), "cs", "de", episode().Items())
	if err == nil || !strings.Contains(err.Error(), "c0") {
		t.Fatalf("expected missing c0, got %v", err)
	}
}

func TestKeepI18n(t *testing.T) {
	old := []domain.Bubble{{Text: "A", I18n: map[string]string{"en": "A-en"}}, {Text: "B", I18n: map[string]string{"en": "B-en"}}}
	edited := []domain.Bubble{{Text: "A", I18n: map[string]string{"en": "client junk"}}, {Text: "B2", I18n: map[string]string{"en": "B-en"}}}
	if !translate.KeepI18n(old, edited) {
		t.Fatal("B changed")
	}
	if edited[0].I18n["en"] != "A-en" || edited[1].I18n != nil {
		t.Fatalf("i18n after edit %+v", edited)
	}
	same := []domain.Bubble{{Text: "A"}, {Text: "B"}}
	if translate.KeepI18n(old, same) || same[1].I18n["en"] != "B-en" {
		t.Fatal("unchanged texts keep translations and report no change")
	}
}

func TestTargets(t *testing.T) {
	if got := strings.Join(translate.Targets([]string{"ja", "cs", "xx", "en"}, "cs"), ","); got != "en,ja" {
		t.Fatal(got)
	}
	if n := len(translate.Targets(nil, "cs")); n != 11 {
		t.Fatalf("all minus source: %d", n)
	}
}
