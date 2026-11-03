// Package trailer renders a vertical (9:16) trailer of a gamebook for TikTok / Shorts: chosen panels and Wan loops
// with a slow push-in, crossfades, a caption per shot, a title and an end card, over a music track. The shots and
// captions are hand-picked in data/gamebooks/<id>/trailer.yaml; frames are piped to ffmpeg (H.264 + AAC).
//
// It replaces m0/shorts.py for trailers (Go, no Python): a short is the whole episode, a trailer a montage.
package trailer

import (
	"fmt"
	"image"
	"image/color"
	"image/draw"
	_ "image/png"
	"io"
	"math"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	xdraw "golang.org/x/image/draw"
	"gopkg.in/yaml.v3"
)

// Spec is data/gamebooks/<id>/trailer.yaml.
type Spec struct {
	Title    string  `yaml:"title"`    // on the title card
	Tagline  string  `yaml:"tagline"`  // under the title
	Note     string  `yaml:"note"`     // content note on the title card (e.g. the subject of the story)
	End      string  `yaml:"end"`      // end card line under the title
	TitleAt  Ref     `yaml:"title_at"` // the image behind the title card
	Shots    []Shot  `yaml:"shots"`
	Fade     float64 `yaml:"fade"`      // crossfade, s
	TitleDur float64 `yaml:"title_dur"` // s
	EndDur   float64 `yaml:"end_dur"`   // s
}

// Ref names a panel: story node and panel index.
type Ref struct {
	Node  string `yaml:"node"`
	Panel int    `yaml:"panel"`
}

// Shot is one panel on screen: the loop when the panel has one (unless still: true), with an optional caption.
type Shot struct {
	Ref     `yaml:",inline"`
	Dur     float64 `yaml:"dur"`
	Caption string  `yaml:"caption"`
	Still   bool    `yaml:"still"`
	Zoom    float64 `yaml:"zoom"` // push-in over the shot, fraction (default 0.06)
}

// Options of one render.
type Options struct {
	Spec     string // trailer.yaml
	ID       string // gamebook id (stories gb_<id>_<node>)
	Panels   string // out/local
	Music    string // audio file ("" = silence)
	Volume   float64
	Font     string // caption font (.ttf/.otf/.ttc)
	FontIdx  int
	Title    string // title font
	TitleIdx int
	Out      string // .mp4
	FFmpeg   string
}

const (
	W, H = 1080, 1920
	FPS  = 30
	top  = 220 // TikTok top bar: no lettering above
	safe = 420 // caption and buttons at the bottom: no lettering below H - safe
)

// source is one shot's pictures: a still (one frame) or a loop.
type source struct {
	anim *Anim
}

func (s source) at(t float64) *image.RGBA {
	a := s.anim
	if len(a.Frames) == 1 {
		return a.Frames[0]
	}
	total := 0.0
	for _, d := range a.Delays {
		total += d.Seconds()
	}
	t = math.Mod(t, total)
	for i, d := range a.Delays {
		if t < d.Seconds() {
			return a.Frames[i]
		}
		t -= d.Seconds()
	}
	return a.Frames[len(a.Frames)-1]
}

type segment struct {
	dur   float64
	frame func(t float64, dst *image.RGBA)
}

