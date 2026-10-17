// Package integration runs the API + worker against a real Postgres with fake Spark services.
//
//	docker compose up -d db
//	WEBTOON_TEST_DATABASE_URL=postgres://webtoon:webtoon@localhost:5434/webtoon?sslmode=disable go test ./internal/integration/
//
// Each run creates (and drops) its own database, so the dev database is untouched.
package integration

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"

	"github.com/ol1n/webtoon/backend/data"
	"github.com/ol1n/webtoon/backend/internal/api"
	"github.com/ol1n/webtoon/backend/internal/comfy"
	"github.com/ol1n/webtoon/backend/internal/db"
	"github.com/ol1n/webtoon/backend/internal/db/dbq"
	"github.com/ol1n/webtoon/backend/internal/fakes"
	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/seed"
	"github.com/ol1n/webtoon/backend/internal/store"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/testutil"
	"github.com/ol1n/webtoon/backend/internal/wd14"
	"github.com/ol1n/webtoon/backend/internal/worker"
)

const envURL = "WEBTOON_TEST_DATABASE_URL"

// freshDB creates a throwaway database next to the one in WEBTOON_TEST_DATABASE_URL.
func freshDB(t *testing.T) string {
	t.Helper()
	base := os.Getenv(envURL)
	if base == "" {
		t.Skipf("%s not set; start Postgres with `docker compose up -d db`", envURL)
	}
	ctx := context.Background()
	admin, err := pgx.Connect(ctx, base)
	if err != nil {
		t.Fatalf("connect: %v", err)
	}
	var b [4]byte
	rand.Read(b[:])
	name := "webtoon_test_" + hex.EncodeToString(b[:])
	if _, err := admin.Exec(ctx, "CREATE DATABASE "+name); err != nil {
		t.Fatalf("create db: %v", err)
	}
	t.Cleanup(func() {
		admin.Exec(context.Background(), "DROP DATABASE IF EXISTS "+name+" WITH (FORCE)")
		admin.Close(context.Background())
	})
	u, _ := url.Parse(base)
	u.Path = "/" + name
	return u.String()
}

type env struct {
	t     *testing.T
	s     *store.Store
	w     *worker.Worker
	srv   *httptest.Server
	llm   *fakes.LLM
	comfy *fakes.Comfy
	wd14  *fakes.WD14
	media string
}

