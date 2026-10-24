package pack

import (
	"archive/zip"
	"bytes"
	"context"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"image"
	"image/color"
	"image/png"
	"io"
	"os"
	"path/filepath"
	"testing"
	"time"
)

func needCwebp(t *testing.T) {
	t.Helper()
	if err := CheckCwebp(); err != nil {
		t.Skip(err)
	}
}

func writePNG(t *testing.T, path string, w, h int) {
	t.Helper()
	img := image.NewRGBA(image.Rect(0, 0, w, h))
	for y := range h {
		for x := range w {
			img.Set(x, y, color.RGBA{uint8(x), uint8(y), 128, 255})
		}
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	if err := png.Encode(f, img); err != nil {
		t.Fatal(err)
	}
}

// webpSize reads the canvas size from a WebP header (VP8 / VP8L / VP8X).
func webpSize(t *testing.T, b []byte) (int, int) {
	t.Helper()
	if len(b) < 30 || string(b[:4]) != "RIFF" || string(b[8:12]) != "WEBP" {
		t.Fatalf("not a WebP (%d bytes)", len(b))
	}
	switch string(b[12:16]) {
	case "VP8 ":
		return int(binary.LittleEndian.Uint16(b[26:28]) & 0x3fff), int(binary.LittleEndian.Uint16(b[28:30]) & 0x3fff)
	case "VP8L":
		bits := binary.LittleEndian.Uint32(b[21:25])
		return int(bits&0x3fff) + 1, int((bits>>14)&0x3fff) + 1
	case "VP8X":
		w := int(b[24]) | int(b[25])<<8 | int(b[26])<<16
		h := int(b[27]) | int(b[28])<<8 | int(b[29])<<16
		return w + 1, h + 1
	}
	t.Fatalf("unknown chunk %q", b[12:16])
	return 0, 0
}

func TestCoverCrop(t *testing.T) {
	for _, c := range []struct{ w, h, x, y, cw, ch int }{
		{832, 1216, 0, 0, 832, 1216},  // already the cover aspect
		{1216, 832, 323, 0, 569, 832}, // landscape: full height, centered
		{416, 1000, 0, 196, 416, 608}, // too tall: full width, centered
	} {
		x, y, cw, ch := coverCrop(c.w, c.h)
		if x != c.x || y != c.y || cw != c.cw || ch != c.ch {
			t.Errorf("%dx%d: got %d %d %d %d, want %d %d %d %d", c.w, c.h, x, y, cw, ch, c.x, c.y, c.cw, c.ch)
		}
	}
}

func TestConvertAndCover(t *testing.T) {
	needCwebp(t)
	dir := t.TempDir()
	src := filepath.Join(dir, "p.png")
	writePNG(t, src, 64, 40)
	ctx := context.Background()
	if err := convertPNG(ctx, src, filepath.Join(dir, "p.webp")); err != nil {
		t.Fatal(err)
	}
	b, _ := os.ReadFile(filepath.Join(dir, "p.webp"))
	if w, h := webpSize(t, b); w != 64 || h != 40 {
		t.Errorf("panel %dx%d", w, h)
	}
	if err := makeCover(ctx, src, filepath.Join(dir, "c.webp")); err != nil {
		t.Fatal(err)
	}
	b, _ = os.ReadFile(filepath.Join(dir, "c.webp"))
	if w, h := webpSize(t, b); w != rule().Cover.Width || h != rule().Cover.Height {
		t.Errorf("cover %dx%d", w, h)
	}
	if err := convertPNG(ctx, filepath.Join(dir, "missing.png"), filepath.Join(dir, "x.webp")); err == nil {
		t.Error("missing source must fail")
	}
}

// TestBuildZip stages media for a two-story pack and checks the zip: entry order, methods,
// manifest, dimensions, loops copied unchanged, covers written next to the catalog.
func TestBuildZip(t *testing.T) {
	needCwebp(t)
	media := t.TempDir()
	out := t.TempDir()
	w := worlds("w_a")[0]
	e1, e2 := ep("cp_a", 1, 2), ep("cp_b", 1, 1)
	loopBytes := []byte("RIFF\x00\x00\x00\x00WEBPVP8Xfake-animated-loop")
	for _, e := range []Episode{e1, e2} {
		for _, p := range e.Panels {
			writePNG(t, filepath.Join(media, p.ImagePath), 48, 72)
			if p.VideoPath != "" {
				if err := os.WriteFile(filepath.Join(media, p.VideoPath), loopBytes, 0o644); err != nil {
					t.Fatal(err)
				}
			}
		}
	}
	now := time.Date(2026, 10, 23, 8, 0, 0, 0, time.UTC)
	opts := Options{ID: "demo", Title: "Demo", Version: 1, MediaDir: media, OutDir: out, Now: now, Workers: 2}
	parts, err := Plan(opts, []Story{story(w, 1, e1), story(w, 1, e2)})
	if err != nil {
		t.Fatal(err)
	}
	ps, err := buildPart(context.Background(), opts, parts[0])
	if err != nil {
		t.Fatal(err)
	}
	if ps.Path != filepath.Join(out, "packs", "demo-v1.zip") || ps.Stories != 2 || ps.Episodes != 2 || ps.Panels != 3 || ps.Loops != 2 || ps.Bytes == 0 || len(ps.SHA256) != 64 {
		t.Fatalf("summary %+v", ps)
	}
	if st, err := os.Stat(ps.Path); err != nil || st.Size() != ps.Bytes {
		t.Fatalf("zip size: %v %v", st, err)
	}
	zr, err := zip.OpenReader(ps.Path)
	if err != nil {
		t.Fatal(err)
	}
	defer zr.Close()
	var names []string
	for _, f := range zr.File {
		names = append(names, f.Name)
		wantMethod := uint16(zip.Store)
		if f.Name == "pack.json" {
			wantMethod = zip.Deflate
		}
		if f.Method != wantMethod {
			t.Errorf("%s: method %d", f.Name, f.Method)
		}
		if !f.Modified.Equal(now) {
			t.Errorf("%s: modified %v", f.Name, f.Modified)
		}
	}
	want := fmt.Sprint([]string{"pack.json", "covers/cp_a.webp", "covers/cp_b.webp",
		"media/ep_a_1/p00.webp", "media/ep_a_1/p00_loop.webp", "media/ep_a_1/p01.webp",
		"media/ep_b_1/p00.webp", "media/ep_b_1/p00_loop.webp"})
	if fmt.Sprint(names) != want {
		t.Fatalf("entries\n got %v\nwant %v", names, want)
	}
	read := func(name string) []byte {
		t.Helper()
		for _, f := range zr.File {
			if f.Name == name {
				rc, err := f.Open()
				if err != nil {
					t.Fatal(err)
				}
				defer rc.Close()
				b, _ := io.ReadAll(rc)
				return b
			}
		}
		t.Fatalf("%s missing", name)
		return nil
	}
	var m Manifest
	if err := json.Unmarshal(read("pack.json"), &m); err != nil {
		t.Fatal(err)
	}
	if m.ID != "demo" || len(m.Stories) != 2 || len(m.Episodes) != 2 || len(m.Worlds) != 1 || m.GeneratedAt != "2026-10-23T08:00:00Z" {
		t.Fatalf("manifest %+v", m)
	}
	p0 := m.Episodes[0]["panels"].([]any)[0].(map[string]any)
	if p0["image_url"] != "media/ep_a_1/p00.webp" || p0["video_url"] != "media/ep_a_1/p00_loop.webp" {
		t.Fatalf("panel 0 %v", p0)
	}
	if w, h := webpSize(t, read("media/ep_a_1/p00.webp")); w != 48 || h != 72 {
		t.Errorf("panel %dx%d", w, h)
	}
	if w, h := webpSize(t, read("covers/cp_a.webp")); w != rule().Cover.Width || h != rule().Cover.Height {
		t.Errorf("cover %dx%d", w, h)
	}
	if !bytes.Equal(read("media/ep_a_1/p00_loop.webp"), loopBytes) {
		t.Error("loop must be copied unchanged")
	}
	cover, err := os.ReadFile(filepath.Join(out, "covers", "cp_b.webp"))
	if err != nil || !bytes.Equal(cover, read("covers/cp_b.webp")) {
		t.Errorf("cover next to the catalog: %v", err)
	}

	// Same input, same bytes.
	ps2, err := buildPart(context.Background(), opts, parts[0])
	if err != nil || ps2.SHA256 != ps.SHA256 {
		t.Errorf("not deterministic: %s vs %s (%v)", ps2.SHA256, ps.SHA256, err)
	}

	// A panel whose PNG is missing on disk is a hard error, not a silent gap.
	os.Remove(filepath.Join(media, e2.Panels[0].ImagePath))
	if _, err := buildPart(context.Background(), opts, parts[0]); err == nil {
		t.Error("missing PNG must fail")
	}
}
