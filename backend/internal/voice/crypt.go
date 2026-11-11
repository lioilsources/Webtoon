package voice

import (
	"crypto/aes"
	"crypto/cipher"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"
)

// Box encrypts files at rest: AES-256-GCM, file = magic "TFV1" | 12-byte nonce | ciphertext+tag.
// The relative path is the additional data, so a file moved to another voice does not decrypt.
// Subkeys are derived from the master key with HMAC-SHA256, one per purpose.
type Box struct {
	aead   cipher.AEAD
	urlKey []byte
	dir    string
}

const boxMagic = "TFV1"

func derive(master []byte, purpose string) []byte {
	m := hmac.New(sha256.New, master)
	m.Write([]byte("toonfork-voice/" + purpose))
	return m.Sum(nil)
}

// NewBox returns nil when key is empty (voices disabled, fail closed).
func NewBox(key []byte, dir string) (*Box, error) {
	if len(key) == 0 {
		return nil, nil
	}
	if len(key) != 32 {
		return nil, errors.New("voice data key must be 32 bytes")
	}
	blk, err := aes.NewCipher(derive(key, "enc/v1"))
	if err != nil {
		return nil, err
	}
	aead, err := cipher.NewGCM(blk)
	if err != nil {
		return nil, err
	}
	return &Box{aead: aead, urlKey: derive(key, "url/v1"), dir: dir}, nil
}

// Write encrypts data to dir/rel (0600, parent dirs 0700) via a temp file and rename.
func (b *Box) Write(rel string, data []byte) error {
	nonce := make([]byte, b.aead.NonceSize())
	if _, err := rand.Read(nonce); err != nil {
		return err
	}
	out := make([]byte, 0, len(boxMagic)+len(nonce)+len(data)+b.aead.Overhead())
	out = append(out, boxMagic...)
	out = append(out, nonce...)
	out = b.aead.Seal(out, nonce, data, []byte(rel))
	p := filepath.Join(b.dir, rel)
	if err := os.MkdirAll(filepath.Dir(p), 0o700); err != nil {
		return err
	}
	tmp, err := os.CreateTemp(filepath.Dir(p), ".tmp-*")
	if err != nil {
		return err
	}
	if _, err := tmp.Write(out); err != nil {
		tmp.Close()
		os.Remove(tmp.Name())
		return err
	}
	if err := tmp.Close(); err != nil {
		os.Remove(tmp.Name())
		return err
	}
	if err := os.Chmod(tmp.Name(), 0o600); err != nil {
		os.Remove(tmp.Name())
		return err
	}
	return os.Rename(tmp.Name(), p)
}

// Read decrypts dir/rel.
func (b *Box) Read(rel string) ([]byte, error) {
	raw, err := os.ReadFile(filepath.Join(b.dir, rel))
	if err != nil {
		return nil, err
	}
	ns := b.aead.NonceSize()
	if len(raw) < len(boxMagic)+ns || string(raw[:len(boxMagic)]) != boxMagic {
		return nil, fmt.Errorf("%s: not an encrypted voice file", rel)
	}
	nonce := raw[len(boxMagic) : len(boxMagic)+ns]
	pt, err := b.aead.Open(nil, nonce, raw[len(boxMagic)+ns:], []byte(rel))
	if err != nil {
		return nil, fmt.Errorf("%s: decrypt: %w", rel, err)
	}
	return pt, nil
}

// removeVoiceDir deletes everything stored for a voice (works without the key, too).
func removeVoiceDir(dataDir, voiceID string) error {
	if !isUUID(voiceID) {
		return fmt.Errorf("refusing to remove voice dir %q", voiceID)
	}
	return os.RemoveAll(filepath.Join(dataDir, voiceDir(voiceID)))
}

func voiceDir(voiceID string) string { return filepath.Join("voices", voiceID) }

func samplePath(voiceID, ext string) string {
	return filepath.Join(voiceDir(voiceID), "sample."+ext+".enc")
}

func linePath(voiceID, hash string) string {
	return filepath.Join(voiceDir(voiceID), "lines", hash+".m4a.enc")
}

// --- signed line URLs --------------------------------------------------------------

// urlBucket rounds expiries up to the next bucket boundary, so a line asked for twice within a
// bucket gets the same URL; it stays valid between ttl and ttl+urlBucket.
const urlBucket = 15 * time.Minute

func (b *Box) sign(voiceID, hash string, exp int64) string {
	m := hmac.New(sha256.New, b.urlKey)
	fmt.Fprintf(m, "%s\x1f%s\x1f%d", voiceID, hash, exp)
	return hex.EncodeToString(m.Sum(nil)[:16])
}

// LineURL is the path (with query) of a signed, short-lived line URL valid for at least ttl.
func (b *Box) LineURL(voiceID, hash string, now time.Time, ttl time.Duration) string {
	exp := now.Add(ttl).Truncate(urlBucket).Add(urlBucket).Unix()
	return "/v1/player/lines/" + voiceID + "/" + hash + ".m4a?exp=" + strconv.FormatInt(exp, 10) + "&sig=" + b.sign(voiceID, hash, exp)
}

// CheckLineURL validates exp and sig of a line URL.
func (b *Box) CheckLineURL(voiceID, hash, expS, sig string, now time.Time) bool {
	exp, err := strconv.ParseInt(expS, 10, 64)
	if err != nil || now.Unix() > exp {
		return false
	}
	return hmac.Equal([]byte(sig), []byte(b.sign(voiceID, hash, exp)))
}
