"""Free-form screenplay → storyboard JSON via a local LLM (skills/storyboard-writer), or visual QA of a rendered story.

    python3 m0/adapt.py --id rl_01_santorini --style fashion_editorial scenare/santorini.md [--dry-run]
    python3 m0/adapt.py --audience kids --id lx_k2_01 data/scripts/kids2/k2_01.md   # kids adventure (story.kids.schema.json)
    python3 m0/adapt.py --qa out/romance/rl_01_santorini          # contact sheet → list of panels to redo

Model: any OpenAI-compatible chat endpoint (WEBTOON_LLM, WEBTOON_LLM_MODEL; CF Access headers when set).
`response_format: json_schema` is sent for guided decoding (vLLM/xgrammar); the same schema plus the rule
checks of rules/storyboard.yaml (engine: m0/rules.py) validate the answer locally. Writes data/stories/<id>/{world,storyboard}.json in the m0 format
used by stories_romance.py, so render.py / run_romance.sh work unchanged.
"""

import argparse
import base64
import io
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

import rules
from common import DATA, LLM_MODEL, LLM_URL, load_json, save_json, split_tags, vocab as common_vocab

SKILL = Path(os.environ.get("WEBTOON_SKILL_DIR") or Path(__file__).resolve().parent.parent / "skills" / "storyboard-writer")
# Every rule below lives in rules/storyboard.yaml (why each exists is commented there); the names stay for importers.
R = rules.load("storyboard")
ENGINE = rules.storyboard()
SHOTS, KINDS, GAPS = R["shots"], R["bubble_kinds"], R["gaps"]
BANNED, AGE_BANNED, KIDS_SFW, KIDS_BANNED = (ENGINE.re[k] for k in ("banned", "age_banned", "kids_sfw", "kids_banned"))
FREE_AUDIENCE = R["adapt"]["free"]["audience"]
HUMAN_KINDS = set(R["human_kinds"])
AGE_BY_KIND = {k: v["regex"] for k, v in R["age_by_kind"].items()}
CF_ID, CF_SECRET = os.environ.get("WEBTOON_CF_ACCESS_ID"), os.environ.get("WEBTOON_CF_ACCESS_SECRET")


