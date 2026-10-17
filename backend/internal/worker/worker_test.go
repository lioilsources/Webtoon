package worker_test

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/ol1n/webtoon/backend/internal/comfy"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/fakes"
	"github.com/ol1n/webtoon/backend/internal/llm"
	"github.com/ol1n/webtoon/backend/internal/storyboard"
	"github.com/ol1n/webtoon/backend/internal/testutil"
	"github.com/ol1n/webtoon/backend/internal/wd14"
	"github.com/ol1n/webtoon/backend/internal/worker"
)

type harness struct {
	t     *testing.T
	store *memStore
	w     *worker.Worker
	llm   *fakes.LLM
	comfy *fakes.Comfy
	wd14  *fakes.WD14
	media string
}

func newHarness(t *testing.T) *harness {
	t.Helper()
	g := testutil.Golden(t)
	h := &harness{t: t, media: t.TempDir()}
	h.llm = fakes.NewLLM(string(g["ep1_raw"]))
	h.comfy = fakes.NewComfy()
	h.wd14 = fakes.NewWD14(map[string]float64{"short hair": 0.9, "green eyes": 0.8, "freckles": 0.5, "smile": 0.7})
	t.Cleanup(func() { h.llm.Close(); h.comfy.Close(); h.wd14.Close() })

	h.store = newMemStore(testutil.World(t), testutil.Styles(t))
	lc := llm.New(h.llm.URL+"/v1", "test-model")
	lc.RetryWait = time.Millisecond
	cc := comfy.New(h.comfy.URL)
	cc.PollInterval = time.Millisecond
	gen := &storyboard.Generator{LLM: lc, Vocab: testutil.Vocab(t), Attempts: 3}
	clock := func() time.Time { h.store.mu.Lock(); defer h.store.mu.Unlock(); return h.store.now }
	h.w = worker.New(worker.Config{ID: "test", MediaDir: h.media, Backoff: 5 * time.Minute, RetryBase: time.Second, Clock: clock},
		h.store, gen, cc, wd14.New(h.wd14.URL))
	return h
}

// drain runs due jobs until none is left; returns how many ran.
func (h *harness) drain() int {
	h.t.Helper()
	n := 0
	for ; n < 200; n++ {
		did, err := h.w.RunOnce(context.Background(), "test/0")
		if err != nil {
			h.t.Fatal(err)
		}
		if !did {
			return n
		}
	}
	h.t.Fatal("job loop did not settle")
	return n
}

func (h *harness) step() {
	h.t.Helper()
	if did, err := h.w.RunOnce(context.Background(), "test/0"); err != nil || !did {
		h.t.Fatalf("expected a job: did=%v err=%v", did, err)
	}
}

