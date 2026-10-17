"""Story text → strip with the LLM on llm.ol1n.com wherever a model is needed — a quality test of those models.

    python3 kids/llm_story.py                                  # all kids/texts/*.txt, storyboard by the LLM
    python3 kids/llm_story.py --story 03_les --model bench-gemma --vl-model vl
    python3 kids/llm_story.py --storyboard hand                # hand-written kids/stories/*.json, VL check only

Where the LLM is called (each call logged with model, latency, raw reply → out/kids_llm/<run>/<story>/llm_log.jsonl):

  1. storyboard   story text → world (characters with booru tag_prompt + desc_en, locations) and 8 panels
                  in the kids/stories format; validated, rejected attempts go back with the errors
  2. tags         booru tags outside the WD14 vocabulary → existing tags (m0 translate_tags)
  3. check        the vision model looks at every rendered panel and says whether it shows the scene;
                  a panel under --min-score is re-rendered with a new seed (--retries times), the best kept

There is no fallback: a model that does not answer stops the run, so a bad strip never pretends to be
the model's work. Output: out/kids_llm/<run>/<story>.png + report.json (scores, attempts, timings).
"""

import argparse
import base64
import io
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("WEBTOON_LLM", "https://llm.ol1n.com/v1")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import make_strips  # noqa: E402  (sets up m0 on sys.path and the ComfyUI URL)
import common  # noqa: E402
import compose  # noqa: E402
from common import DATA, OUT, dedupe, filter_tags, http_json, load_json, save_json, split_tags  # noqa: E402
from PIL import Image  # noqa: E402

KIDS = Path(__file__).resolve().parent
SHOTS = ["establishing", "wide", "medium", "close-up"]
KINDS = ["speech", "shout", "thought", "narration"]

STORYBOARD = """You turn a short Czech children's story into a vertical webtoon storyboard for an SDXL anime model
(NoobAI-XL, Danbooru tags). Output strict JSON, nothing else:
{
  "world": {
    "id": "<slug>", "title": "<Czech title>",
    "characters": [{"id": "<slug>", "name": "<Czech name>",
                    "count_tag": "1girl" | "1boy" | null,      // null for animals and creatures
                    "tag_prompt": "<Danbooru design tags only: age (child), hair, eyes, clothes, species, colours>",
                    "desc_en": "<one English sentence: who it is and what it looks like>"}],
    "locations": [{"id": "<slug>", "tag_prompt": "<Danbooru tags: indoors/outdoors, place, time of day, lighting>"}]
  },
  "storyboard": {
    "title": "<Czech title>",
    "panels": [{
      "shot": "establishing" | "wide" | "medium" | "close-up",
      "location_id": "<location id>",
      "characters": [{"id": "<character id>"}],          // only who is visible; max 3
      "visual_tags": ["<Danbooru tags: pose, action, expression, props, camera>"],  // no hair/clothes, no names
      "scene_en": "<one English sentence describing exactly what the panel shows>",
      "bubbles": [{"kind": "speech" | "shout" | "thought" | "narration", "speaker": "<character id or null>", "text": "<Czech>"}],
      "sfx": [{"text": "<Czech onomatopoeia>"}],
      "gap_after": "small" | "medium" | "large"
    }]
  }
}
Rules:
- One panel per story beat (8 panels for a short story, up to 24 for a long one), covering every scene in order. Panel 0 is "establishing" with no characters.
- Keep every line of dialogue from the story VERBATIM in a bubble of its speaker (Czech, same punctuation).
  Story actions that are not dialogue (e.g. "Maxík štěká") become a short narration bubble or an sfx.
- Max 2 bubbles per panel. A panel with an animal only adds "no humans" to visual_tags.
- Children are drawn as children ("child" in tag_prompt), everything stays wholesome and friendly.
- Design tags (hair, eyes, clothes, colours) belong ONLY to tag_prompt so every panel draws the character the same."""

CHECK = """You review one panel of a children's picture-book webtoon before it is published.
The panel should show: {scene}
Characters that must be visible: {chars}
Answer strict JSON: {{"score": <0-10, how well the image shows the intended scene>,
  "missing": ["<intended element that is absent or wrong>"], "extra": ["<unwanted element, e.g. duplicated character>"],
  "safe_for_kids": true|false}}"""


