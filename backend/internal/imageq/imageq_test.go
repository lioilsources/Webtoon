package imageq_test

import (
	"bytes"
	"context"
	"testing"
	"time"

	"github.com/ol1n/webtoon/backend/internal/comfy"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/fakes"
	"github.com/ol1n/webtoon/backend/internal/imageq"
	"github.com/ol1n/webtoon/backend/internal/upstream"
)

func newClient(f *fakes.ImageAPI) *imageq.Client {
	c := imageq.New(f.URL, "id.access", "secret")
	c.PollInterval = time.Millisecond
	c.Timeout = 2 * time.Second
	return c
}

func graph(seed int64, ip *comfy.IPAdapter) comfy.Graph {
	p := domain.Preset{Checkpoint: "noobai.safetensors", Steps: 20, CFG: 5, Sampler: "euler", Scheduler: "normal"}
	return comfy.Workflow("1girl", "lowres", 832, 1216, seed, p, "webtoon/test", ip)
}

func TestRunDoneWithHeaders(t *testing.T) {
	f := fakes.NewImageAPI()
	defer f.Close()
	f.Polls = 2
	images, err := newClient(f).Run(context.Background(), graph(1, nil))
	if err != nil {
		t.Fatal(err)
	}
	if len(images) != 1 || !bytes.Equal(images[0], f.PNGBytes) {
		t.Fatalf("images = %d", len(images))
	}
	for _, h := range f.Headers() {
		if h.Get("X-Project") != "webtoon" || h.Get("CF-Access-Client-Id") != "id.access" || h.Get("CF-Access-Client-Secret") != "secret" {
			t.Fatalf("headers %v", h)
		}
	}
}

func TestSameGraphReattaches(t *testing.T) {
	f := fakes.NewImageAPI()
	defer f.Close()
	c := newClient(f)
	ctx := context.Background()
	if _, err := c.Run(ctx, graph(1, nil)); err != nil {
		t.Fatal(err)
	}
	if _, err := c.Run(ctx, graph(1, nil)); err != nil { // same client_ref: the finished job
		t.Fatal(err)
	}
	if _, err := c.Run(ctx, graph(2, nil)); err != nil { // reseed: a new job
		t.Fatal(err)
	}
	if n := f.Submits(); n != 2 {
		t.Fatalf("submits = %d, want 2", n)
	}
}

func TestWaitingWindowIsUnavailable(t *testing.T) {
	f := fakes.NewImageAPI()
	defer f.Close()
	f.Closed.Store(true)
	c := newClient(f)
	ctx := context.Background()
	if _, err := c.Run(ctx, graph(1, nil)); !upstream.IsUnavailable(err) {
		t.Fatalf("Run err = %v, want unavailable", err)
	}
	if err := c.Ping(ctx); !upstream.IsUnavailable(err) {
		t.Fatalf("Ping err = %v, want unavailable", err)
	}
	// The window opens: the retry finds the queued job instead of submitting another.
	f.Closed.Store(false)
	if err := c.Ping(ctx); err != nil {
		t.Fatal(err)
	}
	if _, err := c.Run(ctx, graph(1, nil)); err != nil {
		t.Fatal(err)
	}
	if n := f.Submits(); n != 1 {
		t.Fatalf("submits = %d, want 1", n)
	}
}

func TestJobErrorIsNotUnavailable(t *testing.T) {
	f := fakes.NewImageAPI()
	defer f.Close()
	f.Fail.Store(true)
	_, err := newClient(f).Run(context.Background(), graph(1, nil))
	if err == nil || upstream.IsUnavailable(err) {
		t.Fatalf("err = %v, want a plain error", err)
	}
}

func TestServerDownIsUnavailable(t *testing.T) {
	f := fakes.NewImageAPI()
	c := newClient(f)
	f.Close()
	if _, err := c.Run(context.Background(), graph(1, nil)); !upstream.IsUnavailable(err) {
		t.Fatalf("err = %v, want unavailable", err)
	}
}

func TestUploadGoesWithTheJob(t *testing.T) {
	f := fakes.NewImageAPI()
	defer f.Close()
	c := newClient(f)
	ctx := context.Background()
	name, err := c.Upload(ctx, fakes.TinyPNG(), "webtoon_w/x_hero ref.png")
	if err != nil {
		t.Fatal(err)
	}
	if name != "webtoon_w_x_hero_ref.png" {
		t.Fatalf("name = %q", name)
	}
	if _, err := c.Run(ctx, graph(1, &comfy.IPAdapter{Image: name})); err != nil {
		t.Fatal(err)
	}
	if in := f.Inputs(); len(in) != 1 || in[0] != name {
		t.Fatalf("inputs = %v", in)
	}
	if _, err := c.Run(ctx, graph(2, &comfy.IPAdapter{Image: "missing.png"})); err == nil {
		t.Fatal("a graph loading an image that was never uploaded must fail")
	}
}

func TestTagPassthrough(t *testing.T) {
	wd := fakes.NewWD14(map[string]float64{"red hair": 0.9})
	defer wd.Close()
	f := fakes.NewImageAPI()
	defer f.Close()
	f.WD14 = wd
	tags, err := newClient(f).Tag(context.Background(), fakes.TinyPNG())
	if err != nil {
		t.Fatal(err)
	}
	if tags.General["red hair"] != 0.9 || tags.Rating["explicit"] > 0.1 {
		t.Fatalf("tags = %+v", tags)
	}
	if wd.Requests.Load() != 1 {
		t.Fatal("tag did not reach WD14")
	}
}
