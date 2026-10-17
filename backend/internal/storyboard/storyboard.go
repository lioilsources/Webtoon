// Package storyboard turns a premise / player choice into a validated storyboard (§5.1–5.3).
// Port of m0/storyboard.py: same system prompt, validation rules, tag translation step and
// lenient rule check.
package storyboard

import (
	"context"
	"encoding/json"
	"fmt"
	"slices"
	"strconv"
	"strings"

	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/pyfmt"
	"github.com/ol1n/webtoon/backend/internal/tags"
)

var (
	Shots       = []string{"close-up", "medium", "wide", "over-shoulder", "establishing"}
	BubbleKinds = []string{"speech", "thought", "shout", "narration"}
	Gaps        = []string{"small", "medium", "large"}
)

const (
	MinPanels = 6
	MaxPanels = 8
)

const systemTmpl = `You are the storyboard writer of an interactive vertical webtoon. You write ONE episode as strict JSON.

WORLD (static bible):
{world}

CHARACTERS (use only these ids):
{characters}

LOCATIONS (use only these ids):
{locations}

CANON NODES not yet reached (the episode may advance at most one): {canon}
CONSTRAINTS (never break): {constraints}

OUTPUT JSON schema:
{
  "title": "<episode title in {lang}>",
  "panels": [
    {
      "shot": one of {shots},
      "location_id": "<location id>",
      "characters": [{"id": "<character id>", "emotion": "<booru emotion tag>", "action": "<booru pose/action tags>"}],
      "visual_prompt": "<comma separated Danbooru tags: pose, action, expression, props, lighting, camera angle. NO character design tags (hair/clothes are added automatically), NO names, NO text>",
      "bubbles": [{"speaker_id": "<character id or null for narration>", "text": "<{lang}>", "kind": one of {kinds}}],
      "sfx": [{"text": "<onomatopoeia>", "style": "bold|shaky|soft"}],
      "gap_after": one of {gaps}
    }
  ],
  "choices": [
    {"kind": "closed", "text": "<{lang}>"},
    {"kind": "closed", "text": "<{lang}>"},
    {"kind": "free", "text": "Nebo napiš, co uděláš…"}
  ],
  "state_diff": {"current_location": "<location id>", "open_threads_add": [], "open_threads_remove": [], "facts_add": [], "timeline_add": "<one sentence>", "mood": "<word>"},
  "canon_nodes_reached": ["<canon node id>"]
}

Rules:
- {min_p}-{max_p} panels. Start with an establishing or wide shot. Vary shots. End on a hook that sets up the choices.
- An "establishing" panel has NO characters.
- Max 2 bubbles per panel, max ~12 words per bubble. Text in {lang}, fits the speech style of the character.
- visual_prompt uses ONLY real Danbooru tags (e.g. "standing, holding letter, looking at viewer, surprised, open mouth, glowing, from side, wind, hair blowing").
- 2-3 closed choices + exactly 1 free choice.
`

// Ordered like the prototype's dicts so the JSON text matches.
type worldCtx struct {
	Title    string `json:"title"`
	Synopsis string `json:"synopsis"`
	Tone     string `json:"tone"`
	Audience string `json:"audience"`
	Rules    any    `json:"rules"`
}

type charCtx struct {
	ID          string  `json:"id"`
	Name        string  `json:"name"`
	Role        string  `json:"role"`
	Personality *string `json:"personality"`
	SpeechStyle *string `json:"speech_style"`
}

type locCtx struct {
	ID          string `json:"id"`
	Name        string `json:"name"`
	Description string `json:"description"`
}

func strOrNil(s string) *string {
	if s == "" {
		return nil
	}
	return &s
}

