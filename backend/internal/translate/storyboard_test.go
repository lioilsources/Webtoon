package translate_test

import (
	"context"
	"encoding/json"
	"strings"
	"testing"
	"time"

	"github.com/ol1n/webtoon/backend/internal/fakes"
	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/translate"
)

// As m0/common.py writes it: indent 2, UTF-8, no trailing newline, fields the backend does not know.
const sbFile = `{
  "title": "Lia a měsíce",
  "panels": [
    {
      "shot": "establishing",
      "bubbles": [
        {
          "speaker_id": "",
          "text": "Loď letí <rychle> & tiše.",
          "kind": "narration"
        }
      ],
      "x_ratio": 2.50,
      "x_custom": {
        "keep": true
      }
    },
    {
      "shot": "close",
      "bubbles": [],
      "sfx": []
    },
    {
      "shot": "medium",
      "bubbles": [
        {
          "speaker_id": "c_lia",
          "text": "Ahoj!",
          "kind": "speech"
        },
        {
          "speaker_id": "c_lia",
          "text": "",
          "kind": "thought"
        }
      ]
    }
  ],
  "choices": [
    {
      "kind": "closed",
      "text": "Přistát"
    }
  ]
}`

func TestStoryboardFileInPlace(t *testing.T) {
	f := fakes.NewLLM("{}")
	defer f.Close()
	c := llm.New(f.URL+"/v1", "m")
	c.RetryWait = time.Millisecond

	sb, err := translate.ParseStoryboardFile([]byte(sbFile), "", map[string]string{"c_lia": "Lia"})
	if err != nil {
		t.Fatal(err)
	}
	if got := strings.Join(sb.Missing([]string{"cs", "en", "de"}), ","); got != "en,de" {
		t.Fatalf("missing %q (source cs is no target)", got)
	}
	saves := 0
	done, err := translate.TranslateStoryboard(context.Background(), c, sb, []string{"en", "de"}, false, func(string) error { saves++; return nil })
	if err != nil || strings.Join(done, ",") != "en,de" || saves != 2 || f.Calls(fakes.KindBubbles) != 2 {
		t.Fatalf("done %v err %v saves %d calls %d", done, err, saves, f.Calls(fakes.KindBubbles))
	}
	out, err := sb.Marshal()
	if err != nil {
		t.Fatal(err)
	}
	s := string(out)
	for _, want := range []string{
		"{\n  \"title\": \"Lia a měsíce\",\n  \"title_i18n\": {\n    \"de\": \"[German] Lia a měsíce\",",
		`"text": "Loď letí <rychle> & tiše.",`, // no HTML escaping, UTF-8 as is
		`"en": "[English] Loď letí <rychle> & tiše."`,
		`"x_ratio": 2.50,`, // number literal kept
		"\"x_custom\": {\n        \"keep\": true\n      }",
		`"en": "[English] Přistát"`,
		`"en": "[English] Ahoj!"`,
	} {
		if !strings.Contains(s, want) {
			t.Errorf("output lacks %q:\n%s", want, s)
		}
	}
	if strings.HasSuffix(s, "\n") {
		t.Error("trailing newline added")
	}
	// The empty thought gets no i18n; the panel order and keys stay.
	var parsed struct {
		Panels []struct {
			Bubbles []map[string]any `json:"bubbles"`
		} `json:"panels"`
	}
	if err := json.Unmarshal(out, &parsed); err != nil {
		t.Fatal(err)
	}
	if _, ok := parsed.Panels[2].Bubbles[1]["i18n"]; ok || len(parsed.Panels) != 3 {
		t.Fatalf("panels %+v", parsed.Panels)
	}

	// Rerun on the written file: complete, nothing to do; -force asks again.
	again, err := translate.ParseStoryboardFile(out, "cs", nil)
	if err != nil {
		t.Fatal(err)
	}
	if m := again.Missing([]string{"en", "de"}); len(m) != 0 || strings.Join(again.Languages(), ",") != "en,de" {
		t.Fatalf("missing %v languages %v", m, again.Languages())
	}
	done, err = translate.TranslateStoryboard(context.Background(), c, again, []string{"en", "de"}, false, nil)
	if err != nil || len(done) != 0 || f.Calls(fakes.KindBubbles) != 2 {
		t.Fatalf("complete file translated again: %v %v", done, err)
	}
	if done, _ = translate.TranslateStoryboard(context.Background(), c, again, []string{"en"}, true, nil); len(done) != 1 {
		t.Fatalf("force: %v", done)
	}
}
