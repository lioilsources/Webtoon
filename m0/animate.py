"""Seamless 1–3 s loops for storyboard panels marked `animate` (PLAN-motion-panels.md, phase 1).

    python3 m0/animate.py --world data/stories/<id>/world.json --storyboard data/stories/<id>/storyboard.json --run <id>
                          [--panels 0,2] [--seconds 2] [--seed-base 9000] [--skip-existing] [--force] [--dry-run]

Takes the finished still out/<day>/<run>/pNN_s0.png and runs Wan 2.2 I2V 14B (Lightning, 4 steps) through
WanFirstLastFrameToVideo with start = end = that still, so the clip closes on itself without a cut. The graph is a
port of video-stack/workflows/flf2v_lightning_portrait.json; the clip is saved as an animated WebP (the Flutter
Image widget plays it natively) plus three frames (first, middle, last) that go through the same WD14 safety check
as a panel. Output: out/<day>/<run>/pNN_video.webp, pNN_v{0,1,2}.png, meta_video.json.
"""

import argparse
import datetime
import os
import random
import re
import time
from pathlib import Path

import comfy
import rules
from common import OUT, load_json, save_json, wd14_tag
from render import MAX_RESEED, safety

# Loop rules (fps, size, negatives, the per-story limit) with their reasons: rules/base/animate.yaml (+ profiles),
# rules/base/storyboard.yaml.
R = rules.load("animate")
FPS = R["fps"]
MAX_ANIMATED = rules.get("storyboard.limits.max_animated")  # one loop costs about 11 stills (PLAN-motion-panels §3)
SIZE = {k: tuple(v) for k, v in R["size"].items()}
NEGATIVE = ", ".join(R["negative"]["common"] + R["negative"]["tail"])


def negative(profile=None):
    n = rules.cfg("animate", profile)["negative"]
    return ", ".join(n["common"] + n["tail"])


NEGATIVE_FREE = negative("free")
STYLE_TAIL_TAGS = R["style_tail_tags"]


def frames(seconds):
    """Wan VAE compresses time 4:1 → length must be 4n+1; 16 fps → 17 / 33 / 49 for 1 / 2 / 3 s."""
    return FPS * seconds + 1


def size_for(png_path):
    from PIL import Image
    w, h = Image.open(png_path).size
    return SIZE["portrait" if h >= w else "landscape"]


def style_tail(preset):
    return ", ".join(preset.get("aesthetic_tags", [])[:STYLE_TAIL_TAGS])


