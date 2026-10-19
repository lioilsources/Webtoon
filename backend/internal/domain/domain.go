// Package domain holds the pipeline-facing types: the world as the storyboard
// LLM sees it, style presets, and the storyboard JSON itself (WEBTOON_PLAN §2, §5).
package domain

import (
	"bytes"
	"encoding/json"
	"fmt"
	"strings"
)

type World struct {
	ID          string         `json:"id"`
	OwnerID     string         `json:"owner_id"`
	Title       string         `json:"title"`
	Synopsis    string         `json:"synopsis"`
	Tone        string         `json:"tone"`
	Audience    string         `json:"audience"`
	Language    string         `json:"language"`
	StyleID     string         `json:"style_id"`
	Visibility  string         `json:"visibility,omitempty"`
	Bible       map[string]any `json:"bible"`
	Canon       Canon          `json:"canon"`
	Permissions Permissions    `json:"permissions"`
	Characters  []Character    `json:"characters"`
	Locations   []Location     `json:"locations"`
}

type Canon struct {
	Nodes       []CanonNode `json:"nodes"`
	Constraints []any       `json:"constraints"`
}

type CanonNode struct {
	ID   string `json:"id"`
	Text string `json:"text"`
}

type Permissions struct {
	CanAddCharacters   bool     `json:"can_add_characters"`
	CanCreateCharacter bool     `json:"can_create_character"`
	CanChangeLocation  bool     `json:"can_change_location"`
	AllowedLocations   []string `json:"allowed_locations,omitempty"`
	MaxEpisodes        int      `json:"max_episodes,omitempty"`
}

type Character struct {
	ID              string   `json:"id"`
	OwnerID         string   `json:"owner_id,omitempty"`
	Name            string   `json:"name"`
	Role            string   `json:"role"`
	CountTag        string   `json:"count_tag,omitempty"`
	Description     string   `json:"description,omitempty"`
	Personality     string   `json:"personality,omitempty"`
	SpeechStyle     string   `json:"speech_style,omitempty"`
	TagPrompt       string   `json:"tag_prompt,omitempty"`
	ReferenceImages []string `json:"reference_images,omitempty"`
	IdentityLevel   string   `json:"identity_level,omitempty"`
	IdentityAsset   string   `json:"identity_asset,omitempty"`
	// IPAdapter tunes the IP-Adapter when IdentityLevel is "ip_adapter" (nil = defaults).
	// M0 result: prompt-only is the default identity level.
	IPAdapter *IPAdapterConfig `json:"ip_adapter,omitempty"`
	// Wardrobe (romance worlds): Base tags + one of Outfits, picked per panel by SBChar.Outfit.
	// Photo is a sentence description for photoreal presets (Preset.Natural).
	Base    string            `json:"base,omitempty"`
	Photo   string            `json:"photo,omitempty"`
	Outfits map[string]string `json:"outfits,omitempty"`
}

// Design is the character's tags in a panel: Base + the named outfit (or outfit tags given
// inline), falling back to TagPrompt when the panel names no outfit (m0 prompts.design_of).
func (c Character) Design(outfit string) string {
	if outfit == "" || c.Base == "" {
		return c.TagPrompt
	}
	if o, ok := c.Outfits[outfit]; ok {
		return c.Base + ", " + o
	}
	return c.Base + ", " + outfit
}

// Wear is the outfit text of a panel for the natural prompt: the named outfit, inline tags,
// or the "default" outfit when the panel names none.
func (c Character) Wear(outfit string) string {
	if outfit == "" {
		return c.Outfits["default"]
	}
	if o, ok := c.Outfits[outfit]; ok {
		return o
	}
	return outfit
}

// IPAdapterConfig mirrors m0/render.py --ip-preset / --ip-weight / --ip-end. Zero values mean
// the defaults (PLUS (high strength), 0.6, 0.8); a face crop works at weight 0.3–0.4.
type IPAdapterConfig struct {
	Preset string  `json:"preset,omitempty"`
	Weight float64 `json:"weight,omitempty"`
	EndAt  float64 `json:"end_at,omitempty"`
}

// IPAdapterPresets are the IPAdapterUnifiedLoader presets usable with SDXL.
var IPAdapterPresets = []string{"PLUS (high strength)", "PLUS FACE (portraits)", "STANDARD (medium strength)", "VIT-G (medium strength)"}

type Location struct {
	ID              string   `json:"id"`
	Name            string   `json:"name"`
	Description     string   `json:"description,omitempty"`
	TagPrompt       string   `json:"tag_prompt,omitempty"`
	ReferenceImages []string `json:"reference_images,omitempty"`
	Mood            string   `json:"mood,omitempty"`
}

