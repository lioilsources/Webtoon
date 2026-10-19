package comfy_test

import (
	"context"
	"encoding/json"
	"reflect"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/comfy"
	"github.com/ol1n/webtoon/backend/internal/domain"
	"github.com/ol1n/webtoon/backend/internal/testutil"
	"github.com/ol1n/webtoon/backend/internal/upstream"
)

func inputs(g comfy.Graph, node string) map[string]any {
	return g[node].(map[string]any)["inputs"].(map[string]any)
}

func TestWorkflowVariants(t *testing.T) {
	p := domain.Preset{Checkpoint: "noob.safetensors", Prediction: "eps", Sampler: "euler_ancestral",
		Scheduler: "normal", Steps: 28, CFG: 5}
	g := comfy.Workflow("pos", "neg", 832, 1216, 42, p, "webtoon/x/p00", nil)
	if len(g) != 7 || inputs(g, "sample")["seed"] != int64(42) || inputs(g, "ckpt")["ckpt_name"] != "noob.safetensors" {
		t.Fatalf("eps graph: %v", g)
	}
	if m := inputs(g, "sample")["model"].([]any); m[0] != "ckpt" {
		t.Fatalf("model %v", m)
	}

	p.Prediction = "v"
	g = comfy.Workflow("pos", "neg", 832, 1216, 1, p, "x", &comfy.IPAdapter{Image: "ref.png", Weight: 0.8})
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
	if inputs(g, "ipload")["preset"] != comfy.DefaultIPPreset || inputs(g, "ipapply")["end_at"] != comfy.DefaultIPEnd {
		t.Fatal("ip-adapter defaults")
	}
	ip := comfy.IPAdapterFor("face.png", &domain.IPAdapterConfig{Preset: "PLUS FACE (portraits)", Weight: 0.35, EndAt: 0.6})
	g = comfy.Workflow("pos", "neg", 832, 1216, 1, p, "x", ip)
	if inputs(g, "ipload")["preset"] != "PLUS FACE (portraits)" || inputs(g, "ipapply")["weight"] != 0.35 ||
		inputs(g, "ipapply")["end_at"] != 0.6 {
		t.Fatalf("configured ip-adapter %v %v", inputs(g, "ipload"), inputs(g, "ipapply"))
	}
	if g := comfy.Workflow("pos", "neg", 832, 1216, 1, p, "x", &comfy.IPAdapter{}); g["ipapply"] != nil {
		t.Fatal("adapter without image must render prompt-only")
	}

	p.Loras = []domain.Lora{{Name: "style.safetensors", Strength: 0.8}, {Name: "detail.safetensors", Strength: 0.5}}
	g = comfy.Workflow("pos", "neg", 832, 1216, 1, p, "x", nil)
	if m := inputs(g, "lora0")["model"].([]any); m[0] != "ckpt" || inputs(g, "lora0")["strength_clip"] != 0.8 {
		t.Fatalf("lora0 %v", inputs(g, "lora0"))
	}
	if m := inputs(g, "lora1")["clip"].([]any); m[0] != "lora0" || inputs(g, "lora1")["lora_name"] != "detail.safetensors" {
		t.Fatalf("lora1 %v", inputs(g, "lora1"))
	}
	for _, id := range []string{"pos", "neg"} {
		if c := inputs(g, id)["clip"].([]any); c[0] != "lora1" || c[1] != 1 {
			t.Fatalf("%s clip %v", id, c)
		}
	}
	if m := inputs(g, "vpred")["model"].([]any); m[0] != "lora1" {
		t.Fatalf("v-pred must wrap the last LoRA, got %v", m)
	}
}

func TestLoraJSON(t *testing.T) {
	var p domain.Preset
	if err := json.Unmarshal([]byte(`{"loras": [["a/b.safetensors", 0.9]]}`), &p); err != nil {
		t.Fatal(err)
	}
	if len(p.Loras) != 1 || p.Loras[0] != (domain.Lora{Name: "a/b.safetensors", Strength: 0.9}) {
		t.Fatalf("loras %v", p.Loras)
	}
	if b, _ := json.Marshal(p.Loras); string(b) != `[["a/b.safetensors",0.9]]` {
		t.Fatalf("marshal %s", b)
	}
	if err := json.Unmarshal([]byte(`{"loras": [["only-name"]]}`), &p); err == nil {
		t.Fatal("malformed lora must fail")
	}
}

// TestWorkflowMatchesPrototype compares the graph with m0/comfy.workflow (golden), as JSON.
func TestWorkflowMatchesPrototype(t *testing.T) {
	gold := testutil.Golden(t)
	var cases []struct {
		Args struct {
			Positive, Negative string
			Width, Height      int
			Seed               int64
			Preset             string
			Prefix             string
			Ref                string
			IPWeight           float64 `json:"ip_weight"`
			IPPreset           string  `json:"ip_preset"`
			IPEnd              float64 `json:"ip_end"`
		} `json:"args"`
		Graph json.RawMessage `json:"graph"`
	}
	testutil.GoldenField(t, gold, "workflows", &cases)
	st := testutil.Styles(t)
	for i, c := range cases {
		a := c.Args
		var ip *comfy.IPAdapter
		if a.Ref != "" {
			ip = &comfy.IPAdapter{Image: a.Ref, Weight: a.IPWeight, Preset: a.IPPreset, EndAt: a.IPEnd}
		}
		got := comfy.Workflow(a.Positive, a.Negative, a.Width, a.Height, a.Seed, st.Presets[a.Preset], a.Prefix, ip)
		var gotAny, wantAny any
		b, _ := json.Marshal(got)
		json.Unmarshal(b, &gotAny)        //nolint:errcheck
		json.Unmarshal(c.Graph, &wantAny) //nolint:errcheck
		if !reflect.DeepEqual(gotAny, wantAny) {
			t.Errorf("workflow %d\n got: %s\nwant: %s", i, b, c.Graph)
		}
	}
	if len(cases) == 0 {
		t.Fatal("no golden workflows")
	}
}

func TestPingUnreachable(t *testing.T) {
	// Port 1 on localhost: nothing listens, connection refused. Never the real ComfyUI.
	c := comfy.New("http://127.0.0.1:1")
	if err := c.Ping(context.Background()); !upstream.IsUnavailable(err) {
		t.Fatalf("got %v", err)
	}
}
