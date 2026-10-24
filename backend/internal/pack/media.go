package pack

import (
	"bytes"
	"context"
	"fmt"
	"image/png"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"sync"
)

// CheckCwebp fails clearly when the WebP encoder is not installed.
func CheckCwebp() error {
	if _, err := exec.LookPath("cwebp"); err != nil {
		return fmt.Errorf("cwebp not found in PATH (brew install webp / apt install webp): %w", err)
	}
	return nil
}

func cwebp(ctx context.Context, args ...string) error {
	cmd := exec.CommandContext(ctx, "cwebp", append([]string{"-quiet", "-q", strconv.Itoa(rule().WebPQuality)}, args...)...)
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("cwebp %v: %w: %s", args, err, bytes.TrimSpace(stderr.Bytes()))
	}
	return nil
}

// convertPNG encodes a panel PNG as WebP (rules webp_quality, 85) with the same dimensions.
func convertPNG(ctx context.Context, src, dst string) error {
	return cwebp(ctx, src, "-o", dst)
}

// makeCover crops the panel to the cover aspect (centered) and scales it to the rules cover size (416×608).
// cwebp applies -crop before -resize.
func makeCover(ctx context.Context, src, dst string) error {
	f, err := os.Open(src)
	if err != nil {
		return err
	}
	cfg, err := png.DecodeConfig(f)
	f.Close()
	if err != nil {
		return fmt.Errorf("%s: %w", src, err)
	}
	x, y, w, h := coverCrop(cfg.Width, cfg.Height)
	c := rule().Cover
	return cwebp(ctx, "-crop", itoa(x), itoa(y), itoa(w), itoa(h), "-resize", itoa(c.Width), itoa(c.Height), src, "-o", dst)
}

// coverCrop is the largest centered rectangle of the cover aspect inside a w×h image.
func coverCrop(w, h int) (x, y, cw, ch int) {
	coverWidth, coverHeight := rule().Cover.Width, rule().Cover.Height
	if w*coverHeight > h*coverWidth { // too wide: keep the height
		ch = h
		cw = h * coverWidth / coverHeight
	} else {
		cw = w
		ch = w * coverHeight / coverWidth
	}
	return (w - cw) / 2, (h - ch) / 2, cw, ch
}

func itoa(n int) string { return strconv.Itoa(n) }

func copyFile(src, dst string) error {
	b, err := os.ReadFile(src)
	if err != nil {
		return err
	}
	return os.WriteFile(dst, b, 0o644)
}

// stage produces every media file of a part under dir (same relative paths as in the zip),
// running cwebp on a worker pool. The first error cancels the rest.
func stage(ctx context.Context, dir string, files []File, workers int) error {
	if workers <= 0 {
		workers = runtime.NumCPU()
	}
	for _, f := range files {
		if _, err := os.Stat(f.Src); err != nil {
			return fmt.Errorf("media for %s: %w", f.Path, err)
		}
		if err := os.MkdirAll(filepath.Dir(filepath.Join(dir, filepath.FromSlash(f.Path))), 0o755); err != nil {
			return err
		}
	}
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()
	jobs := make(chan File)
	var (
		wg       sync.WaitGroup
		mu       sync.Mutex
		firstErr error
	)
	fail := func(err error) {
		mu.Lock()
		if firstErr == nil {
			firstErr = err
			cancel()
		}
		mu.Unlock()
	}
	for range workers {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for f := range jobs {
				dst := filepath.Join(dir, filepath.FromSlash(f.Path))
				var err error
				switch f.Kind {
				case kindConvert:
					err = convertPNG(ctx, f.Src, dst)
				case kindCover:
					err = makeCover(ctx, f.Src, dst)
				default:
					err = copyFile(f.Src, dst)
				}
				if err != nil {
					fail(fmt.Errorf("%s: %w", f.Path, err))
				}
			}
		}()
	}
loop:
	for _, f := range files {
		select {
		case jobs <- f:
		case <-ctx.Done():
			break loop
		}
	}
	close(jobs)
	wg.Wait()
	if firstErr != nil {
		return firstErr
	}
	return ctx.Err()
}
