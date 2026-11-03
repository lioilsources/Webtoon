package preview

import (
	"math"
	"strings"
	"unicode"

	"github.com/ol1n/webtoon/backend/internal/domain"
)

// bubbleLayout is one bubble in one language, in panel pixels of the compose width (rules width × panel height):
// the box, the wrapped lines and the tail (from C toward T; S = 1 leaves the bottom edge, -1 the top).
type bubbleLayout struct {
	X          float64     `json:"x"`
	Y          float64     `json:"y"`
	W          float64     `json:"w"`
	H          float64     `json:"h"`
	FontSize   float64     `json:"fs"`
	LineHeight float64     `json:"lh"`
	Lines      []string    `json:"lines"`
	Tail       *[5]float64 `json:"tail,omitempty"` // cx, cy, tx, ty, s
}

type box struct{ x0, y0, x1, y1 float64 }

// placeAll lays out the panel's bubbles in language lang the way m0/compose.py draws them: narration first, then
// talk, each placed off the face boxes (or in the corners without faces), the later one never over the earlier.
func placeAll(cr composeRules, p domain.SBPanel, bubbles []bubbleJSON, H float64, lang string) {
	W := float64(cr.Width)
	var faces []box
	for _, f := range p.Faces {
		b := box{f[0] * W, f[1] * H, f[2] * W, f[3] * H}
		if b.x1 > 0 && b.y1 > 0 && b.x0 < W && b.y0 < H {
			faces = append(faces, box{math.Max(0, b.x0), math.Max(0, b.y0), math.Min(W, b.x1), math.Min(H, b.y1)})
		}
	}
	var narr, talk []int
	for i, b := range bubbles {
		if b.Kind == "narration" {
			narr = append(narr, i)
		} else {
			talk = append(talk, i)
		}
	}
	var placed []box
	place := func(i, slot int) {
		b := &bubbles[i]
		l, at := placeOne(cr, b.Kind, b.Text[lang], lang, slot, W, H, faces, placed)
		placed = append(placed, at)
		if b.Layout == nil {
			b.Layout = map[string]bubbleLayout{}
		}
		b.Layout[lang] = l
	}
	for k, i := range narr {
		place(i, k)
	}
	off := 0
	if len(narr) > 0 {
		off = 1
	}
	for k, i := range talk {
		place(i, k+off)
	}
}

func placeOne(cr composeRules, kind, text, lang string, slot int, W, H float64, faces, placed []box) (bubbleLayout, box) {
	B := cr.Bubble
	fs := B.FontSize
	if kind == "shout" {
		fs = B.ShoutFontSize
	}
	maxW := W * B.MaxWidth
	if kind == "narration" {
		maxW = W * B.NarrationMaxWidth
	}
	lines := wrap(text, lang, fs, maxW-B.TextInset)
	lh := math.Floor(fs * B.LineHeight)
	tw := 0.0
	for _, l := range lines {
		tw = math.Max(tw, textWidth(l, fs))
	}
	bw, bh := math.Floor(tw)+B.Pad[0], lh*float64(len(lines))+B.Pad[1]
	m := B.Margin
	var x, y float64
	switch {
	case len(faces) > 0:
		x, y = offFaces(cr, W, H, bw, bh, kind, slot, faces, placed, m)
	case kind == "narration":
		x, y = m, m+float64(slot)*(bh+12)
	default:
		right := slot%2 == 1
		x, y = m, m+float64(slot/2)*(bh+30)
		if right {
			x, y = W-bw-m, y+40
		}
	}
	// two long bubbles would overlap side by side: the later one goes below the previous
	for _, p := range placed {
		if x < p.x1 && p.x0 < x+bw && y < p.y1+30 && p.y0 < y+bh {
			y = p.y1 + 50
		}
	}
	l := bubbleLayout{X: r1(x), Y: r1(y), W: r1(bw), H: r1(bh), FontSize: fs, LineHeight: lh, Lines: lines}
	if kind != "narration" {
		t := tail(cr, x, y, bw, bh, W, H, faces)
		for i := range t {
			t[i] = r1(t[i])
		}
		l.Tail = t
	}
	return l, box{x, y, x + bw, y + bh}
}