// SystemPrompt renders the storyboard system prompt for a world and the campaign's reached canon nodes.
func SystemPrompt(w *domain.World, canonProgress []string) string {
	chars := make([]charCtx, 0, len(w.Characters))
	for _, c := range w.Characters {
		chars = append(chars, charCtx{c.ID, c.Name, c.Role, strOrNil(c.Personality), strOrNil(c.SpeechStyle)})
	}
	locs := make([]locCtx, 0, len(w.Locations))
	for _, l := range w.Locations {
		locs = append(locs, locCtx{l.ID, l.Name, l.Description})
	}
	canon := []domain.CanonNode{}
	for _, n := range w.Canon.Nodes {
		if !slices.Contains(canonProgress, n.ID) {
			canon = append(canon, n)
		}
	}
	lang := w.Language
	if lang == "" {
		lang = "cs"
	}
	r := strings.NewReplacer(
		"{world}", pyfmt.JSON(worldCtx{w.Title, w.Synopsis, w.Tone, w.Audience, w.Rules()}),
		"{characters}", pyfmt.JSON(chars),
		"{locations}", pyfmt.JSON(locs),
		"{canon}", pyfmt.JSON(canon),
		"{constraints}", pyfmt.JSON(w.Constraints()),
		"{lang}", lang,
		"{shots}", pyfmt.Repr(Shots),
		"{kinds}", pyfmt.Repr(BubbleKinds),
		"{gaps}", pyfmt.Repr(Gaps),
		"{min_p}", strconv.Itoa(MinPanels),
		"{max_p}", strconv.Itoa(MaxPanels),
	)
	return r.Replace(systemTmpl)
}

// UserPrompt = the prototype's user message: story state + premise / player choice.
func UserPrompt(state any, premise string) string {
	if state == nil {
		state = map[string]any{}
	}
	return "STORY STATE: " + pyfmt.JSON(state) + "\n\nEPISODE PREMISE / PLAYER CHOICE:\n" + premise
}

// Validate returns schema problems (empty = ok) and normalises sb in place: fixes
// establishing-with-characters, defaults bubble kind / gap, fills visual_tags /
// unmapped_phrases. Tag translation (one LLM call) runs only when the schema is valid.
func Validate(ctx context.Context, sb *domain.Storyboard, w *domain.World, vocab *tags.Vocab, c llm.JSONCaller) ([]string, error) {
	var errs []string
	charIDs := map[string]bool{}
	for _, ch := range w.Characters {
		charIDs[ch.ID] = true
	}
	allowed := map[string]bool{}
	for _, id := range w.AllowedLocations() {
		allowed[id] = true
	}
	if sb.Panels == nil {
		return []string{"panels missing"}, nil
	}
	if n := len(sb.Panels); n < MinPanels || n > MaxPanels {
		errs = append(errs, fmt.Sprintf("panel count %d not in %d-%d", n, MinPanels, MaxPanels))
	}
	for i := range sb.Panels {
		p := &sb.Panels[i]
		if !slices.Contains(Shots, p.Shot) {
			errs = append(errs, fmt.Sprintf("panel %d: bad shot %s", i, pyfmt.Repr(p.Shot)))
		}
		if !allowed[p.LocationID] {
			errs = append(errs, fmt.Sprintf("panel %d: location %s not allowed", i, pyfmt.Repr(p.LocationID)))
		}
		for _, ch := range p.Characters {
			if !charIDs[ch.ID] {
				errs = append(errs, fmt.Sprintf("panel %d: unknown character %s", i, pyfmt.Repr(ch.ID)))
			}
		}
		if p.Shot == "establishing" && len(p.Characters) > 0 {
			p.Shot = "wide" // cheap fix rather than a regeneration
		}
		for j := range p.Bubbles {
			b := &p.Bubbles[j]
			if !slices.Contains(BubbleKinds, b.Kind) {
				b.Kind = "speech"
			}
			speakerOK := b.SpeakerID != nil && charIDs[*b.SpeakerID]
			if !speakerOK && b.Kind != "narration" {
				var sp any
				if b.SpeakerID != nil {
					sp = *b.SpeakerID
				}
				errs = append(errs, fmt.Sprintf("panel %d: bubble speaker %s unknown", i, pyfmt.Repr(sp)))
			}
		}
		if p.Bubbles == nil {
			p.Bubbles = []domain.Bubble{}
		}
		if p.SFX == nil {
			p.SFX = []domain.SFX{}
		}
		if p.Characters == nil {
			p.Characters = []domain.SBChar{}
		}
		if !slices.Contains(Gaps, p.GapAfter) {
			p.GapAfter = "medium"
		}
		t := tags.Split(string(p.VisualPrompt))
		for _, ch := range p.Characters {
			t = append(t, tags.Split(ch.Emotion.Value())...)
			t = append(t, tags.Split(ch.Action.Value())...)
		}
		p.VisualTags, p.UnmappedPhrases = vocab.Filter(tags.Dedupe(t))
	}
	var closed, free int
	for _, ch := range sb.Choices {
		switch ch.Kind {
		case "closed":
			closed++
		case "free":
			free++
		}
	}
	if closed < 2 || closed > 3 || free != 1 {
		errs = append(errs, fmt.Sprintf("choices: %d closed / %d free", closed, free))
	}
	if len(errs) > 0 {
		// The prototype translated even here, but a schema-invalid storyboard is always
		// regenerated, so the call would be wasted.
		return errs, nil
	}
	// One LLM call for the whole episode instead of one per panel.
	var phrases []string
	for _, p := range sb.Panels {
		phrases = append(phrases, p.UnmappedPhrases...)
	}
	phrases = tags.Dedupe(phrases)
	if len(phrases) > 0 {
		mapped, err := vocab.Translate(ctx, c, phrases)
		if err != nil {
			return nil, err
		}
		for i := range sb.Panels {
			p := &sb.Panels[i]
			extra := []string{}
			for _, u := range p.UnmappedPhrases {
				extra = append(extra, mapped[u]...)
			}
			p.VisualTags = tags.Dedupe(append(p.VisualTags, extra...))
		}
	}
	return nil, nil
}

