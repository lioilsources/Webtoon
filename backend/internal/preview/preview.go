// Package preview builds a static web preview of a gamebook (all nodes as strips) for sharing outside the app:
// downscaled panels, the Wan loops in place, and the bubbles as HTML text in every language the storyboards carry,
// switchable on the page. Bubbles are placed like m0/compose.py (face boxes avoided, rules/base/compose.yaml), but
// sized from an estimate of the text width, so one layout per language.
//
// The page is the M0 stand-in of the reader, not the reader: the app lays bubbles out itself.
package preview

import (
	"encoding/json"
	"fmt"
	"image"
	"image/jpeg"
	_ "image/png"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"golang.org/x/image/draw"
	"gopkg.in/yaml.v3"

	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/pack"
)

// Options of one preview build.
type Options struct {
	Graph   string // data/gamebooks/<id>/graph.yaml
	Stories string // data/stories (storyboard.json of gb_<id>_<node>)
	Panels  string // out/local (pNN_s0.png and pNN_video.webp of gb_<id>_<node>)
	Compose string // rules/base/compose.yaml
	Out     string // output directory: index.html, p/, l/
	Width   int    // panel width of the JPEGs
	Quality int    // JPEG quality
	Lang    string // the storyboards' own language
	Unit    string // what a node is called on the page ("dějství", "obraz")
	Theme   string // dark | light
	Lede    string // a sentence under the title
}

type storyboard struct {
	Title     string            `json:"title"`
	TitleI18n map[string]string `json:"title_i18n"`
	Panels    []domain.SBPanel  `json:"panels"`
}

type composeRules struct {
	Width      int            `yaml:"width"`
	Gaps       map[string]int `yaml:"gaps"`
	DefaultGap int            `yaml:"default_gap"`
	Bubble     struct {
		FontSize          float64   `yaml:"font_size"`
		ShoutFontSize     float64   `yaml:"shout_font_size"`
		MaxWidth          float64   `yaml:"max_width"`
		NarrationMaxWidth float64   `yaml:"narration_max_width"`
		TextInset         float64   `yaml:"text_inset"`
		LineHeight        float64   `yaml:"line_height"`
		Pad               []float64 `yaml:"pad"`
		Margin            float64   `yaml:"margin"`
	} `yaml:"bubble"`
	Faces struct {
		Pad       float64            `yaml:"pad"`
		Step      float64            `yaml:"step"`
		BubbleGap float64            `yaml:"bubble_gap"`
		Cost      map[string]float64 `yaml:"cost"`
	} `yaml:"faces"`
}

// page data, read by the page's script
type bookJSON struct {
	Titles map[string]string `json:"titles"`
	Langs  []string          `json:"langs"`
	Acts   []actJSON         `json:"acts"`
}

type actJSON struct {
	ID     string            `json:"id"`
	Titles map[string]string `json:"titles"`
	Panels []panelJSON       `json:"panels"`
}

type panelJSON struct {
	Src     string       `json:"src"`
	Loop    bool         `json:"loop,omitempty"`
	Ratio   float64      `json:"ratio"` // height / width
	Gap     float64      `json:"gap"`   // white space under the panel, % of the width
	Bubbles []bubbleJSON `json:"bubbles,omitempty"`
}

type bubbleJSON struct {
	Kind string            `json:"kind"`
	Text map[string]string `json:"text"`
	// Layout per language, in panel pixels at the compose width (the page scales the panel's SVG)
	Layout map[string]bubbleLayout `json:"layout"`
}