// Render writes the trailer and returns its length.
func Render(o Options) (time.Duration, error) {
	raw, err := os.ReadFile(o.Spec)
	if err != nil {
		return 0, err
	}
	var sp Spec
	if err := yaml.Unmarshal(raw, &sp); err != nil {
		return 0, fmt.Errorf("%s: %w", o.Spec, err)
	}
	if sp.Fade == 0 {
		sp.Fade = 0.4
	}
	if sp.TitleDur == 0 {
		sp.TitleDur = 3
	}
	if sp.EndDur == 0 {
		sp.EndDur = 3
	}
	capFace, err := loadFace(o.Font, o.FontIdx)
	if err != nil {
		return 0, err
	}
	titleFace, err := loadFace(o.Title, o.TitleIdx)
	if err != nil {
		return 0, err
	}
	load := func(r Ref, still bool) (source, error) {
		dir := filepath.Join(o.Panels, fmt.Sprintf("gb_%s_%s", o.ID, r.Node))
		loop := filepath.Join(dir, fmt.Sprintf("p%02d_video.webp", r.Panel))
		if _, err := os.Stat(loop); err == nil && !still {
			a, err := DecodeWebPAnim(loop)
			return source{a}, err
		}
		img, err := readImage(filepath.Join(dir, fmt.Sprintf("p%02d_s0.png", r.Panel)))
		if err != nil {
			return source{}, err
		}
		return source{&Anim{Frames: []*image.RGBA{img}, Delays: []time.Duration{time.Second}}}, nil
	}

	var segs []segment
	// title card: the chosen panel blurred and dimmed, title, tagline, note
	tsrc, err := load(sp.TitleAt, true)
	if err != nil {
		return 0, err
	}
	bg := backdrop(tsrc.at(0))
	card := image.NewRGBA(image.Rect(0, 0, W, H))
	draw.Draw(card, card.Bounds(), bg, image.Point{}, draw.Src)
	y := H/2 - 220
	y = drawCentered(card, titleFace, 104, sp.Title, y, 940, color.White, 6)
	if sp.Tagline != "" {
		y = drawCentered(card, capFace, 48, sp.Tagline, y+40, 900, color.RGBA{235, 235, 235, 255}, 4)
	}
	if sp.Note != "" {
		drawCentered(card, capFace, 34, sp.Note, H-safe-120, 900, color.RGBA{220, 220, 220, 255}, 3)
	}
	segs = append(segs, segment{sp.TitleDur, func(t float64, dst *image.RGBA) { draw.Draw(dst, dst.Bounds(), card, image.Point{}, draw.Src) }})

	for _, s := range sp.Shots {
		src, err := load(s.Ref, s.Still)
		if err != nil {
			return 0, fmt.Errorf("shot %s/%d: %w", s.Node, s.Panel, err)
		}
		zoom := s.Zoom
		if zoom == 0 {
			zoom = 0.06
		}
		var capLayer *image.RGBA
		if s.Caption != "" {
			capLayer = image.NewRGBA(image.Rect(0, 0, W, H))
			lines := wrapText(capFace, 58, s.Caption, 900)
			lh := 58 * 1.3
			y0 := float64(H-safe) - lh*float64(len(lines)) - 20
			drawCentered(capLayer, capFace, 58, s.Caption, int(y0), 900, color.White, 5)
		}
		first := src.at(0)
		land := first.Bounds().Dx() > first.Bounds().Dy()
		var back *image.RGBA
		if land {
			back = backdrop(first)
		}
		dur := s.Dur
		segs = append(segs, segment{dur, func(t float64, dst *image.RGBA) {
			img := src.at(t)
			k := 1 + zoom*t/dur
			if land {
				draw.Draw(dst, dst.Bounds(), back, image.Point{}, draw.Src)
				fit(dst, img, k, true)
			} else {
				fit(dst, img, k, false)
			}
			if capLayer != nil {
				draw.Draw(dst, dst.Bounds(), capLayer, image.Point{}, draw.Over)
			}
		}})
	}

	// end card: the last shot blurred, title again and the end line
	last := sp.Shots[len(sp.Shots)-1]
	lsrc, err := load(last.Ref, true)
	if err != nil {
		return 0, err
	}
	endCard := image.NewRGBA(image.Rect(0, 0, W, H))
	draw.Draw(endCard, endCard.Bounds(), backdrop(lsrc.at(0)), image.Point{}, draw.Src)
	y = drawCentered(endCard, titleFace, 96, sp.Title, H/2-160, 940, color.White, 6)
	if sp.End != "" {
		drawCentered(endCard, capFace, 50, sp.End, y+50, 900, color.RGBA{240, 240, 240, 255}, 4)
	}
	segs = append(segs, segment{sp.EndDur, func(t float64, dst *image.RGBA) { draw.Draw(dst, dst.Bounds(), endCard, image.Point{}, draw.Src) }})

	total := -sp.Fade * float64(len(segs)-1)
	for _, s := range segs {
		total += s.dur
	}
	return time.Duration(total * float64(time.Second)), encode(o, segs, sp.Fade, total)
}

func encode(o Options, segs []segment, fade, total float64) error {
	args := []string{"-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", fmt.Sprintf("%dx%d", W, H),
		"-r", fmt.Sprint(FPS), "-i", "-"}
	if o.Music != "" {
		args = append(args, "-stream_loop", "-1", "-i", o.Music, "-af",
			fmt.Sprintf("volume=%.2f,afade=t=in:d=1,afade=t=out:st=%.2f:d=2.5", o.Volume, total-2.5))
	} else {
		args = append(args, "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo")
	}
	args = append(args, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
		"-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-t", fmt.Sprintf("%.2f", total),
		"-movflags", "+faststart", o.Out)
	cmd := exec.Command(o.FFmpeg, args...)
	cmd.Stderr = os.Stderr
	in, err := cmd.StdinPipe()
	if err != nil {
		return err
	}
	if err := cmd.Start(); err != nil {
		return err
	}
	if err := frames(in, segs, fade); err != nil {
		in.Close()
		cmd.Wait() //nolint:errcheck
		return err
	}
	in.Close()
	return cmd.Wait()
}

