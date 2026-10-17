// Package tags handles booru tags: normalisation, filtering against the WD14 vocabulary,
// and the LLM-assisted translation of free-text phrases (port of m0/common.py).
package tags

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/pyfmt"
)

// ExtraTags are tags the WD14 vocabulary lacks but the SDXL booru models understand.
var ExtraTags = []string{
	"masterpiece", "best quality", "newest", "absurdres", "highres", "very aesthetic",
	"general", "sensitive", "safe", "1girl", "1boy", "2girls", "2boys", "no humans",
	"establishing shot", "wide shot", "close-up", "medium shot", "over-the-shoulder shot",
}

// Vocab is the WD14 general-tag list (frequency ranked) plus ExtraTags.
type Vocab struct {
	ranked []string
	set    map[string]struct{}
}

// LoadVocab parses data/wd14_tags.json ({"model": ..., "general": [...]}).
func LoadVocab(raw []byte) (*Vocab, error) {
	var f struct {
		General []string `json:"general"`
	}
	if err := json.Unmarshal(raw, &f); err != nil {
		return nil, fmt.Errorf("wd14 tags: %w", err)
	}
	return NewVocab(f.General), nil
}

func NewVocab(general []string) *Vocab {
	v := &Vocab{ranked: general, set: make(map[string]struct{}, len(general)+len(ExtraTags))}
	for _, t := range general {
		v.set[t] = struct{}{}
	}
	for _, t := range ExtraTags {
		v.set[t] = struct{}{}
	}
	return v
}

func (v *Vocab) Has(t string) bool { _, ok := v.set[t]; return ok }

var wsRE = regexp.MustCompile(`\s+`)

// Norm = norm_tag: trim, lowercase, "_" → " ", collapse whitespace.
func Norm(t string) string {
	t = strings.ReplaceAll(strings.ToLower(strings.TrimSpace(t)), "_", " ")
	return wsRE.ReplaceAllString(t, " ")
}

// Split = split_tags: a string is split on commas, a list is taken item by item; blanks dropped.
func Split(s any) []string {
	var items []string
	switch x := s.(type) {
	case nil:
		return nil
	case string:
		items = strings.Split(x, ",")
	case []string:
		items = x
	case []any:
		for _, it := range x {
			if str, ok := it.(string); ok {
				items = append(items, str)
			} else if it != nil {
				items = append(items, fmt.Sprint(it))
			}
		}
	default:
		items = strings.Split(fmt.Sprint(x), ",")
	}
	out := make([]string, 0, len(items))
	for _, t := range items {
		if strings.TrimSpace(t) != "" {
			out = append(out, Norm(t))
		}
	}
	return out
}

var weightedRE = regexp.MustCompile(`^\((.*?)(:[\d.]+)?\)$`)

// Filter splits tags into (known, unknown). Weighted tags "(red hair:1.2)" are checked by
// their bare tag; "artist:x" passes untouched.
func (v *Vocab) Filter(tags []string) (known, unknown []string) {
	known, unknown = []string{}, []string{}
	for _, t := range tags {
		bare := weightedRE.ReplaceAllString(t, "$1")
		if strings.HasPrefix(t, "artist:") || v.Has(bare) {
			known = append(known, t)
		} else {
			unknown = append(unknown, t)
		}
	}
	return known, unknown
}

func Dedupe(tags []string) []string {
	seen := make(map[string]struct{}, len(tags))
	out := make([]string, 0, len(tags))
	for _, t := range tags {
		if _, ok := seen[t]; !ok {
			seen[t] = struct{}{}
			out = append(out, t)
		}
	}
	return out
}

var stopwords = map[string]bool{"a": true, "an": true, "the": true, "of": true, "in": true, "on": true, "at": true,
	"with": true, "and": true, "to": true, "from": true, "is": true, "girl": true, "boy": true}

var wordRE = regexp.MustCompile(`[a-z]+`)

// Candidates = tag_candidates: vocabulary tags sharing a word with phrase, most frequent first.
func (v *Vocab) Candidates(phrase string, limit int) []string {
	words := map[string]bool{}
	for _, w := range wordRE.FindAllString(strings.ToLower(phrase), -1) {
		if !stopwords[w] && len(w) > 2 {
			words[w] = true
		}
	}
	var singular []string
	for w := range words {
		if strings.HasSuffix(w, "s") {
			singular = append(singular, w[:len(w)-1])
		}
	}
	for _, w := range singular {
		words[w] = true
	}
	hits := []string{}
	for _, t := range v.ranked {
		for _, tw := range strings.Fields(t) {
			if words[tw] {
				hits = append(hits, t)
				break
			}
		}
		if len(hits) >= limit {
			break
		}
	}
	return hits
}

const translatePrompt = `Map each free-text phrase to EXISTING Danbooru tags for an SDXL anime model.
For each phrase you get candidate tags from the tag dictionary; prefer them, but you may use other very common Danbooru tags.
Drop phrases that are not visual or are already covered (e.g. "teen girl" — counts are added automatically, "vertical composition").
Phrases with candidates:
%s
Output JSON: {"map": {"<phrase>": ["<tag>", ...]}}`

const translateSystem = "You are a Danbooru tagging expert."

// TranslatePrompt renders the user message exactly as the prototype did (Python repr of phrase and candidates).
func (v *Vocab) TranslatePrompt(phrases []string) string {
	lines := make([]string, len(phrases))
	for i, p := range phrases {
		lines[i] = "- " + pyfmt.Repr(p) + ": " + pyfmt.Repr(v.Candidates(p, 8))
	}
	return fmt.Sprintf(translatePrompt, strings.Join(lines, "\n"))
}

// Translate = translate_tags: free-text phrases → {phrase: [known booru tags]} via one LLM call.
func (v *Vocab) Translate(ctx context.Context, c llm.JSONCaller, phrases []string) (map[string][]string, error) {
	if len(phrases) == 0 {
		return map[string][]string{}, nil
	}
	raw, err := c.JSON(ctx, translateSystem, v.TranslatePrompt(phrases), 0.2)
	if err != nil {
		return nil, err
	}
	var res struct {
		Map map[string]any `json:"map"`
	}
	if err := json.Unmarshal(raw, &res); err != nil {
		return map[string][]string{}, nil // shape mismatch: treat like an empty map, as .get("map", {}) would
	}
	out := make(map[string][]string, len(res.Map))
	for p, t := range res.Map {
		known, _ := v.Filter(Split(t))
		out[p] = known
	}
	return out, nil
}