// Build writes the preview into opts.Out and returns the number of panels and loops.
func Build(opts Options) (panels, loops int, err error) {
	g, err := pack.ReadGraph(opts.Graph)
	if err != nil {
		return 0, 0, err
	}
	var cr composeRules
	raw, err := os.ReadFile(opts.Compose)
	if err != nil {
		return 0, 0, err
	}
	if err := yaml.Unmarshal(raw, &cr); err != nil {
		return 0, 0, fmt.Errorf("%s: %w", opts.Compose, err)
	}
	if len(cr.Bubble.Pad) != 2 || cr.Width == 0 {
		return 0, 0, fmt.Errorf("%s: bubble.pad and width are required", opts.Compose)
	}
	for _, d := range []string{"p", "l"} {
		if err := os.MkdirAll(filepath.Join(opts.Out, d), 0o755); err != nil {
			return 0, 0, err
		}
	}

	book := bookJSON{Titles: map[string]string{opts.Lang: g.Title}}
	for l, t := range g.TitleI18n {
		book.Titles[l] = t
	}
	var sbs []storyboard
	langs := map[string]bool{opts.Lang: true}
	for _, node := range g.GraphOrder() {
		id := "gb_" + g.ID + "_" + node
		var sb storyboard
		raw, err := os.ReadFile(filepath.Join(opts.Stories, id, "storyboard.json"))
		if err != nil {
			return 0, 0, err
		}
		if err := json.Unmarshal(raw, &sb); err != nil {
			return 0, 0, fmt.Errorf("%s: %w", id, err)
		}
		act := actJSON{ID: node, Titles: map[string]string{opts.Lang: sb.Title}}
		for l, t := range sb.TitleI18n {
			act.Titles[l], langs[l] = t, true
		}
		dir := filepath.Join(opts.Panels, id)
		for i, p := range sb.Panels {
			name := fmt.Sprintf("%s_p%02d", node, i)
			loop := filepath.Join(dir, fmt.Sprintf("p%02d_video.webp", i))
			_, statErr := os.Stat(loop)
			looped := statErr == nil && p.Animate
			still := filepath.Join(dir, fmt.Sprintf("p%02d_s0.png", i))
			jpg := ""
			if !looped { // a looped panel shows its loop; its still is not published
				jpg = filepath.Join(opts.Out, "p", name+".jpg")
			}
			w, h, err := panelJPEG(still, jpg, opts.Width, opts.Quality)
			if err != nil {
				return 0, 0, fmt.Errorf("%s panel %d: %w", id, i, err)
			}
			pj := panelJSON{Src: "p/" + name + ".jpg", Ratio: float64(h) / float64(w)}
			gap, ok := cr.Gaps[p.GapAfter]
			if !ok {
				gap = cr.DefaultGap
			}
			pj.Gap = 100 * float64(gap) / float64(cr.Width)
			if looped {
				if err := copyFile(loop, filepath.Join(opts.Out, "l", name+".webp")); err != nil {
					return 0, 0, err
				}
				pj.Src, pj.Loop = "l/"+name+".webp", true
				loops++
			}
			for _, b := range p.Bubbles {
				for l := range b.I18n {
					langs[l] = true
				}
			}
			pj.Bubbles = bubbleTexts(p, opts.Lang)
			act.Panels = append(act.Panels, pj)
			panels++
		}
		book.Acts = append(book.Acts, act)
		sbs = append(sbs, sb)
	}
	book.Langs = sortedLangs(langs, opts.Lang)
	// every language gets a layout (a bubble without that translation shows the original)
	for a := range book.Acts {
		for p := range book.Acts[a].Panels {
			pj := &book.Acts[a].Panels[p]
			for b := range pj.Bubbles {
				for _, l := range book.Langs {
					if _, ok := pj.Bubbles[b].Text[l]; !ok {
						pj.Bubbles[b].Text[l] = pj.Bubbles[b].Text[opts.Lang]
					}
				}
			}
		}
	}
	for a, sb := range sbs {
		for p := range book.Acts[a].Panels {
			pj := &book.Acts[a].Panels[p]
			H := float64(cr.Width) * pj.Ratio
			for _, l := range book.Langs {
				placeAll(cr, sb.Panels[p], pj.Bubbles, H, l)
			}
		}
	}
	html, err := page(g, book, opts, panels, loops)
	if err != nil {
		return 0, 0, err
	}
	return panels, loops, os.WriteFile(filepath.Join(opts.Out, "index.html"), html, 0o644)
}

func sortedLangs(set map[string]bool, first string) []string {
	out := []string{first}
	rest := []string{}
	for l := range set {
		if l != first {
			rest = append(rest, l)
		}
	}
	sort.Strings(rest)
	return append(out, rest...)
}

// panelJPEG scales the PNG to width w and writes it as JPEG (dst "" only reads its size); returns the source size.
func panelJPEG(src, dst string, w, quality int) (int, int, error) {
	f, err := os.Open(src)
	if err != nil {
		return 0, 0, err
	}
	defer f.Close()
	if dst == "" {
		c, _, err := image.DecodeConfig(f)
		return c.Width, c.Height, err
	}
	img, _, err := image.Decode(f)
	if err != nil {
		return 0, 0, err
	}
	b := img.Bounds()
	h := b.Dy() * w / b.Dx()
	out := image.NewRGBA(image.Rect(0, 0, w, h))
	draw.CatmullRom.Scale(out, out.Bounds(), img, b, draw.Src, nil)
	o, err := os.Create(dst)
	if err != nil {
		return 0, 0, err
	}
	defer o.Close()
	return b.Dx(), b.Dy(), jpeg.Encode(o, out, &jpeg.Options{Quality: quality})
}

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	if _, err := io.Copy(out, in); err != nil {
		out.Close()
		return err
	}
	return out.Close()
}

// bubbleTexts: the panel's bubbles with their text in every language (positions come later, per language).
func bubbleTexts(p domain.SBPanel, lang string) []bubbleJSON {
	var out []bubbleJSON
	for _, b := range p.Bubbles {
		bj := bubbleJSON{Kind: b.Kind, Text: map[string]string{lang: b.Text}}
		if bj.Kind == "" {
			bj.Kind = "speech"
		}
		for l, t := range b.I18n {
			bj.Text[l] = strings.TrimSpace(t)
		}
		out = append(out, bj)
	}
	return out
}