// frames writes every frame: each segment in turn, the last `fade` seconds blended into the next one.
func frames(w io.Writer, segs []segment, fade float64) error {
	a := image.NewRGBA(image.Rect(0, 0, W, H))
	b := image.NewRGBA(image.Rect(0, 0, W, H))
	for k, s := range segs {
		start := 0.0
		if k > 0 {
			start = fade // already shown blended into the previous segment
		}
		var next *segment
		if k+1 < len(segs) {
			next = &segs[k+1]
		}
		for n := int(math.Round(start * FPS)); n < int(math.Round(s.dur*FPS)); n++ {
			t := float64(n) / FPS
			s.frame(t, a)
			if next != nil && t > s.dur-fade {
				tn := t - (s.dur - fade)
				next.frame(tn, b)
				blend(a, b, tn/fade)
			}
			if _, err := w.Write(a.Pix); err != nil {
				return err
			}
		}
	}
	return nil
}

func blend(a, b *image.RGBA, f float64) {
	fb := uint32(f * 256)
	fa := 256 - fb
	for i := range a.Pix {
		a.Pix[i] = uint8((uint32(a.Pix[i])*fa + uint32(b.Pix[i])*fb) >> 8)
	}
}

// fit draws img scaled by k around the centre: cover the frame (portrait), or fill the width a little low (landscape).
func fit(dst, img *image.RGBA, k float64, land bool) {
	sb := img.Bounds()
	sw, sh := float64(sb.Dx()), float64(sb.Dy())
	var s float64
	if land {
		s = W / sw * k
	} else {
		s = math.Max(W/sw, H/sh) * k
	}
	dw, dh := sw*s, sh*s
	x0, y0 := (W-dw)/2, (H-dh)/2
	if land {
		y0 += 80
	}
	r := image.Rect(int(x0), int(y0), int(x0+dw), int(y0+dh))
	xdraw.ApproxBiLinear.Scale(dst, r, img, sb, draw.Src, nil)
}

// backdrop: img covering the frame, blurred (scaled down, three box-blur passes, scaled up) and dimmed.
func backdrop(img *image.RGBA) *image.RGBA {
	const sw, sh = 108, 192
	sb := img.Bounds()
	s := math.Max(sw/float64(sb.Dx()), sh/float64(sb.Dy()))
	cw, ch := int(sw/s), int(sh/s)
	crop := image.Rect(sb.Min.X+(sb.Dx()-cw)/2, sb.Min.Y+(sb.Dy()-ch)/2, 0, 0)
	crop.Max = crop.Min.Add(image.Pt(cw, ch))
	small := image.NewRGBA(image.Rect(0, 0, sw, sh))
	xdraw.ApproxBiLinear.Scale(small, small.Bounds(), img, crop, draw.Src, nil)
	for i := 0; i < 3; i++ {
		boxBlur(small, 4)
	}
	out := image.NewRGBA(image.Rect(0, 0, W, H))
	xdraw.CatmullRom.Scale(out, out.Bounds(), small, small.Bounds(), draw.Src, nil)
	for i := 0; i < len(out.Pix); i += 4 {
		for c := 0; c < 3; c++ {
			out.Pix[i+c] = uint8(float64(out.Pix[i+c]) * 0.55)
		}
	}
	return out
}

// boxBlur blurs img in place with a (2r+1)² box (horizontal, then vertical; edges clamped).
func boxBlur(img *image.RGBA, r int) {
	w, h := img.Bounds().Dx(), img.Bounds().Dy()
	tmp := make([]uint8, len(img.Pix))
	pass := func(src, dst []uint8, horiz bool) {
		n, m := w, h
		if !horiz {
			n, m = h, w
		}
		for j := 0; j < m; j++ {
			for i := 0; i < n; i++ {
				var sum [4]int
				for k := -r; k <= r; k++ {
					ii := min(max(i+k, 0), n-1)
					x, y := ii, j
					if !horiz {
						x, y = j, ii
					}
					p := y*img.Stride + x*4
					for c := 0; c < 4; c++ {
						sum[c] += int(src[p+c])
					}
				}
				x, y := i, j
				if !horiz {
					x, y = j, i
				}
				p := y*img.Stride + x*4
				for c := 0; c < 4; c++ {
					dst[p+c] = uint8(sum[c] / (2*r + 1))
				}
			}
		}
	}
	pass(img.Pix, tmp, true)
	pass(tmp, img.Pix, false)
}

func readImage(path string) (*image.RGBA, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()
	img, _, err := image.Decode(f)
	if err != nil {
		return nil, fmt.Errorf("%s: %w", path, err)
	}
	return toRGBA(img), nil
}