class LLMLog:
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)

    def call(self, role, model, messages, temperature, max_tokens=6000):
        t0 = time.time()
        resp = http_json("POST", f"{common.LLM_URL}/chat/completions", {
            "model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}}, timeout=600)
        content = resp["choices"][0]["message"]["content"] or ""
        rec = {"role": role, "model": model, "served_by": resp.get("model"), "seconds": round(time.time() - t0, 1),
               "usage": resp.get("usage"), "reply": content}
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        try:
            return common._extract_json(content), rec
        except (ValueError, json.JSONDecodeError):
            return None, rec


def validate(data):
    errs = []
    try:
        world, panels = data["world"], data["storyboard"]["panels"]
        chars = {c["id"] for c in world["characters"]}
        locs = {l["id"] for l in world["locations"]}
    except (KeyError, TypeError) as e:
        return [f"missing key {e}"]
    if not 6 <= len(panels) <= 26:
        errs.append(f"{len(panels)} panels, expected 8-24")
    for c in world["characters"]:
        c["tag_prompt"] = ", ".join(split_tags(c.get("tag_prompt") or ""))
    for l in world["locations"]:
        l["tag_prompt"] = ", ".join(split_tags(l.get("tag_prompt") or ""))
    for i, p in enumerate(panels):
        p["visual_tags"] = split_tags(p.get("visual_tags") or [])
        if p.get("shot") not in SHOTS:
            errs.append(f"panel {i}: shot {p.get('shot')!r}")
        if p.get("location_id") not in locs:
            errs.append(f"panel {i}: unknown location {p.get('location_id')!r}")
        for c in p.get("characters", []):
            if c.get("id") not in chars:
                errs.append(f"panel {i}: unknown character {c.get('id')!r}")
        if p.get("shot") == "establishing" and p.get("characters"):
            p["shot"] = "wide"
        if not p.get("scene_en"):
            errs.append(f"panel {i}: scene_en missing")
        for b in p.get("bubbles", []):
            if b.get("kind") not in KINDS:
                b["kind"] = "speech"
        p.setdefault("gap_after", "medium")
    return errs


def llm_storyboard(text, model, log, attempts=3):
    feedback, history = "", []
    for attempt in range(attempts):
        data, rec = log.call("storyboard", model, [{"role": "system", "content": STORYBOARD},
                                                   {"role": "user", "content": text + feedback}], 0.6)
        errs = ["reply is not JSON"] if data is None else validate(data)
        history.append({"attempt": attempt, "seconds": rec["seconds"], "errors": errs})
        print(f"    storyboard attempt {attempt}: {rec['seconds']}s, {len(errs)} problems", flush=True)
        if not errs:
            return data, history
        feedback = "\n\nYOUR PREVIOUS ATTEMPT WAS REJECTED. Fix:\n- " + "\n- ".join(errs)
    raise RuntimeError(f"storyboard failed validation after {attempts} attempts: {history[-1]['errors']}")


def map_tags(data, model, log):
    """Out-of-vocabulary booru tags → known ones (one LLM call per story)."""
    common.LLM_MODEL = model
    fields = [(c, "tag_prompt") for c in data["world"]["characters"]] + \
             [(l, "tag_prompt") for l in data["world"]["locations"]]
    unknown = []
    for obj, key in fields:
        unknown += filter_tags(split_tags(obj.get(key, "")))[1]
    for p in data["storyboard"]["panels"]:
        unknown += filter_tags(split_tags(p.get("visual_tags", [])))[1]
    unknown = [u for u in dedupe(unknown) if u not in make_strips.KIDS_POS]
    if not unknown:
        return {}
    t0 = time.time()
    mapped = common.translate_tags(unknown)
    with open(log.path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"role": "tags", "model": model, "seconds": round(time.time() - t0, 1),
                             "in": unknown, "out": mapped}, ensure_ascii=False) + "\n")
    # Keep the original tag too: NoobAI knows many tags WD14 does not, the mapping only adds.
    for obj, key in fields:
        tags = split_tags(obj.get(key, ""))
        obj[key] = ", ".join(dedupe(tags + [m for t in tags for m in mapped.get(t, [])]))
    for p in data["storyboard"]["panels"]:
        tags = split_tags(p.get("visual_tags", []))
        p["visual_tags"] = dedupe(tags + [m for t in tags for m in mapped.get(t, [])])
    return mapped


