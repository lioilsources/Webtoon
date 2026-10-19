// Package prompt builds the positive/negative image prompt of a storyboard panel (§5.4).
// Port of m0/prompts.py. Order: quality, count tags, character tag_prompt, artist/style
// preset, shot tags, scene tags, location tags, special (SFW) tags.
package prompt

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/tags"
)

// designRE matches design attributes owned by the character's tag_prompt; scene tags must not override them.
var designRE = regexp.MustCompile(`\b(hair|eyes|skin|freckles|jacket|shirt|shorts|skirt|pantyhose|footwear|boots|dress|uniform)\b`)

// expressionRE matches scene tags that mention hair/eyes but describe a moment, not the design.
var expressionRE = regexp.MustCompile(`^(closed eyes|half-closed eyes|wet hair|hair blowing|messy hair|hand on cheek|tears)$|^looking `)

// LowerRE matches design tags outside the frame of a close-up; left in, they pull the camera back to full body.
var LowerRE = regexp.MustCompile(`\b(shorts|skirt|pants|pantyhose|thighhighs|legwear|socks|footwear|boots|shoes)\b`)

// FeetRE matches design tags outside the frame of medium / over-shoulder shots.
var FeetRE = regexp.MustCompile(`\b(footwear|boots|shoes|socks)\b`)

// InFrame drops the design tags the shot does not show (close-up: lower body; medium and
// over-shoulder: footwear). Used for the prompt and for identity scoring.
func InFrame(design []string, shot string) []string {
	var re *regexp.Regexp
	switch shot {
	case "close-up":
		re = LowerRE
	case "medium", "over-shoulder":
		re = FeetRE
	default:
		return design
	}
	out := make([]string, 0, len(design))
	for _, t := range design {
		if !re.MatchString(t) {
			out = append(out, t)
		}
	}
	return out
}

var countTags = map[string]bool{"1girl": true, "1boy": true, "2girls": true, "2boys": true, "3girls": true,
	"multiple girls": true, "multiple boys": true, "solo": true, "no humans": true}

type Result struct {
	Positive string        `json:"positive"`
	Negative string        `json:"negative"`
	Width    int           `json:"width"`
	Height   int           `json:"height"`
	PresetID string        `json:"preset_id"`
	Preset   domain.Preset `json:"-"`
}

func CountTags(chars []domain.Character) []string {
	var girls, boys int
	for _, c := range chars {
		switch c.CountTag {
		case "1girl":
			girls++
		case "1boy":
			boys++
		}
	}
	var out []string
	if girls > 0 {
		if girls == 1 {
			out = append(out, "1girl")
		} else {
			out = append(out, fmt.Sprintf("%dgirls", girls))
		}
	}
	if boys > 0 {
		if boys == 1 {
			out = append(out, "1boy")
		} else {
			out = append(out, fmt.Sprintf("%dboys", boys))
		}
	}
	switch len(chars) {
	case 0:
		out = append(out, "no humans")
	case 1:
		out = append(out, "solo")
	}
	return out
}

