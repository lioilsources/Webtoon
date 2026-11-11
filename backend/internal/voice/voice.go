// Package voice is the player's own voice for the Toonfork app (docs/voice-backend.md):
// anonymous device tokens, the voice sample upload with consent and an IAP receipt, the line
// synthesis queue for the Spark worker (internal/voiceworker) and short-lived signed line URLs.
//
// Voice samples are biometric data. They live only in DataDir, encrypted with AES-256-GCM
// (key from VOICE_DATA_KEY), and are never logged. Deleting a voice removes the sample and the
// rendered lines at once and queues the deletion of the AiStack voice on Spark.
package voice

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"os"
	"strconv"
	"strings"
	"time"

	"golang.org/x/text/unicode/norm"
)

// Voice statuses. "deleting" voices are invisible to the app (404) until the Spark side is gone.
const (
	StatusQueued   = "queued"
	StatusReady    = "ready"
	StatusFailed   = "failed"
	StatusDeleting = "deleting"
)

// Task kinds and statuses of the Spark worker queue (table voice_tasks).
const (
	KindVoiceCreate = "voice_create"
	KindVoiceDelete = "voice_delete"
	KindLines       = "lines"

	TaskQueued    = "queued"
	TaskRunning   = "running"
	TaskDone      = "done"
	TaskFailed    = "failed"
	TaskCancelled = "cancelled"
)

var (
	ErrNotFound    = errors.New("not found")
	ErrVoiceExists = errors.New("voice_exists")
	ErrLeaseLost   = errors.New("task lease lost")
)

type Device struct {
	ID         string
	TokenHash  string
	Platform   string
	CreatedAt  time.Time
	LastSeenAt time.Time
}

type Voice struct {
	ID              string
	DeviceID        string // "" once the device is gone
	Status          string
	Error           string
	SampleFile      string // relative to DataDir, encrypted; "" after deletion
	SampleExt       string // m4a | wav
	SampleBytes     int
	SampleDurationS float64
	ReceiptPlatform string // ios | android | test
	ReceiptOrigID   string // original transaction id (App Store) / order id (Play)
	ReceiptTxID     string
	CreatedAt       time.Time
	UpdatedAt       time.Time
	LastUsedAt      time.Time
}

// Consent is the audit record of the player's consent. It holds no biometric data and outlives
// the voice by Config.ConsentRetention.
type Consent struct {
	VoiceID      string
	DeviceID     string
	Text         string
	SHA256       string
	Version      string
	ConsentedAt  time.Time
	DeletedAt    *time.Time
	DeleteReason string
}

// Line is one rendered line in the cache, keyed by Hash (LineHash).
type Line struct {
	VoiceID   string
	Hash      string
	Lang      string
	File      string // relative to DataDir, encrypted
	Bytes     int
	DurationS float64
	CreatedAt time.Time
}

// TaskLine is one requested line: the app's key, the normalized text and its cache hash.
type TaskLine struct {
	Key  string `json:"key"`
	Text string `json:"text"`
	Hash string `json:"hash"`
}

type Task struct {
	ID         string
	Kind       string
	VoiceID    string
	DeviceID   string
	Lang       string
	Lines      []TaskLine
	IdemKey    string
	Priority   int
	Status     string
	Error      string
	Attempts   int
	Worker     string
	RunAfter   time.Time
	LeaseUntil *time.Time
	CreatedAt  time.Time
	UpdatedAt  time.Time
	FinishedAt *time.Time
}

// NormalizeText is the text that is voiced and hashed: NFC, trimmed, inner whitespace collapsed.
func NormalizeText(s string) string {
	return strings.Join(strings.Fields(norm.NFC.String(s)), " ")
}

// LineHash is the cache key of a line: sha256(voice_id 0x1f lang 0x1f normalized text).
// The same text in the same voice and language is voiced once and gets the same URL.
func LineHash(voiceID, lang, text string) string {
	h := sha256.Sum256([]byte(voiceID + "\x1f" + lang + "\x1f" + NormalizeText(text)))
	return hex.EncodeToString(h[:])
}

// SHA256Hex returns the hex sha256 of s.
func SHA256Hex(s string) string {
	h := sha256.Sum256([]byte(s))
	return hex.EncodeToString(h[:])
}

// AudioVoiceID is the voice id in the AiStack audio service (^[a-z0-9][a-z0-9_-]{1,47}$).
func AudioVoiceID(prefix, voiceID string) string { return prefix + voiceID }

