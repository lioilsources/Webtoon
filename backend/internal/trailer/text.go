package trailer

import (
	"fmt"
	"image"
	"image/color"
	"os"
	"strings"

	"golang.org/x/image/font"
	"golang.org/x/image/font/opentype"
	"golang.org/x/image/math/fixed"
)

// fontFile is a parsed font (one face of a collection); faces per size are made on demand.
type fontFile struct {
	f     *opentype.Font
	faces map[float64]font.Face
}

func loadFace(path string, idx int) (*fontFile, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var f *opentype.Font
	if strings.HasSuffix(strings.ToLower(path), ".ttc") {
		col, err := opentype.ParseCollection(raw)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", path, err)
		}
		if f, err = col.Font(idx); err != nil {
			return nil, fmt.Errorf("%s face %d: %w", path, idx, err)
		}
	} else if f, err = opentype.Parse(raw); err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	return &fontFile{f: f, faces: map[float64]font.Face{}}, nil
}

func (ff *fontFile) face(size float64) font.Face {
	if fc, ok := ff.faces[size]; ok {
		return fc
	}
	fc, err := opentype.NewFace(ff.f, &opentype.FaceOptions{Size: size, DPI: 72, Hinting: font.HintingFull})
	if err != nil {
		panic(err) // only bad sizes fail
	}
	ff.faces[size] = fc
	return fc
}

func wrapText(ff *fontFile, size float64, text string, maxW int) []string {
	fc := ff.face(size)
	var lines []string
	cur := ""
	for _, w := range strings.Fields(text) {
		trial := strings.TrimSpace(cur + " " + w)
		if cur == "" || font.MeasureString(fc, trial).Ceil() <= maxW {
			cur = trial
		} else {
			lines, cur = append(lines, cur), w
		}
	}
	if cur != "" {
		lines = append(lines, cur)
	}
	return lines
}

// drawCentered letters text centred in lines of at most maxW from top y, with a dark outline `stroke` px wide;
// returns the y under the last line.
func drawCentered(dst *image.RGBA, ff *fontFile, size float64, text string, y, maxW int, fill color.Color, stroke int) int {
	fc := ff.face(size)
	lh := int(size * 1.3)
	asc := fc.Metrics().Ascent.Ceil()
	for _, line := range wrapText(ff, size, text, maxW) {
		w := font.MeasureString(fc, line).Ceil()
		x := (W - w) / 2
		// outline: the text in black at every offset within the stroke radius, then the fill on top
		dark := image.NewUniform(color.RGBA{0, 0, 0, 220})
		for dy := -stroke; dy <= stroke; dy++ {
			for dx := -stroke; dx <= stroke; dx++ {
				if dx*dx+dy*dy > stroke*stroke {
					continue
				}
				d := font.Drawer{Dst: dst, Src: dark, Face: fc, Dot: fixed.P(x+dx, y+asc+dy)}
				d.DrawString(line)
			}
		}
		d := font.Drawer{Dst: dst, Src: image.NewUniform(fill), Face: fc, Dot: fixed.P(x, y+asc)}
		d.DrawString(line)
		y += lh
	}
	return y
}