// Rules returns bible.rules as the LLM prompts expect it (an empty list when absent).
func (w *World) Rules() any {
	if r, ok := w.Bible["rules"]; ok && r != nil {
		return r
	}
	return []any{}
}

func (w *World) Constraints() []any {
	if w.Canon.Constraints == nil {
		return []any{}
	}
	return w.Canon.Constraints
}

func (w *World) Character(id string) (Character, bool) {
	for _, c := range w.Characters {
		if c.ID == id {
			return c, true
		}
	}
	return Character{}, false
}

func (w *World) Location(id string) (Location, bool) {
	for _, l := range w.Locations {
		if l.ID == id {
			return l, true
		}
	}
	return Location{}, false
}

// AllowedLocations mirrors the prototype: permissions.allowed_locations, or every location when unset/empty.
func (w *World) AllowedLocations() []string {
	if len(w.Permissions.AllowedLocations) > 0 {
		return w.Permissions.AllowedLocations
	}
	ids := make([]string, 0, len(w.Locations))
	for _, l := range w.Locations {
		ids = append(ids, l.ID)
	}
	return ids
}

// --- styles ------------------------------------------------------------------

type Styles struct {
	Presets        map[string]Preset   `json:"presets"`
	AlwaysNegative []string            `json:"always_negative"`
	SFWPositive    []string            `json:"sfw_positive"`
	SFWNegative    []string            `json:"sfw_negative"`
	ShotTags       map[string][]string `json:"shot_tags"`
	ShotSize       map[string][2]int   `json:"shot_size"`
	KidsNegative   []string            `json:"kids_negative"`
	AdultNegative  []string            `json:"adult_negative"`
	// NaturalShot is the sentence form of ShotTags for Preset.Natural.
	NaturalShot map[string][]string `json:"natural_shot"`
}

// AudienceNegative is the extra negative of a world's audience (kids / adult).
func (s *Styles) AudienceNegative(audience string) []string {
	switch audience {
	case "kids":
		return s.KidsNegative
	case "adult":
		return s.AdultNegative
	}
	return nil
}

type Preset struct {
	Checkpoint    string   `json:"checkpoint"`
	Prediction    string   `json:"prediction"`
	ArtistTags    []string `json:"artist_tags"`
	AestheticTags []string `json:"aesthetic_tags"`
	QualityPos    []string `json:"quality_pos"`
	QualityNeg    []string `json:"quality_neg"`
	Sampler       string   `json:"sampler"`
	Scheduler     string   `json:"scheduler"`
	Steps         int      `json:"steps"`
	CFG           float64  `json:"cfg"`
	// Natural: photoreal checkpoints read sentences better than booru tags (prompt.Build).
	Natural bool `json:"natural,omitempty"`
	// Loras: style LoRAs chained after the checkpoint, styles.json [[file, strength], ...].
	Loras []Lora `json:"loras,omitempty"`
}

// Lora is one style LoRA; strength applies to both model and CLIP.
type Lora struct {
	Name     string
	Strength float64
}

func (l *Lora) UnmarshalJSON(b []byte) error {
	var pair []json.RawMessage
	if err := json.Unmarshal(b, &pair); err != nil || len(pair) != 2 {
		return fmt.Errorf("lora: want [file, strength], got %s", b)
	}
	if err := json.Unmarshal(pair[0], &l.Name); err != nil {
		return fmt.Errorf("lora file: %w", err)
	}
	if err := json.Unmarshal(pair[1], &l.Strength); err != nil {
		return fmt.Errorf("lora strength: %w", err)
	}
	return nil
}

func (l Lora) MarshalJSON() ([]byte, error) { return json.Marshal([]any{l.Name, l.Strength}) }

// --- storyboard (§5.2) -------------------------------------------------------

type Storyboard struct {
	Title             string              `json:"title"`
	Panels            []SBPanel           `json:"panels"`
	Choices           []Choice            `json:"choices"`
	StateDiff         json.RawMessage     `json:"state_diff"` // kept raw: key order is preserved for the rule-check prompt
	CanonNodesReached FlexList            `json:"canon_nodes_reached"`
	Validation        []ValidationAttempt `json:"_validation,omitempty"`
	Warnings          []string            `json:"_warnings,omitempty"`
}

// StateDiffMap decodes state_diff (empty map when absent or not an object).
func (sb *Storyboard) StateDiffMap() map[string]any {
	m := map[string]any{}
	if len(sb.StateDiff) > 0 {
		_ = json.Unmarshal(sb.StateDiff, &m)
	}
	if m == nil {
		m = map[string]any{}
	}
	return m
}