// offFaces is compose.place_off_faces: the cheapest top-left corner over the left/right (and centre) columns.
func offFaces(cr composeRules, W, H, bw, bh float64, kind string, slot int, faces, placed []box, m float64) (float64, float64) {
	F := cr.Faces
	pad := F.Pad * W
	type zone struct {
		box
		cost float64
	}
	var zones []zone
	for _, f := range faces {
		zones = append(zones, zone{box{f.x0 - pad, f.y0 - pad, f.x1 + pad, f.y1 + pad}, F.Cost["face"]})
	}
	rightFirst := kind != "narration" && slot%2 == 1
	other := F.Cost["other_side"]
	type col struct{ x, cost float64 }
	xs := []col{{m, 0}, {W - bw - m, other}}
	if rightFirst {
		xs = []col{{m, other}, {W - bw - m, 0}}
	}
	if kind != "narration" {
		xs = append(xs, col{math.Floor((W - bw) / 2), F.Cost["centre"]})
	}
	y0 := m
	if len(placed) > 0 {
		y0 = math.Max(m, placed[len(placed)-1].y0)
	}
	best, bx, by := math.Inf(1), m, y0
	for y := y0; y <= math.Max(y0, H-bh-m); y += F.Step {
		for _, c := range xs {
			free := true
			for _, p := range placed {
				g := F.BubbleGap
				if c.x < p.x1+g && p.x0-g < c.x+bw && y < p.y1+g && p.y0-g < y+bh {
					free = false
					break
				}
			}
			if !free {
				continue
			}
			covered := 0.0
			for _, z := range zones {
				ix := math.Min(c.x+bw, z.x1) - math.Max(c.x, z.x0)
				iy := math.Min(y+bh, z.y1) - math.Max(y, z.y0)
				if ix > 0 && iy > 0 {
					covered += z.cost * ix * iy / ((z.x1 - z.x0) * (z.y1 - z.y0))
				}
			}
			cost := covered + F.Cost["height"]*y/H + c.cost
			if cost < best {
				best, bx, by = cost, c.x, y
			}
		}
	}
	return bx, by
}

// tail toward the nearest face, stopping short of it (compose.draw_bubble); without faces down and inward.
func tail(cr composeRules, x, y, bw, bh, W, H float64, faces []box) *[5]float64 {
	cx, cy := x+bw/2, y+bh
	tx, ty := cx-40, math.Min(H-20, y+bh+48)
	if cx < W/2 {
		tx = cx + 40
	}
	if len(faces) > 0 {
		f := faces[0]
		bestD := math.Inf(1)
		for _, c := range faces {
			d := math.Pow((c.x0+c.x1)/2-cx, 2) + math.Pow((c.y0+c.y1)/2-(y+bh/2), 2)
			if d < bestD {
				bestD, f = d, c
			}
		}
		fx, fy := (f.x0+f.x1)/2, (f.y0+f.y1)/2
		below := fy > y+bh/2
		edge := f.y1
		cy = y
		if below {
			cy, edge = y+bh, f.y0
		}
		dx, dy := fx-cx, edge-cy
		dist := math.Max(1, math.Hypot(dx, dy))
		length := math.Min(90, math.Max(36, dist-18))
		tx, ty = cx+dx/dist*length, cy+dy/dist*length
		if (ty > cy) != below {
			ty = cy - 36
			if below {
				ty = cy + 36
			}
		}
	}
	s := 1.0
	if ty < cy {
		s = -1
	}
	return &[5]float64{cx, cy, tx, ty, s}
}

// wrap breaks text into lines of at most maxW (estimated); Japanese and Chinese break between characters.
func wrap(text, lang string, fs, maxW float64) []string {
	if lang == "ja" || strings.HasPrefix(lang, "zh") {
		var lines []string
		cur := ""
		for _, r := range text {
			if cur != "" && textWidth(cur+string(r), fs) > maxW {
				lines, cur = append(lines, cur), ""
			}
			cur += string(r)
		}
		if cur != "" {
			lines = append(lines, cur)
		}
		return lines
	}
	var lines []string
	cur := ""
	for _, w := range strings.Fields(text) {
		trial := strings.TrimSpace(cur + " " + w)
		if textWidth(trial, fs) <= maxW || cur == "" {
			cur = trial
		} else {
			lines, cur = append(lines, cur), w
		}
	}
	if cur != "" {
		lines = append(lines, cur)
	}
	if len(lines) == 0 {
		lines = []string{""}
	}
	return lines
}

// textWidth estimates the advance of s in the page's bold rounded sans (Nunito) at size fs; CJK is full width.
func textWidth(s string, fs float64) float64 {
	w := 0.0
	for _, r := range s {
		switch {
		case unicode.In(r, unicode.Han, unicode.Hiragana, unicode.Katakana, unicode.Hangul) || r >= 0x3000 && r <= 0x303f || r >= 0xff00 && r <= 0xffef:
			w += 1.0
		case r == ' ':
			w += 0.26
		case strings.ContainsRune("iljI.,:;'!|ı", r):
			w += 0.28
		case strings.ContainsRune("mwMWЖШЩЮжшщю", r):
			w += 0.85
		case unicode.IsUpper(r) || unicode.IsDigit(r):
			w += 0.64
		case unicode.Is(unicode.Cyrillic, r):
			w += 0.58
		default:
			w += 0.54
		}
	}
	return w * fs
}

func r1(v float64) float64 { return math.Round(v*10) / 10 }
