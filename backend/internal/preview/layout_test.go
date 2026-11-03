package preview

import (
	"testing"

	"github.com/ol1n/webtoon/backend/internal/domain"
)

func testRules() composeRules {
	var cr composeRules
	cr.Width = 800
	cr.Bubble.FontSize, cr.Bubble.ShoutFontSize = 26, 30
	cr.Bubble.MaxWidth, cr.Bubble.NarrationMaxWidth = 0.62, 0.8
	cr.Bubble.TextInset, cr.Bubble.LineHeight, cr.Bubble.Margin = 40, 1.25, 22
	cr.Bubble.Pad = []float64{44, 30}
	cr.Faces.Pad, cr.Faces.Step, cr.Faces.BubbleGap = 0.04, 12, 12
	cr.Faces.Cost = map[string]float64{"face": 1000, "sfx": 400, "height": 60, "other_side": 8, "centre": 14}
	return cr
}

func TestWrapJapaneseBreaksBetweenCharacters(t *testing.T) {
	lines := wrap("肺が痛いし、外の人たちは今日、空気が有毒だって言ってた。", "ja", 26, 300)
	if len(lines) < 2 {
		t.Fatalf("one long line: %q", lines)
	}
	for _, l := range lines {
		if w := textWidth(l, 26); w > 300 {
			t.Errorf("line %q is %.0f wide", l, w)
		}
	}
}

func TestBubblesStayOffTheFaceAndInReadingOrder(t *testing.T) {
	cr := testRules()
	H := 1169.0
	p := domain.SBPanel{Faces: [][4]float64{{0.3, 0.05, 0.7, 0.45}}} // a face across the top middle
	bs := []bubbleJSON{
		{Kind: "speech", Text: map[string]string{"cs": "Tati… mně ta maska strašně dře."}},
		{Kind: "speech", Text: map[string]string{"cs": "Nemůžu přes ni pořádně dýchat."}},
	}
	placeAll(cr, p, bs, H, "cs")
	face := box{0.3 * 800, 0.05 * H, 0.7 * 800, 0.45 * H}
	prevY := -1.0
	for i, b := range bs {
		l := b.Layout["cs"]
		if l.X < face.x1 && face.x0 < l.X+l.W && l.Y < face.y1 && face.y0 < l.Y+l.H {
			t.Errorf("bubble %d %+v covers the face", i, l)
		}
		if l.Y < prevY {
			t.Errorf("bubble %d above the previous one", i)
		}
		if l.Tail == nil {
			t.Errorf("bubble %d has no tail", i)
		}
		prevY = l.Y
	}
}
