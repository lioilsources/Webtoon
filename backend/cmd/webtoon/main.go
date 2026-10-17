// Command webtoon is the Webtoon backend: HTTP API + episode worker pool over Postgres.
//
//	webtoon [serve]                     API and/or worker depending on MODE (all|api|worker)
//	webtoon migrate                     apply migrations and exit
//	webtoon seed [-world f] [-styles f] [-owner id] [-visibility v]
//	                                    import the M0 world + style presets (embedded copies by default)
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/ol1n/webtoon/backend/data"
	"github.com/ol1n/webtoon/backend/internal/api"
	"github.com/ol1n/webtoon/backend/internal/comfy"
	"github.com/ol1n/webtoon/backend/internal/config"
	"github.com/ol1n/webtoon/backend/internal/db"
	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/seed"
	"github.com/ol1n/webtoon/backend/internal/store"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/tags"
	"github.com/ol1n/webtoon/backend/internal/wd14"
	"github.com/ol1n/webtoon/backend/internal/worker"
)

func main() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))
	cmd := "serve"
	args := os.Args[1:]
	if len(args) > 0 {
		cmd, args = args[0], args[1:]
	}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	cfg := config.Load()
	var err error
	switch cmd {
	case "serve":
		err = serve(ctx, cfg)
	case "migrate":
		err = db.Migrate(cfg.DatabaseURL)
	case "seed":
		err = runSeed(ctx, cfg, args)
	default:
		err = fmt.Errorf("unknown command %q (serve|migrate|seed)", cmd)
	}
	if err != nil {
		slog.Error("fatal", "cmd", cmd, "err", err)
		os.Exit(1)
	}
}

func openStore(ctx context.Context, cfg config.Config) (*store.Store, error) {
	if err := db.Migrate(cfg.DatabaseURL); err != nil {
		return nil, err
	}
	pool, err := pgxpool.New(ctx, cfg.DatabaseURL)
	if err != nil {
		return nil, err
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, err
	}
	return store.New(pool), nil
}

func runSeed(ctx context.Context, cfg config.Config, args []string) error {
	fs := flag.NewFlagSet("seed", flag.ExitOnError)
	worldPath := fs.String("world", "", "world JSON (default: embedded data/world_m0.json)")
	stylesPath := fs.String("styles", "", "styles JSON (default: embedded data/styles.json)")
	owner := fs.String("owner", cfg.SeedOwner, "owner_id of the seeded world")
	vis := fs.String("visibility", "public", "visibility of the seeded world")
	fs.Parse(args) //nolint:errcheck
	s, err := openStore(ctx, cfg)
	if err != nil {
		return err
	}
	defer s.Pool.Close()
	return doSeed(ctx, s, *worldPath, *stylesPath, *owner, *vis)
}

func doSeed(ctx context.Context, s *store.Store, worldPath, stylesPath, owner, vis string) error {
	worldRaw, stylesRaw := data.WorldM0, data.Styles
	var err error
	if worldPath != "" {
		if worldRaw, err = os.ReadFile(worldPath); err != nil {
			return err
		}
	}
	if stylesPath != "" {
		if stylesRaw, err = os.ReadFile(stylesPath); err != nil {
			return err
		}
	}
	n, err := seed.Styles(ctx, s, stylesRaw)
	if err != nil {
		return err
	}
	w, err := seed.World(ctx, s, worldRaw, owner, vis)
	if err != nil {
		return err
	}
	slog.Info("seeded", "presets", n, "world", w.ID, "characters", len(w.Characters), "locations", len(w.Locations), "owner", owner)
	return nil
}

func serve(ctx context.Context, cfg config.Config) error {
	s, err := openStore(ctx, cfg)
	if err != nil {
		return err
	}
	defer s.Pool.Close()
	if cfg.Seed {
		if err := doSeed(ctx, s, "", "", cfg.SeedOwner, "public"); err != nil {
			return err
		}
	}
	if err := os.MkdirAll(cfg.MediaDir, 0o755); err != nil {
		return err
	}

	runAPI := cfg.Mode == "all" || cfg.Mode == "api"
	runWorker := (cfg.Mode == "all" || cfg.Mode == "worker") && cfg.Workers > 0
	if !runAPI && !runWorker {
		return errors.New("nothing to run: check MODE / WORKERS")
	}

	var wk *worker.Worker
	if runWorker {
		vocab, err := tags.LoadVocab(data.WD14Tags)
		if err != nil {
			return err
		}
		gen := &storyboard.Generator{LLM: llm.New(cfg.LLMURL, cfg.LLMModel), Vocab: vocab, Attempts: 3}
		wk = worker.New(worker.Config{MediaDir: cfg.MediaDir, Backoff: cfg.Backoff, MaxAttempts: cfg.MaxAttempts},
			s, gen, comfy.New(cfg.ComfyURL), wd14.New(cfg.WD14URL))
	}

	var wg sync.WaitGroup
	if wk != nil {
		wg.Add(1)
		go func() { defer wg.Done(); wk.Run(ctx, cfg.Workers) }()
	}

	slog.Info("webtoon ready", "mode", cfg.Mode, "addr", cfg.ListenAddr, "workers", cfg.Workers,
		"llm", cfg.LLMURL, "model", cfg.LLMModel, "comfy", cfg.ComfyURL, "wd14", cfg.WD14URL,
		"media_dir", cfg.MediaDir, "backoff", cfg.Backoff)

	if runAPI {
		var waker api.Waker
		if wk != nil {
			waker = wk
		}
		srv := &http.Server{Addr: cfg.ListenAddr, ReadHeaderTimeout: 10 * time.Second,
			Handler: api.New(api.Config{MediaDir: cfg.MediaDir, MediaBaseURL: cfg.MediaBaseURL, MaxAttempts: cfg.MaxAttempts}, s, waker).Handler()}
		go func() {
			<-ctx.Done()
			shut, cancel := context.WithTimeout(context.Background(), 10*time.Second)
			defer cancel()
			srv.Shutdown(shut) //nolint:errcheck
		}()
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			return err
		}
	}
	wg.Wait()
	return nil
}