func TestEpisodeEndToEnd(t *testing.T) {
	h := newHarness(t)
	w := testutil.World(t)
	h.store.addCampaignWithEpisode("cp1", "ep1", storyboard.FirstPremise(w), nil)

	// 1) episode job: storyboard → validator → 6 panel jobs.
	h.step()
	ep := h.store.episode("ep1")
	if ep.Status != "generating" || ep.PanelsTotal != 6 || len(h.store.jobs) != 7 {
		t.Fatalf("after storyboard: status=%s total=%d jobs=%d err=%s", ep.Status, ep.PanelsTotal, len(h.store.jobs), ep.Error)
	}
	if h.llm.Calls(fakes.KindStoryboard) != 1 || h.llm.Calls(fakes.KindTranslate) != 1 || h.llm.Calls(fakes.KindRuleCheck) != 1 {
		t.Fatalf("llm calls sb=%d tr=%d rc=%d", h.llm.Calls(fakes.KindStoryboard), h.llm.Calls(fakes.KindTranslate), h.llm.Calls(fakes.KindRuleCheck))
	}
	if h.llm.Calls(fakes.KindModeration) != 0 {
		t.Fatal("no free text → no moderation call")
	}
	ids := []string{}
	for _, c := range ep.Choices {
		ids = append(ids, c.ID)
	}
	if strings.Join(ids, ",") != "c1,c2,c3,free" {
		t.Fatalf("choice ids %v", ids)
	}

	// 2) panels appear progressively.
	h.step()
	if ep := h.store.episode("ep1"); ep.PanelsReady != 1 || ep.Status != "generating" {
		t.Fatalf("after first panel: ready=%d status=%s", ep.PanelsReady, ep.Status)
	}
	h.drain()

	ep = h.store.episode("ep1")
	if ep.Status != "ready" || ep.PanelsReady != 6 || ep.Error != "" {
		t.Fatalf("final: status=%s ready=%d err=%s", ep.Status, ep.PanelsReady, ep.Error)
	}
	for i := range 6 {
		p := h.store.panel("ep1", i)
		if p.Status != "ready" || p.Result == nil {
			t.Fatalf("panel %d: %s %s", i, p.Status, p.Error)
		}
		b, err := os.ReadFile(filepath.Join(h.media, filepath.FromSlash(p.Result.ImagePath)))
		if err != nil || len(b) == 0 {
			t.Fatalf("panel %d image: %v", i, err)
		}
		if !strings.HasPrefix(p.Result.Prompt, "masterpiece, best quality") || !strings.Contains(p.Result.Negative, "speech bubble") {
			t.Fatalf("panel %d prompt: %s | %s", i, p.Result.Prompt, p.Result.Negative)
		}
		if len(p.SB.Characters) > 0 && (p.Result.IdentityScore == nil || *p.Result.IdentityScore <= 0) {
			t.Fatalf("panel %d identity missing", i)
		}
	}
	// The ComfyUI graph carries the built prompt, preset and seed.
	gr := h.comfy.Graphs()
	if len(gr) != 6 {
		t.Fatalf("graphs %d", len(gr))
	}
	pos := gr[0]["pos"].(map[string]any)["inputs"].(map[string]any)["text"].(string)
	if pos != h.store.panel("ep1", 0).Result.Prompt {
		t.Fatal("graph prompt differs from stored prompt")
	}
	if ck := gr[0]["ckpt"].(map[string]any)["inputs"].(map[string]any)["ckpt_name"]; ck != "noobai-xl-eps11.safetensors" {
		t.Fatalf("checkpoint %v", ck)
	}

	// 3) state_diff merged into the campaign + snapshot.
	c := h.store.campaigns["cp1"]
	if c.State.CurrentLocation != "l_cliff" || len(c.State.Timeline) != 1 || c.State.Timeline[0].Episode != 1 {
		t.Fatalf("state %+v", c.State)
	}
	if strings.Join(c.CanonProgress, ",") != "c1" {
		t.Fatalf("canon %v", c.CanonProgress)
	}
	if ep.Snapshot == nil || ep.Snapshot.CurrentLocation != "l_cliff" {
		t.Fatal("snapshot missing")
	}
	for _, j := range h.store.jobs {
		if j.Status != "done" {
			t.Fatalf("job %d %s: %s", j.ID, j.Status, j.LastErr)
		}
	}

	// 4) regenerate one panel: new seed, episode stays ready, state not applied twice.
	before := h.store.panel("ep1", 2).Seed
	h.store.mu.Lock()
	h.store.panels["ep1"][2].Status = "pending"
	h.store.enqueue(worker.KindPanel, worker.PanelPayload{EpisodeID: "ep1", Panel: 2, Regenerate: true}, 3)
	h.store.mu.Unlock()
	h.drain()
	p2 := h.store.panel("ep1", 2)
	if p2.Status != "ready" || p2.Seed == before {
		t.Fatalf("regenerate: status=%s seed %d→%d", p2.Status, before, p2.Seed)
	}
	if ep := h.store.episode("ep1"); ep.Status != "ready" || len(h.store.campaigns["cp1"].State.Timeline) != 1 {
		t.Fatal("regenerate must not refinalize the episode")
	}
}

