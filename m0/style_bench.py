"""Style benchmark: every candidate style × the fixed test scenes it may draw → images, thumbs, results.json.

    python3 m0/style_bench_gen.py                        # (re)writes data/style_bench/{candidates,scenes}.json
    python3 m0/style_bench.py --dry-run [--prompts]      # job count + GPU time estimate, nothing rendered
    python3 m0/style_bench.py [--only id1,id2] [--family watercolor,ink] [--scenes d_landscape] [--limit N]
    python3 m0/style_bench.py export curation.json       # → data/style_bench/curated_presets.json
    python3 m0/style_bench.py merge                      # dry-run diff of curated presets against data/styles.json

Render: out/style_bench/<candidate>/<scene>.png (832x1216, landscape scene 1216x832), a 512 px WebP thumb
<scene>.webp next to it for images WD14 rates safe, and out/style_bench/results.json (all paths relative to
out/style_bench). Resumable: an image whose PNG and record exist is skipped; one whose WD14 check failed
("unchecked") is re-tagged, not re-drawn. Jobs run grouped by checkpoint so ComfyUI loads each model once.
Honors out/PAUSE (waits) and WEBTOON_DEADLINE=HH:MM (stops, exit 3) like render.py.

Prompts come from prompts.build() over a synthetic world/storyboard panel (scenes.json), the candidate standing
in as the world's preset, so a benchmark image is what that preset would draw in a real episode.

Curation file (written by the gallery):
    {"candidates": {"<id>": {"verdict": "keep|drop|maybe", "stars": 1-5, "name": "...", "note": "...",
                             "preset_id": "<optional new key>"}}}
"""

import argparse
import copy
import difflib
import io
import json
import os
import sys
import time
from pathlib import Path

import comfy
import prompts
from common import DATA, OUT, COMFY_URL, http, http_json, load_json, save_json, wd14_tag
from render import safety

BENCH = DATA / "style_bench"
SEC_PER_IMAGE = 12.0      # SDXL 28 steps at 832x1216 on Spark
SEC_PER_SWITCH = 20.0     # checkpoint load when the next job uses another model
THUMB = 512
MAX_ERRORS = 5            # consecutive ComfyUI errors → ComfyUI is gone, stop
CURATION_KEYS = {"verdict", "stars", "name", "note", "preset_id"}
META_KEYS = {"id", "name", "family", "source", "audiences", "scenes_only", "lora_axis"}


# --- jobs ------------------------------------------------------------------------------------------------------

def preset_of(cand):
    return {k: v for k, v in cand.items() if k not in META_KEYS}


def allowed(cand, scene):
    if cand.get("scenes_only") and scene["id"] not in cand["scenes_only"]:
        return False
    return not scene["requires"] or bool(set(cand["audiences"]) & set(scene["requires"]))


def world_for(cand, scene):
    return {"id": f"w_bench_{scene['id']}", "audience": scene["audience"], "style_id": cand["id"],
            "characters": scene["characters"], "locations": scene["locations"]}


def build(cand, scene, styles):
    st = {**styles, "presets": {cand["id"]: preset_of(cand)}}
    return prompts.build(scene["panel"], world_for(cand, scene), st, cand["id"], sfw=True)


def make_jobs(cands, scenes, styles):
    jobs = []
    for c in sorted(cands, key=lambda c: (c["checkpoint"], c["id"])):
        for s in scenes:
            if allowed(c, s):
                jobs.append({"cand": c, "scene": s, "seed": s["seed"], "p": build(c, s, styles)})
    return jobs


def estimate(jobs, sec=SEC_PER_IMAGE):
    switches = len({j["cand"]["checkpoint"] for j in jobs})
    return len(jobs) * sec + switches * SEC_PER_SWITCH


def fmt_time(s):
    return f"{int(s // 3600)} h {int(s % 3600 // 60):02d} min" if s >= 3600 else f"{int(s // 60)} min {int(s % 60):02d} s"