const ruleCheckTmpl = `You check a webtoon episode against the world rules and constraints.
RULES: {rules}
CONSTRAINTS: {constraints}
AUDIENCE: {audience}
Episode JSON:
{episode}
Report ONLY violations that actually HAPPEN on-panel (a character explicitly does the forbidden thing, or content unfit for the audience).
Also check the offered choices: a choice suggesting self-harm or suicide, or content unfit for the audience, IS a violation (panel = "choices").
Intentions, hints, mysteries, moving toward a place or mere mentions are NOT violations. Doing something adjacent is NOT a violation (delivering a letter is not opening it).
Output JSON: {"violations": [{"rule": "<quoted rule>", "panel": <index>, "evidence": "<what exactly happens>", "certain": true|false}]}
Empty list if none. When in doubt, do not report.`

const ruleCheckSystem = "You are a strict continuity editor."

type slimPanel struct {
	VisualPrompt string          `json:"visual_prompt"`
	Bubbles      []domain.Bubble `json:"bubbles"`
}

type slimEpisode struct {
	Title     string          `json:"title"`
	Panels    []slimPanel     `json:"panels"`
	Choices   []domain.Choice `json:"choices"`
	StateDiff json.RawMessage `json:"state_diff"`
}

func RuleCheckPrompt(sb *domain.Storyboard, w *domain.World) string {
	diff := sb.StateDiff
	if len(diff) == 0 {
		diff = json.RawMessage("null")
	}
	slim := slimEpisode{Title: sb.Title, Choices: sb.Choices, StateDiff: diff}
	for _, p := range sb.Panels {
		slim.Panels = append(slim.Panels, slimPanel{string(p.VisualPrompt), p.Bubbles})
	}
	audience := w.Audience
	if audience == "" {
		audience = "None"
	}
	r := strings.NewReplacer(
		"{rules}", pyfmt.Repr(w.Rules()),
		"{constraints}", pyfmt.Repr(w.Constraints()),
		"{audience}", audience,
		"{episode}", pyfmt.JSON(slim),
	)
	return r.Replace(ruleCheckTmpl)
}