func TestComfyDownBacksOffWithoutFailing(t *testing.T) {
	h := newHarness(t)
	h.store.addCampaignWithEpisode("cp1", "ep1", "premise", nil)
	h.step() // storyboard (LLM is up)
	h.comfy.Down.Store(true)
	before := h.store.now
	h.step() // first panel job: ComfyUI unreachable

	j := h.store.job(2)
	if j.Status != "queued" || j.Attempts != 0 || !j.RunAfter.Equal(before.Add(5*time.Minute)) {
		t.Fatalf("job after outage: %+v", j)
	}
	if p := h.store.panel("ep1", 0); p.Status != "pending" || !strings.Contains(p.Error, "waiting") {
		t.Fatalf("panel %+v", p)
	}
	if ep := h.store.episode("ep1"); ep.Status != "generating" {
		t.Fatalf("episode must keep generating, got %s", ep.Status)
	}
	if len(h.comfy.Graphs()) != 0 {
		t.Fatal("nothing may be queued on a down ComfyUI")
	}
	// The other panel jobs also defer; nothing fails however often we poll.
	h.drain()
	for _, j := range h.store.jobs[1:] {
		if j.Status != "queued" || j.Attempts != 0 {
			t.Fatalf("job %d: %s attempts=%d", j.ID, j.Status, j.Attempts)
		}
	}
	// ComfyUI window opens: jobs run after the backoff.
	h.comfy.Down.Store(false)
	if n := h.drain(); n != 0 {
		t.Fatalf("jobs ran before run_after: %d", n)
	}
	h.store.advance(5*time.Minute + time.Second)
	h.drain()
	if ep := h.store.episode("ep1"); ep.Status != "ready" || ep.PanelsReady != 6 {
		t.Fatalf("after recovery: %s %d", ep.Status, ep.PanelsReady)
	}
}

func TestLLMDownBacksOff(t *testing.T) {
	h := newHarness(t)
	h.store.addCampaignWithEpisode("cp1", "ep1", "premise", nil)
	h.llm.Down.Store(true)
	h.step()
	j := h.store.job(1)
	if j.Status != "queued" || j.Attempts != 0 || !strings.Contains(j.LastErr, "llm unavailable") {
		t.Fatalf("job %+v", j)
	}
	if ep := h.store.episode("ep1"); ep.Status != "queued" || !strings.Contains(ep.Error, "waiting") {
		t.Fatalf("episode %s %q", ep.Status, ep.Error)
	}
	h.llm.Down.Store(false)
	h.store.advance(6 * time.Minute)
	h.drain()
	if ep := h.store.episode("ep1"); ep.Status != "ready" {
		t.Fatalf("status %s err %s", ep.Status, ep.Error)
	}
}

func TestUnsafeOutputReseedsThenFails(t *testing.T) {
	h := newHarness(t)
	h.store.addCampaignWithEpisode("cp1", "ep1", "premise", nil)
	h.step()

	h.wd14.Unsafe(2) // panel 0: two unsafe renders, third is fine
	h.step()
	p0 := h.store.panel("ep1", 0)
	if p0.Status != "ready" || len(p0.Result.Attempts) != 3 || len(p0.Result.Attempts[2].Unsafe) != 0 {
		t.Fatalf("panel 0: %s attempts=%+v", p0.Status, p0.Result.Attempts)
	}
	if p0.Result.Attempts[0].Seed == p0.Result.Attempts[1].Seed {
		t.Fatal("reseed must change the seed")
	}

	h.wd14.Always.Store(true) // panel 1: always unsafe → failed after 1 + MaxReseed renders
	h.step()
	p1 := h.store.panel("ep1", 1)
	if p1.Status != "failed" || len(p1.Result.Attempts) != 1+wd14.MaxReseed || p1.Result.ImagePath != "" {
		t.Fatalf("panel 1: %+v", p1.Result)
	}
	h.wd14.Always.Store(false)
	h.drain()
	ep := h.store.episode("ep1")
	if ep.Status != "ready" || ep.PanelsReady != 5 || ep.Error != "1 of 6 panels failed" {
		t.Fatalf("episode %s ready=%d err=%q", ep.Status, ep.PanelsReady, ep.Error)
	}
	if _, err := os.Stat(filepath.Join(h.media, "episodes", "ep1")); err != nil {
		t.Fatal(err)
	}
	entries, _ := os.ReadDir(filepath.Join(h.media, "episodes", "ep1"))
	if len(entries) != 5 {
		t.Fatalf("unsafe image must not be stored: %d files", len(entries))
	}
}

