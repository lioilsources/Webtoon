package translate

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"

	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/llm"
)

// StoryboardFile is a storyboard.json (m0/adapt.py output) translated before it is rendered, so
// an imported episode is already in every language. Translations land in the file in the shape
// the API serves: panels[].bubbles[].i18n, choices[].i18n and a top-level title_i18n. Everything
// else in the file (unknown fields, key order, number literals) is written back unchanged.
type StoryboardFile struct {
	Episode
	Source string // world language ("" = cs)
	raw    []byte
}

// ParseStoryboardFile reads a storyboard.json. names maps character ids to names (speaker voice).
func ParseStoryboardFile(raw []byte, source string, names map[string]string) (*StoryboardFile, error) {
	var sb struct {
		domain.Storyboard
		TitleI18n map[string]string `json:"title_i18n"`
	}
	if err := json.Unmarshal(raw, &sb); err != nil {
		return nil, fmt.Errorf("storyboard: %w", err)
	}
	if source == "" {
		source = "cs"
	}
	f := &StoryboardFile{Source: source, raw: raw}
	f.Title, f.TitleI18n, f.Choices, f.Names = sb.Title, sb.TitleI18n, sb.Choices, names
	if f.TitleI18n == nil {
		f.TitleI18n = map[string]string{}
	}
	f.Panels = make([][]domain.Bubble, len(sb.Panels))
	for i, p := range sb.Panels {
		f.Panels[i] = p.Bubbles
	}
	return f, nil
}

// Missing lists the targets (Langs order, without the source) the file is not complete in.
func (f *StoryboardFile) Missing(langs []string) []string {
	var out []string
	for _, l := range Targets(langs, f.Source) {
		if !f.Complete(l) {
			out = append(out, l)
		}
	}
	return out
}

// Apply stores one language's result (same rules as the episode store: only onto unchanged originals).
func (f *StoryboardFile) Apply(r Result) {
	if r.Title != nil && f.Title == r.Title.Src {
		f.TitleI18n[r.Lang] = r.Title.Dst
	}
	for p, pairs := range r.Bubbles {
		if p < len(f.Panels) {
			ApplyBubbles(f.Panels[p], r.Lang, pairs)
		}
	}
	ApplyChoices(f.Choices, r.Lang, r.Choices)
}

// TranslateStoryboard translates f into every target language that is not complete (all of them
// with force), one Run per language as for episodes. After each language it calls save (may be
// nil), so an interrupted run keeps what it finished. Returns the languages it translated.
func TranslateStoryboard(ctx context.Context, c llm.JSONCaller, f *StoryboardFile, langs []string, force bool, save func(lang string) error) ([]string, error) {
	items := f.Items()
	var done []string
	for _, lang := range Targets(langs, f.Source) {
		if !force && f.Complete(lang) {
			continue
		}
		got, err := Run(ctx, c, f.Source, lang, items)
		if err != nil {
			return done, err
		}
		f.Apply(f.Collect(lang, got))
		if save != nil {
			if err := save(lang); err != nil {
				return done, err
			}
		}
		done = append(done, lang)
	}
	return done, nil
}

