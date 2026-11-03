package trailer

import (
	"image/png"
	"os"
	"path/filepath"
	"testing"
)

// TestDecodeWan decodes a real Wan loop when one is on disk (WEBTOON_TEST_LOOP), else skips.
func TestDecodeWan(t *testing.T) {
	p := os.Getenv("WEBTOON_TEST_LOOP")
	if p == "" {
		t.Skip("WEBTOON_TEST_LOOP not set")
	}
	a, err := DecodeWebPAnim(p)
	if err != nil {
		t.Fatal(err)
	}
	if len(a.Frames) < 10 {
		t.Fatalf("%d frames", len(a.Frames))
	}
	if out := os.Getenv("WEBTOON_TEST_OUT"); out != "" {
		f, _ := os.Create(filepath.Join(out, "frame.png"))
		png.Encode(f, a.Frames[len(a.Frames)/2]) //nolint:errcheck
		f.Close()
	}
	t.Logf("%d frames, %v each, %v", len(a.Frames), a.Delays[0], a.Frames[0].Bounds())
}