func TestFreeTextModeration(t *testing.T) {
	h := newHarness(t)
	h.store.addCampaignWithEpisode("cp1", "ep1", "premise", &worker.Chosen{ChoiceID: "free", Kind: "free", Text: "Vesna udělá něco ZAKÁZÁNO"})
	h.drain()
	ep := h.store.episode("ep1")
	if ep.Status != "failed" || !strings.Contains(ep.Error, "moderation") || ep.Moderation == nil || ep.Moderation.Allowed {
		t.Fatalf("episode %s %q %+v", ep.Status, ep.Error, ep.Moderation)
	}
	if h.llm.Calls(fakes.KindStoryboard) != 0 {
		t.Fatal("blocked input must not reach the storyboard step")
	}
	if j := h.store.job(1); j.Status != "failed" || j.Attempts != 1 {
		t.Fatalf("moderation block is permanent: %+v", j)
	}

	h2 := newHarness(t)
	h2.store.addCampaignWithEpisode("cp1", "ep1", "premise", &worker.Chosen{ChoiceID: "free", Kind: "free", Text: "Vesna schová dopis"})
	h2.drain()
	if ep := h2.store.episode("ep1"); ep.Status != "ready" || h2.llm.Calls(fakes.KindModeration) != 1 {
		t.Fatalf("allowed free text: %s, moderation calls %d", ep.Status, h2.llm.Calls(fakes.KindModeration))
	}
}

func TestStoryboardFailureRetriesThenFails(t *testing.T) {
	h := newHarness(t)
	h.llm.Storyboard = func(string) string { return `{"title": "x", "panels": []}` }
	h.store.addCampaignWithEpisode("cp1", "ep1", "premise", nil)
	for range 3 {
		h.drain()
		h.store.advance(time.Hour)
	}
	j := h.store.job(1)
	if j.Status != "failed" || j.Attempts != 3 {
		t.Fatalf("job %+v", j)
	}
	if ep := h.store.episode("ep1"); ep.Status != "failed" || !strings.Contains(ep.Error, "storyboard failed validation") {
		t.Fatalf("episode %s %q", ep.Status, ep.Error)
	}
	if n := h.llm.Calls(fakes.KindStoryboard); n != 9 {
		t.Fatalf("3 job attempts × 3 storyboard attempts = 9 calls, got %d", n)
	}
}

func TestIPAdapterReferenceUpload(t *testing.T) {
	h := newHarness(t)
	ref := filepath.Join(h.media, "refs", "vesna.png")
	os.MkdirAll(filepath.Dir(ref), 0o755)
	os.WriteFile(ref, fakes.TinyPNG(), 0o644)
	h.store.world.Characters[0].IdentityLevel = "ip_adapter"
	h.store.world.Characters[0].ReferenceImages = []string{"refs/vesna.png"}
	h.store.addCampaignWithEpisode("cp1", "ep1", "premise", nil)
	h.drain()
	if ep := h.store.episode("ep1"); ep.Status != "ready" {
		t.Fatalf("status %s", ep.Status)
	}
	if len(h.comfy.Uploads()) == 0 {
		t.Fatal("reference not uploaded")
	}
	withIP := 0
	for _, g := range h.comfy.Graphs() {
		if _, ok := g["ipapply"]; ok {
			withIP++
		}
	}
	chars := 0
	for i := range 6 {
		if len(h.store.panel("ep1", i).SB.Characters) > 0 {
			chars++
		}
	}
	if withIP != chars {
		t.Fatalf("IP-Adapter on %d graphs, %d panels have characters", withIP, chars)
	}
	for _, g := range h.comfy.Graphs() {
		if n, ok := g["ipapply"]; ok {
			in := n.(map[string]any)["inputs"].(map[string]any)
			load := g["ipload"].(map[string]any)["inputs"].(map[string]any)
			if in["weight"] != 0.6 || in["end_at"] != 0.8 || load["preset"] != "PLUS (high strength)" {
				t.Fatalf("default IP-Adapter settings: %v %v", in, load)
			}
		}
	}
}