func setup(t *testing.T) *env {
	dsn := freshDB(t)
	if err := db.Migrate(dsn); err != nil {
		t.Fatal(err)
	}
	if err := db.Migrate(dsn); err != nil { // idempotent
		t.Fatal(err)
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(pool.Close)
	s := store.New(pool)
	if _, err := seed.Styles(ctx, s, data.Styles); err != nil {
		t.Fatal(err)
	}
	if _, err := seed.World(ctx, s, data.WorldM0, "author", "public"); err != nil {
		t.Fatal(err)
	}
	if _, err := seed.World(ctx, s, data.WorldM0, "author", "public"); err != nil { // upsert twice
		t.Fatal(err)
	}

	g := testutil.Golden(t)
	e := &env{t: t, s: s, llm: fakes.NewLLM(string(g["ep1_raw"])), comfy: fakes.NewComfy(),
		wd14: fakes.NewWD14(map[string]float64{"short hair": 0.9, "green eyes": 0.9})}
	t.Cleanup(func() { e.llm.Close(); e.comfy.Close(); e.wd14.Close() })
	lc := llm.New(e.llm.URL+"/v1", "m")
	lc.RetryWait = time.Millisecond
	cc := comfy.New(e.comfy.URL)
	cc.PollInterval = time.Millisecond
	media := t.TempDir()
	e.media = media
	e.w = worker.New(worker.Config{ID: "it", MediaDir: media, Backoff: 5 * time.Minute, RetryBase: time.Second},
		s, &storyboard.Generator{LLM: lc, Vocab: testutil.Vocab(t)}, cc, wd14.New(e.wd14.URL))
	e.srv = httptest.NewServer(api.New(api.Config{MediaDir: media, MaxUpload: 64 << 10, LLM: lc, Vocab: testutil.Vocab(t)}, s, e.w).Handler())
	t.Cleanup(e.srv.Close)
	return e
}

func (e *env) drain() {
	e.t.Helper()
	for range 500 {
		did, err := e.w.RunOnce(context.Background(), "it/0")
		if err != nil {
			e.t.Fatal(err)
		}
		if !did {
			return
		}
	}
	e.t.Fatal("jobs did not settle")
}

func (e *env) do(method, path, user string, body any, wantCode int) map[string]any {
	e.t.Helper()
	var rd io.Reader
	if body != nil {
		b, _ := json.Marshal(body)
		rd = bytes.NewReader(b)
	}
	req, _ := http.NewRequest(method, e.srv.URL+path, rd)
	if user != "" {
		req.Header.Set("X-User-ID", user)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		e.t.Fatal(err)
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != wantCode {
		e.t.Fatalf("%s %s as %q: %d, want %d: %s", method, path, user, resp.StatusCode, wantCode, raw)
	}
	out := map[string]any{}
	_ = json.Unmarshal(raw, &out)
	return out
}

func TestFullFlow(t *testing.T) {
	e := setup(t)
	ctx := context.Background()

	// --- worlds -------------------------------------------------------------
	e.do("POST", "/worlds", "", map[string]any{"title": "x", "style_id": "clean_webtoon"}, 401)
	created := e.do("POST", "/worlds", "author2", map[string]any{
		"title": "Testovací svět", "style_id": "clean_webtoon", "audience": "kids",
		"characters": []any{map[string]any{"id": "c_a", "name": "A", "role": "playable", "count_tag": "1boy"}},
		"locations":  []any{map[string]any{"id": "l_a", "name": "Les", "tag_prompt": "forest"}},
	}, 201)
	if len(created["characters"].([]any)) != 1 || created["owner_id"] != "author2" {
		t.Fatalf("created %v", created)
	}
	e.do("POST", "/worlds", "author2", map[string]any{"title": "x", "style_id": "nope"}, 400)

	list := e.do("GET", "/worlds", "", nil, 200)["worlds"].([]any)
	if len(list) != 1 || list[0].(map[string]any)["id"] != "w_skyisles" {
		t.Fatalf("anonymous sees only public worlds: %v", list)
	}
	if n := len(e.do("GET", "/worlds", "author2", nil, 200)["worlds"].([]any)); n != 2 {
		t.Fatalf("owner sees own private world too: %d", n)
	}
	e.do("GET", "/worlds/"+created["id"].(string), "player", nil, 404)

	world := e.do("GET", "/worlds/w_skyisles", "player", nil, 200)
	if len(world["characters"].([]any)) != 1 || len(world["locations"].([]any)) != 4 {
		t.Fatalf("world %v", world)
	}
	e.do("PATCH", "/worlds/w_skyisles", "player", map[string]any{"tone": "x"}, 403)
	patched := e.do("PATCH", "/worlds/w_skyisles", "author", map[string]any{"tone": "temný"}, 200)
	if patched["tone"] != "temný" || patched["title"] != "Nebeské ostrovy" {
		t.Fatalf("patch %v", patched)
	}
	e.do("PATCH", "/worlds/w_skyisles", "author", map[string]any{"audience": "babies"}, 400)
	e.do("POST", "/worlds/w_skyisles/characters", "player", map[string]any{"name": "Hráčka"}, 403)
	e.do("POST", "/worlds/w_skyisles/characters", "author", map[string]any{"id": "c_otto", "name": "Otto", "role": "npc", "count_tag": "1boy"}, 201)
	e.do("POST", "/worlds/w_skyisles/characters", "author", map[string]any{"id": "c_otto", "name": "Otto"}, 409)
	e.do("POST", "/worlds/w_skyisles/locations", "player", map[string]any{"name": "Sklep"}, 403)
	e.do("POST", "/worlds/w_skyisles/locations", "author", map[string]any{"id": "l_cellar", "name": "Sklep"}, 201)

	// --- campaign + first episode ----------------------------------------------
	e.do("POST", "/campaigns", "player", map[string]any{"world_id": "w_skyisles", "player_character_id": "c_otto"}, 403)
	camp := e.do("POST", "/campaigns", "player", map[string]any{"world_id": "w_skyisles"}, 201)
	c := camp["campaign"].(map[string]any)
	cid, ep1 := c["id"].(string), camp["first_episode_id"].(string)
	if c["player_character_id"] != "c_vesna" {
		t.Fatalf("default player character %v", c["player_character_id"])
	}
	e.do("GET", "/campaigns/"+cid, "stranger", nil, 404)
	e.do("POST", "/campaigns/"+cid+"/episodes", "player", map[string]any{"choice_id": "c1"}, 409) // still generating

	got := e.do("GET", "/episodes/"+ep1, "player", nil, 200)
	if got["status"] != "queued" {
		t.Fatalf("episode %v", got)
	}
	e.drain()
	got = e.do("GET", "/episodes/"+ep1, "player", nil, 200)
	if got["status"] != "ready" || got["panels_ready"].(float64) != 6 || got["credits_cost"].(float64) != 6 {
		t.Fatalf("episode %v", got)
	}
	panels := got["panels"].([]any)
	img := panels[0].(map[string]any)["image_url"].(string)
	if !strings.HasPrefix(img, "/media/episodes/"+ep1+"/p00_") {
		t.Fatalf("image url %s", img)
	}
	resp, err := http.Get(e.srv.URL + img)
	if err != nil || resp.StatusCode != 200 || resp.Header.Get("Content-Type") != "image/png" {
		t.Fatalf("media: %v %v", err, resp)
	}
	resp.Body.Close()
	for _, bad := range []string{"/media/episodes", "/media/../go.mod", "/media/episodes/" + ep1 + "/nope.png"} {
		r, _ := http.Get(e.srv.URL + bad)
		if r.StatusCode != 404 {
			t.Fatalf("%s → %d", bad, r.StatusCode)
		}
		r.Body.Close()
	}

	campState := e.do("GET", "/campaigns/"+cid, "player", nil, 200)
	st := campState["state"].(map[string]any)
	if st["current_location"] != "l_cliff" || len(campState["canon_progress"].([]any)) != 1 {
		t.Fatalf("campaign state %v", campState)
	}
	// The world owner can read the campaign but not play it.
	e.do("GET", "/campaigns/"+cid, "author", nil, 200)
	e.do("POST", "/campaigns/"+cid+"/episodes", "author", map[string]any{"choice_id": "c1"}, 403)

	// --- second episode from a closed choice -------------------------------------
	e.do("POST", "/campaigns/"+cid+"/episodes", "player", map[string]any{"choice_id": "c9"}, 400)
	e.do("POST", "/campaigns/"+cid+"/episodes", "player", map[string]any{}, 400)
	e.do("POST", "/campaigns/"+cid+"/episodes", "player", map[string]any{"choice_id": "free"}, 400)
	ep2 := e.do("POST", "/campaigns/"+cid+"/episodes", "player", map[string]any{"choice_id": "c2"}, 202)["episode_id"].(string)
	e.do("POST", "/campaigns/"+cid+"/episodes", "player", map[string]any{"choice_id": "c1"}, 409)
	e.drain()
	got = e.do("GET", "/episodes/"+ep2, "player", nil, 200)
	if got["status"] != "ready" || got["chosen"].(map[string]any)["choice_id"] != "c2" {
		t.Fatalf("ep2 %v", got)
	}
	e2, _ := e.s.Q.GetEpisode(ctx, ep2)
	if !strings.HasPrefix(e2.Premise, `Previous episode: "Dopis bez adresy". It ended with: [`) {
		t.Fatalf("premise %q", e2.Premise)
	}
	if !strings.Contains(e2.Premise, "The player chose: \"") {
		t.Fatalf("premise %q", e2.Premise)
	}

	// --- panel edits -------------------------------------------------------------------
	e.do("PATCH", "/episodes/"+ep2+"/panels/1", "player", map[string]any{
		"bubbles": []any{map[string]any{"speaker_id": "c_vesna", "text": "Nový text", "kind": "speech"}}}, 200)
	e.do("PATCH", "/episodes/"+ep2+"/panels/1", "player", map[string]any{
		"bubbles": []any{map[string]any{"speaker_id": "c_nobody", "text": "x", "kind": "speech"}}}, 400)
	e.do("PATCH", "/episodes/"+ep2+"/panels/1", "stranger", map[string]any{"regenerate": true}, 404)
	e.do("PATCH", "/episodes/"+ep2+"/panels/99", "player", map[string]any{"regenerate": true}, 404)
	before, _ := e.s.Q.GetPanel(ctx, mustPanelKey(ep2, 1))
	p := e.do("PATCH", "/episodes/"+ep2+"/panels/1", "player", map[string]any{"regenerate": true}, 202)
	if p["status"] != "pending" {
		t.Fatalf("panel %v", p)
	}
	e.do("PATCH", "/episodes/"+ep2+"/panels/1", "player", map[string]any{"regenerate": true}, 409)
	if got := e.do("GET", "/episodes/"+ep2, "player", nil, 200); got["panels_ready"].(float64) != 5 || got["status"] != "ready" {
		t.Fatalf("during regenerate %v", got)
	}
	e.drain()
	after, _ := e.s.Q.GetPanel(ctx, mustPanelKey(ep2, 1))
	if after.Status != "ready" || after.Seed == before.Seed || after.ImagePath == before.ImagePath {
		t.Fatalf("regenerate: %+v → %+v", before.Seed, after.Seed)
	}
	var bubbles []map[string]any
	json.Unmarshal(after.Bubbles, &bubbles)
	if bubbles[0]["text"] != "Nový text" {
		t.Fatalf("bubbles %v", bubbles)
	}

	// --- free text, blocked by moderation -----------------------------------------------
	ep3 := e.do("POST", "/campaigns/"+cid+"/episodes", "player", map[string]any{"free_text": "něco ZAKÁZÁNO"}, 202)["episode_id"].(string)
	e.drain()
	got = e.do("GET", "/episodes/"+ep3, "player", nil, 200)
	if got["status"] != "failed" || !strings.Contains(got["error"].(string), "moderation") {
		t.Fatalf("ep3 %v", got)
	}
	// ...the player can try again; the new episode continues from the last ready one (ep2).
	ep4 := e.do("POST", "/campaigns/"+cid+"/episodes", "player", map[string]any{"free_text": "Vesna schová dopis"}, 202)
	if ep4["index"].(float64) != 4 {
		t.Fatalf("ep4 %v", ep4)
	}

	// --- ComfyUI off-schedule: panel jobs back off, the episode keeps generating -----------
	e.comfy.Down.Store(true)
	e.drain()
	got = e.do("GET", "/episodes/"+ep4["episode_id"].(string), "player", nil, 200)
	if got["status"] != "generating" || got["panels_ready"].(float64) != 0 {
		t.Fatalf("ep4 during outage %v", got)
	}
	jobs, _ := e.s.Q.ListJobs(ctx)
	deferred := 0
	for _, j := range jobs {
		if j.Status == "queued" {
			deferred++
			if j.Attempts != 0 || time.Until(j.RunAfter) < 4*time.Minute || !strings.Contains(j.LastError, "comfyui unavailable") {
				t.Fatalf("deferred job %+v", j)
			}
		}
		if j.Status == "failed" && j.Kind == worker.KindPanel {
			t.Fatalf("panel job failed during outage: %+v", j)
		}
	}
	if deferred != 6 {
		t.Fatalf("deferred %d", deferred)
	}
	e.comfy.Down.Store(false)
	if _, err := e.s.Pool.Exec(ctx, "UPDATE jobs SET run_after = now() WHERE status = 'queued'"); err != nil {
		t.Fatal(err)
	}
	e.drain()
	got = e.do("GET", "/episodes/"+ep4["episode_id"].(string), "player", nil, 200)
	if got["status"] != "ready" {
		t.Fatalf("ep4 after outage %v", got)
	}
	cs := e.do("GET", "/campaigns/"+cid, "player", nil, 200)
	if n := len(cs["state"].(map[string]any)["timeline"].([]any)); n != 3 {
		t.Fatalf("timeline entries %d (ep1, ep2, ep4)", n)
	}
	if n := len(cs["episodes"].([]any)); n != 4 {
		t.Fatalf("episodes %d", n)
	}

	// --- stats ----------------------------------------------------------------------------
	e.do("GET", "/worlds/w_skyisles/stats", "player", nil, 403)
	stats := e.do("GET", "/worlds/w_skyisles/stats", "author", nil, 200)
	ch := stats["choices"].(map[string]any)
	if stats["campaigns"].(float64) != 1 || stats["episodes"].(float64) != 4 || stats["episodes_failed"].(float64) != 1 ||
		ch["by_kind"].(map[string]any)["closed"].(float64) != 1 || ch["by_kind"].(map[string]any)["free"].(float64) != 2 ||
		ch["by_choice"].(map[string]any)["c2"].(float64) != 1 {
		t.Fatalf("stats %v", stats)
	}
	if stats["canon_reached"].(map[string]any)["c1"].(float64) != 1 {
		t.Fatalf("canon stats %v", stats)
	}
	// where players stopped + choices per episode (the choice leading to episode i+1 is made at the end of i)
	if st := stats["stopped_at"].([]any); len(st) != 1 || st[0].(map[string]any)["episode"].(float64) != 4 {
		t.Fatalf("stopped_at %v", st)
	}
	perEp := stats["choices_by_episode"].([]any)
	if len(perEp) != 3 {
		t.Fatalf("choices_by_episode %v", perEp)
	}
	first := perEp[0].(map[string]any)
	if first["episode"].(float64) != 1 || first["total"].(float64) != 1 || first["choices"].(map[string]any)["c2"].(float64) != 1 {
		t.Fatalf("choices_by_episode[0] %v", first)
	}
	if perEp[1].(map[string]any)["choices"].(map[string]any)["free"].(float64) != 1 {
		t.Fatalf("choices_by_episode[1] %v", perEp[1])
	}
	if pc := stats["player_created"].([]any); len(pc) != 0 {
		t.Fatalf("player_created %v", pc)
	}
}

func mustPanelKey(ep string, i int32) dbq.GetPanelParams {
	return dbq.GetPanelParams{EpisodeID: ep, Idx: i}
}

// TestClaimSkipLocked checks that concurrent workers never claim the same job.
func TestClaimSkipLocked(t *testing.T) {
	dsn := freshDB(t)
	if err := db.Migrate(dsn); err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		t.Fatal(err)
	}
	defer pool.Close()
	s := store.New(pool)
	for i := range 40 {
		if _, err := s.Enqueue(ctx, nil, "noop", map[string]int{"i": i}, 3); err != nil {
			t.Fatal(err)
		}
	}
	var mu sync.Mutex
	seen := map[int64]string{}
	var wg sync.WaitGroup
	for w := range 8 {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for {
				j, err := s.ClaimJob(ctx, fmt.Sprintf("w%d", w))
				if err != nil {
					t.Error(err)
					return
				}
				if j == nil {
					return
				}
				mu.Lock()
				if prev, dup := seen[j.ID]; dup {
					t.Errorf("job %d claimed by %s and w%d", j.ID, prev, w)
				}
				seen[j.ID] = fmt.Sprintf("w%d", w)
				mu.Unlock()
				s.CompleteJob(ctx, j.ID)
			}
		}()
	}
	wg.Wait()
	if len(seen) != 40 {
		t.Fatalf("claimed %d of 40", len(seen))
	}
	// Deferral does not burn attempts; stale running jobs are requeued.
	id, _ := s.Enqueue(ctx, nil, "noop", map[string]int{}, 3)
	j, _ := s.ClaimJob(ctx, "w")
	if j == nil || j.ID != id || j.Attempts != 1 {
		t.Fatalf("%+v", j)
	}
	s.DeferJob(ctx, id, time.Now().Add(-time.Minute), "down")
	j, _ = s.ClaimJob(ctx, "w")
	if j == nil || j.Attempts != 1 {
		t.Fatalf("after defer %+v", j)
	}
	if n, _ := s.RequeueStaleJobs(ctx, time.Now().Add(time.Minute)); n != 1 {
		t.Fatalf("requeued %d", n)
	}
}
