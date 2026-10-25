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
//	webtoon export-pack (-type kids -n 1 | -pack id -title t) [-version 1] [-release-tag t]
//	                    (-out dir [-product id | -free] | -starter file.zip)
//	                    (-campaigns a,b | -worlds w,x | -world-prefix w_r_,w_ra_ | -starter-pick data/starter_showcase.yaml)
//	                                    build an offline content pack (PACK_FORMAT.md) from the DB + MEDIA_DIR;
//	                                    catalog mode writes releases/<tag>/<asset> + catalog.json and prints the
//	                                    `gh release create` command (never runs it)
//	webtoon catalog-bundles -out dir    rewrite catalog.json base_urls/types/bundles from rules/base/pack.yaml (no DB)
package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
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
	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/demo"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/imageq"
	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/pack"
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
	case "export-pack":
		err = runExportPack(ctx, cfg, args)
	case "catalog-bundles":
		err = runCatalogBundles(args)
	case "set-faces":
		err = runSetFaces(ctx, cfg, args)
	default:
		err = fmt.Errorf("unknown command %q (serve|migrate|seed|import-demo|translate|export-pack|catalog-bundles|set-faces)", cmd)
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

// runSetFaces copies panels[].faces of a storyboard (m0/faces.py --storyboard) onto an episode that was imported
// before its faces were measured. Panels without faces in the storyboard are left as they are.
func runSetFaces(ctx context.Context, cfg config.Config, args []string) error {
	fs := flag.NewFlagSet("set-faces", flag.ExitOnError)
	episode := fs.String("episode", "", "episode id")
	fs.Usage = func() {
		fmt.Fprintln(fs.Output(), "usage: webtoon set-faces -episode <id> <storyboard.json>")
		fs.PrintDefaults()
	}
	fs.Parse(args) //nolint:errcheck
	if *episode == "" || fs.NArg() != 1 {
		fs.Usage()
		os.Exit(2)
	}
	raw, err := os.ReadFile(fs.Arg(0))
	if err != nil {
		return err
	}
	var sb domain.Storyboard
	if err := json.Unmarshal(raw, &sb); err != nil {
		return fmt.Errorf("%s: %w", fs.Arg(0), err)
	}
	s, err := openStore(ctx, cfg)
	if err != nil {
		return err
	}
	defer s.Pool.Close()
	q := dbq.New(s.Pool)
	panels, err := q.ListPanels(ctx, *episode)
	if err != nil {
		return err
	}
	if len(panels) != len(sb.Panels) {
		return fmt.Errorf("episode %s has %d panels, the storyboard %d", *episode, len(panels), len(sb.Panels))
	}
	n := 0
	for i, p := range sb.Panels {
		if p.Faces == nil {
			continue
		}
		if err := q.SetPanelFaces(ctx, dbq.SetPanelFacesParams{EpisodeID: *episode, Idx: int32(i), Faces: store.MustJSON(p.Faces)}); err != nil {
			return err
		}
		n++
	}
	fmt.Printf("%s: faces of %d/%d panels\n", *episode, n, len(panels))
	return nil
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
	sbFlag := fs.String("storyboard", "", "comma-separated storyboard.json paths (or positional args): translate the files in place, no database")
	fs.Parse(args) //nolint:errcheck
	langs := cfg.Langs
	if *langsFlag != "" {
		langs = strings.Split(*langsFlag, ",")
	}
	if len(langs) == 0 {
		return errors.New("no target languages (WEBTOON_LANGS=none and no -langs)")
	}
	if files := append(splitList(*sbFlag), fs.Args()...); *sbFlag != "" || len(files) > 0 {
		if *episode != "" || *all {
			return errors.New("translate takes -storyboard files or -episode/-all, not both")
		}
		if len(files) == 0 {
			return errors.New("translate -storyboard needs at least one file")
		}
		return runTranslateStoryboards(ctx, cfg, files, langs, *force)
	}
	if (*episode == "") == !*all {
		return errors.New("translate needs -episode id or -all (or -storyboard files)")
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

// runTranslateStoryboards translates storyboard.json files in place before they are rendered
// (world.json next to each gives the source language and speaker names). Files run one after
// another; a failed file is reported and the rest still run. Each language is saved as soon as it
// is done, so a rerun continues where an interrupted one stopped.
func runTranslateStoryboards(ctx context.Context, cfg config.Config, files, langs []string, force bool) error {
	lc := llm.New(cfg.LLMURL, cfg.LLMModel)
	lc.AccessID, lc.AccessSecret = cfg.CFAccessID, cfg.CFAccessSecret
	var failed []string
	for i, path := range files {
		if ctx.Err() != nil {
			failed = append(failed, files[i:]...)
			break
		}
		start := time.Now()
		done, skipped, err := translateStoryboardFile(ctx, lc, path, langs, force)
		if err != nil {
			fmt.Printf("[%d/%d] FAIL %s: %v (translated %v before)\n", i+1, len(files), path, err, done)
			failed = append(failed, path)
			continue
		}
		if skipped {
			fmt.Printf("[%d/%d] skip %s: already complete\n", i+1, len(files), path)
			continue
		}
		fmt.Printf("[%d/%d] ok %s: %v in %s\n", i+1, len(files), path, done, time.Since(start).Round(time.Second))
	}
	fmt.Printf("translate -storyboard: %d files, %d failed\n", len(files), len(failed))
	if len(failed) > 0 {
		return fmt.Errorf("%d of %d storyboards failed: %v", len(failed), len(files), failed)
	}
	return nil
}

func translateStoryboardFile(ctx context.Context, c llm.JSONCaller, path string, langs []string, force bool) ([]string, bool, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, false, err
	}
	var world struct {
		Language   string `json:"language"`
		Characters []struct {
			ID   string `json:"id"`
			Name string `json:"name"`
		} `json:"characters"`
	}
	wpath := filepath.Join(filepath.Dir(path), "world.json")
	if wraw, err := os.ReadFile(wpath); err == nil {
		if err := json.Unmarshal(wraw, &world); err != nil {
			return nil, false, fmt.Errorf("%s: %w", wpath, err)
		}
	} else if !errors.Is(err, os.ErrNotExist) {
		return nil, false, err
	}
	names := map[string]string{}
	for _, ch := range world.Characters {
		names[ch.ID] = ch.Name
	}
	f, err := translate.ParseStoryboardFile(raw, world.Language, names)
	if err != nil {
		return nil, false, err
	}
	if !force && len(f.Missing(langs)) == 0 {
		return nil, true, nil
	}
	save := func(lang string) error {
		out, err := f.Marshal()
		if err != nil {
			return err
		}
		tmp := path + ".tmp"
		if err := os.WriteFile(tmp, out, 0o644); err != nil {
			return err
		}
		return os.Rename(tmp, path)
	}
	done, err := translate.TranslateStoryboard(ctx, c, f, langs, force, save)
	return done, false, err
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

// runExportPack builds a content pack (PACK_FORMAT.md). It only reads the database, so it opens
// the pool without running migrations.
func runExportPack(ctx context.Context, cfg config.Config, args []string) error {
	fs := flag.NewFlagSet("export-pack", flag.ExitOnError)
	var o pack.Options
	fs.StringVar(&o.ID, "pack", "", "pack id, [a-z0-9-] (default with -type/-n: rules naming, e.g. kids-1)")
	fs.StringVar(&o.Title, "title", "", "pack title (default with -type/-n: the type's title + n)")
	fs.IntVar(&o.Version, "version", 0, "pack version; part of the release tag (default 1, or the pick file's)")
	fs.StringVar(&o.ProductID, "product", "", "store product id of a paid pack (default with -n: pack_<type>_<n>)")
	fs.BoolVar(&o.Free, "free", false, "free pack (no product)")
	fs.StringVar(&o.Type, "type", "", "pack type, rules/base/pack.yaml types (default: the worlds' profile / audience)")
	fs.IntVar(&o.N, "n", 0, "pack number within its type; derives id, product and release tag")
	fs.StringVar(&o.ReleaseTag, "release-tag", "", "GitHub release of the zips (default: rules naming, pack-<type>-<n>-v<version>)")
	fs.StringVar(&o.OutDir, "out", "", "webtoon-content checkout: writes releases/<tag>/, covers/ and merges catalog.json")
	fs.StringVar(&o.Starter, "starter", "", "write this single zip (e.g. ../app/assets/packs/starter.zip) and touch no catalog")
	fs.StringVar(&o.BaseURL, "base-url", "", "catalog base_urls.pages (default: rules/base/pack.yaml)")
	pickFile := fs.String("starter-pick", "", "starter selection: yaml of world picks (data/starter_showcase.yaml)")
	graphFile := fs.String("gamebook", "", "gamebook graph (data/gamebooks/<id>/graph.yaml): its nodes' worlds, one zip, catalog gamebooks[]")
	fs.IntVar(&o.Workers, "workers", 0, "parallel cwebp processes (default: CPUs)")
	fs.BoolVar(&o.Force, "force", false, "overwrite an existing zip")
	campaigns := fs.String("campaigns", "", "comma-separated campaign ids")
	worlds := fs.String("worlds", "", "comma-separated world ids (all their campaigns)")
	prefixes := fs.String("world-prefix", "", "comma-separated world id prefixes (all campaigns of matching worlds)")
	fs.Parse(args) //nolint:errcheck
	if fs.NArg() != 0 {
		return fmt.Errorf("export-pack takes flags only, got %v", fs.Args())
	}
	o.MediaDir = cfg.MediaDir
	sel := pack.Selection{Campaigns: splitList(*campaigns), Worlds: splitList(*worlds), WorldPrefixes: splitList(*prefixes)}
	if *pickFile != "" {
		r, err := pack.LoadRules()
		if err != nil {
			return err
		}
		pf, err := pack.ReadPicks(*pickFile, r)
		if err != nil {
			return err
		}
		sel.Picks = pf.Picks
		if o.ID == "" {
			o.ID = pf.Pack.ID
		}
		if o.Title == "" {
			o.Title = pf.Pack.Title
		}
		if o.Version == 0 {
			o.Version = pf.Pack.Version
		}
	}
	if *graphFile != "" {
		g, err := pack.ReadGraph(*graphFile)
		if err != nil {
			return err
		}
		o.Gamebook = g
		if len(sel.Campaigns) == 0 && len(sel.Worlds) == 0 && len(sel.WorldPrefixes) == 0 {
			sel = g.Selection()
		}
	}
	if o.Version == 0 {
		o.Version = 1
	}
	if err := sel.Validate(); err != nil {
		return err
	}
	pool, err := pgxpool.New(ctx, cfg.DatabaseURL)
	if err != nil {
		return err
	}
	defer pool.Close()
	if err := pool.Ping(ctx); err != nil {
		return err
	}
	sum, err := pack.Run(ctx, dbq.New(pool), o, sel)
	if err != nil {
		return err
	}
	for _, n := range sum.Notes {
		fmt.Fprintln(os.Stderr, "note:", n)
	}
	for _, p := range sum.Parts {
		part := p.Part
		if part == "" {
			part = "-"
		}
		fmt.Printf("part %s  %s\n  stories %d  episodes %d  panels %d  loops %d  bytes %d  sha256 %s\n",
			part, p.Path, p.Stories, p.Episodes, p.Panels, p.Loops, p.Bytes, p.SHA256)
	}
	if sum.CatalogPath != "" {
		fmt.Printf("catalog %s  version %d\n", sum.CatalogPath, sum.CatalogVersion)
		fmt.Printf("upload the zips (then commit catalog.json + covers/ of the Pages repo):\n  %s\n", sum.GhCommand)
	}
	return nil
}

// runCatalogBundles rewrites base_urls, types and bundles of catalog.json from rules/base/pack.yaml (a new bundle
// or type needs no export). No database.
func runCatalogBundles(args []string) error {
	fs := flag.NewFlagSet("catalog-bundles", flag.ExitOnError)
	out := fs.String("out", "", "webtoon-content checkout holding catalog.json (required)")
	baseURL := fs.String("base-url", "", "catalog base_urls.pages (default: rules/base/pack.yaml)")
	fs.Parse(args) //nolint:errcheck
	if *out == "" || fs.NArg() != 0 {
		return errors.New("usage: webtoon catalog-bundles -out <webtoon-content dir> [-base-url url]")
	}
	c, err := pack.RefreshCatalog(filepath.Join(*out, "catalog.json"), *baseURL, time.Now())
	if err != nil {
		return err
	}
	fmt.Printf("catalog %s  version %d  types %d  bundles %d\n", filepath.Join(*out, "catalog.json"), c.Version, len(c.Types), len(c.Bundles))
	return nil
}

func splitList(s string) []string {
	var out []string
	for _, v := range strings.Split(s, ",") {
		if v = strings.TrimSpace(v); v != "" {
			out = append(out, v)
		}
	}
	return out
}
