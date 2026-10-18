"""Kids stories → finished webtoon strips, rendered on the public ol1n.com endpoints.

    CF_ACCESS_CLIENT_ID=… CF_ACCESS_CLIENT_SECRET=… python3 kids/make_strips.py            # all stories
    python3 kids/make_strips.py --story 03_les --backend flux                              # one story via FLUX
    python3 kids/make_strips.py --placeholder                                              # layout check, no GPU

Storyboards are hand-written in kids/stories/*.json (world + storyboard in the m0 format, plus a
natural-language `scene_en` and per-character `desc_en` for FLUX). Backends:

  comfy  comfyui.ol1n.com, SDXL booru prompt from m0/prompts.build (preset from styles.json)
  flux   llm.ol1n.com/nim/flux-schnell — gen-queue async job (submit 202 → poll → /result JPEG),
         the same protocol as Ol1nLLM's FluxNimService
  auto   comfy, but a panel can pin "backend": "flux" in its JSON

Panels are cached in out/kids/<story>/<backend>/pNN_s0.png, so a rerun only renders what is missing.
Output strip: out/kids/<story>.png
"""

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "m0"))
os.environ.setdefault("WEBTOON_COMFY", "https://comfyui.ol1n.com")

import comfy  # noqa: E402
import jobs  # noqa: E402
import compose  # noqa: E402
import prompts  # noqa: E402
from common import DATA, OUT, http, http_json, load_json  # noqa: E402
from PIL import Image  # noqa: E402

STORIES = Path(__file__).resolve().parent / "stories"
FLUX_URL = os.environ.get("FLUX_NIM_URL", "https://llm.ol1n.com").rstrip("/")
FLUX_STYLE = ("Children's picture-book webtoon illustration, soft pastel colors, clean lineart, flat shading, "
              "cute rounded characters, wholesome and friendly, no text, no speech bubbles.")
KIDS_POS = ["cute", "wholesome", "pastel colors"]
KIDS_NEG = ["horror", "scary", "creepy face", "realistic"]


NATURAL_NEG = ("text, speech bubble, watermark, signature, logo, comic panel, multiple views, nsfw, nude, "
               "underwear, cleavage, suggestive, blood, gore, horror, scary, creepy face, deformed, extra limbs, "
               "bad anatomy, bad hands")
SHOT_EN = {"establishing": "wide establishing shot, no people", "wide": "wide shot, full body",
           "medium": "medium shot", "close-up": "close-up"}


def natural_prompt(panel, world, pre):
    """Sentence prompt for models that read prose (Juggernaut, FLUX): style, shot, scene, who is in it."""
    chars = {c["id"]: c for c in world["characters"]}
    who = " ".join(chars[c["id"]]["desc_en"] + "." for c in panel.get("characters", []) if c["id"] in chars)
    loc = next((l.get("desc_en", "") for l in world["locations"] if l["id"] == panel.get("location_id")), "")
    trig = ", ".join(l["trigger"] for l in pre.get("loras", []) if l.get("trigger"))
    if pre.get("who_first"):
        # SDXL reads ~77 CLIP tokens; descriptions after the scene got merged into whoever the scene names
        # first (the pug wore the girl's apron). Who first, scene second, setting last.
        parts = [trig, pre["style_text"], SHOT_EN.get(panel.get("shot"), ""), who, panel["scene_en"] + ".", loc]
    else:
        parts = [trig, pre["style_text"], SHOT_EN.get(panel.get("shot"), ""), panel["scene_en"] + ".", who, loc,
                 panel.get("extra_en", "")]
    return " ".join(x.strip() for x in parts if x and x.strip())


