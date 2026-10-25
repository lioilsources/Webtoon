package pack

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"io"
	"maps"
	"os"
	"path/filepath"
	"slices"
	"time"
)

// writeZip writes pack.json and the extra JSON files in name order (deflated), followed by the staged media files
// in the given order (stored: WebP is already compressed). Entry times are fixed to mod, so the same input gives
// the same bytes. Returns size and sha256 of the zip.
func writeZip(path string, manifest Manifest, extra map[string][]byte, stageDir string, files []File, mod time.Time) (int64, string, error) {
	body, err := json.Marshal(manifest)
	if err != nil {
		return 0, "", err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return 0, "", err
	}
	out, err := os.Create(path)
	if err != nil {
		return 0, "", err
	}
	defer out.Close()
	h := sha256.New()
	cw := &countWriter{w: io.MultiWriter(out, h)}
	zw := zip.NewWriter(cw)
	mod = mod.UTC()
	w, err := zw.CreateHeader(&zip.FileHeader{Name: "pack.json", Method: zip.Deflate, Modified: mod})
	if err != nil {
		return 0, "", err
	}
	if _, err := w.Write(body); err != nil {
		return 0, "", err
	}
	for _, name := range slices.Sorted(maps.Keys(extra)) {
		w, err := zw.CreateHeader(&zip.FileHeader{Name: name, Method: zip.Deflate, Modified: mod})
		if err != nil {
			return 0, "", err
		}
		if _, err := w.Write(extra[name]); err != nil {
			return 0, "", err
		}
	}
	for _, f := range files {
		w, err := zw.CreateHeader(&zip.FileHeader{Name: f.Path, Method: zip.Store, Modified: mod})
		if err != nil {
			return 0, "", err
		}
		src, err := os.Open(filepath.Join(stageDir, filepath.FromSlash(f.Path)))
		if err != nil {
			return 0, "", err
		}
		_, err = io.Copy(w, src)
		src.Close()
		if err != nil {
			return 0, "", err
		}
	}
	if err := zw.Close(); err != nil {
		return 0, "", err
	}
	if err := out.Close(); err != nil {
		return 0, "", err
	}
	return cw.n, hex.EncodeToString(h.Sum(nil)), nil
}

type countWriter struct {
	w io.Writer
	n int64
}

func (c *countWriter) Write(p []byte) (int, error) {
	n, err := c.w.Write(p)
	c.n += int64(n)
	return n, err
}
