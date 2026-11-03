package trailer

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"image"
	"image/draw"
	"os"
	"time"

	"golang.org/x/image/webp"
)

// Anim is a decoded WebP: full frames (canvas size) and how long each stays up. A still WebP is one frame.
type Anim struct {
	Frames []*image.RGBA
	Delays []time.Duration
}

// DecodeWebPAnim decodes an animated WebP (the Wan loops of m0/animate.py). x/image/webp reads only one frame, so
// the RIFF is walked here: every ANMF frame (its ALPH + VP8/VP8L) is wrapped into a single-image WebP, decoded, and
// drawn onto the canvas with the frame's offset, blend and dispose flags.
func DecodeWebPAnim(path string) (*Anim, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	if len(raw) < 12 || string(raw[0:4]) != "RIFF" || string(raw[8:12]) != "WEBP" {
		return nil, fmt.Errorf("%s: not a WebP", path)
	}
	var cw, ch int
	var frames []chunk
	for _, c := range chunks(raw[12:]) {
		switch c.id {
		case "VP8X":
			if len(c.data) >= 10 {
				cw, ch = 1+int(u24(c.data[4:])), 1+int(u24(c.data[7:]))
			}
		case "ANMF":
			frames = append(frames, c)
		}
	}
	if len(frames) == 0 { // a still
		img, err := webp.Decode(bytes.NewReader(raw))
		if err != nil {
			return nil, err
		}
		return &Anim{Frames: []*image.RGBA{toRGBA(img)}, Delays: []time.Duration{time.Second}}, nil
	}
	canvas := image.NewRGBA(image.Rect(0, 0, cw, ch))
	out := &Anim{}
	var prev image.Rectangle
	disposePrev := false
	for _, f := range frames {
		d := f.data
		if len(d) < 16 {
			return nil, errors.New("short ANMF chunk")
		}
		x, y := 2*int(u24(d[0:])), 2*int(u24(d[3:]))
		w, h := 1+int(u24(d[6:])), 1+int(u24(d[9:]))
		dur := time.Duration(u24(d[12:])) * time.Millisecond
		flags := d[15]
		blend := flags&0x02 == 0 // bit 1 set = do not blend
		dispose := flags&0x01 != 0
		if disposePrev {
			draw.Draw(canvas, prev, image.Transparent, image.Point{}, draw.Src)
		}
		img, err := webp.Decode(bytes.NewReader(single(d[16:], w, h)))
		if err != nil {
			return nil, fmt.Errorf("%s frame %d: %w", path, len(out.Frames), err)
		}
		r := image.Rect(x, y, x+w, y+h)
		op := draw.Src
		if blend {
			op = draw.Over
		}
		draw.Draw(canvas, r, img, img.Bounds().Min, op)
		snap := image.NewRGBA(canvas.Bounds())
		copy(snap.Pix, canvas.Pix)
		out.Frames = append(out.Frames, snap)
		if dur <= 0 {
			dur = 62 * time.Millisecond
		}
		out.Delays = append(out.Delays, dur)
		prev, disposePrev = r, dispose
	}
	return out, nil
}

type chunk struct {
	id   string
	data []byte
}

func chunks(b []byte) []chunk {
	var out []chunk
	for len(b) >= 8 {
		n := int(binary.LittleEndian.Uint32(b[4:8]))
		if 8+n > len(b) {
			break
		}
		out = append(out, chunk{string(b[0:4]), b[8 : 8+n]})
		b = b[8+n+n%2:]
	}
	return out
}

// single wraps one frame's chunks (ALPH? + VP8 | VP8L) into a standalone WebP that x/image/webp can decode.
func single(frame []byte, w, h int) []byte {
	var body bytes.Buffer
	hasAlpha := false
	for _, c := range chunks(frame) {
		if c.id == "ALPH" {
			hasAlpha = true
		}
	}
	if hasAlpha { // VP8 + ALPH needs a VP8X header announcing the alpha
		x := make([]byte, 10)
		x[0] = 0x10
		put24(x[4:], uint32(w-1))
		put24(x[7:], uint32(h-1))
		writeChunk(&body, "VP8X", x)
	}
	body.Write(frame)
	var out bytes.Buffer
	out.WriteString("RIFF")
	binary.Write(&out, binary.LittleEndian, uint32(4+body.Len())) //nolint:errcheck
	out.WriteString("WEBP")
	out.Write(body.Bytes())
	return out.Bytes()
}

func writeChunk(b *bytes.Buffer, id string, data []byte) {
	b.WriteString(id)
	binary.Write(b, binary.LittleEndian, uint32(len(data))) //nolint:errcheck
	b.Write(data)
	if len(data)%2 == 1 {
		b.WriteByte(0)
	}
}

func u24(b []byte) uint32 { return uint32(b[0]) | uint32(b[1])<<8 | uint32(b[2])<<16 }

func put24(b []byte, v uint32) { b[0], b[1], b[2] = byte(v), byte(v>>8), byte(v>>16) }

func toRGBA(img image.Image) *image.RGBA {
	if r, ok := img.(*image.RGBA); ok {
		return r
	}
	r := image.NewRGBA(img.Bounds())
	draw.Draw(r, r.Bounds(), img, img.Bounds().Min, draw.Src)
	return r
}
