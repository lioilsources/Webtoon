package integration

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/ol1n/webtoon/backend/internal/fakes"
)

// upload POSTs a multipart "file" field.
func (e *env) upload(path, user, filename string, data []byte, wantCode int) map[string]any {
	e.t.Helper()
	var buf bytes.Buffer
	mw := multipart.NewWriter(&buf)
	fw, _ := mw.CreateFormFile("file", filename)
	fw.Write(data)
	mw.Close()
	req, _ := http.NewRequest("POST", e.srv.URL+path, &buf)
	req.Header.Set("Content-Type", mw.FormDataContentType())
	req.Header.Set("X-User-ID", user)
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		e.t.Fatal(err)
	}
	defer resp.Body.Close()
	raw, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != wantCode {
		e.t.Fatalf("upload %s: %d, want %d: %s", path, resp.StatusCode, wantCode, raw)
	}
	out := map[string]any{}
	_ = json.Unmarshal(raw, &out)
	return out
}

func strs(v any) []string {
	var out []string
	for _, x := range v.([]any) {
		out = append(out, x.(string))
	}
	return out
}

func TestAuthorTools(t *testing.T) {
	e := setup(t)
	ctx := context.Background()

	// --- style presets + my worlds ---------------------------------------------------
	presets := e.do("GET", "/style_presets", "", nil, 200)["presets"].([]any)
	var clean map[string]any
	for _, p := range presets {
		if p.(map[string]any)["id"] == "clean_webtoon" {
			clean = p.(map[string]any)
		}
	}
	if len(presets) < 3 || clean == nil || len(clean["artist_tags"].([]any)) != 2 || clean["preview_url"] != nil {
		t.Fatalf("presets %v", presets)
	}
	os.MkdirAll(filepath.Join(e.media, "styles"), 0o755)
	os.WriteFile(filepath.Join(e.media, "styles", "hassaku_soft.png"), fakes.TinyPNG(), 0o644)
	presets = e.do("GET", "/style_presets", "", nil, 200)["presets"].([]any)
	for _, p := range presets {
		if p := p.(map[string]any); p["id"] == "hassaku_soft" && p["preview_url"] != "/media/styles/hassaku_soft.png" {
			t.Fatalf("preview %v", p)
		}
	}

	e.do("POST", "/worlds", "dm", map[string]any{"title": "x", "style_id": "clean_webtoon",
		"locations": []any{map[string]any{"id": "l_a", "name": "A"}}, "permissions": map[string]any{"allowed_locations": []string{"l_zz"}}}, 400)
	wd := e.do("POST", "/worlds", "dm", map[string]any{
		"title": "Les", "style_id": "clean_webtoon", "visibility": "private",
		"bible":       map[string]any{"rules": []string{"Žádná magie."}, "factions": []string{"Hajní"}, "lore": "x"},
		"locations":   []any{map[string]any{"id": "l_forest", "name": "Les", "description": "Hustý jehličnatý les."}, map[string]any{"id": "l_hut", "name": "Chata"}},
		"characters":  []any{map[string]any{"id": "c_ema", "name": "Ema", "role": "playable", "count_tag": "1girl", "description": "Dívka s copánky."}},
		"permissions": map[string]any{"allowed_locations": []string{"l_forest", "l_hut"}, "can_create_character": true},
	}, 201)
	wid := wd["id"].(string)
	if c := wd["characters"].([]any)[0].(map[string]any); len(c["reference_urls"].([]any)) != 0 {
		t.Fatalf("character %v", c)
	}
	mine := e.do("GET", "/worlds?owner=me", "dm", nil, 200)["worlds"].([]any)
	if len(mine) != 1 || mine[0].(map[string]any)["id"] != wid {
		t.Fatalf("my worlds %v", mine)
	}
	if n := len(e.do("GET", "/worlds?owner=me", "author", nil, 200)["worlds"].([]any)); n != 1 {
		t.Fatalf("author owns w_skyisles only: %d", n)
	}
	e.do("GET", "/worlds?owner=me", "", nil, 401)
	e.do("POST", "/worlds", "dm", map[string]any{"title": "x", "style_id": "clean_webtoon",
		"characters": []any{map[string]any{"name": "B", "count_tag": "3cats"}}}, 400)

	// --- canon editor: ordered nodes, ids kept / assigned, constraints trimmed ------------
	base := "/worlds/" + wid
	got := e.do("PATCH", base, "dm", map[string]any{"canon": map[string]any{
		"nodes":       []any{map[string]any{"text": " Ema najde stopu "}, map[string]any{"id": "c1", "text": "Bouře"}, map[string]any{"text": "Konec"}},
		"constraints": []any{" Nikdo nezemře. ", ""},
	}}, 200)
	canon := got["canon"].(map[string]any)
	nodes := canon["nodes"].([]any)
	if len(nodes) != 3 || nodes[0].(map[string]any)["id"] != "n1" || nodes[0].(map[string]any)["text"] != "Ema najde stopu" ||
		nodes[1].(map[string]any)["id"] != "c1" || nodes[2].(map[string]any)["id"] != "n2" {
		t.Fatalf("canon nodes %v", nodes)
	}
	if cs := strs(canon["constraints"]); len(cs) != 1 || cs[0] != "Nikdo nezemře." {
		t.Fatalf("constraints %v", cs)
	}
	e.do("PATCH", base, "dm", map[string]any{"canon": map[string]any{"nodes": []any{map[string]any{"id": "a", "text": "x"}, map[string]any{"id": "a", "text": "y"}}}}, 400)
	e.do("PATCH", base, "dm", map[string]any{"canon": map[string]any{"nodes": []any{map[string]any{"text": "  "}}}}, 400)
	e.do("PATCH", base, "dm", map[string]any{"permissions": map[string]any{"allowed_locations": []string{"l_nope"}}}, 400)
	e.do("PATCH", base, "dm", map[string]any{"permissions": map[string]any{"max_episodes": -1}}, 400)
	got = e.do("PATCH", base, "dm", map[string]any{"permissions": map[string]any{
		"can_add_characters": true, "can_create_character": true, "can_change_location": false, "allowed_locations": []string{"l_forest", "l_hut"}, "max_episodes": 20}}, 200)
	if p := got["permissions"].(map[string]any); p["max_episodes"].(float64) != 20 || p["can_add_characters"] != true {
		t.Fatalf("permissions %v", p)
	}

	// --- character PATCH --------------------------------------------------------------------
	cbase := base + "/characters/c_ema"
	e.do("PATCH", cbase, "stranger", map[string]any{"name": "x"}, 404) // private world
	e.do("PATCH", base+"/characters/c_nobody", "dm", map[string]any{"name": "x"}, 404)
	ch := e.do("PATCH", cbase, "dm", map[string]any{"tag_prompt": "Long_Hair,  twin braids , ,long hair, brown eyes", "personality": "odvážná"}, 200)
	if ch["tag_prompt"] != "long hair, twin braids, brown eyes" || ch["personality"] != "odvážná" || ch["name"] != "Ema" {
		t.Fatalf("patched %v", ch)
	}
	e.do("PATCH", cbase, "dm", map[string]any{"ip_adapter": map[string]any{"preset": "SUPER"}}, 400)
	e.do("PATCH", cbase, "dm", map[string]any{"ip_adapter": map[string]any{"weight": 3}}, 400)
	e.do("PATCH", cbase, "dm", map[string]any{"identity_level": "magic"}, 400)
	ch = e.do("PATCH", cbase, "dm", map[string]any{"identity_level": "ip_adapter",
		"ip_adapter": map[string]any{"preset": "PLUS FACE (portraits)", "weight": 0.35, "end_at": 0.6}}, 200)
	if ip := ch["ip_adapter"].(map[string]any); ch["identity_level"] != "ip_adapter" || ip["weight"].(float64) != 0.35 || ip["preset"] != "PLUS FACE (portraits)" {
		t.Fatalf("ip adapter %v", ch)
	}
	world, _ := e.s.LoadWorld(ctx, nil, wid)
	if c, _ := world.Character("c_ema"); c.IPAdapter == nil || c.IPAdapter.EndAt != 0.6 {
		t.Fatalf("stored ip adapter %+v", c.IPAdapter)
	}
	ch = e.do("PATCH", cbase, "dm", map[string]any{"name": "Ema"}, 200) // absent ip_adapter = keep
	if ch["ip_adapter"] == nil {
		t.Fatal("ip_adapter dropped by an unrelated patch")
	}
	ch = e.do("PATCH", cbase, "dm", map[string]any{"ip_adapter": nil, "identity_level": "prompt"}, 200)
	if _, ok := ch["ip_adapter"]; ok {
		t.Fatalf("ip_adapter not cleared %v", ch)
	}

	// --- tag_prompt generation (fake LLM, repair pass) -----------------------------------------
	tp := e.do("POST", cbase+"/tag_prompt", "dm", nil, 200)
	if tp["tag_prompt"] != "short hair, orange hair, green eyes" || strings.Join(strs(tp["dropped"]), ",") != "brown boots" ||
		tp["replaced"].(map[string]any)["copper hair"] == nil || tp["notes"] != "fake" {
		t.Fatalf("tag_prompt %v", tp)
	}
	if e.llm.Calls(fakes.KindTagPrompt) != 1 || e.llm.Calls(fakes.KindTagRepair) != 1 {
		t.Fatalf("llm calls %d/%d", e.llm.Calls(fakes.KindTagPrompt), e.llm.Calls(fakes.KindTagRepair))
	}
	// not saved until the author PATCHes it
	if c := e.do("GET", base, "dm", nil, 200)["characters"].([]any)[0].(map[string]any); c["tag_prompt"] != "long hair, twin braids, brown eyes" {
		t.Fatalf("generation must not save: %v", c["tag_prompt"])
	}
	e.do("POST", base+"/characters/c_ema/tag_prompt", "dm", map[string]any{"description": "  "}, 400)
	e.llm.Down.Store(true)
	e.do("POST", cbase+"/tag_prompt", "dm", nil, 503)
	e.llm.Down.Store(false)
	ltp := e.do("POST", base+"/locations/l_forest/tag_prompt", "dm", map[string]any{"description": "Hustý les"}, 200)
	if ltp["tag_prompt"] == "" {
		t.Fatalf("location tags %v", ltp)
	}
	e.do("POST", base+"/locations/l_hut/tag_prompt", "dm", nil, 400) // no description

	// --- reference upload ------------------------------------------------------------------------
	e.upload(cbase+"/references", "stranger", "a.png", fakes.TinyPNG(), 404)
	e.upload(cbase+"/references", "dm", "a.txt", []byte("hello, not an image"), 400)
	e.upload(cbase+"/references", "dm", "big.png", append(fakes.TinyPNG(), make([]byte, 70<<10)...), 413)
	ch = e.upload(cbase+"/references", "dm", "a.png", fakes.TinyPNG(), 201)
	ch = e.upload(cbase+"/references", "dm", "b.png", fakes.TinyPNG(), 201)
	refs, urls := strs(ch["reference_images"]), strs(ch["reference_urls"])
	if len(refs) != 2 || !strings.HasPrefix(refs[0], "characters/"+wid+"/c_ema/ref_") || urls[0] != "/media/"+refs[0] {
		t.Fatalf("refs %v %v", refs, urls)
	}
	resp, err := http.Get(e.srv.URL + urls[1])
	if err != nil || resp.StatusCode != 200 {
		t.Fatalf("reference media %v %v", err, resp)
	}
	resp.Body.Close()
	e.do("PATCH", cbase, "dm", map[string]any{"reference_images": []string{"episodes/x.png"}}, 400)
	e.do("PATCH", cbase, "dm", map[string]any{"reference_images": []string{refs[0], refs[0]}}, 400)
	ch = e.do("PATCH", cbase, "dm", map[string]any{"reference_images": []string{refs[1]}}, 200)
	if r := strs(ch["reference_images"]); len(r) != 1 || r[0] != refs[1] {
		t.Fatalf("reorder/remove %v", r)
	}
	lref := e.upload(base+"/locations/l_forest/references", "dm", "l.png", fakes.TinyPNG(), 201)
	if len(strs(lref["reference_urls"])) != 1 {
		t.Fatalf("location refs %v", lref)
	}

	// --- character sheet: backs off while ComfyUI is down, then picks the best candidate ----------
	e.do("POST", base+"/characters", "dm", map[string]any{"id": "c_bare", "name": "Bez tagů"}, 201)
	e.do("POST", base+"/characters/c_bare/sheet", "dm", nil, 400) // no tag_prompt yet
	e.do("POST", cbase+"/sheet", "dm", map[string]any{"seeds": 9}, 400)
	sh := e.do("POST", cbase+"/sheet", "dm", map[string]any{"seeds": 3}, 202)
	sid := sh["id"].(string)
	if sh["status"] != "queued" || sh["seeds"].(float64) != 3 || sh["done"].(float64) != 0 {
		t.Fatalf("sheet %v", sh)
	}
	e.do("POST", cbase+"/sheet", "dm", nil, 409)
	e.comfy.Down.Store(true)
	e.drain()
	sh = e.do("GET", "/sheets/"+sid, "dm", nil, 200)
	if sh["status"] != "queued" || !strings.HasPrefix(sh["error"].(string), "waiting: ") {
		t.Fatalf("sheet during outage %v", sh)
	}
	e.comfy.Down.Store(false)
	if _, err := e.s.Pool.Exec(ctx, "UPDATE jobs SET run_after = now() WHERE status = 'queued'"); err != nil {
		t.Fatal(err)
	}
	e.drain()
	sh = e.do("GET", "/sheets/"+sid, "dm", nil, 200)
	ims := sh["images"].([]any)
	if sh["status"] != "ready" || sh["done"].(float64) != 3 || len(ims) != 3 || sh["best"] == nil || sh["best_image_url"] == nil ||
		!strings.Contains(sh["prompt"].(string), "white background") {
		t.Fatalf("sheet %v", sh)
	}
	if im := ims[0].(map[string]any); im["status"] != "ok" || im["image_url"] == nil {
		t.Fatalf("image %v", im)
	}
	e.do("GET", "/sheets/"+sid, "stranger", nil, 404)
	if l := e.do("GET", cbase+"/sheets", "dm", nil, 200)["sheets"].([]any); len(l) != 1 {
		t.Fatalf("sheets %v", l)
	}
	ch = e.do("GET", base, "dm", nil, 200)["characters"].([]any)[0].(map[string]any)
	if r := strs(ch["reference_images"]); len(r) != 2 || !strings.Contains(r[1], "sheet_"+sid) {
		t.Fatalf("best sheet image not added to references %v", r)
	}

	// --- player-created character, playing your own world, delete rules --------------------------
	e.do("PATCH", base, "dm", map[string]any{"visibility": "public"}, 200)
	pc := e.do("POST", base+"/characters", "player", map[string]any{"name": "Hráčův hrdina", "description": "kluk"}, 201)
	if pc["role"] != "player_created" {
		t.Fatalf("player character %v", pc)
	}
	e.do("PATCH", base+"/characters/"+pc["id"].(string), "player", map[string]any{"role": "npc"}, 403)
	e.do("PATCH", base+"/characters/"+pc["id"].(string), "player", map[string]any{"speech_style": "stručně"}, 200)
	e.do("PATCH", cbase, "player", map[string]any{"name": "x"}, 403)

	camp := e.do("POST", "/campaigns", "dm", map[string]any{"world_id": wid}, 201) // "Zahraj si vlastní svět"
	if camp["campaign"].(map[string]any)["player_character_id"] != "c_ema" || camp["first_episode_id"] == nil {
		t.Fatalf("own campaign %v", camp)
	}
	e.do("DELETE", cbase, "dm", nil, 409)
	e.do("DELETE", base+"/characters/c_bare", "player", nil, 403)
	e.do("DELETE", base+"/characters/c_bare", "dm", nil, 204)
	e.do("DELETE", base+"/characters/c_bare", "dm", nil, 404)

	// --- locations ---------------------------------------------------------------------------------
	lb := base + "/locations/l_hut"
	e.do("PATCH", lb, "player", map[string]any{"mood": "x"}, 403)
	loc := e.do("PATCH", lb, "dm", map[string]any{"tag_prompt": "Indoors, wooden_wall", "mood": "útulná"}, 200)
	if loc["tag_prompt"] != "indoors, wooden wall" || loc["mood"] != "útulná" || loc["name"] != "Chata" {
		t.Fatalf("location %v", loc)
	}
	e.do("DELETE", lb, "dm", nil, 204)
	got = e.do("GET", base, "dm", nil, 200)
	if al := strs(got["permissions"].(map[string]any)["allowed_locations"]); len(al) != 1 || al[0] != "l_forest" || len(got["locations"].([]any)) != 1 {
		t.Fatalf("after location delete %v", got["permissions"])
	}

	stats := e.do("GET", base+"/stats", "dm", nil, 200)
	if stats["player_created_characters"].(float64) != 1 || len(stats["player_created"].([]any)) != 1 ||
		stats["player_created"].([]any)[0].(map[string]any)["owner_id"] != "player" {
		t.Fatalf("stats %v", stats)
	}
	if st := stats["stopped_at"].([]any); len(st) != 1 || st[0].(map[string]any)["episode"].(float64) != 1 {
		t.Fatalf("stopped_at %v", st)
	}
}