def vl_check(png, panel, world, model, log):
    im = Image.open(io.BytesIO(png)).convert("RGB")
    im.thumbnail((768, 768))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    names = {c["id"]: c.get("desc_en") or c["name"] for c in world["characters"]}
    chars = "; ".join(names[c["id"]] for c in panel.get("characters", []) if c["id"] in names) or "none"
    prompt = CHECK.format(scene=panel.get("scene_en", ""), chars=chars)
    data, rec = log.call("check", model, [{"role": "user", "content": [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}}]}],
        0.1, max_tokens=800)
    if not data or "score" not in data:
        return {"score": None, "raw": rec["reply"][:300], "seconds": rec["seconds"]}
    data["seconds"] = rec["seconds"]
    return data


def run_story(name, args, styles, run_dir):
    sdir = run_dir / name
    log = LLMLog(sdir / "llm_log.jsonl")
    report = {"story": name, "storyboard": args.storyboard, "model": args.model, "vl_model": args.vl_model}
    sb_path = sdir / "storyboard.json"
    if sb_path.exists():
        data = load_json(sb_path)
    elif args.storyboard == "hand":
        data = load_json(KIDS / "stories" / f"{name}.json")
    else:
        text = (KIDS / "texts" / f"{name}.txt").read_text(encoding="utf-8")
        data, report["storyboard_attempts"] = llm_storyboard(text, args.model, log)
        report["tag_map"] = map_tags(data, args.model, log)
    save_json(sb_path, data)
    world, panels = data["world"], data["storyboard"]["panels"]

    report["panels"] = []
    for i, panel in enumerate(panels):
        f = sdir / f"p{i:02d}_s0.png"
        tries, best = [], None
        base = panel.get("seed", args.seed_base + i * 100)
        for k in range(args.retries + 1):
            seed = base + k * 17
            png, _ = make_strips.comfy_render(panel, world, styles, args.preset, seed)
            verdict = vl_check(png, panel, world, args.vl_model, log) if args.vl_model else {"score": None}
            tries.append({"seed": seed, **verdict})
            score = verdict.get("score")
            print(f"    p{i:02d} seed={seed} score={score} missing={verdict.get('missing')} extra={verdict.get('extra')}", flush=True)
            if best is None or (score or 0) > (best[1] or 0):
                best = (png, score)
            if score is None or score >= args.min_score:
                break
        f.write_bytes(best[0])
        report["panels"].append({"panel": i, "scene_en": panel.get("scene_en"), "final_score": best[1], "tries": tries})
        save_json(sdir / "report.json", report)

    strip = compose.compose(data["storyboard"], sdir, 0)
    out = run_dir / f"{name}.png"
    strip.save(out, optimize=True)
    scores = [p["final_score"] for p in report["panels"] if p["final_score"] is not None]
    report["mean_score"] = round(sum(scores) / len(scores), 2) if scores else None
    save_json(sdir / "report.json", report)
    print(f"  {out}  mean VL score {report['mean_score']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--story", action="append", help="file stem from kids/texts (default: all)")
    ap.add_argument("--storyboard", choices=["llm", "hand"], default="llm")
    ap.add_argument("--model", default=os.environ.get("WEBTOON_LLM_MODEL", "openclaw-default"))
    ap.add_argument("--vl-model", default="vl", help="empty string = no visual check")
    ap.add_argument("--min-score", type=float, default=7)
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--preset", default="clean_webtoon")
    ap.add_argument("--seed-base", type=int, default=7000)
    ap.add_argument("--run", default=None, help="run directory name (default: <storyboard>-<model>)")
    args = ap.parse_args()

    if not os.environ.get("CF_ACCESS_CLIENT_ID"):
        raise SystemExit("CF_ACCESS_CLIENT_ID / CF_ACCESS_CLIENT_SECRET are not set")
    styles = load_json(DATA / "styles.json")
    make_strips.check_checkpoint(styles["presets"][args.preset]["checkpoint"])
    names = args.story or sorted(p.stem for p in (KIDS / "texts").glob("*.txt"))
    run_dir = OUT / "kids_llm" / (args.run or f"{args.storyboard}-{args.model if args.storyboard == 'llm' else 'hand'}")
    for name in names:
        print(f"{name}:", flush=True)
        run_story(name, args, styles, run_dir)


if __name__ == "__main__":
    main()