# --- results.json ----------------------------------------------------------------------------------------------

def rel(cid, scene, ext):
    return f"{cid}/{scene}.{ext}"


def load_results(out):
    f = out / "results.json"
    return load_json(f) if f.exists() else {}


def write_results(out, cands, scenes, images, missing=None):
    """Whole file every time (atomic), so a gallery can read it mid-run."""
    by_c = {}
    for r in images.values():
        by_c.setdefault(r["candidate"], []).append(r["scene"])
    doc = {
        "_note": "m0/style_bench.py — paths are relative to this file's directory. thumb is null for images that "
                 "are unsafe/unchecked/error: show thumbs only.",
        "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "scenes": {s["id"]: {"name": s["name"], "seed": s["seed"], "orientation": s["orientation"],
                             "requires": s["requires"]} for s in scenes},
        "candidates": {c["id"]: {"name": c["name"], "family": c["family"], "source": c["source"],
                                 "checkpoint": c["checkpoint"], "audiences": c["audiences"],
                                 "artist_tags": c["artist_tags"], "aesthetic_tags": c["aesthetic_tags"],
                                 "loras": c.get("loras") or [], "lora_axis": c.get("lora_axis"),
                                 "scenes": [s["id"] for s in scenes if allowed(c, s)],
                                 "rendered": sorted(by_c.get(c["id"], []))} for c in cands},
        "missing_models": missing or {},  # candidates skipped this run: checkpoint/LoRA not on ComfyUI
        "images": sorted(images.values(), key=lambda r: (r["candidate"], r["scene"])),
    }
    tmp = out / "results.json.tmp"
    save_json(tmp, doc)
    os.replace(tmp, out / "results.json")


def thumb(png, dst):
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGB")
    im.thumbnail((THUMB, THUMB), Image.LANCZOS)
    im.save(dst, "WEBP", quality=82, method=6)


def check(rec, png, out, scene):
    """WD14 rating + safety → updates rec, writes or removes the thumb."""
    t = out / rel(rec["candidate"], rec["scene"], "webp")
    try:
        tags = wd14_tag(png)
    except Exception as e:  # WD14 down: keep the image, no thumb, retag on the next run
        rec.update(status="unchecked", rating=None, unsafe=None, thumb=None, error=f"wd14: {e}"[:300])
        t.unlink(missing_ok=True)
        return
    bad = safety(tags, scene["audience"])
    rec.update(rating={k: round(v, 3) for k, v in tags.get("rating", {}).items()}, unsafe=bad or None)
    rec.pop("error", None)
    if bad:
        rec.update(status="unsafe", thumb=None)
        t.unlink(missing_ok=True)  # never a thumb of an unsafe image
    else:
        thumb(png, t)
        rec.update(status="ok", thumb=t.relative_to(out).as_posix())


# --- preflight -------------------------------------------------------------------------------------------------

def available_models():
    """{"checkpoints": set, "loras": set} from ComfyUI /object_info."""
    def names(node, field):
        info = http_json("GET", f"{COMFY_URL}/object_info/{node}", timeout=30)
        return set(info[node]["input"]["required"][field][0])
    return {"checkpoints": names("CheckpointLoaderSimple", "ckpt_name"), "loras": names("LoraLoader", "lora_name")}


def missing_models(cand, models):
    miss = [cand["checkpoint"]] if cand["checkpoint"] not in models["checkpoints"] else []
    return miss + [l for l, _ in cand.get("loras") or [] if l not in models["loras"]]


def free_gpu():
    try:
        http("POST", f"{COMFY_URL}/free", {"unload_models": True, "free_memory": True}, timeout=30)
    except Exception as e:
        print(f"/free failed: {e}")


# --- run -------------------------------------------------------------------------------------------------------

