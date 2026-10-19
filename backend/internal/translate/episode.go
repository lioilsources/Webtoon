package translate

import (
	"fmt"

	"github.com/ol1n/webtoon/backend/internal/domain"
)

// Episode is the reader-facing text of one episode, as stored (originals + i18n maps).
type Episode struct {
	Title     string
	TitleI18n map[string]string
	Panels    [][]domain.Bubble // per panel index
	Choices   []domain.Choice
	Names     map[string]string // character id → name
}

// Complete reports whether every non-empty text has a translation into lang.
func (e *Episode) Complete(lang string) bool {
	if e.Title != "" && e.TitleI18n[lang] == "" {
		return false
	}
	for _, bs := range e.Panels {
		for _, b := range bs {
			if b.Text != "" && b.I18n[lang] == "" {
				return false
			}
		}
	}
	for _, c := range e.Choices {
		if c.Text != "" && c.I18n[lang] == "" {
			return false
		}
	}
	return true
}

// Languages lists the targets (Langs order) the episode is fully translated into.
func (e *Episode) Languages() []string {
	var out []string
	for _, l := range Langs {
		if e.Complete(l) {
			out = append(out, l)
		}
	}
	return out
}

// Items lists every non-empty text of the episode for the prompt.
func (e *Episode) Items() []Item {
	var items []Item
	if e.Title != "" {
		items = append(items, Item{ID: "title", Kind: "title", Text: e.Title})
	}
	for p, bs := range e.Panels {
		for i, b := range bs {
			if b.Text == "" {
				continue
			}
			it := Item{ID: BubbleID(p, i), Kind: b.Kind, Text: b.Text}
			if b.SpeakerID != nil {
				it.Speaker = e.Names[*b.SpeakerID]
			}
			items = append(items, it)
		}
	}
	for i, c := range e.Choices {
		if c.Text != "" {
			items = append(items, Item{ID: ChoiceID(i), Kind: "choice", Text: c.Text})
		}
	}
	return items
}

func BubbleID(panel, bubble int) string { return fmt.Sprintf("p%db%d", panel, bubble) }
func ChoiceID(i int) string             { return fmt.Sprintf("c%d", i) }

// Pair is one translated text together with the original it was made from; stores apply it only
// while the original is unchanged (an edit during translation wins).
type Pair struct{ Src, Dst string }

// Result is one language's translation of an episode, keyed by position.
type Result struct {
	Lang    string
	Title   *Pair
	Choices map[int]Pair
	Bubbles map[int]map[int]Pair // panel → bubble
}

// Collect maps Run's id → text reply back onto episode positions.
func (e *Episode) Collect(lang string, got map[string]string) Result {
	r := Result{Lang: lang, Choices: map[int]Pair{}, Bubbles: map[int]map[int]Pair{}}
	if t, ok := got["title"]; ok && e.Title != "" {
		r.Title = &Pair{Src: e.Title, Dst: t}
	}
	for p, bs := range e.Panels {
		for i, b := range bs {
			if t, ok := got[BubbleID(p, i)]; ok && b.Text != "" {
				if r.Bubbles[p] == nil {
					r.Bubbles[p] = map[int]Pair{}
				}
				r.Bubbles[p][i] = Pair{Src: b.Text, Dst: t}
			}
		}
	}
	for i, c := range e.Choices {
		if t, ok := got[ChoiceID(i)]; ok && c.Text != "" {
			r.Choices[i] = Pair{Src: c.Text, Dst: t}
		}
	}
	return r
}

// ApplyBubbles sets lang on bubbles whose text still equals the translated original.
func ApplyBubbles(bs []domain.Bubble, lang string, pairs map[int]Pair) bool {
	changed := false
	for i, p := range pairs {
		if i < len(bs) && bs[i].Text == p.Src {
			if bs[i].I18n == nil {
				bs[i].I18n = map[string]string{}
			}
			bs[i].I18n[lang] = p.Dst
			changed = true
		}
	}
	return changed
}

// ApplyChoices is ApplyBubbles for choices.
func ApplyChoices(cs []domain.Choice, lang string, pairs map[int]Pair) {
	for i, p := range pairs {
		if i < len(cs) && cs[i].Text == p.Src {
			if cs[i].I18n == nil {
				cs[i].I18n = map[string]string{}
			}
			cs[i].I18n[lang] = p.Dst
		}
	}
}

// KeepI18n carries translations from old to edited bubbles at the same position when the text
// is unchanged and drops them otherwise. Reports whether any original text changed.
func KeepI18n(old, edited []domain.Bubble) bool {
	changed := len(old) != len(edited)
	for i := range edited {
		if i < len(old) && old[i].Text == edited[i].Text {
			edited[i].I18n = old[i].I18n
			continue
		}
		edited[i].I18n = nil
		changed = true
	}
	return changed
}
