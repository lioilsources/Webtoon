"""Storyboard → panels via ComfyUI, with SFW check and identity scoring by WD14.

    python3 m0/render.py --storyboard out/dev/storyboard_ep1.json --run ep1_noob [--preset clean_webtoon]
                         [--seeds 2] [--ref out/.../sheet.png] [--dry-run]
    python3 m0/render.py --sheet --run sheet_vesna --seeds 4     # character reference sheet

Output: out/<YYYY-MM-DD>/<run>/pNN_sK.png + meta.json
"""

import argparse
import datetime
import random
from pathlib import Path

import comfy
import prompts
from common import DATA, OUT, load_json, save_json, split_tags, wd14_tag

# Rating thresholds on WD14 output for audience-safe panels.
UNSAFE = {"explicit": 0.2, "questionable": 0.3}
DESIGN_THRESHOLD = 0.35
MAX_RESEED = 2


def sheet_panel(char):
    return {"shot": "sheet", "location_id": None, "characters": [{"id": char["id"]}],
            "visual_tags": ["standing", "full body", "looking at viewer", "smile", "white background",
                            "simple background", "straight-on", "arms at sides"]}


def safety(tags):
    r = tags.get("rating", {})
    bad = {k: round(r.get(k, 0), 3) for k, lim in UNSAFE.items() if r.get(k, 0) > lim}
    return bad


def identity(tags, char):
    """Recall of the character's design tags among WD14-detected tags."""
    design = split_tags(char.get("tag_prompt") or "")
    seen = {t for t, conf in tags.get("general", {}).items() if conf >= DESIGN_THRESHOLD}
    hit = [t for t in design if t in seen]
    return {"recall": round(len(hit) / max(1, len(design)), 3), "missing": [t for t in design if t not in seen]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default=str(DATA / "world_m0.json"))
    ap.add_argument("--storyboard")
    ap.add_argument("--sheet", action="store_true", help="render character reference sheet instead")
    ap.add_argument("--character", default=None)
    ap.add_argument("--run", required=True)
    ap.add_argument("--preset", default=None)
    ap.add_argument("--seeds", type=int, default=1)
    ap.add_argument("--seed-base", type=int, default=1000)
    ap.add_argument("--ref", default=None, help="reference image for IP-Adapter")
    ap.add_argument("--ip-weight", type=float, default=0.6)
    ap.add_argument("--panels", default=None, help="comma separated panel indices")
    ap.add_argument("--no-sfw", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    world = load_json(args.world)
    styles = load_json(DATA / "styles.json")
    char = next(c for c in world["characters"] if args.character in (None, c["id"]))
    if args.sheet:
        panels = [sheet_panel(char)]
    else:
        panels = load_json(args.storyboard)["panels"]
    idx = [int(i) for i in args.panels.split(",")] if args.panels else list(range(len(panels)))

    day = datetime.date.today().isoformat()
    outdir = OUT / day / args.run
    jobs = []
    for i in idx:
        p = prompts.build(panels[i], world, styles, args.preset, sfw=not args.no_sfw)
        for k in range(args.seeds):
            jobs.append((i, k, p, args.seed_base + i * 100 + k))
    print(f"{len(jobs)} images → {outdir}  (preset={args.preset or world['style_id']}, ref={args.ref})")
    if args.dry_run:
        for i, k, p, seed in jobs:
            print(f"\n[p{i:02d} s{k} seed={seed} {p['width']}x{p['height']}]\n+ {p['positive']}\n- {p['negative']}")
        return
    if not comfy.is_up():
        raise SystemExit("ComfyUI is not reachable — check the Spark schedule (ComfyUI window 07–13) with Director.")

    ref_name = None
    if args.ref:
        ref_name = comfy.upload(Path(args.ref).read_bytes(), f"webtoon_{args.run}_ref.png")

    meta = {"run": args.run, "preset": args.preset or world["style_id"], "ref": args.ref,
            "ip_weight": args.ip_weight if args.ref else None, "storyboard": args.storyboard, "images": []}
    outdir.mkdir(parents=True, exist_ok=True)
    for i, k, p, seed in jobs:
        rec = {"panel": i, "variant": k, "width": p["width"], "height": p["height"],
               "positive": p["positive"], "negative": p["negative"], "attempts": []}
        for attempt in range(MAX_RESEED + 1):
            s = seed if attempt == 0 else random.randint(0, 2**31)
            g = comfy.workflow(p["positive"], p["negative"], p["width"], p["height"], s, p["preset"],
                               f"webtoon/{day}/{args.run}/p{i:02d}_s{k}", ref_image=ref_name, ip_weight=args.ip_weight)
            png = comfy.run(g)[0]
            tags = wd14_tag(png)
            bad = safety(tags) if not args.no_sfw else {}
            rec["attempts"].append({"seed": s, "unsafe": bad})
            if not bad:
                break
        name = f"p{i:02d}_s{k}.png"
        (outdir / name).write_bytes(png)
        rec.update(file=name, seed=s, status="failed" if bad else "ok", rating=tags.get("rating"))
        if panels[i].get("characters"):
            rec["identity"] = identity(tags, char)
        meta["images"].append(rec)
        ident = rec.get("identity", {}).get("recall")
        print(f"p{i:02d} s{k} seed={s} {rec['status']} identity={ident}")
        save_json(outdir / "meta.json", meta)

    scored = [r["identity"]["recall"] for r in meta["images"] if "identity" in r]
    if scored:
        meta["identity_mean"] = round(sum(scored) / len(scored), 3)
        print(f"mean identity recall: {meta['identity_mean']}")
    save_json(outdir / "meta.json", meta)


if __name__ == "__main__":
    main()
