// Command webtoon is the Webtoon backend: HTTP API + episode worker pool over Postgres.
//
//	webtoon [serve]                     API and/or worker depending on MODE (all|api|worker)
//	webtoon migrate                     apply migrations and exit
//	webtoon seed [-world f] [-styles f] [-owner id] [-visibility v]
//	                                    import the M0 world + style presets (embedded copies by default)
//	webtoon import-demo [-campaign id | -world id -player id] [-character id] [-variant n] <storyboard.json> <panel_dir>
//	                                    insert a ready episode from M0 outputs (no LLM/ComfyUI calls)
//	webtoon translate [-episode id | -all] [-langs en,de] [-force] [-inline]
//	                                    translate ready episodes' bubbles (enqueue jobs, or call the LLM right here)
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
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/ol1n/webtoon/backend/data"
	"github.com/ol1n/webtoon/backend/internal/api"
	"github.com/ol1n/webtoon/backend/internal/comfy"
	"github.com/ol1n/webtoon/backend/internal/config"
	"github.com/ol1n/webtoon/backend/internal/db"
	"github.com/ol1n/webtoon/backend/internal/demo"
	"github.com/ol1n/webtoon/backend/internal/imageq"
	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/seed"
	"github.com/ol1n/webtoon/backend/internal/store"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/tags"
	"github.com/ol1n/webtoon/backend/internal/translate"
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
	case "import-demo":
		err = runImportDemo(ctx, cfg, args)
	case "translate":
		err = runTranslate(ctx, cfg, args)
	default:
		err = fmt.Errorf("unknown command %q (serve|migrate|seed|import-demo|translate)", cmd)
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