// RuleCheck returns violations the checker is certain about; uncertain ones are ignored.
func RuleCheck(ctx context.Context, sb *domain.Storyboard, w *domain.World, c llm.JSONCaller) ([]string, error) {
	raw, err := c.JSON(ctx, ruleCheckSystem, RuleCheckPrompt(sb, w), 0.1)
	if err != nil {
		return nil, err
	}
	var res struct {
		Violations []any `json:"violations"`
	}
	if err := json.Unmarshal(raw, &res); err != nil {
		return nil, nil
	}
	var out []string
	for _, v := range res.Violations {
		m, ok := v.(map[string]any)
		if !ok {
			continue
		}
		if certain, ok := m["certain"].(bool); ok && certain {
			out = append(out, fmt.Sprintf("panel %s: %s — %s", pyStr(m["panel"]), pyStr(m["rule"]), pyStr(m["evidence"])))
		}
	}
	return out, nil
}

// pyStr = Python str() on a decoded JSON value.
func pyStr(v any) string {
	switch x := v.(type) {
	case string:
		return x
	case nil:
		return "None"
	default:
		return pyfmt.Repr(x)
	}
}

// Generator bundles what Generate needs.
type Generator struct {
	LLM      llm.JSONCaller
	Vocab    *tags.Vocab
	Attempts int // prototype: 3
}

// Error is returned when no attempt produced a schema-valid storyboard.
type Error struct{ Log []domain.ValidationAttempt }

func (e *Error) Error() string {
	b, _ := json.Marshal(e.Log)
	return "storyboard failed validation: " + string(b)
}

// Generate asks the LLM for a storyboard up to Attempts times, feeding validation errors back.
// A schema-valid storyboard the rule checker still objects to is accepted after the last attempt,
// with Warnings set.
func (g *Generator) Generate(ctx context.Context, w *domain.World, state any, canonProgress []string, premise string) (*domain.Storyboard, error) {
	attempts := g.Attempts
	if attempts <= 0 {
		attempts = 3
	}
	system := SystemPrompt(w, canonProgress)
	user := UserPrompt(state, premise)
	feedback := ""
	var log []domain.ValidationAttempt
	var soft *domain.Storyboard
	var softErrs []string
	for attempt := range attempts {
		raw, err := g.LLM.JSON(ctx, system, user+feedback, 0.8)
		if err != nil {
			return nil, err
		}
		sb := &domain.Storyboard{}
		var errs []string
		if err := json.Unmarshal(raw, sb); err != nil {
			errs = []string{"invalid JSON structure: " + err.Error()}
		} else if errs, err = Validate(ctx, sb, w, g.Vocab, g.LLM); err != nil {
			return nil, err
		}
		ruleOnly := false
		if len(errs) == 0 {
			violations, err := RuleCheck(ctx, sb, w, g.LLM)
			if err != nil {
				return nil, err
			}
			for _, v := range violations {
				errs = append(errs, "rule violation: "+v)
			}
			ruleOnly = len(errs) > 0
		}
		log = append(log, domain.ValidationAttempt{Attempt: attempt, Errors: nonNil(errs)})
		if len(errs) == 0 {
			sb.Validation = log
			return sb, nil
		}
		if ruleOnly {
			soft, softErrs = sb, errs
		}
		feedback = "\n\nYOUR PREVIOUS ATTEMPT WAS REJECTED. Fix these problems:\n- " + strings.Join(errs, "\n- ")
	}
	if soft != nil {
		// Schema-valid but the rule checker still objects: accept, flag for review.
		soft.Validation = log
		soft.Warnings = softErrs
		return soft, nil
	}
	return nil, &Error{Log: log}
}

func nonNil(s []string) []string {
	if s == nil {
		return []string{}
	}
	return s
}