def chat(messages, schema=None, temperature=0.4, max_tokens=6000):
    # qwen36 runs with --reasoning-parser: thinking lands in reasoning_content, content stays JSON. Ask to skip it anyway.
    body = {"model": LLM_MODEL, "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
            "chat_template_kwargs": {"enable_thinking": False}}
    if schema:
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": schema["title"], "schema": schema, "strict": True}}
    req = urllib.request.Request(LLM_URL.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    if CF_ID and CF_SECRET:
        req.add_header("CF-Access-Client-Id", CF_ID)
        req.add_header("CF-Access-Client-Secret", CF_SECRET)
    if os.environ.get("WEBTOON_LLM_STREAM"):  # slow models: stream so the gateway's request timeout never fires
        body["stream"] = True
        req.data = json.dumps(body).encode()
        parts, reasoning = [], []
        with urllib.request.urlopen(req, timeout=1800) as r:
            for line in r:
                line = line.decode().strip()
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                delta = json.loads(line[6:])["choices"][0].get("delta", {})
                parts.append(delta.get("content") or "")
                reasoning.append(delta.get("reasoning_content") or "")
        # Nemotron's reasoning parser routes the whole answer to reasoning_content when thinking is off.
        content = "".join(parts) or "".join(reasoning)
    else:
        with urllib.request.urlopen(req, timeout=600) as r:
            msg = json.load(r)["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning_content") or ""
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    if os.environ.get("WEBTOON_ADAPT_DUMP"):
        d = Path(os.environ["WEBTOON_ADAPT_DUMP"])
        d.mkdir(parents=True, exist_ok=True)
        (d / f"last_raw_{os.getpid()}.txt").write_text(content)
    # First JSON object only: some models append a second copy or trailing text after it.
    return json.JSONDecoder().raw_decode(content[content.find("{"):])[0]


# --- adaptation ---------------------------------------------------------------------------------

def missing_fields(story, kids=False):
    """Required keys from story(.kids).schema.json, checked by hand (no jsonschema dependency): rules/storyboard.yaml `required`."""
    return ENGINE.missing_fields(story, kids)


def check(story, world_tags=None, free=False, audience="adult"):
    """Rule checks the schema cannot express (rules/storyboard.yaml `checks`). Returns a list of problems (empty = ok)."""
    return ENGINE.check(story, world_tags, free=free, audience=audience)


def to_m0(story, style, free=False, audience="adult"):
    """Lean model output → world.json + storyboard.json exactly as stories_romance.py (kids: stories_kids.py) writes them."""
    aud = rules.mode(free, audience)
    kids, M = aud == "kids", R["to_m0"]
    chars = []
    for c in story["characters"]:
        # kids: a creature/robot/spirit has no count tag, so prompts.count_tags() says "no humans" when it is alone
        human = c.get("kind", R["default_kind"]) in HUMAN_KINDS
        count = M["count_tag"]["f"] if c["gender"] == "f" else M["count_tag"]["other"]
        chars.append({"id": c["id"], "name": c["name"], "role": M["role"]["human" if human else "nonhuman"],
                      "count_tag": count if human else M["count_tag"]["nonhuman"], "human": human,
                      "description": c["photo"], "base": c["base"], "outfits": c["outfits"], "photo": c["photo"],
                      "tag_prompt": c["base"] + ", " + c["outfits"][R["required"]["outfit"]],
                      "identity_level": M["identity_level"], "reference_images": []})
    locs = [{"id": l["id"], "name": l["name"], "description": l["name"], "tag_prompt": l["tag_prompt"], "mood": ""}
            for l in story["locations"]]
    world = {"id": "w_" + story["id"], "title": story["title"], "synopsis": story["synopsis"],
             "tone": M["tone"]["kids" if kids else "adult"],
             "audience": audience, "language": M["language"], "style_id": style,
             "bible": {"rules": list(M["bible_rules"][aud]), "factions": []},
             **({"free": True} if free else {}),
             "canon": {"nodes": [], "constraints": [story["ending"]]},
             "permissions": {"allowed_locations": [l["id"] for l in locs]},
             "characters": chars, "locations": locs}
    panels = []
    for p in story["panels"]:
        tags = list(p["visual_tags"])
        if len(p["characters"]) == 2 and not kids:
            tags = list(M["couple_tags"]) + tags
        panels.append({"shot": p["shot"], "location_id": p["location_id"], "characters": p["characters"],
                       "visual_tags": tags, "bubbles": p["bubbles"],
                       "sfx": [{"text": s, "style": M["sfx_style"]} for s in p["sfx"]], "gap_after": p["gap_after"],
                       **({"animate": True, "motion": p["motion"]} if p.get("animate") and p.get("motion") else {})})
    # kids strips use compose.py's default (children's) fonts, like data/stories/les
    fonts = M["fonts"][aud]
    return world, {"title": story["title"], **({"fonts": fonts} if fonts else {}), "panels": panels}


def free_prompt(system):
    """adapt_system.md for --free: SFW passages out, adult-only rules in. Fails loudly when the skill text drifts."""
    F = R["adapt"]["free"]
    lines = system.splitlines()
    i = next(n for n, l in enumerate(lines) if l.startswith("AUDIENCE:"))
    lines[i] = FREE_AUDIENCE
    out = "\n".join(lines)
    s, e = out.index(F["cut"]["from"]), out.index(F["cut"]["to"])
    out = out[:s] + F["cut"]["heading"] + out[e:]
    for old, new in F["replace"]:
        assert old in out, f"adapt_system.md changed, update rules/storyboard.yaml adapt.free.replace: {old[:40]}"
        out = out.replace(old, new)
    return out


def adapt(args):
    A = R["adapt"]
    sel = "kids" if args.audience == "kids" else "adult"
    # kids: own schema, prompt and few-shot (skills/storyboard-writer/{schema/story.kids.schema.json,prompts/adapt_system_kids.md,examples/kids_park.*})
    schema = load_json(SKILL / "schema" / A["schema"][sel])
    system = (SKILL / "prompts" / A["system"][sel]).read_text().replace("{lang}", A["lang"])
    if args.free:
        system = free_prompt(system)
    example = A["example"][sel]
    ex_in = (SKILL / "examples" / f"{example}.input.md").read_text()
    ex_json = load_json(SKILL / "examples" / f"{example}.output.json")
    ex_out = json.dumps(ex_json, ensure_ascii=False)
    if args.free:  # the example must pass the free fence itself, or the model copies what it rejects
        for old, new in A["free"]["example_replace"]:
            ex_out = ex_out.replace(old, new)
    source = Path(args.source).read_text()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"id: {ex_json['id']}\n\nSCREENPLAY:\n{ex_in}"},
        {"role": "assistant", "content": ex_out},
        {"role": "user", "content": f"id: {args.id}\n\nSCREENPLAY:\n{source}"},
    ]
    if args.dry_run:
        print(json.dumps(messages, ensure_ascii=False, indent=1)[:4000], "...\n[dry-run] no model call")
        return
    vocab = common_vocab()  # WD14 general tags (+ EXTRA_TAGS); set(<the json dict>) was just its keys
    for attempt in range(args.attempts):
        try:
            story = chat(messages, schema=schema, temperature=A["temperature"]["first" if attempt == 0 else "retry"])
        except ValueError as e:  # not JSON at all (model ignored the schema): counts as a failed attempt
            print(f"attempt {attempt + 1}: invalid JSON: {e}")
            messages.append({"role": "user", "content": f"Your answer was not valid JSON ({e}). Return the full JSON object again, nothing else."})
            continue
        story["id"] = args.id
        if os.environ.get("WEBTOON_ADAPT_DUMP"):  # keep every raw attempt for A/B analysis
            save_json(Path(os.environ["WEBTOON_ADAPT_DUMP"]) / f"{args.id}.a{attempt + 1}.json", story)
        errs = check(story, vocab, free=args.free, audience=args.audience)
        if not errs:
            break
        print(f"attempt {attempt + 1}: {len(errs)} problems", *errs[:8], sep="\n  ")
        messages += [{"role": "assistant", "content": json.dumps(story, ensure_ascii=False)},
                     {"role": "user", "content": "Fix these problems and return the full corrected JSON:\n- " + "\n- ".join(errs)}]
    else:
        sys.exit("gave up: output never passed validation")
    world, sb = to_m0(story, args.style, free=args.free, audience=args.audience)
    d = DATA / "stories" / args.id
    save_json(d / "world.json", world)
    save_json(d / "storyboard.json", sb)
    print(f"{args.id}: {len(sb['panels'])} panels, {len(world['characters'])} characters, style {args.style} → {d}")


