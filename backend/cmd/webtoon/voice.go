package main

import (
	"context"
	"errors"
	"flag"
	"log/slog"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/ol1n/webtoon/backend/internal/voice"
	"github.com/ol1n/webtoon/backend/internal/voice/receipt"
	"github.com/ol1n/webtoon/backend/internal/voiceworker"
)

// newVoiceServer builds the player voice API (docs/voice-backend.md). A configuration error
// never stops the Studio API: voices are then disabled (503 voice_unavailable / fail closed).
func newVoiceServer(pool *pgxpool.Pool) *voice.Server {
	log := slog.Default()
	vcfg, err := voice.ConfigFromEnv()
	if err != nil {
		log.Error("voice config, voices disabled", "err", err)
		vcfg.DataKey = nil
	}
	rcfg := receipt.ConfigFromEnv()
	rv, err := receipt.New(rcfg, log)
	if err != nil {
		log.Error("voice receipts: Play disabled", "err", err)
		rcfg.GoogleSAFile = ""
		if rv, err = receipt.New(rcfg, log); err != nil {
			log.Error("voice receipts, voices disabled", "err", err)
			return nil
		}
	}
	vs, err := voice.New(vcfg, voice.NewPGStore(pool), rv, nil, log)
	if err != nil {
		log.Error("voice server, voices disabled", "err", err)
		return nil
	}
	if n, err := strconv.Atoi(os.Getenv("VOICE_RECEIPT_MAX_DEVICES")); err == nil && n >= 0 {
		vs.ReceiptMaxDevices = n
	}
	return vs
}

// runVoiceWorker is `webtoon voice-worker [-once]`: the Spark side of the player voice.
func runVoiceWorker(ctx context.Context, args []string) error {
	fs := flag.NewFlagSet("voice-worker", flag.ExitOnError)
	once := fs.Bool("once", false, "work the queue until it is empty, then exit")
	fs.Parse(args) //nolint:errcheck

	apiURL, token := os.Getenv("VOICE_API_URL"), os.Getenv("VOICE_WORKER_TOKEN")
	if apiURL == "" || token == "" {
		return errors.New("VOICE_API_URL and VOICE_WORKER_TOKEN are required (deploy/voice-worker/worker.env)")
	}
	name := os.Getenv("VOICE_WORKER_NAME")
	if name == "" {
		name, _ = os.Hostname()
	}
	log := slog.Default().With("component", "voice-worker")
	hc := &http.Client{Timeout: 2 * time.Minute}
	cfg := voiceworker.DefaultConfig()
	w := &voiceworker.Worker{
		API:   &voiceworker.APIClient{BaseURL: apiURL, Token: token, Worker: name, HTTP: hc},
		Audio: &voiceworker.AudioClient{BaseURL: envOr("AUDIO_URL", "http://localhost:8093"), Key: os.Getenv("AUDIO_API_KEY"), HTTP: hc},
		Cfg:   cfg,
		Encode: func(ctx context.Context, parts []string, out string) (float64, error) {
			return voiceworker.EncodeLine(ctx, parts, out, cfg.Encode)
		},
		Measure: voiceworker.MeasureTake,
		TmpDir:  envOr("VOICE_WORK_DIR", os.TempDir()),
		Log:     log,
		Now:     time.Now,
	}
	if b := envOr("SPARK_BROKER", "http://localhost:8100"); !strings.EqualFold(b, "off") {
		prio, err := strconv.Atoi(envOr("VOICE_BROKER_PRIORITY", "20"))
		if err != nil {
			return errors.New("VOICE_BROKER_PRIORITY: not a number")
		}
		w.Broker = &voiceworker.Broker{BaseURL: b, Token: os.Getenv("SPARK_BROKER_TOKEN"), Project: "webtoon",
			Session: "toonfork-voice-worker", Title: "Toonfork: hlasy hráčů", Services: []string{"tts"},
			Priority: prio, LeaseMin: 30, HTTP: &http.Client{Timeout: 30 * time.Second}, Log: log, Now: time.Now,
			Poll: 15 * time.Second, Beat: 2 * time.Minute}
	} else {
		log.Warn("SPARK_BROKER=off: working without a broker lease (only for local tests)")
	}
	log.Info("voice worker ready", "api", apiURL, "worker", name, "broker", w.Broker != nil)
	return w.Run(ctx, *once)
}
