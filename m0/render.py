"""Storyboard → panels via ComfyUI, with SFW check and identity scoring by WD14.

    python3 m0/render.py --storyboard out/dev/storyboard_ep1.json --run ep1_noob [--preset clean_webtoon]
                         [--seeds 2] [--ref out/.../sheet.png] [--dry-run]
    python3 m0/render.py --sheet --run sheet_vesna --seeds 4     # character reference sheet

Output: out/<YYYY-MM-DD>/<run>/pNN_sK.png + meta.json
"""

import argparse
import datetime
import os
import random
import re
import time
from pathlib import Path

import comfy
import prompts
import rules
from common import DATA, OUT, load_json, save_json, split_tags, wd14_tag

# WD14 thresholds, reseeds and IP-Adapter defaults: rules/base/render.yaml and the profiles (with the reasons).
R = rules.load("render")
UNSAFE = dict(R["rating_limits"])
UNSAFE_KIDS = dict(rules.cfg("render", "kids")["rating_limits"])
DESIGN_THRESHOLD = R["design_threshold"]
MAX_RESEED = R["max_reseed"]
ADULT_TAG_LIMITS = dict(rules.cfg("render", "harlequin")["tag_limits"])
AGE_TAG_LIMITS = dict(rules.cfg("render", "free")["tag_limits"])  # free worlds: never dropped
IP = R["ip_adapter"]


def sheet_panel(char):
    return {"shot": "sheet", "location_id": None, "characters": [{"id": char["id"]}],
            "visual_tags": list(R["sheet_tags"])}


def safety(tags, audience="teen", free=False, profile=None):
    """WD14 tags → {tag: score} over the profile's limits (empty = safe). The profile: given, else from audience /
    free (a teen world has none: the base rating limits only). free: no rating check, the age limits never dropped."""
    R = rules.cfg("render", profile or ("free" if free else rules.profile_of(False, audience)))
    g, r = tags.get("general", {}), tags.get("rating", {})
    bad = {k: round(r.get(k, 0), 3) for k, lim in R["rating_limits"].items() if r.get(k, 0) > lim}
    bad.update({k: round(g[k], 3) for k, lim in R["tag_limits"].items() if g.get(k, 0) > lim})
    return bad