# --- visual QA ----------------------------------------------------------------------------------

def contact_sheet(run_dir, max_w=2000):
    """Numbered grid of p*_s0.png as one JPEG (one image per request: vLLM mm limit)."""
    from PIL import Image, ImageDraw
    files = sorted(run_dir.glob("p*_s0.png"))
    ims = []
    for f in files:
        im = Image.open(f).convert("RGB")
        im.thumbnail((400, 400))
        ImageDraw.Draw(im).text((6, 4), f.name[1:3].lstrip("0") or "0", fill="yellow")
        ims.append(im)
    cols = 4
    w = max(i.width for i in ims)
    h = max(i.height for i in ims)
    sheet = Image.new("RGB", (cols * w, -(-len(ims) // cols) * h), "white")
    for n, im in enumerate(ims):
        sheet.paste(im, ((n % cols) * w, (n // cols) * h))
    if sheet.width > max_w:
        sheet = sheet.resize((max_w, round(sheet.height * max_w / sheet.width)))
    buf = io.BytesIO()
    sheet.save(buf, "JPEG", quality=85)
    return buf.getvalue(), len(ims)


def qa(args):
    run_dir = Path(args.qa)
    sid = run_dir.name
    sb = load_json(DATA / "stories" / sid / "storyboard.json")
    jpg, n = contact_sheet(run_dir)
    prompt = (SKILL / "prompts" / "visual_qa.md").read_text()
    messages = [{"role": "system", "content": prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": f"Story {sid}, {n} panels. Storyboard:\n{json.dumps(sb['panels'], ensure_ascii=False)}"},
                    {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(jpg).decode()}}]}]
    if args.dry_run:
        (run_dir / "contact_sheet.jpg").write_bytes(jpg)
        print(f"[dry-run] sheet {len(jpg) // 1024} kB → {run_dir / 'contact_sheet.jpg'}")
        return
    verdict = chat(messages, temperature=0)
    save_json(run_dir / "qa.json", verdict)
    bad = [p for p in verdict.get("panels", []) if not p.get("ok", True)]
    for p in bad:
        print(f"p{p['n']:02d} {','.join(p.get('issues', []))}: {p.get('note', '')}")
    redo = ",".join(str(i) for i in verdict.get("redo", []))
    print(f"{sid}: {len(bad)}/{n} flagged; redo → m0/fix_panels.sh {sid}:{redo}" if redo else f"{sid}: all {n} panels ok")


PM = R["pick_motion"]
PICK_SCHEMA = {"title": "MotionPick", "type": "object", "additionalProperties": False, "required": ["panels"],
               "properties": {"panels": {"type": "array", "maxItems": R["limits"]["max_animated"], "items": {
                   "type": "object", "additionalProperties": False, "required": ["n", "motion"],
                   "properties": {"n": {"type": "integer", "minimum": 0},
                                  "motion": {"type": "string", "maxLength": PM["max_motion_chars"]}}}}}}


def pick_motion(args):
    """Existing (already rendered) storyboard → the model picks <= 2 panels to loop and writes their motion prompts."""
    d = DATA / "stories" / args.pick_motion
    sb = load_json(d / "storyboard.json")
    prompt = (SKILL / "prompts" / R["adapt"]["system"]["adult"]).read_text()
    rule = next(l for l in prompt.splitlines() if l.startswith(PM["rule_prefix"]))
    panels = [{"n": i, "shot": p["shot"], "people": len(p["characters"]), "tags": p["visual_tags"],
               "text": " / ".join(b["text"] for b in p["bubbles"])} for i, p in enumerate(sb["panels"])]
    messages = [{"role": "system", "content": PM["system"]
                 + rule.lstrip("- ") + "\nAnswer JSON: {\"panels\": [{\"n\": <panel index>, \"motion\": \"...\"}]}"},
                {"role": "user", "content": json.dumps(panels, ensure_ascii=False)}]
    if args.dry_run:
        print(json.dumps(messages, ensure_ascii=False, indent=1)[:3000])
        return
    for attempt in range(args.attempts):
        try:
            got = chat(messages, schema=PICK_SCHEMA, temperature=R["adapt"]["temperature"]["first" if attempt == 0 else "retry"]
                       )["panels"][:R["limits"]["max_animated"]]
        except (ValueError, KeyError) as e:
            print(f"attempt {attempt + 1}: invalid answer: {e}")
            continue
        errs = []
        for g in got:
            p = sb["panels"][g["n"]] if 0 <= g["n"] < len(sb["panels"]) else None
            if p is None:
                errs.append(f"panel {g['n']} does not exist")
            elif any(ENGINE.re[k].search(g["motion"]) for k in PM["banned"]):
                errs.append(f"panel {g['n']}: banned action in motion")
            elif len(p["characters"]) > 1 and not ENGINE.re["ambient_motion"].search(g["motion"]):
                errs.append(f"panel {g['n']}: two people may only get ambient motion")
        if not errs:
            break
        print(f"attempt {attempt + 1}:", *errs, sep="\n  ")
        messages.append({"role": "user", "content": "Fix: " + "; ".join(errs)})
    else:
        sys.exit("gave up")
    for p in sb["panels"]:
        p.pop("animate", None), p.pop("motion", None)
    for g in got:
        sb["panels"][g["n"]].update(animate=True, motion=g["motion"])
    save_json(d / "storyboard.json", sb)
    print(f"{args.pick_motion}: " + "; ".join(f"p{g['n']:02d} {g['motion']}" for g in got))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?", help="screenplay text file")
    ap.add_argument("--id", help="story id, e.g. rl_01_santorini")
    ap.add_argument("--style", help="preset from data/styles.json (default fashion_editorial; kids: clean_webtoon_noartist)")
    ap.add_argument("--audience", choices=["adult", "kids"], default="adult", help="kids: adventure strip for 6–12, story.kids.schema.json")
    ap.add_argument("--attempts", type=int, default=R["adapt"]["attempts"])
    ap.add_argument("--qa", help="rendered story dir (out/<day>/<id>) → visual QA instead of adaptation")
    ap.add_argument("--pick-motion", help="story id: let the model pick <= 2 rendered panels to animate")
    ap.add_argument("--free", action="store_true", help="experimental run outside the app: no SFW rules, adults only")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.free and args.audience == "kids":
        ap.error("--free is adults only, it cannot be combined with --audience kids")
    args.style = args.style or R["adapt"]["default_style"]["kids" if args.audience == "kids" else "adult"]
    if args.pick_motion:
        pick_motion(args)
    elif args.qa:
        qa(args)
    elif args.source and args.id:
        adapt(args)
    else:
        ap.error("either <source> with --id, or --qa <dir>")


if __name__ == "__main__":
    main()