// Build renders the prompt; presetID "" uses the world's style_id. sfw adds the SFW presets.
func Build(p *domain.SBPanel, w *domain.World, styles *domain.Styles, presetID string, sfw bool) (*Result, error) {
	if presetID == "" {
		presetID = w.StyleID
	}
	preset, ok := styles.Presets[presetID]
	if !ok {
		return nil, fmt.Errorf("unknown style preset %q", presetID)
	}
	var chars []domain.Character
	var outfits []string
	for _, pc := range p.Characters {
		if c, ok := w.Character(pc.ID); ok {
			chars = append(chars, c)
			outfits = append(outfits, pc.Outfit)
		}
	}
	if preset.Natural {
		return natural(p, w, styles, preset, presetID, chars, outfits, sfw), nil
	}

	var allTags []string
	for i, c := range chars {
		allTags = append(allTags, tags.Split(c.Design(outfits[i]))...)
	}
	// Scene filtering still knows the full design, only the prompt drops out-of-frame tags.
	design := map[string]bool{}
	for _, t := range allTags {
		design[t] = true
	}
	charTags := InFrame(allTags, p.Shot)

	var scene []string
	for _, t := range p.VisualTags {
		if countTags[t] {
			continue
		}
		if len(chars) > 0 && !design[t] && !expressionRE.MatchString(t) && designRE.MatchString(t) {
			continue
		}
		scene = append(scene, t)
	}
	var locTags []string
	if loc, ok := w.Location(p.LocationID); ok {
		locTags = tags.Split(loc.TagPrompt)
	}
	if p.Shot == "close-up" && len(locTags) > 3 {
		locTags = locTags[:3] // a full scene description pulls the camera back to a medium shot
	}
	var shot []string
	for _, t := range styles.ShotTags[p.Shot] {
		if len(chars) > 0 && t == "no humans" {
			continue
		}
		shot = append(shot, t)
	}

	var pos []string
	pos = append(pos, preset.QualityPos...)
	pos = append(pos, CountTags(chars)...)
	pos = append(pos, charTags...)
	pos = append(pos, preset.ArtistTags...)
	pos = append(pos, preset.AestheticTags...)
	pos = append(pos, shot...)
	pos = append(pos, scene...)
	pos = append(pos, locTags...)
	if sfw {
		pos = append(pos, styles.SFWPositive...)
	}
	pos = tags.Dedupe(pos)

	var neg []string
	neg = append(neg, preset.QualityNeg...)
	neg = append(neg, styles.AlwaysNegative...)
	if sfw {
		neg = append(neg, styles.SFWNegative...)
	}
	neg = append(neg, styles.AudienceNegative(w.Audience)...)
	neg = tags.Dedupe(neg)
	// A negative tag the scene needs (e.g. "letters" vs. a letter being delivered) would fight the positive.
	posForms := map[string]bool{}
	for _, t := range pos {
		posForms[t] = true
		posForms[t+"s"] = true
	}
	kept := neg[:0]
	for _, t := range neg {
		if !posForms[t] {
			kept = append(kept, t)
		}
	}

	wh, ok := styles.ShotSize[p.Shot]
	if !ok {
		wh = [2]int{832, 1216}
	}
	return &Result{
		Positive: strings.Join(pos, ", "), Negative: strings.Join(kept, ", "),
		Width: wh[0], Height: wh[1], PresetID: presetID, Preset: preset,
	}, nil
}

// natural builds the prompt for photoreal checkpoints (Juggernaut, RealVis, …), which read
// sentences better than booru tags: each character is its Photo description (or design tags)
// plus the panel's outfit (m0 prompts._natural).
func natural(p *domain.SBPanel, w *domain.World, styles *domain.Styles, preset domain.Preset, presetID string,
	chars []domain.Character, outfits []string, sfw bool) *Result {
	var people []string
	for i, c := range chars {
		desc := c.Photo
		if desc == "" {
			desc = c.Design(outfits[i])
		}
		if wear := c.Wear(outfits[i]); wear != "" {
			desc += ", wearing " + wear
		}
		people = append(people, desc)
	}
	var action []string
	for _, t := range p.VisualTags {
		if !countTags[t] && t != "couple" && t != "hetero" {
			action = append(action, t)
		}
	}
	var lead []string
	switch len(people) {
	case 0:
		lead = append([]string{"no people, empty scene"}, action...)
	case 1:
		lead = append([]string{"(one person:1.1)", "(" + people[0] + ":1.2)"}, action...)
	case 2:
		// Photoreal models drop the second person unless the pair leads the prompt.
		lead = append([]string{"(a romantic couple, two people, a woman and a man together in frame:1.3)"}, action...)
		for _, d := range people {
			lead = append(lead, "("+d+":1.2)")
		}
	default:
		lead = append([]string{fmt.Sprintf("(a group of %d people:1.2)", len(people))}, action...)
		for _, d := range people {
			lead = append(lead, "("+d+":1.1)")
		}
	}
	var pos []string
	pos = append(pos, preset.QualityPos...)
	pos = append(pos, styles.NaturalShot[p.Shot]...)
	pos = append(pos, lead...)
	if loc, ok := w.Location(p.LocationID); ok {
		pos = append(pos, tags.Split(loc.TagPrompt)...)
	}
	pos = append(pos, preset.AestheticTags...)

	var neg []string
	neg = append(neg, preset.QualityNeg...)
	neg = append(neg, styles.AlwaysNegative...)
	if sfw {
		neg = append(neg, styles.SFWNegative...)
	}
	neg = append(neg, styles.AudienceNegative(w.Audience)...)

	wh, ok := styles.ShotSize[p.Shot]
	if !ok {
		wh = [2]int{832, 1216}
	}
	return &Result{
		Positive: strings.Join(tags.Dedupe(pos), ", "), Negative: strings.Join(tags.Dedupe(neg), ", "),
		Width: wh[0], Height: wh[1], PresetID: presetID, Preset: preset,
	}
}
