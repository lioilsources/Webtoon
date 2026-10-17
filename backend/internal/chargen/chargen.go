// Package chargen turns a character (or location) description into a fixed booru tag_prompt
// (WEBTOON_PLAN §5.4 level 1). Port of m0/gen_character.py: up to 3 LLM attempts, each followed
// by a repair pass that maps tags missing from the WD14 vocabulary to existing ones; the attempt
// with the fewest unknown tags wins.
package chargen

import (
	"context"
	"encoding/json"
	"strings"

	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/pyfmt"
	"github.com/ol1n/webtoon/backend/internal/tags"
)

// CharacterSystem is gen_character.SYSTEM, verbatim.
const CharacterSystem = `You convert a character description into a FIXED Danbooru tag list for an SDXL anime model (NoobAI-XL / Illustrious).
Rules:
- Output JSON: {"tags": ["...", ...], "notes": "..."}
- Only real Danbooru general tags, lowercase, spaces instead of underscores.
- Describe the DESIGN only: hair color + length + style, eye color, face marks, every clothing item separately (with color), accessories, body marks.
- 12-25 tags, ordered: hair, eyes, face, top, bottom, legwear, footwear, accessories.
- NO count tags (1girl), NO pose, NO emotion, NO background, NO camera, NO quality tags, NO character/copyright names.
- Use the most common Danbooru spelling (e.g. "short hair", "messy hair", "green eyes", "freckles", "goggles on head", "black pantyhose", "cross-laced footwear").
- Colors must use standard Danbooru color words (orange hair, brown hair, aqua eyes...), never "copper", "auburn" etc.
- Hair color and eye color are MANDATORY.
`

// LocationSystem is the same idea for Location.tag_prompt (not in the prototype, which wrote
// location tags by hand): scenery tags only, appended after the scene tags of every panel.
const LocationSystem = `You convert a location description into a FIXED Danbooru tag list for an SDXL anime model (NoobAI-XL / Illustrious).
Rules:
- Output JSON: {"tags": ["...", ...], "notes": "..."}
- Only real Danbooru general tags, lowercase, spaces instead of underscores.
- Describe the PLACE only: indoors or outdoors first, then the kind of place, architecture, notable objects, lighting, time of day, weather.
- 6-12 tags, most important first; the first 3 tags must identify the place on their own (close-ups keep only those).
- NO characters, NO count tags (1girl, no humans), NO camera, NO quality tags, NO copyright names.
- Use the most common Danbooru spelling (e.g. "indoors", "wooden floor", "bookshelf", "window", "sunlight", "night sky", "paper lantern").
`

const repairTmpl = `These Danbooru tags do not exist: {unknown}
For each, give the closest EXISTING Danbooru general tag(s) that keep the visual meaning (e.g. "copper hair" -> "orange hair", "brown boots" -> "brown footwear", "boots"; "leather bracelet" -> "bracelet"). Drop it only if nothing fits.
Output JSON: {"replace": {"<bad tag>": ["<tag>", ...]}}`

// RepairPrompt renders gen_character.REPAIR for the unknown tags (Python list repr).
func RepairPrompt(unknown []string) string {
	return strings.Replace(repairTmpl, "{unknown}", pyfmt.Repr(unknown), 1)
}

// UserPrompt is the prototype's user message.
func UserPrompt(name, description string) string {
	return "Name: " + name + "\nDescription: " + description
}

const Attempts = 3

// Result of one generation.
type Result struct {
	Tags     []string            `json:"tags"`     // known tags, in order (the tag_prompt)
	Unknown  []string            `json:"unknown"`  // make_tag_prompt's second value: repair output still not in the vocabulary
	Dropped  []string            `json:"dropped"`  // LLM tags lost entirely: unknown and no known replacement
	Replaced map[string][]string `json:"replaced"` // unknown LLM tag → known replacements
	Notes    string              `json:"notes"`
}

// TagPrompt joins the tags as stored in Character.tag_prompt.
func (r *Result) TagPrompt() string { return strings.Join(r.Tags, ", ") }

// Generate = make_tag_prompt. system is CharacterSystem or LocationSystem.
func Generate(ctx context.Context, c llm.JSONCaller, v *tags.Vocab, system, name, description string) (*Result, error) {
	user := UserPrompt(name, description)
	var best *Result
	for range Attempts {
		raw, err := c.JSON(ctx, system, user, 0.3)
		if err != nil {
			return nil, err
		}
		var res map[string]any
		_ = json.Unmarshal(raw, &res)
		cand := tags.Dedupe(tags.Split(res["tags"]))
		known, unknown := v.Filter(cand)
		r := &Result{Dropped: []string{}, Replaced: map[string][]string{}}
		if n, ok := res["notes"].(string); ok {
			r.Notes = n
		}
		if len(unknown) > 0 {
			raw, err := c.JSON(ctx, system, RepairPrompt(unknown), 0.2)
			if err != nil {
				return nil, err
			}
			var rep struct {
				Replace map[string]any `json:"replace"`
			}
			_ = json.Unmarshal(raw, &rep)
			var fixed []string
			for _, u := range unknown {
				repl := tags.Split(rep.Replace[u])
				fixed = append(fixed, repl...)
				k, _ := v.Filter(repl)
				if len(k) > 0 {
					r.Replaced[u] = k
				} else {
					r.Dropped = append(r.Dropped, u)
				}
			}
			var k2 []string
			k2, unknown = v.Filter(fixed)
			known = tags.Dedupe(append(known, k2...))
		}
		r.Tags, r.Unknown = known, unknown
		if best == nil || len(unknown) < len(best.Unknown) {
			best = r
		}
		if len(unknown) == 0 {
			break
		}
	}
	return best, nil
}