def select(cands, args):
    if args.only:
        ids = args.only.split(",")
        unknown = [i for i in ids if i not in {c["id"] for c in cands}]
        if unknown:
            raise SystemExit(f"unknown candidate ids: {unknown}")
        cands = [c for c in cands if c["id"] in ids]
    if args.family:
        cands = [c for c in cands if c["family"] in args.family.split(",")]
    if args.checkpoint:
        cands = [c for c in cands if any(k in c["checkpoint"] for k in args.checkpoint.split(","))]
    return cands


def cmd_run(args):
    out = Path(args.out)
    cands_all = load_json(BENCH / "candidates.json")["candidates"]
    scenes = load_json(BENCH / "scenes.json")["scenes"]
    styles = load_json(DATA / "styles.json")
    cands = select(cands_all, args)
    run_scenes = [s for s in scenes if not args.scenes or s["id"] in args.scenes.split(",")]
    jobs = make_jobs(cands, run_scenes, styles)

    old = load_results(out)
    images = {(r["candidate"], r["scene"]): r for r in old.get("images", [])}
    done = {k for k, r in images.items() if r.get("status") in ("ok", "unsafe") and (out / r["file"]).exists()}
    pending = [j for j in jobs if (j["cand"]["id"], j["scene"]["id"]) not in done]
    n_done = len(jobs) - len(pending)
    if args.limit:
        pending = pending[:args.limit]

    n_by_scene = {s["id"]: sum(j["scene"]["id"] == s["id"] for j in jobs) for s in run_scenes}
    print(f"{len(cands)} candidates × scenes → {len(jobs)} images {n_by_scene}; {n_done} done, "
          f"{len(pending)} to render{f' (--limit {args.limit})' if args.limit else ''} → {out}")
    print(f"estimate: {fmt_time(estimate(pending, args.sec))} for {len(pending)} images "
          f"({args.sec:g} s/image + {SEC_PER_SWITCH:g} s per checkpoint load, "
          f"{len({j['cand']['checkpoint'] for j in pending})} checkpoints); all {len(jobs)}: {fmt_time(estimate(jobs, args.sec))}")
    if args.dry_run:
        if args.prompts:
            for j in pending:
                p = j["p"]
                print(f"\n[{j['cand']['id']} / {j['scene']['id']} seed={j['seed']} {p['width']}x{p['height']}]"
                      f"\n+ {p['positive']}\n- {p['negative']}")
        return 0
    if not pending:
        write_results(out, cands_all, scenes, images)
        return 0
    if not comfy.is_up():
        raise SystemExit("ComfyUI is not reachable — run through sparkctl exec (see the report / README).")

    models = available_models()
    skip = {}
    for c in {j["cand"]["id"]: j["cand"] for j in pending}.values():
        miss = missing_models(c, models)
        if miss:
            skip[c["id"]] = miss
            print(f"skip {c['id']}: missing {miss}")
    pending = [j for j in pending if j["cand"]["id"] not in skip]

    out.mkdir(parents=True, exist_ok=True)
    errors = 0
    stats = {"ok": 0, "unsafe": 0, "unchecked": 0, "error": 0}
    for n, j in enumerate(pending, 1):
        c, s, p = j["cand"], j["scene"], j["p"]
        key = (c["id"], s["id"])
        if os.environ.get("WEBTOON_DEADLINE") and time.strftime("%H:%M") >= os.environ["WEBTOON_DEADLINE"]:
            print(f"deadline {os.environ['WEBTOON_DEADLINE']} reached, stopping (resume later)")
            return 3
        while (OUT / "PAUSE").exists():
            time.sleep(20)
        f = out / rel(c["id"], s["id"], "png")
        rec = {"candidate": c["id"], "scene": s["id"], "seed": j["seed"], "checkpoint": c["checkpoint"],
               "family": c["family"], "width": p["width"], "height": p["height"], "file": f.relative_to(out).as_posix(),
               "thumb": None, "positive": p["positive"], "negative": p["negative"]}
        prev = images.get(key)
        if prev and prev.get("status") == "unchecked" and f.exists():  # drawn already, only WD14 missed it
            rec.update(seconds=prev.get("seconds"), rendered_at=prev.get("rendered_at"))
            png = f.read_bytes()
        else:
            t0 = time.time()
            try:
                g = comfy.workflow(p["positive"], p["negative"], p["width"], p["height"], j["seed"], p["preset"],
                                   f"style_bench/{c['id']}/{s['id']}")
                png = comfy.run(g)[0]
            except Exception as e:
                errors += 1
                stats["error"] += 1
                rec.update(status="error", error=str(e)[:500], seconds=round(time.time() - t0, 1))
                images[key] = rec
                write_results(out, cands_all, scenes, images, skip)
                print(f"[{n}/{len(pending)}] {c['id']} / {s['id']} ERROR {e}"[:300])
                if errors >= MAX_ERRORS:
                    print(f"{MAX_ERRORS} errors in a row, stopping")
                    return 2
                continue
            errors = 0
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(png)
            rec.update(seconds=round(time.time() - t0, 1), rendered_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
        check(rec, png, out, s)
        stats[rec["status"]] += 1
        images[key] = rec
        write_results(out, cands_all, scenes, images, skip)
        print(f"[{n}/{len(pending)}] {c['id']} / {s['id']} {rec['status']} {rec.get('seconds')} s"
              + (f" unsafe={rec['unsafe']}" if rec.get("unsafe") else ""))
    write_results(out, cands_all, scenes, images, skip)
    free_gpu()
    print(json.dumps({"images": {"ok": stats["ok"], "failed": stats["unsafe"] + stats["error"] + stats["unchecked"]}}))
    return 0


# --- export / merge --------------------------------------------------------------------------------------------

def best_thumb(results, cid):
    for r in results.get("images", []):  # scene order a, b, c, d: the first safe one
        if r["candidate"] == cid and r.get("thumb"):
            return r["thumb"]
    return None


def cmd_export(args):
    cur = load_json(args.curation)
    entries = cur.get("candidates")
    if not isinstance(entries, dict):
        raise SystemExit('curation JSON needs {"candidates": {"<id>": {...}}}')
    cands = {c["id"]: c for c in load_json(BENCH / "candidates.json")["candidates"]}
    errs = []
    for cid, e in entries.items():
        if cid not in cands:
            errs.append(f"{cid}: unknown candidate")
            continue
        if e.get("verdict") not in ("keep", "drop", "maybe"):
            errs.append(f"{cid}: verdict must be keep|drop|maybe, got {e.get('verdict')!r}")
        if "stars" in e and e["stars"] is not None and not (isinstance(e["stars"], int) and 1 <= e["stars"] <= 5):
            errs.append(f"{cid}: stars must be 1–5")
        if set(e) - CURATION_KEYS:
            errs.append(f"{cid}: unknown keys {sorted(set(e) - CURATION_KEYS)}")
    if errs:
        raise SystemExit("curation errors:\n  " + "\n  ".join(errs))

    verdicts = {"keep"} | ({"maybe"} if args.include_maybe else set())
    keep = [cid for cid, e in entries.items() if e["verdict"] in verdicts and (e.get("stars") or 0) >= args.min_stars]
    keep.sort(key=lambda cid: (-(entries[cid].get("stars") or 0), cid))  # best first, stable
    results = load_results(Path(args.results_dir))
    presets, meta = {}, {}
    for cid in keep:
        e, c = entries[cid], cands[cid]
        pid = e.get("preset_id") or cid
        if pid in presets:
            raise SystemExit(f"preset id {pid} used twice")
        presets[pid] = preset_of(c)
        meta[pid] = {"candidate": cid, "name": e.get("name") or c["name"], "stars": e.get("stars"),
                     "note": e.get("note", ""), "verdict": e["verdict"], "family": c["family"], "source": c["source"],
                     "audiences": c["audiences"], "preview": best_thumb(results, cid)}
    save_json(args.out, {
        "_note": "m0/style_bench.py export — `presets` has the exact data/styles.json preset shape (merge into "
                 "styles.json → presets); `_curation` is metadata (name, stars, audiences, preview thumb relative "
                 "to out/style_bench/).",
        "presets": presets, "_curation": meta})
    print(f"{len(presets)} presets ({', '.join(presets) or '-'}) → {args.out}")
    counts = {v: sum(e["verdict"] == v for e in entries.values()) for v in ("keep", "maybe", "drop")}
    print(f"curation: {counts}, {len(cands) - len(entries)} candidates not rated")
    return 0


def preset_diff(old, new):
    keys = list(dict.fromkeys([*old, *new]))
    return [f"    {k}: {json.dumps(old.get(k), ensure_ascii=False)} → {json.dumps(new.get(k), ensure_ascii=False)}"
            for k in keys if old.get(k) != new.get(k)]


def cmd_merge(args):
    styles = load_json(DATA / "styles.json")
    curated = load_json(args.curated)["presets"]
    merged = copy.deepcopy(styles)
    added, changed, same = [], [], []
    for pid, p in curated.items():
        old = styles["presets"].get(pid)
        if old is None:
            added.append(pid)
        elif old == p:
            same.append(pid)
            continue
        else:
            changed.append(pid)
            print(f"~ {pid}\n" + "\n".join(preset_diff(old, p)))
        merged["presets"][pid] = p
    for pid in added:
        p = curated[pid]
        print(f"+ {pid}: {p['checkpoint']} | {', '.join(p['artist_tags'] + p['aesthetic_tags'])}"
              + (f" | loras {p['loras']}" if p.get("loras") else ""))
    print(f"\n{len(added)} new, {len(changed)} changed, {len(same)} unchanged → presets {len(styles['presets'])} → "
          f"{len(merged['presets'])}")
    if args.unified:
        a = json.dumps(styles, ensure_ascii=False, indent=2).splitlines()
        b = json.dumps(merged, ensure_ascii=False, indent=2).splitlines()
        sys.stdout.writelines(l + "\n" for l in difflib.unified_diff(a, b, "data/styles.json", "data/styles.json (merged)",
                                                                    lineterm=""))
    print("dry-run: data/styles.json not modified")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in ("run", "export", "merge"):
        argv.insert(0, "run")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="render (default)")
    r.add_argument("--dry-run", action="store_true")
    r.add_argument("--prompts", action="store_true", help="with --dry-run: print every prompt")
    r.add_argument("--only", help="comma separated candidate ids")
    r.add_argument("--family", help="comma separated families")
    r.add_argument("--checkpoint", help="comma separated substrings of checkpoint file names")
    r.add_argument("--scenes", help="comma separated scene ids")
    r.add_argument("--limit", type=int, default=0, help="render at most N images this run")
    r.add_argument("--sec", type=float, default=SEC_PER_IMAGE, help="seconds per image for the estimate")
    r.add_argument("--out", default=str(OUT / "style_bench"))
    e = sub.add_parser("export", help="curation JSON → curated_presets.json")
    e.add_argument("curation")
    e.add_argument("--out", default=str(BENCH / "curated_presets.json"))
    e.add_argument("--results-dir", default=str(OUT / "style_bench"), help="for the preview thumb")
    e.add_argument("--include-maybe", action="store_true")
    e.add_argument("--min-stars", type=int, default=0)
    m = sub.add_parser("merge", help="dry-run diff of curated presets against data/styles.json")
    m.add_argument("--curated", default=str(BENCH / "curated_presets.json"))
    m.add_argument("--unified", action="store_true", help="also print a unified diff of styles.json")
    args = ap.parse_args(argv)
    return {"run": cmd_run, "export": cmd_export, "merge": cmd_merge}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
