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


def comfy_render(panel, world, styles, preset, seed):
    p = prompts.build(panel, world, styles, preset)
    pos = p["positive"] + ", " + ", ".join(KIDS_POS)
    neg = p["negative"] + ", " + ", ".join(KIDS_NEG)
    g = comfy.workflow(pos, neg, p["width"], p["height"], seed, p["preset"], f"webtoon/kids/{world['id']}")
    return comfy.run(g)[0], pos


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
    name = path.stem
    outdir = OUT / "kids" / name / backend
    log = []
    if not placeholder:
        outdir.mkdir(parents=True, exist_ok=True)
        for i, panel in enumerate(sb["panels"]):
            f = outdir / f"p{i:02d}_s0.png"
            if f.exists():
                continue
            seed = seed_base + i * 100
            use = panel.get("backend", "comfy") if backend == "auto" else backend
            t0 = time.time()
            png, prompt = (flux_render(panel, world, seed) if use == "flux"
                           else comfy_render(panel, world, styles, preset, seed))
            f.write_bytes(png)
            log.append({"panel": i, "backend": use, "seed": seed, "prompt": prompt})
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", action="append", help="story file stem, e.g. 01_park (default: all)")
    ap.add_argument("--backend", choices=["comfy", "flux", "auto"], default="comfy")
    ap.add_argument("--preset", default="clean_webtoon")
    ap.add_argument("--seed-base", type=int, default=7000)
    ap.add_argument("--placeholder", action="store_true", help="layout check without rendering")
    args = ap.parse_args()

    styles = load_json(DATA / "styles.json")
    paths = sorted(STORIES.glob("*.json"))
    if args.story:
        paths = [p for p in paths if p.stem in args.story]
    if not args.placeholder:
        if not os.environ.get("CF_ACCESS_CLIENT_ID"):
            raise SystemExit("CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET are not set — *.ol1n.com is behind Cloudflare Access")
        if args.backend != "flux":
            check_checkpoint(styles["presets"][args.preset]["checkpoint"])
    for p in paths:
        render_story(p, args.backend, args.preset, styles, args.seed_base, args.placeholder)


if __name__ == "__main__":
    main()
