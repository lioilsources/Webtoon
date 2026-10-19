// Package config reads the service configuration from the environment.
package config

import (
	"os"
	"strconv"
	"strings"
	"time"
)

type Config struct {
	LLMURL         string        // WEBTOON_LLM
	LLMModel       string        // WEBTOON_LLM_MODEL
	ComfyURL       string        // WEBTOON_COMFY
	WD14URL        string        // WEBTOON_WD14
	ImageAPI       string        // WEBTOON_IMAGE_API: AiStack Image API base URL; set = used instead of ComfyURL + WD14URL
	CFAccessID     string        // WEBTOON_CF_ACCESS_ID: Cloudflare Access service token (Image API and LLM)
	CFAccessSecret string        // WEBTOON_CF_ACCESS_SECRET
	DatabaseURL    string        // DATABASE_URL
	MediaDir       string        // MEDIA_DIR
	MediaBaseURL   string        // MEDIA_BASE_URL (prefix of image URLs in API responses)
	Workers        int           // WORKERS (0 = no worker pool in this process)
	Mode           string        // MODE: all | api | worker
	ListenAddr     string        // LISTEN_ADDR
	Backoff        time.Duration // WEBTOON_BACKOFF: delay when LLM/ComfyUI/WD14 is down
	MaxAttempts    int           // WEBTOON_MAX_ATTEMPTS for ordinary failures
	Seed           bool          // WEBTOON_SEED: import the embedded M0 world + styles on startup
	SeedOwner      string        // WEBTOON_SEED_OWNER
	CORSOrigins    []string      // WEBTOON_CORS_ORIGINS: comma-separated browser origins allowed to call the API ("*" = any)
}

func envList(key string) []string {
	var out []string
	for _, v := range strings.Split(os.Getenv(key), ",") {
		if v = strings.TrimSpace(v); v != "" {
			out = append(out, v)
		}
	}
	return out
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func envInt(key string, fallback int) int {
	if v := os.Getenv(key); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return fallback
}

func envDur(key string, fallback time.Duration) time.Duration {
	if v := os.Getenv(key); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			return d
		}
	}
	return fallback
}

func Load() Config {
	return Config{
		LLMURL:         envOr("WEBTOON_LLM", "http://192.168.88.66:8080/v1"),
		LLMModel:       envOr("WEBTOON_LLM_MODEL", "openclaw-default"),
		ComfyURL:       envOr("WEBTOON_COMFY", "http://192.168.88.66:8188"),
		WD14URL:        envOr("WEBTOON_WD14", "http://192.168.88.66:8097"),
		ImageAPI:       os.Getenv("WEBTOON_IMAGE_API"),
		CFAccessID:     os.Getenv("WEBTOON_CF_ACCESS_ID"),
		CFAccessSecret: os.Getenv("WEBTOON_CF_ACCESS_SECRET"),
		DatabaseURL:    envOr("DATABASE_URL", "postgres://webtoon:webtoon@localhost:5434/webtoon?sslmode=disable"),
		MediaDir:       envOr("MEDIA_DIR", "./media"),
		MediaBaseURL:   envOr("MEDIA_BASE_URL", "/media"),
		CORSOrigins:    envList("WEBTOON_CORS_ORIGINS"),
		Workers:        envInt("WORKERS", 2),
		Mode:           envOr("MODE", "all"),
		ListenAddr:     envOr("LISTEN_ADDR", ":8095"),
		Backoff:        envDur("WEBTOON_BACKOFF", 5*time.Minute),
		MaxAttempts:    envInt("WEBTOON_MAX_ATTEMPTS", 3),
		Seed:           envOr("WEBTOON_SEED", "false") == "true",
		SeedOwner:      envOr("WEBTOON_SEED_OWNER", "seed"),
	}
}