type ValidationAttempt struct {
	Attempt int      `json:"attempt"`
	Errors  []string `json:"errors"`
}

type SBPanel struct {
	Shot            string     `json:"shot"`
	LocationID      string     `json:"location_id"`
	Characters      []SBChar   `json:"characters"`
	VisualPrompt    FlexString `json:"visual_prompt"`
	Bubbles         []Bubble   `json:"bubbles"`
	SFX             []SFX      `json:"sfx"`
	GapAfter        string     `json:"gap_after"`
	VisualTags      []string   `json:"visual_tags"`
	UnmappedPhrases []string   `json:"unmapped_phrases"`
	// Motion panels (PLAN-motion-panels): Animate renders a 1–3 s seamless loop from the still,
	// Motion is the Wan I2V prompt ("subject motion + ambient + static camera"). Optional in
	// every storyboard; absent fields keep old data as it is.
	Animate     bool   `json:"animate,omitempty"`
	Motion      string `json:"motion,omitempty"`
	LoopSeconds int    `json:"loop_seconds,omitempty"`
}

type SBChar struct {
	ID      string   `json:"id"`
	Outfit  string   `json:"outfit,omitempty"`
	Emotion FlexList `json:"emotion"`
	Action  FlexList `json:"action"`
}

type Bubble struct {
	SpeakerID *string `json:"speaker_id"`
	Text      string  `json:"text"` // original, in the world's language
	Kind      string  `json:"kind"`
	// I18n holds machine translations of Text keyed by language (en, de, pt-BR, …); dropped when Text changes.
	I18n map[string]string `json:"i18n,omitempty"`
}

type SFX struct {
	Text  string `json:"text"`
	Style string `json:"style,omitempty"`
}

type Choice struct {
	ID   string            `json:"id,omitempty"`
	Kind string            `json:"kind"`
	Text string            `json:"text"`
	I18n map[string]string `json:"i18n,omitempty"`
}

// FlexString accepts a JSON string, null, a number or a list of strings (joined by ", ").
// LLMs are inconsistent about tag fields.
type FlexString string

func (f *FlexString) UnmarshalJSON(b []byte) error {
	b = bytes.TrimSpace(b)
	if len(b) == 0 || string(b) == "null" {
		*f = ""
		return nil
	}
	var s string
	if err := json.Unmarshal(b, &s); err == nil {
		*f = FlexString(s)
		return nil
	}
	var l []any
	if err := json.Unmarshal(b, &l); err == nil {
		parts := make([]string, 0, len(l))
		for _, v := range l {
			parts = append(parts, fmt.Sprint(v))
		}
		*f = FlexString(strings.Join(parts, ", "))
		return nil
	}
	var v any
	if err := json.Unmarshal(b, &v); err != nil {
		return err
	}
	*f = FlexString(fmt.Sprint(v))
	return nil
}

// FlexList keeps the shape the LLM sent: a list stays a list of items, a string
// stays one item (split_tags in the prototype splits a string on commas and keeps list items).
type FlexList struct {
	Items  []string
	IsList bool
}

func (f *FlexList) UnmarshalJSON(b []byte) error {
	b = bytes.TrimSpace(b)
	*f = FlexList{}
	if len(b) == 0 || string(b) == "null" {
		return nil
	}
	var s string
	if err := json.Unmarshal(b, &s); err == nil {
		f.Items = []string{s}
		return nil
	}
	var l []any
	if err := json.Unmarshal(b, &l); err == nil {
		f.IsList = true
		for _, v := range l {
			if v == nil {
				continue
			}
			if s, ok := v.(string); ok {
				f.Items = append(f.Items, s)
			} else {
				f.Items = append(f.Items, fmt.Sprint(v))
			}
		}
		return nil
	}
	var v any
	if err := json.Unmarshal(b, &v); err != nil {
		return err
	}
	f.Items = []string{fmt.Sprint(v)}
	return nil
}

func (f FlexList) MarshalJSON() ([]byte, error) {
	if f.IsList || len(f.Items) != 1 {
		if f.Items == nil {
			return []byte("[]"), nil
		}
		return json.Marshal(f.Items)
	}
	return json.Marshal(f.Items[0])
}

// Value is what split_tags gets: the list itself, or the single string.
func (f FlexList) Value() any {
	if f.IsList {
		return f.Items
	}
	if len(f.Items) == 0 {
		return ""
	}
	return f.Items[0]
}

// Strings returns the items (a single string stays whole).
func (f FlexList) Strings() []string { return f.Items }

func NewFlexList(items ...string) FlexList { return FlexList{Items: items, IsList: true} }