def graph(start_image, motion, preset, width, height, length, seed, prefix, free=False, profile=None):
    """FLF2V loop graph: same nodes and parameters as video-stack flf2v_lightning_portrait.json, plus
    SaveAnimatedWEBP and three SaveImage probes (first / middle / last frame) for the WD14 check."""
    positive = motion.strip().rstrip(".")
    tail = style_tail(preset)
    if tail:
        positive += ", " + tail
    g = {
        "unet_high": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "lora_high": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["unet_high", 0], "lora_name": "Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1_high_noise_model.safetensors", "strength_model": 1.0}},
        "shift_high": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["lora_high", 0], "shift": 5.0}},
        "unet_low": {"class_type": "UNETLoader", "inputs": {"unet_name": "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors", "weight_dtype": "default"}},
        "lora_low": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["unet_low", 0], "lora_name": "Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1_low_noise_model.safetensors", "strength_model": 1.0}},
        "shift_low": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["lora_low", 0], "shift": 5.0}},
        "clip": {"class_type": "CLIPLoader", "inputs": {"clip_name": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "type": "wan", "device": "default"}},
        "pos": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": positive}},
        "neg": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["clip", 0], "text": negative(profile) if profile else NEGATIVE_FREE if free else NEGATIVE}},
        "still": {"class_type": "LoadImage", "inputs": {"image": start_image}},
        "vae": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_2.1_vae.safetensors"}},
        # start_image and end_image are the same still → the loop closes on itself.
        "flf": {"class_type": "WanFirstLastFrameToVideo", "inputs": {
            "positive": ["pos", 0], "negative": ["neg", 0], "vae": ["vae", 0],
            "width": width, "height": height, "length": length, "batch_size": 1,
            "start_image": ["still", 0], "end_image": ["still", 0]}},
        "sample_high": {"class_type": "KSamplerAdvanced", "inputs": {
            "add_noise": "enable", "noise_seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
            "model": ["shift_high", 0], "positive": ["flf", 0], "negative": ["flf", 1], "latent_image": ["flf", 2],
            "start_at_step": 0, "end_at_step": 2, "return_with_leftover_noise": "enable"}},
        "sample_low": {"class_type": "KSamplerAdvanced", "inputs": {
            "add_noise": "disable", "noise_seed": seed, "steps": 4, "cfg": 1.0, "sampler_name": "euler", "scheduler": "simple",
            "model": ["shift_low", 0], "positive": ["flf", 0], "negative": ["flf", 1], "latent_image": ["sample_high", 0],
            "start_at_step": 2, "end_at_step": 4, "return_with_leftover_noise": "disable"}},
        "decode": {"class_type": "VAEDecode", "inputs": {"samples": ["sample_low", 0], "vae": ["vae", 0]}},
        "webp": {"class_type": "SaveAnimatedWEBP", "inputs": {
            "images": ["decode", 0], "filename_prefix": prefix, "fps": float(FPS), "lossless": False, "quality": R["webp_quality"], "method": "default"}},
    }
    for name, idx in (("v0", 0), ("v1", length // 2), ("v2", length - 1)):
        g[f"pick_{name}"] = {"class_type": "ImageFromBatch", "inputs": {"image": ["decode", 0], "batch_index": idx, "length": 1}}
        g[f"save_{name}"] = {"class_type": "SaveImage", "inputs": {"images": [f"pick_{name}", 0], "filename_prefix": f"{prefix}_{name}"}}
    return g


def ambient_phrases(wd14):
    """meta.json wd14_tags {tag: score} → up to ambient.max_phrases loop phrases (rules/base/animate.yaml from_tags)."""
    A = R["ambient"]
    out = []
    for tag, _ in sorted(wd14.items(), key=lambda x: -x[1]):
        for e in A["from_tags"]:
            if any(tag == k or re.search(rf"(?<!\S){re.escape(k)}(?!\S)", tag) for k in e["tags"]):
                if e["phrase"] not in out:
                    out.append(e["phrase"])
                break
        if len(out) >= A["max_phrases"]:
            break
    return out or [A["default"]]


def loop_motion(panel, motion, wd14):
    """The motion prompt a loop actually gets. Without wd14 tags (a run from before they were stored): the storyboard
    motion unchanged. Establishing / empty panels and panels with 2+ characters: ambient only from the still's tags;
    one character: its subject motion (from the storyboard) plus the tag-derived ambient."""
    if wd14 is None:
        return motion
    A = R["ambient"]
    n = len(panel.get("characters", []))
    phrases = ambient_phrases(wd14)
    if n >= 2:
        return A["template"].format(ambient=", ".join(phrases))
    if n == 0 or panel.get("shot") == "establishing":
        return A["template_empty"].format(ambient=", ".join(phrases))
    core = re.sub(r",?\s*static camera$", "", motion.strip().rstrip("."), flags=re.I)
    extra = [p for p in phrases if p.lower() not in core.lower()]
    return A["template_single"].format(motion=core, ambient=", ".join(extra)) if extra else motion


def wd14_by_panel(meta_path):
    """out/<day>/<run>/meta.json → {panel: wd14_tags} of the s0 stills (panels without them are left out)."""
    if not meta_path.exists():
        return {}
    return {r["panel"]: r["wd14_tags"] for r in load_json(meta_path).get("images", [])
            if r.get("variant") == 0 and r.get("wd14_tags") is not None}


def select_panels(panels, explicit, force):
    if explicit:
        idx = [int(i) for i in explicit.split(",")]
    else:
        idx = [i for i, p in enumerate(panels) if p.get("animate") and p.get("motion")]
    if len(idx) > MAX_ANIMATED and not force:
        raise SystemExit(f"{len(idx)} animated panels, limit is {MAX_ANIMATED} per story (one loop ≈ 11 stills); use --force to override")
    return idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", required=True)
    ap.add_argument("--storyboard", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--panels", default=None, help="comma separated panel indices (default: panels with animate+motion)")
    ap.add_argument("--seconds", type=int, default=2, choices=(1, 2, 3))
    ap.add_argument("--seed-base", type=int, default=9000)
    ap.add_argument("--skip-existing", action="store_true", help="keep loops already on disk")
    ap.add_argument("--force", action="store_true", help=f"allow more than {MAX_ANIMATED} loops")
    ap.add_argument("--profile", choices=rules.profiles(), help="negative and safety profile (default: the world's)")
    ap.add_argument("--dry-run", action="store_true", help="write the graphs to out/, call nothing")
    args = ap.parse_args()

    world = load_json(args.world)
    sb = load_json(args.storyboard)
    styles = load_json(Path(__file__).resolve().parent.parent / "data" / "styles.json")
    preset = styles["presets"][world["style_id"]]
    free = bool(world.get("free"))
    profile = args.profile or rules.world_profile(world)
    panels = sb["panels"]
    idx = select_panels(panels, args.panels, args.force)
    day = os.environ.get("WEBTOON_DAY") or datetime.date.today().isoformat()
    outdir = OUT / day / args.run
    outdir.mkdir(parents=True, exist_ok=True)
    length = frames(args.seconds)
    print(f"{len(idx)} loops × {args.seconds} s ({length} frames) → {outdir}  (preset={world['style_id']})")

    meta_path = outdir / "meta_video.json"
    meta = load_json(meta_path) if meta_path.exists() else {"run": args.run, "fps": FPS, "videos": []}
    if args.skip_existing:
        meta["videos"] = [r for r in meta["videos"] if (outdir / r["file"]).exists()]
        idx = [i for i in idx if not (outdir / f"p{i:02d}_video.webp").exists()]

    wd14 = wd14_by_panel(outdir / "meta.json")  # render.py's WD14 tags of the stills (older runs: none)
    jobs = []
    for i in idx:
        still = outdir / f"p{i:02d}_s0.png"
        if not still.exists():
            print(f"p{i:02d}: still {still.name} missing, render it first — skipped")
            continue
        motion = loop_motion(panels[i], panels[i].get("motion") or R["default_motion"], wd14.get(i))
        w, h = size_for(still)
        jobs.append((i, still, motion, w, h, args.seed_base + i * 100))

    if args.dry_run:
        for i, still, motion, w, h, seed in jobs:
            g = graph(f"webtoon_{args.run}_p{i:02d}.png", motion, preset, w, h, length, seed, f"webtoon/{day}/{args.run}/p{i:02d}_video", free=free, profile=profile)
            path = outdir / f"p{i:02d}_video_graph.json"
            save_json(path, g)
            print(f"[p{i:02d} {w}x{h} len={length} seed={seed}] + {g['pos']['inputs']['text']}\n  graph → {path}")
        return
    if not comfy.is_up():
        raise SystemExit("ComfyUI is not reachable — check the Spark schedule (ComfyUI window 07–13) with Director.")

    for i, still, motion, w, h, seed in jobs:
        while (OUT / "PAUSE").exists():  # shared-GPU courtesy, same as render.py
            time.sleep(20)
        name = comfy.upload(still.read_bytes(), f"webtoon_{args.run}_p{i:02d}.png")
        rec = {"panel": i, "seconds": args.seconds, "frames": length, "width": w, "height": h, "motion": motion, "attempts": []}
        t0 = time.time()
        for attempt in range(MAX_RESEED + 1):
            if os.environ.get("WEBTOON_DEADLINE") and time.strftime("%H:%M") >= os.environ["WEBTOON_DEADLINE"]:
                print(f"deadline {os.environ['WEBTOON_DEADLINE']} reached, stopping")
                raise SystemExit(3)
            s = seed if attempt == 0 else random.randint(0, 2**31)
            g = graph(name, motion, preset, w, h, length, s, f"webtoon/{day}/{args.run}/p{i:02d}_video", free=free, profile=profile)
            outs = comfy.run_outputs(g, timeout=1800)
            webp = next((f for f in outs.get("webp", []) if f["filename"].lower().endswith(".webp")), None)
            if webp is None:
                raise RuntimeError(f"p{i:02d}: SaveAnimatedWEBP produced no file: {list(outs)}")
            probes = {k: outs[f"save_{k}"][0]["bytes"] for k in ("v0", "v1", "v2")}
            tags = {k: wd14_tag(b) for k, b in probes.items()}
            bad = {k: v for k, t in tags.items() for v in [safety(t, profile=profile)] if v}
            rec["attempts"].append({"seed": s, "unsafe": bad})
            if not bad:
                break
        (outdir / f"p{i:02d}_video.webp").write_bytes(webp["bytes"])
        for k, b in probes.items():
            (outdir / f"p{i:02d}_{k}.png").write_bytes(b)
        rec.update(file=f"p{i:02d}_video.webp", seed=s, elapsed_s=round(time.time() - t0, 1),
                   status="failed" if bad else "ok", size_kb=len(webp["bytes"]) // 1024,
                   ratings={k: t.get("rating") for k, t in tags.items()})
        meta["videos"] = [r for r in meta["videos"] if r["panel"] != i] + [rec]
        save_json(meta_path, meta)
        print(f"p{i:02d} seed={s} {rec['status']} {rec['elapsed_s']}s {rec['size_kb']} kB")
    print(f"done: {len(jobs)} loops, {sum(r['elapsed_s'] for r in meta['videos'] if r['panel'] in idx):.0f} s total")


if __name__ == "__main__":
    main()