def build_job(panel, world, styles, preset, seed):
    """Graph + the parameters that define it (the job record), without touching the server."""
    pre = styles["presets"][preset]
    w, h = styles["shot_size"].get(panel.get("shot"), [832, 1216])
    prefix = f"webtoon/kids/{world['id']}"
    loras = pre.get("loras", [])
    meta = {"preset": preset, "preset_def": pre, "seed": seed, "width": w, "height": h,
            "loras": [{k: l.get(k) for k in ("name", "strength", "trigger")} for l in loras]}
    if pre.get("graph") == "flux":
        pos = natural_prompt(panel, world, pre)
        meta.update(graph="flux", model=pre["unet"], sampler="euler", scheduler="simple", steps=pre.get("steps", 20),
                    cfg=1.0, guidance=pre.get("guidance", 3.5), positive=pos, negative="")
        return comfy.flux_workflow(pos, w, h, seed, pre, prefix, loras), meta
    if pre.get("dialect") == "natural":
        pos = natural_prompt(panel, world, pre)
        neg = ", ".join([pre.get("negative", ""), NATURAL_NEG] + panel.get("negative_extra", []))
    else:
        p = prompts.build(panel, world, styles, preset)
        pos = p["positive"] + ", " + ", ".join(KIDS_POS)
        neg = p["negative"] + ", " + ", ".join(KIDS_NEG + panel.get("negative_extra", []))
        trig = [l["trigger"] for l in loras if l.get("trigger")]
        if trig:
            pos = ", ".join(trig) + ", " + pos
        w, h = p["width"], p["height"]
        meta.update(width=w, height=h)
    meta.update(graph="sdxl", model=pre["checkpoint"], sampler=pre["sampler"], scheduler=pre["scheduler"],
                steps=pre["steps"], cfg=pre["cfg"], positive=pos, negative=neg)
    return comfy.workflow(pos, neg, w, h, seed, pre, prefix, loras=loras), meta


def comfy_render(panel, world, styles, preset, seed):
    """→ (png, meta). meta is what kids/jobs.py records."""
    graph, meta = build_job(panel, world, styles, preset, seed)
    return comfy.run(graph)[0], meta


def flux_prompt(panel, world):
    chars = {c["id"]: c for c in world["characters"]}
    who = " ".join(chars[c["id"]]["desc_en"] + "." for c in panel.get("characters", []) if c["id"] in chars)
    return f"{FLUX_STYLE} {panel['scene_en']}. {who}".strip()


def flux_render(panel, world, seed, timeout=600):
    prompt = flux_prompt(panel, world)
    body = {"prompt": prompt, "width": 1024, "height": 1024, "steps": 4, "seed": seed}
    job = http_json("POST", f"{FLUX_URL}/nim/flux-schnell/v1/infer", body)
    jid = job["id"]
    t0 = time.time()
    while time.time() - t0 < timeout:
        st = http_json("GET", f"{FLUX_URL}/nim/flux-schnell/jobs/{jid}")
        if st["status"] == "done":
            raw = http("GET", f"{FLUX_URL}/nim/flux-schnell/jobs/{jid}/result")
            buf = io.BytesIO()
            Image.open(io.BytesIO(raw)).convert("RGB").save(buf, "PNG")  # /result is JPEG
            return buf.getvalue(), prompt
        if st["status"] == "error":
            raise RuntimeError(f"flux-schnell job {jid}: {st.get('error')}")
        time.sleep(3)
    raise TimeoutError(f"flux-schnell job {jid} not done in {timeout}s")


