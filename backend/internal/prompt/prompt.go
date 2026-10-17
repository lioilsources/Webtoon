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
	for _, pc := range p.Characters {
		if c, ok := w.Character(pc.ID); ok {
			chars = append(chars, c)
		}
	}

	var charTags []string
	for _, c := range chars {
		charTags = append(charTags, tags.Split(c.TagPrompt)...)
	}
	design := map[string]bool{}
	for _, t := range charTags {
		design[t] = true
	}

	var scene []string
	for _, t := range p.VisualTags {
		if countTags[t] {
			continue
		}
		if len(chars) > 0 && !design[t] && designRE.MatchString(t) {
			continue
		}
		scene = append(scene, t)
	}
	var locTags []string
	if loc, ok := w.Location(p.LocationID); ok {
		locTags = tags.Split(loc.TagPrompt)
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
