package comfy_test

import (
	"context"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/comfy"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/upstream"
)

func inputs(g comfy.Graph, node string) map[string]any {
	return g[node].(map[string]any)["inputs"].(map[string]any)
}

func TestWorkflowVariants(t *testing.T) {
	p := domain.Preset{Checkpoint: "noob.safetensors", Prediction: "eps", Sampler: "euler_ancestral",
		Scheduler: "normal", Steps: 28, CFG: 5}
	g := comfy.Workflow("pos", "neg", 832, 1216, 42, p, "webtoon/x/p00", "", 0.6)
	if len(g) != 7 || inputs(g, "sample")["seed"] != int64(42) || inputs(g, "ckpt")["ckpt_name"] != "noob.safetensors" {
		t.Fatalf("eps graph: %v", g)
	}
	if m := inputs(g, "sample")["model"].([]any); m[0] != "ckpt" {
		t.Fatalf("model %v", m)
	}

	p.Prediction = "v"
	g = comfy.Workflow("pos", "neg", 832, 1216, 1, p, "x", "ref.png", 0.8)
	if inputs(g, "vpred")["sampling"] != "v_prediction" {
		t.Fatal("vpred node missing")
	}
	if m := inputs(g, "ipload")["model"].([]any); m[0] != "vpred" {
		t.Fatalf("IP-Adapter must wrap the v-pred model, got %v", m)
	}
	if m := inputs(g, "sample")["model"].([]any); m[0] != "ipapply" {
		t.Fatalf("sampler model %v", m)
	}
	if inputs(g, "refimg")["image"] != "ref.png" || inputs(g, "ipapply")["weight"] != 0.8 {
		t.Fatal("ip-adapter inputs")
	}
}

func TestPingUnreachable(t *testing.T) {
	// Port 1 on localhost: nothing listens, connection refused. Never the real ComfyUI.
	c := comfy.New("http://127.0.0.1:1")
	if err := c.Ping(context.Background()); !upstream.IsUnavailable(err) {
		t.Fatalf("got %v", err)
	}
}