// Marshal returns the original file with the i18n maps set (indent 2, no ASCII/HTML escaping,
// like m0/common.py writes it).
func (f *StoryboardFile) Marshal() ([]byte, error) {
	top, err := parseObject(f.raw)
	if err != nil {
		return nil, err
	}
	if len(f.TitleI18n) > 0 {
		top.set("title_i18n", f.TitleI18n, "title")
	}
	var panels []json.RawMessage
	if raw, ok := top.vals["panels"]; ok {
		if err := json.Unmarshal(raw, &panels); err != nil {
			return nil, fmt.Errorf("panels: %w", err)
		}
	}
	for i := range panels {
		if i >= len(f.Panels) {
			break
		}
		p, err := parseObject(panels[i])
		if err != nil {
			return nil, fmt.Errorf("panel %d: %w", i, err)
		}
		if p.vals["bubbles"], err = setI18n(p.vals["bubbles"], func(j int) map[string]string {
			if j < len(f.Panels[i]) {
				return f.Panels[i][j].I18n
			}
			return nil
		}); err != nil {
			return nil, fmt.Errorf("panel %d bubbles: %w", i, err)
		}
		if panels[i], err = p.MarshalJSON(); err != nil {
			return nil, err
		}
	}
	if panels != nil {
		top.set("panels", panels, "")
	}
	if cs, ok := top.vals["choices"]; ok {
		if top.vals["choices"], err = setI18n(cs, func(j int) map[string]string {
			if j < len(f.Choices) {
				return f.Choices[j].I18n
			}
			return nil
		}); err != nil {
			return nil, fmt.Errorf("choices: %w", err)
		}
	}
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	enc.SetIndent("", "  ")
	if err := enc.Encode(top); err != nil {
		return nil, err
	}
	return bytes.TrimRight(buf.Bytes(), "\n"), nil
}

// setI18n sets "i18n" on every object of a JSON array that has translations.
func setI18n(arr json.RawMessage, i18n func(int) map[string]string) (json.RawMessage, error) {
	if len(arr) == 0 || string(arr) == "null" {
		return arr, nil
	}
	var items []json.RawMessage
	if err := json.Unmarshal(arr, &items); err != nil {
		return nil, err
	}
	for j := range items {
		m := i18n(j)
		if len(m) == 0 {
			continue
		}
		o, err := parseObject(items[j])
		if err != nil {
			return nil, err
		}
		o.set("i18n", m, "")
		if items[j], err = o.MarshalJSON(); err != nil {
			return nil, err
		}
	}
	return marshalNoEscape(items)
}

// object is a JSON object that keeps its key order.
type object struct {
	keys []string
	vals map[string]json.RawMessage
}

func parseObject(raw []byte) (*object, error) {
	dec := json.NewDecoder(bytes.NewReader(raw))
	if t, err := dec.Token(); err != nil || t != json.Delim('{') {
		return nil, fmt.Errorf("not a JSON object")
	}
	o := &object{vals: map[string]json.RawMessage{}}
	for dec.More() {
		t, err := dec.Token()
		if err != nil {
			return nil, err
		}
		k := t.(string)
		var v json.RawMessage
		if err := dec.Decode(&v); err != nil {
			return nil, err
		}
		if _, dup := o.vals[k]; !dup {
			o.keys = append(o.keys, k)
		}
		o.vals[k] = v
	}
	return o, nil
}

// set replaces k in place, or adds it after the key `after` (at the end when absent).
func (o *object) set(k string, v any, after string) {
	b, err := marshalNoEscape(v)
	if err != nil {
		panic(err) // maps of strings and raw messages always marshal
	}
	if _, ok := o.vals[k]; !ok {
		at := len(o.keys)
		for i, key := range o.keys {
			if key == after {
				at = i + 1
			}
		}
		o.keys = append(o.keys[:at], append([]string{k}, o.keys[at:]...)...)
	}
	o.vals[k] = b
}

func (o *object) MarshalJSON() ([]byte, error) {
	var buf bytes.Buffer
	buf.WriteByte('{')
	for i, k := range o.keys {
		if i > 0 {
			buf.WriteByte(',')
		}
		kb, _ := marshalNoEscape(k)
		buf.Write(kb)
		buf.WriteByte(':')
		buf.Write(o.vals[k])
	}
	buf.WriteByte('}')
	return buf.Bytes(), nil
}

func marshalNoEscape(v any) (json.RawMessage, error) {
	var buf bytes.Buffer
	enc := json.NewEncoder(&buf)
	enc.SetEscapeHTML(false)
	if err := enc.Encode(v); err != nil {
		return nil, err
	}
	return bytes.TrimRight(buf.Bytes(), "\n"), nil
}