def identity(tags, char, shot=None):
    """Recall of the character's design tags (those in frame for the shot) among WD14-detected tags."""
    # "(brown hair:1.3)" → "brown hair": weights are prompt syntax, WD14 reports bare tags.
    design = [re.sub(r"^\((.*?)(:[\d.]+)?\)$", r"\1", t) for t in split_tags(char.get("tag_prompt") or "")]
    if shot == "close-up":
        design = [t for t in design if not prompts.LOWER_RE.search(t)]
    elif shot in ("medium", "over-shoulder"):
        design = [t for t in design if not prompts.FEET_RE.search(t)]
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
    ap.add_argument("--char-refs", action="store_true",
                    help="render a reference sheet per character (ref_<id>.png), IP-Adapter it into every panel with that character. "
                         "Burns colours on NoobAI even at 0.35, rainbow noise with the strip masks (banff test 2026-10-21)")
    ap.add_argument("--ip-weight", type=float, default=None, help="default 0.6 with --ref, 0.5 with --char-refs")
    ap.add_argument("--ip-preset", default=IP["preset"], help='or "PLUS FACE (portraits)"')
    ap.add_argument("--ip-end", type=float, default=IP["end"])
    ap.add_argument("--panels", default=None, help="comma separated panel indices")
    ap.add_argument("--profile", choices=rules.profiles(), help="safety profile (default: the world's, rules.world_profile)")
    ap.add_argument("--regions", action="store_true", help="own prompt per character over its strip of the frame (two-shots)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--skip-existing", action="store_true", help="resume: keep panels already on disk")
    args = ap.parse_args()

    if args.ip_weight is None:
        args.ip_weight = IP["weight_char_refs"] if args.char_refs else IP["weight_ref"]  # a white-background sheet at full strength also drags its pose and backdrop in
    world = load_json(args.world)
    styles = load_json(DATA / "styles.json")
    char = next(c for c in world["characters"] if args.character in (None, c["id"]))
    by_id = {c["id"]: c for c in world["characters"]}
    if args.sheet:
        panels = [sheet_panel(char)]
    else:
        panels = load_json(args.storyboard)["panels"]
    idx = [int(i) for i in args.panels.split(",")] if args.panels else list(range(len(panels)))

    day = os.environ.get("WEBTOON_DAY") or datetime.date.today().isoformat()  # a batch can span midnight
    outdir = OUT / day / args.run
    jobs = []
    for i in idx:
        p = prompts.build(panels[i], world, styles, args.preset, sfw=not world.get("free"), regional=args.regions)
        for k in range(args.seeds):
            jobs.append((i, k, p, args.seed_base + i * 100 + k))
    print(f"{len(jobs)} images → {outdir}  (preset={args.preset or world['style_id']}, ref={args.ref})")
    if args.dry_run:
        for i, k, p, seed in jobs:
            print(f"\n[p{i:02d} s{k} seed={seed} {p['width']}x{p['height']}]\n+ {p['positive']}\n- {p['negative']}")
            for r in p.get("regions") or []:
                print(f"  region: {r}")
        return
    if not comfy.is_up():
        raise SystemExit("ComfyUI is not reachable — check the Spark schedule (ComfyUI window 07–13) with Director.")

    ref_name = None
    if args.ref:
        ref_name = comfy.upload(Path(args.ref).read_bytes(), f"webtoon_{args.run}_ref.png")

    ip = bool(args.ref or args.char_refs)
    meta = {"run": args.run, "preset": args.preset or world["style_id"], "ref": args.ref, "char_refs": {},
            "ip_weight": args.ip_weight if ip else None,
            "ip_preset": args.ip_preset if ip else None, "ip_end": args.ip_end if ip else None, "storyboard": args.storyboard, "images": []}
    outdir.mkdir(parents=True, exist_ok=True)

    def draw(p, seed, prefix, refs=None):
        """One image with WD14 safety reseeds → (png, tags, unsafe, seed, attempts)."""
        attempts = []
        for attempt in range(MAX_RESEED + 1):
            # ComfyUI window end: WEBTOON_DEADLINE=HH:MM → submit nothing after it (resume later with --skip-existing).
            if os.environ.get("WEBTOON_DEADLINE") and time.strftime("%H:%M") >= os.environ["WEBTOON_DEADLINE"]:
                print(f"deadline {os.environ['WEBTOON_DEADLINE']} reached, stopping")
                raise SystemExit(3)
            s = seed if attempt == 0 else random.randint(0, 2**31)
            g = comfy.workflow(p["positive"], p["negative"], p["width"], p["height"], s, p["preset"], prefix,
                               ref_image=ref_name, ip_weight=args.ip_weight, ip_preset=args.ip_preset, ip_end=args.ip_end,
                               regions=p.get("regions"), refs=refs)
            png = comfy.run(g)[0]
            tags = wd14_tag(png)
            bad = safety(tags, profile=args.profile or rules.world_profile(world))
            attempts.append({"seed": s, "unsafe": bad})
            if not bad:
                break
        return png, tags, bad, s, attempts

    # One sheet per character, drawn once per run and kept (a rerun reuses it, so the face stays put).
    char_refs = {}
    if args.char_refs and not args.sheet:
        old_refs = load_json(outdir / "meta.json").get("char_refs", {}) if (outdir / "meta.json").exists() else {}
        for n, c in enumerate(world["characters"]):
            f = outdir / f"ref_{c['id']}.png"
            rec = old_refs.get(c["id"]) if f.exists() else None
            if not rec:
                p = prompts.build(sheet_panel(c), world, styles, args.preset, sfw=not world.get("free"))
                png, tags, bad, s, attempts = draw(p, args.seed_base + 9000 + n, f"webtoon/{day}/{args.run}/ref_{c['id']}")
                f.write_bytes(png)
                rec = {"file": f.name, "seed": s, "status": "failed" if bad else "ok", "attempts": attempts,
                       "identity": identity(tags, c, "sheet")}
                print(f"ref {c['id']} seed={s} {rec['status']} identity={rec['identity']['recall']}")
            meta["char_refs"][c["id"]] = rec
            if rec["status"] == "ok":  # an unsafe sheet is never fed back into the panels
                char_refs[c["id"]] = comfy.upload(f.read_bytes(), f"webtoon_{args.run}_ref_{c['id']}.png")

    if args.skip_existing and (outdir / "meta.json").exists():
        meta["images"] = [r for r in load_json(outdir / "meta.json")["images"] if (outdir / r["file"]).exists()]
        jobs = [j for j in jobs if not (outdir / f"p{j[0]:02d}_s{j[1]}.png").exists()]
    for i, k, p, seed in jobs:
        rec = {"panel": i, "variant": k, "width": p["width"], "height": p["height"],
               "positive": p["positive"], "negative": p["negative"], "regions": p.get("regions") or [], "attempts": []}
        # Shared-GPU courtesy: while out/PAUSE exists (another job owns ComfyUI) wait between panels.
        while (OUT / "PAUSE").exists():
            time.sleep(20)
        ids = [c["id"] for c in panels[i].get("characters", []) if c["id"] in by_id]
        refs = [(char_refs[cid], strip if len(ids) > 1 else None)
                for cid, strip in zip(ids, comfy.strips(len(ids))) if cid in char_refs]
        png, tags, bad, s, rec["attempts"] = draw(p, seed, f"webtoon/{day}/{args.run}/p{i:02d}_s{k}", refs)
        rec["refs"] = [cid for cid in ids if cid in char_refs]
        name = f"p{i:02d}_s{k}.png"
        (outdir / name).write_bytes(png)
        rec.update(file=name, seed=s, status="failed" if bad else "ok", rating=tags.get("rating"))
        if char["id"] in {c["id"] for c in panels[i].get("characters", [])} or args.sheet:
            rec["identity"] = identity(tags, char, panels[i].get("shot"))
        # Every character in frame, so a drifting second lead shows up too (WD14 tags the whole image:
        # in a two-shot it catches a lost hair colour, not two people swapping theirs).
        rec["identity_by"] = {c["id"]: identity(tags, by_id[c["id"]], panels[i].get("shot"))
                              for c in panels[i].get("characters", []) if c["id"] in by_id}
        meta["images"].append(rec)
        ident = rec.get("identity", {}).get("recall")
        print(f"p{i:02d} s{k} seed={s} {rec['status']} identity={ident}")
        save_json(outdir / "meta.json", meta)

    scored = [r["identity"]["recall"] for r in meta["images"] if "identity" in r]
    if scored:
        meta["identity_mean"] = round(sum(scored) / len(scored), 3)
        print(f"mean identity recall: {meta['identity_mean']}")
    for cid in by_id:
        got = [r["identity_by"][cid]["recall"] for r in meta["images"] if cid in r.get("identity_by", {})]
        if got:
            meta.setdefault("identity_mean_by", {})[cid] = round(sum(got) / len(got), 3)
    if meta.get("identity_mean_by"):
        print("identity per character:", meta["identity_mean_by"])
    save_json(outdir / "meta.json", meta)


if __name__ == "__main__":
    main()