func TestIPAdapterCharacterConfig(t *testing.T) {
	h := newHarness(t)
	ref := filepath.Join(h.media, "refs", "vesna_face.jpg")
	os.MkdirAll(filepath.Dir(ref), 0o755)
	os.WriteFile(ref, fakes.TinyPNG(), 0o644)
	c := &h.store.world.Characters[0]
	c.IdentityLevel = "ip_adapter"
	c.ReferenceImages = []string{"refs/vesna_face.jpg"}
	c.IPAdapter = &domain.IPAdapterConfig{Preset: "PLUS FACE (portraits)", Weight: 0.35, EndAt: 0.6}
	h.store.addCampaignWithEpisode("cp1", "ep1", "premise", nil)
	h.drain()
	ups := h.comfy.Uploads()
	if len(ups) == 0 || !strings.HasSuffix(ups[0], "_ref.jpg") {
		t.Fatalf("uploads %v", ups)
	}
	seen := 0
	for _, g := range h.comfy.Graphs() {
		if n, ok := g["ipapply"]; ok {
			seen++
			in := n.(map[string]any)["inputs"].(map[string]any)
			load := g["ipload"].(map[string]any)["inputs"].(map[string]any)
			if in["weight"] != 0.35 || in["end_at"] != 0.6 || load["preset"] != "PLUS FACE (portraits)" {
				t.Fatalf("character IP-Adapter settings ignored: %v %v", in, load)
			}
		}
	}
	if seen == 0 {
		t.Fatal("no IP-Adapter graph")
	}
	// prompt-only (the default identity level) ignores the config.
	h2 := newHarness(t)
	h2.store.world.Characters[0].IPAdapter = &domain.IPAdapterConfig{Weight: 0.4}
	h2.store.world.Characters[0].ReferenceImages = []string{"refs/x.png"}
	h2.store.addCampaignWithEpisode("cp1", "ep1", "premise", nil)
	h2.drain()
	for _, g := range h2.comfy.Graphs() {
		if _, ok := g["ipapply"]; ok {
			t.Fatal("prompt-only character rendered with IP-Adapter")
		}
	}
}

func TestAssignChoiceIDs(t *testing.T) {
	cs := testutil.StoryboardEP1(t).Choices
	worker.AssignChoiceIDs(cs)
	if cs[0].ID != "c1" || cs[1].ID != "c2" || cs[len(cs)-1].ID != "free" {
		t.Fatalf("%+v", cs)
	}
}

func TestCharacterSheet(t *testing.T) {
	h := newHarness(t)
	h.store.addSheet("sh1", "c_vesna", 4)
	h.drain()
	sh := h.store.sheet("sh1")
	if sh.Status != "ready" || len(sh.Images) != 4 || sh.Best == nil || *sh.Best != 0 {
		t.Fatalf("sheet %+v", sh)
	}
	// Prompt = prompts.build(render.sheet_panel(char)) of the prototype.
	var want struct{ Positive, Negative string }
	testutil.GoldenField(t, testutil.Golden(t), "sheet_prompt", &want)
	if sh.Prompt != want.Positive || sh.Negative != want.Negative {
		t.Fatalf("sheet prompt\n got: %s\nwant: %s", sh.Prompt, want.Positive)
	}
	seeds := map[int64]bool{}
	for _, im := range sh.Images {
		if im.Status != "ok" || im.Path == "" || im.Recall <= 0 {
			t.Fatalf("image %+v", im)
		}
		if _, err := os.Stat(filepath.Join(h.media, im.Path)); err != nil {
			t.Fatal(err)
		}
		seeds[im.Seed] = true
	}
	if len(seeds) != 4 {
		t.Fatalf("seeds %v", seeds)
	}
	refs := h.store.world.Characters[0].ReferenceImages
	if len(refs) != 1 || refs[0] != sh.Images[0].Path {
		t.Fatalf("reference_images %v", refs)
	}
	for _, g := range h.comfy.Graphs() {
		if g["ipapply"] != nil {
			t.Fatal("sheet must render prompt-only")
		}
	}
}

