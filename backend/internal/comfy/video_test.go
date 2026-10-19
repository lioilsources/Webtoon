package comfy_test

import (
	"encoding/json"
	"flag"
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/comfy"
)

var updateVideoGolden = flag.Bool("update-video-golden", false, "rewrite testdata/video_*.json from the current builder")

// The loop graph is golden-tested like the SDXL one: a portrait and a landscape case, compared
// as decoded JSON so map order does not matter. -update-video-golden rewrites the files.
func TestVideoWorkflowGolden(t *testing.T) {
	cases := []struct {
		name          string
		stillW, still int
		seconds       int
	}{
		{"portrait", 832, 1216, 2},
		{"landscape", 1216, 832, 1},
	}
	for _, c := range cases {
		w, h := comfy.VideoSize(c.stillW, c.still)
		g := comfy.VideoWorkflow("loop_ep1_p03.png", "her hair moves in the sea breeze, static camera", "",
			w, h, comfy.VideoLength(c.seconds), 4242, "webtoon/ep1/p03_loop")
		got, _ := json.MarshalIndent(g, "", " ")
		path := filepath.Join("testdata", "video_"+c.name+".json")
		if *updateVideoGolden {
			if err := os.WriteFile(path, got, 0o644); err != nil {
				t.Fatal(err)
			}
		}
		want, err := os.ReadFile(path)
		if err != nil {
			t.Fatal(err)
		}
		var gotAny, wantAny any
		json.Unmarshal(got, &gotAny)   //nolint:errcheck
		json.Unmarshal(want, &wantAny) //nolint:errcheck
		if !reflect.DeepEqual(gotAny, wantAny) {
			t.Errorf("%s:\n got: %s\nwant: %s", c.name, got, want)
		}
	}
}

func TestVideoWorkflowShape(t *testing.T) {
	g := comfy.VideoWorkflow("still.png", "waves, static camera", "", 480, 704, 33, 1, "x")
	flf := g["flf"].(map[string]any)["inputs"].(map[string]any)
	if flf["length"] != 33 || flf["width"] != 480 || flf["height"] != 704 {
		t.Fatalf("flf inputs %v", flf)
	}
	if !reflect.DeepEqual(flf["start_image"], flf["end_image"]) {
		t.Fatal("a loop needs start == end frame")
	}
	saves := 0
	for _, n := range g {
		if ct := n.(map[string]any)["class_type"]; ct == "SaveImage" || ct == "SaveAnimatedWEBP" {
			saves++
		}
	}
	if saves != 4 {
		t.Fatalf("expected 1 WebP + 3 frames, got %d save nodes", saves)
	}
	if w, h := comfy.VideoSize(1216, 832); w != 704 || h != 480 {
		t.Fatalf("landscape size %dx%d", w, h)
	}
	if comfy.VideoLength(3) != 49 || comfy.VideoEstimateSeconds(3) != 200 {
		t.Fatal("length/estimate")
	}
	if !comfy.IsWebP([]byte("RIFF\x00\x00\x00\x00WEBPVP8 ")) || comfy.IsWebP([]byte("\x89PNG")) {
		t.Fatal("IsWebP")
	}
}
