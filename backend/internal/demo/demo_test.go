package demo

import (
	"fmt"
	"image"
	"image/png"
	"os"
	"path/filepath"
	"testing"
)

func writePNG(t *testing.T, path string, w, h int) {
	t.Helper()
	f, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	defer f.Close()
	if err := png.Encode(f, image.NewRGBA(image.Rect(0, 0, w, h))); err != nil {
		t.Fatal(err)
	}
}

func TestFindPanels(t *testing.T) {
	dir := t.TempDir()
	writePNG(t, filepath.Join(dir, "p00_s0.png"), 12, 8)
	writePNG(t, filepath.Join(dir, "p01_s0.png"), 8, 12)
	meta := `{"images": [{"panel": 1, "variant": 0, "seed": 4242, "positive": "1girl", "negative": "text",
		"rating": {"general": 0.99}}]}`
	if err := os.WriteFile(filepath.Join(dir, "meta.json"), []byte(meta), 0o644); err != nil {
		t.Fatal(err)
	}
	got, err := FindPanels(dir, 2, 0)
	if err != nil {
		t.Fatal(err)
	}
	if got[0].Width != 12 || got[0].Height != 8 || got[0].Seed != 1000 {
		t.Errorf("panel 0 = %+v", got[0])
	}
	if got[1].Width != 8 || got[1].Height != 12 || got[1].Seed != 4242 || got[1].Prompt != "1girl" || got[1].Rating["general"] != 0.99 {
		t.Errorf("panel 1 = %+v", got[1])
	}
	if _, err := FindPanels(dir, 3, 0); err == nil {
		t.Error("missing p02 should fail")
	}
	if _, err := FindPanels(dir, 1, 1); err == nil {
		t.Error("missing variant 1 should fail")
	}
	bad := filepath.Join(dir, fmt.Sprintf("p%02d_s%d.png", 0, 2))
	_ = os.WriteFile(bad, []byte("nope"), 0o644)
	if _, err := FindPanels(dir, 1, 2); err == nil {
		t.Error("non-PNG should fail")
	}
}