func TestBestSheetImage(t *testing.T) {
	ims := []worker.SheetImage{{Status: "unsafe", Recall: 0.9}, {Status: "ok", Recall: 0.5}, {Status: "ok", Recall: 0.7}, {Status: "ok", Recall: 0.7}}
	if b := worker.BestSheetImage(ims); b != 2 {
		t.Fatalf("best %d", b)
	}
	if b := worker.BestSheetImage(ims[:1]); b != -1 {
		t.Fatalf("best %d", b)
	}
}

func TestSheetComfyDownResumes(t *testing.T) {
	h := newHarness(t)
	h.store.addSheet("sh1", "c_vesna", 3)
	h.comfy.Down.Store(true)
	h.drain()
	sh := h.store.sheet("sh1")
	if sh.Status != "queued" || !strings.HasPrefix(sh.Error, "waiting: ") || len(sh.Images) != 0 {
		t.Fatalf("during outage %+v", sh)
	}
	if j := h.store.job(1); j.Status != "queued" || j.Attempts != 0 {
		t.Fatalf("job %+v", j)
	}
	// Resume from a partially rendered sheet: one candidate is already there.
	h.store.mu.Lock()
	h.store.sheets["sh1"].Images = []worker.SheetImage{{Seed: 1, Path: "characters/x.png", Status: "ok", Recall: 0.1}}
	h.store.mu.Unlock()
	h.comfy.Down.Store(false)
	h.store.advance(6 * time.Minute)
	h.drain()
	sh = h.store.sheet("sh1")
	if sh.Status != "ready" || len(sh.Images) != 3 || len(h.comfy.Graphs()) != 2 || *sh.Best == 0 {
		t.Fatalf("after outage %+v, %d renders", sh, len(h.comfy.Graphs()))
	}
}

func TestKidsWorldRejectsSensitive(t *testing.T) {
	h := newHarness(t)
	h.wd14.Sensitive = 0.87 // skin-tight outfit: passes for teens
	h.store.addSheet("sh1", "c_vesna", 1)
	h.drain()
	if sh := h.store.sheet("sh1"); sh.Status != "ready" {
		t.Fatalf("teen: %+v", sh)
	}

	k := newHarness(t)
	k.wd14.Sensitive = 0.87
	k.store.world.Audience = "kids"
	k.store.addSheet("sh1", "c_vesna", 1)
	k.drain()
	sh := k.store.sheet("sh1")
	if sh.Status != "failed" || sh.Images[0].Unsafe["sensitive"] != 0.87 || len(k.comfy.Graphs()) != 1+wd14.MaxReseed {
		t.Fatalf("kids: %+v, %d renders", sh, len(k.comfy.Graphs()))
	}
}

func TestSheetAllUnsafeFails(t *testing.T) {
	h := newHarness(t)
	h.wd14.Always.Store(true)
	h.store.addSheet("sh1", "c_vesna", 2)
	h.drain()
	sh := h.store.sheet("sh1")
	if sh.Status != "failed" || !strings.Contains(sh.Error, "unsafe") || len(sh.Images) != 2 || sh.Images[0].Path != "" {
		t.Fatalf("%+v", sh)
	}
	if len(h.comfy.Graphs()) != 2*(1+wd14.MaxReseed) {
		t.Fatalf("renders %d", len(h.comfy.Graphs()))
	}
	if len(h.store.world.Characters[0].ReferenceImages) != 0 {
		t.Fatal("unsafe image became a reference")
	}

	h2 := newHarness(t)
	h2.store.world.Characters[0].TagPrompt = ""
	h2.store.addSheet("sh2", "c_vesna", 2)
	h2.drain()
	if sh := h2.store.sheet("sh2"); sh.Status != "failed" || !strings.Contains(sh.Error, "tag_prompt") {
		t.Fatalf("%+v", sh)
	}
}
