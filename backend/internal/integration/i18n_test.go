package integration

import (
	"context"
	"encoding/json"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/fakes"
)

// Ready episodes are translated; an edited bubble loses its translations until the
// re-enqueued job translates the episode again.
func TestEpisodeTranslations(t *testing.T) {
	e := setup(t, "en", "de")
	ctx := context.Background()
	camp := e.do("POST", "/campaigns", "player", map[string]any{"world_id": "w_skyisles"}, 201)
	ep := camp["first_episode_id"].(string)
	e.drain()

	got := e.do("GET", "/episodes/"+ep, "player", nil, 200)
	if langs, _ := json.Marshal(got["languages"]); string(langs) != `["en","de"]` || got["source_language"] != "cs" {
		t.Fatalf("languages %s source %v", langs, got["source_language"])
	}
	if got["title_i18n"].(map[string]any)["de"] != "[German] "+got["title"].(string) {
		t.Fatalf("title_i18n %v", got["title_i18n"])
	}
	panel := got["panels"].([]any)[1].(map[string]any)
	b0 := panel["bubbles"].([]any)[0].(map[string]any)
	if b0["i18n"].(map[string]any)["en"] != "[English] "+b0["text"].(string) {
		t.Fatalf("bubble %v", b0)
	}
	camps := e.do("GET", "/campaigns/"+camp["campaign"].(map[string]any)["id"].(string), "player", nil, 200)
	if camps["episodes"].([]any)[0].(map[string]any)["title_i18n"].(map[string]any)["en"] == nil {
		t.Fatalf("campaign episode summary without title_i18n: %v", camps["episodes"])
	}
	calls := e.llm.Calls(fakes.KindBubbles)

	// Same text sent back (even with junk i18n from the client): translations kept, nothing enqueued.
	same := map[string]any{"speaker_id": b0["speaker_id"], "text": b0["text"], "kind": b0["kind"], "i18n": map[string]string{"en": "junk"}}
	p := e.do("PATCH", "/episodes/"+ep+"/panels/1", "player", map[string]any{"bubbles": []any{same}}, 200)
	if p["bubbles"].([]any)[0].(map[string]any)["i18n"].(map[string]any)["en"] != b0["i18n"].(map[string]any)["en"] {
		t.Fatalf("unchanged text must keep server translations: %v", p["bubbles"])
	}
	e.drain()
	if e.llm.Calls(fakes.KindBubbles) != calls {
		t.Fatal("unchanged text must not retranslate")
	}

	// Edited text: translations dropped, episode incomplete until the job runs.
	edited := map[string]any{"speaker_id": b0["speaker_id"], "text": "Nový text", "kind": b0["kind"]}
	p = e.do("PATCH", "/episodes/"+ep+"/panels/1", "player", map[string]any{"bubbles": []any{edited}}, 200)
	if _, ok := p["bubbles"].([]any)[0].(map[string]any)["i18n"]; ok {
		t.Fatalf("stale i18n kept: %v", p["bubbles"])
	}
	if n := len(e.do("GET", "/episodes/"+ep, "player", nil, 200)["languages"].([]any)); n != 0 {
		t.Fatalf("episode with an untranslated bubble still offers %d languages", n)
	}
	e.drain()
	row, _ := e.s.Q.GetPanel(ctx, mustPanelKey(ep, 1))
	var bs []map[string]any
	json.Unmarshal(row.Bubbles, &bs) //nolint:errcheck
	if bs[0]["i18n"].(map[string]any)["en"] != "[English] Nový text" {
		t.Fatalf("retranslated bubble %v", bs[0])
	}
	if e.llm.Calls(fakes.KindBubbles) != calls+2 {
		t.Fatalf("expected one call per language after the edit, got %d", e.llm.Calls(fakes.KindBubbles)-calls)
	}
}