func runImportDemo(ctx context.Context, cfg config.Config, args []string) error {
	fs := flag.NewFlagSet("import-demo", flag.ExitOnError)
	campaign := fs.String("campaign", "", "append to this campaign (default: create a new one)")
	world := fs.String("world", "w_skyisles", "world of the new campaign")
	player := fs.String("player", "player", "player_id (X-User-ID) of the new campaign")
	character := fs.String("character", "", "player character (default: first playable)")
	title := fs.String("title", "", "title of the new campaign (default: world title)")
	variant := fs.Int("variant", 0, "image variant: pNN_s<variant>.png")
	fs.Usage = func() {
		fmt.Fprintln(fs.Output(), "usage: webtoon import-demo [flags] <storyboard.json> <panel_dir>")
		fs.PrintDefaults()
	}
	fs.Parse(args) //nolint:errcheck
	if fs.NArg() != 2 {
		fs.Usage()
		return errors.New("import-demo needs <storyboard.json> <panel_dir>")
	}
	sb, err := os.ReadFile(fs.Arg(0))
	if err != nil {
		return err
	}
	s, err := openStore(ctx, cfg)
	if err != nil {
		return err
	}
	defer s.Pool.Close()
	res, err := demo.Import(ctx, s, demo.Options{
		Storyboard: sb, PanelDir: fs.Arg(1), Variant: *variant, MediaDir: cfg.MediaDir,
		CampaignID: *campaign, WorldID: *world, PlayerID: *player, PlayerCharacterID: *character, Title: *title,
	})
	if err != nil {
		return err
	}
	slog.Info("imported demo episode", "campaign", res.CampaignID, "episode", res.EpisodeID, "index", res.Index,
		"panels", res.Panels, "media_dir", cfg.MediaDir)
	return nil
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

	vocab, err := tags.LoadVocab(data.WD14Tags)
	if err != nil {
		return err
	}
	llmClient := llm.New(cfg.LLMURL, cfg.LLMModel)
	llmClient.AccessID, llmClient.AccessSecret = cfg.CFAccessID, cfg.CFAccessSecret
	var wk *worker.Worker
	if runWorker {
		gen := &storyboard.Generator{LLM: llmClient, Vocab: vocab, Attempts: 3}
		var renderer worker.Renderer = comfy.New(cfg.ComfyURL)
		var tagger worker.Tagger = wd14.New(cfg.WD14URL)
		if cfg.ImageAPI != "" {
			iq := imageq.New(cfg.ImageAPI, cfg.CFAccessID, cfg.CFAccessSecret)
			renderer, tagger = iq, iq
		}
		wk = worker.New(worker.Config{MediaDir: cfg.MediaDir, Backoff: cfg.Backoff, MaxAttempts: cfg.MaxAttempts, Langs: cfg.Langs},
			s, gen, renderer, tagger)
	}

	var wg sync.WaitGroup
	if wk != nil {
		wg.Add(1)
		go func() { defer wg.Done(); wk.Run(ctx, cfg.Workers) }()
	}

	slog.Info("webtoon ready", "mode", cfg.Mode, "addr", cfg.ListenAddr, "workers", cfg.Workers,
		"llm", cfg.LLMURL, "model", cfg.LLMModel, "comfy", cfg.ComfyURL, "wd14", cfg.WD14URL, "image_api", cfg.ImageAPI,
		"media_dir", cfg.MediaDir, "backoff", cfg.Backoff, "langs", cfg.Langs)

	if runAPI {
		var waker api.Waker
		if wk != nil {
			waker = wk
		}
		srv := &http.Server{Addr: cfg.ListenAddr, ReadHeaderTimeout: 10 * time.Second,
			Handler: api.New(api.Config{MediaDir: cfg.MediaDir, MediaBaseURL: cfg.MediaBaseURL, MaxAttempts: cfg.MaxAttempts,
				LLM: llmClient, Vocab: vocab, CORSOrigins: cfg.CORSOrigins, Langs: cfg.Langs}, s, waker).Handler()}
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

// runTranslate backfills translations of ready episodes. By default it enqueues one job per episode
// for the worker pool (which waits for the LLM window); -inline calls the LLM from this process.
// Languages an episode already has are skipped unless -force.
func runTranslate(ctx context.Context, cfg config.Config, args []string) error {
	fs := flag.NewFlagSet("translate", flag.ExitOnError)
	episode := fs.String("episode", "", "episode id")
	all := fs.Bool("all", false, "every ready episode")
	langsFlag := fs.String("langs", "", "comma-separated target languages (default WEBTOON_LANGS)")
	force := fs.Bool("force", false, "retranslate languages that are already complete")
	inline := fs.Bool("inline", false, "call the LLM now instead of enqueueing jobs")
	fs.Parse(args) //nolint:errcheck
	if (*episode == "") == !*all {
		return errors.New("translate needs -episode id or -all")
	}
	langs := cfg.Langs
	if *langsFlag != "" {
		langs = strings.Split(*langsFlag, ",")
	}
	if len(langs) == 0 {
		return errors.New("no target languages (WEBTOON_LANGS=none and no -langs)")
	}
	s, err := openStore(ctx, cfg)
	if err != nil {
		return err
	}
	defer s.Pool.Close()
	ids := []string{*episode}
	if *all {
		if ids, err = s.Q.ListReadyEpisodeIDs(ctx); err != nil {
			return err
		}
	}
	var wk *worker.Worker
	if *inline {
		lc := llm.New(cfg.LLMURL, cfg.LLMModel)
		lc.AccessID, lc.AccessSecret = cfg.CFAccessID, cfg.CFAccessSecret
		wk = worker.New(worker.Config{Langs: langs}, s, &storyboard.Generator{LLM: lc}, nil, nil)
	}
	queued, translated, skipped := 0, 0, 0
	for _, id := range ids {
		p := worker.TranslatePayload{EpisodeID: id, Langs: langs, Force: *force}
		if wk == nil {
			et, err := s.LoadEpisodeText(ctx, id)
			if err != nil {
				return err
			}
			if !*force && missingLangs(et, langs) == 0 {
				skipped++
				continue
			}
			if err := s.EnqueueTranslation(ctx, p, cfg.MaxAttempts); err != nil {
				return err
			}
			queued++
			continue
		}
		done, err := wk.TranslateEpisode(ctx, p)
		translated += len(done)
		if err != nil {
			return fmt.Errorf("episode %s: %w (translated %d languages before)", id, err, translated)
		}
		slog.Info("translated", "episode", id, "langs", done)
	}
	slog.Info("translate", "episodes", len(ids), "queued", queued, "skipped_complete", skipped, "translated_langs", translated)
	return nil
}

// missingLangs counts target languages (without the source) the episode is not complete in.
func missingLangs(et *worker.EpisodeText, langs []string) int {
	n := 0
	for _, l := range translate.Targets(langs, et.Source) {
		if !et.Complete(l) {
			n++
		}
	}
	return n
}