def check_checkpoint(name):
    info = http_json("GET", f"{comfy.COMFY_URL}/object_info/CheckpointLoaderSimple", timeout=30)
    have = info["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    if name not in have:
        raise SystemExit(f"checkpoint {name} not on the server; available: {', '.join(have)}")


def render_story(path, backend, preset, styles, seed_base, placeholder):
    data = load_json(path)
    world, sb = data["world"], data["storyboard"]
    preset = preset or world.get("style_id", "clean_webtoon")
    name = path.stem
    outdir = OUT / "kids" / name / backend
    log = []
    if not placeholder:
        outdir.mkdir(parents=True, exist_ok=True)
        for i, panel in enumerate(sb["panels"]):
            f = outdir / f"p{i:02d}_s0.png"
            if f.exists():
                continue
            seed = panel.get("seed", seed_base + i * 100)
            use = panel.get("backend", "comfy") if backend == "auto" else backend
            t0 = time.time()
            if use == "flux":
                png, prompt = flux_render(panel, world, seed)
                meta = {"graph": "nim", "model": "flux-schnell (gen-queue)", "seed": seed, "steps": 4,
                        "width": 1024, "height": 1024, "positive": prompt, "negative": "", "loras": []}
            else:
                png, meta = comfy_render(panel, world, styles, preset, seed)
            f.write_bytes(png)
            jobs.record(name, i, None, meta, png, selected=True, seconds=round(time.time() - t0, 1))
            log.append({"panel": i, "backend": use, "seed": seed, "prompt": meta["positive"]})
            print(f"  {name} p{i:02d} {use} seed={seed} {time.time() - t0:.0f}s", flush=True)
        if log:
            with open(outdir / "log.jsonl", "a", encoding="utf-8") as fh:
                for rec in log:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    strip = compose.compose(sb, outdir, 0, placeholder)
    out = OUT / "kids" / f"{name}{'_placeholder' if placeholder else ''}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    strip.save(out, optimize=True)
    print(f"{out}: {strip.width}x{strip.height}")
    return out


def render_variants(path, preset, styles, panels, n, seed_base=20000):
    """n candidate renders per panel (pNN_vK.png), all recorded as not selected — pick one with --pick."""
    data = load_json(path)
    world, sb = data["world"], data["storyboard"]
    preset = preset or world.get("style_id", "clean_webtoon")
    outdir = OUT / "kids" / path.stem / "comfy"
    outdir.mkdir(parents=True, exist_ok=True)
    for i in panels:
        for k in range(n):
            seed = seed_base + i * 100 + k * 7
            t0 = time.time()
            png, meta = comfy_render(sb["panels"][i], world, styles, preset, seed)
            (outdir / f"p{i:02d}_v{k}.png").write_bytes(png)
            jobs.record(path.stem, i, k, meta, png, selected=False, seconds=round(time.time() - t0, 1))
            print(f"  {path.stem} p{i:02d} v{k} seed={seed} {time.time() - t0:.0f}s", flush=True)


def pick_variant(path, panel, k, seed_base=20000):
    """Promote pNN_vK to the strip image and pin its seed in the storyboard."""
    import shutil
    outdir = OUT / "kids" / path.stem / "comfy"
    shutil.copy(outdir / f"p{panel:02d}_v{k}.png", outdir / f"p{panel:02d}_s0.png")
    data = load_json(path)
    seed = seed_base + panel * 100 + k * 7
    data["storyboard"]["panels"][panel]["seed"] = seed
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    jobs.pick(path.stem, panel, k, seed)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", action="append", help="story file stem, e.g. 01_park (default: all)")
    ap.add_argument("--backend", choices=["comfy", "flux", "auto"], default="comfy")
    ap.add_argument("--preset", default=None, help="style preset (default: the story's world.style_id)")
    ap.add_argument("--seed-base", type=int, default=7000)
    ap.add_argument("--placeholder", action="store_true", help="layout check without rendering")
    ap.add_argument("--variants", type=int, default=0, help="render N candidates for --panels instead of the strip")
    ap.add_argument("--panels", default="", help="comma separated panel indices for --variants")
    ap.add_argument("--pick", action="append", default=[], help="story:panel:variant — promote a candidate")
    args = ap.parse_args()

    styles = load_json(DATA / "styles.json")
    paths = sorted(STORIES.glob("*.json"))
    if args.story:
        paths = [p for p in paths if p.stem in args.story]
    if not args.placeholder:
        if not os.environ.get("CF_ACCESS_CLIENT_ID"):
            raise SystemExit("CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET are not set — *.ol1n.com is behind Cloudflare Access")
        if args.backend != "flux":
            for pre in {args.preset or load_json(p)["world"].get("style_id", "clean_webtoon") for p in paths}:
                if "checkpoint" in styles["presets"][pre]:
                    check_checkpoint(styles["presets"][pre]["checkpoint"])
    if args.pick:
        for spec in args.pick:
            st, pi, k = spec.split(":")
            pick_variant(STORIES / f"{st}.json", int(pi), int(k))
        return
    if args.variants:
        for p in paths:
            render_variants(p, args.preset, styles, [int(i) for i in args.panels.split(",")], args.variants)
        return
    for p in paths:
        render_story(p, args.backend, args.preset, styles, args.seed_base, args.placeholder)


if __name__ == "__main__":
    main()
