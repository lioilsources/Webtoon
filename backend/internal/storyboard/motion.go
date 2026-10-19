package storyboard

import (
	"fmt"
	"regexp"
	"strings"

	"github.com/ol1n/webtoon/backend/internal/domain"
)

// Motion panels (PLAN-motion-panels.md §4): the storyboard may mark up to MaxAnimatedPanels
// panels as a 1–3 s seamless loop. The still is rendered first; the loop is a second job.
const (
	MaxAnimatedPanels  = 2
	DefaultLoopSeconds = 2
	MaxMotionWords     = 15
	MaxMotionLen       = 120
)

// motionBanned is the code-side SFW fence for the Wan prompt: the same vocabulary the
// prompt fence uses for stills plus the actions a loop must never add to a still.
var motionBanned = regexp.MustCompile(`(?i)\b(nude|naked|lingerie|underwear|bra|panties|bikini|swimsuit|swimwear|` +
	`shirtless|topless|cleavage|see-through|wet shirt|crop top|midriff|breasts?|nipples?|bed|lying|` +
	`undress\w*|unzip\w*|unbutton\w*|strip\w*|remov\w+|taking off|takes off|kiss\w*|lick\w*|grop\w*|sex\w*|nsfw)\b`)

// CheckMotion validates an editor-supplied or model-supplied motion prompt.
func CheckMotion(motion string) error {
	m := strings.TrimSpace(motion)
	if m == "" {
		return fmt.Errorf("motion prompt is empty")
	}
	if len(m) > MaxMotionLen {
		return fmt.Errorf("motion prompt longer than %d characters", MaxMotionLen)
	}
	if n := len(strings.Fields(m)); n > MaxMotionWords {
		return fmt.Errorf("motion prompt has %d words, max %d", n, MaxMotionWords)
	}
	if hit := motionBanned.FindString(m); hit != "" {
		return fmt.Errorf("motion prompt contains a banned action %q", hit)
	}
	return nil
}

// LoopSecondsOr clamps the loop length to 1–3 s (0 = default).
func LoopSecondsOr(n int) int {
	switch {
	case n <= 0:
		return DefaultLoopSeconds
	case n > 3:
		return 3
	}
	return n
}

// normalizeMotion applies the loop rules to a model-written storyboard without regenerating:
// a bad motion prompt, a kiss, or more than one person just turns the loop off; beyond
// MaxAnimatedPanels the later ones are dropped. Returns warnings.
func normalizeMotion(sb *domain.Storyboard) []string {
	var warns []string
	kept := 0
	for i := range sb.Panels {
		p := &sb.Panels[i]
		if !p.Animate {
			p.Motion, p.LoopSeconds = "", 0
			continue
		}
		reason := ""
		switch {
		case kept >= MaxAnimatedPanels:
			reason = fmt.Sprintf("more than %d animated panels", MaxAnimatedPanels)
		case len(p.Characters) > 1:
			reason = "two people in motion"
		case CheckMotion(p.Motion) != nil:
			reason = CheckMotion(p.Motion).Error()
		}
		if reason != "" {
			warns = append(warns, fmt.Sprintf("panel %d: loop dropped (%s)", i, reason))
			p.Animate, p.Motion, p.LoopSeconds = false, "", 0
			continue
		}
		p.LoopSeconds = LoopSecondsOr(p.LoopSeconds)
		kept++
	}
	return warns
}

// motionAddendum extends the episode writer's system prompt. It is appended in Generate rather
// than written into systemTmpl so SystemPrompt keeps matching the m0 prototype byte for byte.
const motionAddendum = `
Motion panels (optional, max 2 per episode): add "animate": true and "motion": "<English, max 15 words: subject motion + ambient + 'static camera'>" to at most two panels that will be rendered as a 1–3 s seamless loop — usually the establishing panel (ambient: waves, rain, neon, curtains) and one quiet emotional beat with ONE person (hair in the wind, turning the head, a smile forming). Never a panel with two people acting, never a kiss, never undressing or clothes moving, no camera movement, no speech. Every other panel: "animate": false, "motion": "".
`