// Config of the player voice API. Zero values are filled by withDefaults.
type Config struct {
	DataDir          string        // VOICE_DATA_DIR: encrypted samples and lines (gitignored, JODA only)
	DataKey          []byte        // VOICE_DATA_KEY (64 hex chars); empty = voice endpoints answer 503 voice_unavailable
	WorkerToken      string        // VOICE_WORKER_TOKEN for /v1/worker/*; empty = worker endpoints answer 503
	PublicURL        string        // VOICE_PUBLIC_URL: absolute prefix of line URLs (https://webtoon-api.ol1n.com); "" = relative
	AudioPrefix      string        // VOICE_AUDIO_PREFIX: voice id prefix in AiStack, default "toonfork-"
	Langs            []string      // VOICE_LANGS: languages the clone engine speaks, default cs (chatterbox-cs)
	MaxLines         int           // VOICE_MAX_LINES per request, default 200
	MaxChars         int           // VOICE_MAX_CHARS per line, default 300
	DailyLines       int           // VOICE_DAILY_LINES: newly voiced lines per device and day (UTC), default 300
	Retention        time.Duration // VOICE_RETENTION_DAYS: delete a voice unused this long, default 180 days
	ConsentRetention time.Duration // VOICE_CONSENT_RETENTION_DAYS: keep the consent record after deletion, default 365 days
	URLTTL           time.Duration // VOICE_URL_TTL: lifetime of signed line URLs, default 1h
	ConsentVersion   string        // VOICE_CONSENT_VERSION: used when the app sends no consent_version, default "1"
	DeviceRate       int           // VOICE_DEVICE_RATE: device registrations per IP and hour, default 10
	TaskLease        time.Duration // worker task lease (heartbeat extends it), default 10 min
	MaxTaskAttempts  int           // claims before a task fails for good, default 20 (engine-down retries count)
}

const (
	defaultLeaseMinutes = 10
	MinSampleS          = 5.0
	MaxSampleS          = 30.0
	sampleTolerance     = 0.25 // encoder padding
	MaxSampleBytes      = 5 << 20
	MaxLineBytes        = 2 << 20
)

func (c Config) withDefaults() Config {
	if c.DataDir == "" {
		c.DataDir = "./voice-data"
	}
	if c.AudioPrefix == "" {
		c.AudioPrefix = "toonfork-"
	}
	if len(c.Langs) == 0 {
		c.Langs = []string{"cs"}
	}
	if c.MaxLines <= 0 {
		c.MaxLines = 200
	}
	if c.MaxChars <= 0 {
		c.MaxChars = 300
	}
	if c.DailyLines <= 0 {
		c.DailyLines = 300
	}
	if c.Retention <= 0 {
		c.Retention = 180 * 24 * time.Hour
	}
	if c.ConsentRetention <= 0 {
		c.ConsentRetention = 365 * 24 * time.Hour
	}
	if c.URLTTL <= 0 {
		c.URLTTL = time.Hour
	}
	if c.ConsentVersion == "" {
		c.ConsentVersion = "1"
	}
	if c.DeviceRate <= 0 {
		c.DeviceRate = 10
	}
	if c.TaskLease <= 0 {
		c.TaskLease = defaultLeaseMinutes * time.Minute
	}
	if c.MaxTaskAttempts <= 0 {
		c.MaxTaskAttempts = 20
	}
	c.PublicURL = strings.TrimRight(c.PublicURL, "/")
	return c
}

// ConfigFromEnv reads the VOICE_* variables. A malformed VOICE_DATA_KEY is reported as an error so
// that the API refuses voices instead of storing samples under a wrong key.
func ConfigFromEnv() (Config, error) {
	c := Config{
		DataDir:          os.Getenv("VOICE_DATA_DIR"),
		WorkerToken:      os.Getenv("VOICE_WORKER_TOKEN"),
		PublicURL:        os.Getenv("VOICE_PUBLIC_URL"),
		AudioPrefix:      os.Getenv("VOICE_AUDIO_PREFIX"),
		Langs:            list(os.Getenv("VOICE_LANGS")),
		MaxLines:         envInt("VOICE_MAX_LINES"),
		MaxChars:         envInt("VOICE_MAX_CHARS"),
		DailyLines:       envInt("VOICE_DAILY_LINES"),
		Retention:        time.Duration(envInt("VOICE_RETENTION_DAYS")) * 24 * time.Hour,
		ConsentRetention: time.Duration(envInt("VOICE_CONSENT_RETENTION_DAYS")) * 24 * time.Hour,
		ConsentVersion:   os.Getenv("VOICE_CONSENT_VERSION"),
		DeviceRate:       envInt("VOICE_DEVICE_RATE"),
	}
	if v := os.Getenv("VOICE_URL_TTL"); v != "" {
		d, err := time.ParseDuration(v)
		if err != nil {
			return c, errors.New("VOICE_URL_TTL: " + err.Error())
		}
		c.URLTTL = d
	}
	if k := strings.TrimSpace(os.Getenv("VOICE_DATA_KEY")); k != "" {
		b, err := hex.DecodeString(k)
		if err != nil || len(b) != 32 {
			// Never echo the value.
			return c, errors.New("VOICE_DATA_KEY must be 64 hex characters (openssl rand -hex 32)")
		}
		c.DataKey = b
	}
	return c.withDefaults(), nil
}

func list(s string) []string {
	var out []string
	for _, v := range strings.Split(s, ",") {
		if v = strings.TrimSpace(v); v != "" {
			out = append(out, v)
		}
	}
	return out
}

func envInt(k string) int {
	n, _ := strconv.Atoi(os.Getenv(k))
	return n
}
