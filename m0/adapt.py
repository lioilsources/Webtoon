"""Free-form screenplay → storyboard JSON via a local LLM (skills/storyboard-writer), or visual QA of a rendered story.

    python3 m0/adapt.py --id rl_01_santorini --style fashion_editorial scenare/santorini.md [--dry-run]
    python3 m0/adapt.py --qa out/romance/rl_01_santorini          # contact sheet → list of panels to redo

Model: any OpenAI-compatible chat endpoint (WEBTOON_LLM, WEBTOON_LLM_MODEL; CF Access headers when set).
`response_format: json_schema` is sent for guided decoding (vLLM/xgrammar); the same schema plus the rule
checks below validate the answer locally. Writes data/stories/<id>/{world,storyboard}.json in the m0 format
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

from common import DATA, LLM_MODEL, LLM_URL, load_json, save_json

SKILL = Path(__file__).resolve().parent.parent / "skills" / "storyboard-writer"
SHOTS = ["establishing", "wide", "medium", "close-up", "over-shoulder"]
KINDS = ["speech", "thought", "shout", "narration"]
GAPS = ["small", "medium", "large"]
# Code-side SFW fence: these never appear in tags, outfits or photo sentences, whatever the model says.
BANNED = re.compile(r"\b(nude|naked|lingerie|underwear|bra|panties|bikini|swimsuit|swimwear|shirtless|topless|cleavage|"
                    r"see-through|wet shirt|crop top|midriff|breasts?|large breasts|short stature|loli|child|teen(ager)?|"
                    r"bed|lying|undress\w*|unzip\w*|open shirt|versace|chanel|prada|gucci|calvin klein|victoria'?s secret|"
                    r"dkny|armani|balenciaga|louboutin|dior|hermès|hermes|cartier|rolex)\b", re.I)
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
    with urllib.request.urlopen(req, timeout=600) as r:
        content = json.load(r)["choices"][0]["message"]["content"]
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    return json.loads(content)


# --- adaptation ---------------------------------------------------------------------------------

def check(story, world_tags=None):
    """Rule checks the schema cannot express. Returns a list of problems (empty = ok)."""
    errs = []
    chars = {c["id"]: c for c in story["characters"]}
    locs = {l["id"] for l in story["locations"]}
    for c in story["characters"]:
        for field in ("base", "photo", *c["outfits"].values()):
            m = BANNED.search(field)
            if m:
                errs.append(f"character {c['id']}: banned term '{m.group(0)}' in '{field[:50]}'")
        if re.search(r"\b(wearing|dress|shirt|coat|suit|jacket|trousers|heels|boots)\b", c["photo"], re.I):
            errs.append(f"character {c['id']}: photo sentence must not describe clothing")
        if not re.search(r"\baged (2[3-9]|[3-9]\d)\b", c["photo"]):
            errs.append(f"character {c['id']}: photo must state 'aged N' with N >= 23")
    panels = story["panels"]
    if panels[0]["shot"] != "establishing" or panels[0]["characters"]:
        errs.append("panel 0 must be an establishing shot without characters")
    if panels[-1]["gap_after"] != "large":
        errs.append("last panel must have gap_after 'large'")
    for i, p in enumerate(panels):
        if p["location_id"] not in locs:
            errs.append(f"panel {i}: unknown location {p['location_id']}")
        ids = [c["id"] for c in p["characters"]]
        for c in p["characters"]:
            if c["id"] not in chars:
                errs.append(f"panel {i}: unknown character {c['id']}")
            elif c.get("outfit") and c["outfit"] not in chars[c["id"]]["outfits"]:
                errs.append(f"panel {i}: {c['id']} has no outfit '{c['outfit']}'")
        genders = [chars[c]["gender"] for c in ids if c in chars]
        if len(genders) == 2 and genders[0] == genders[1]:
            errs.append(f"panel {i}: two characters of the same gender")
        if len(ids) == 2 and p["shot"] == "close-up":
            errs.append(f"panel {i}: a couple is never a close-up (collage risk)")
        if p["shot"] == "establishing" and ids:
            errs.append(f"panel {i}: establishing shot with characters")
        joined = ", ".join(p["visual_tags"]) + " " + " ".join(b["text"] for b in p["bubbles"])
        m = BANNED.search(", ".join(p["visual_tags"]))
        if m:
            errs.append(f"panel {i}: banned tag '{m.group(0)}'")
        for b in p["bubbles"]:
            if b["kind"] == "narration" and b["speaker_id"]:
                errs.append(f"panel {i}: narration must have empty speaker_id")
            if b["kind"] != "narration" and b["speaker_id"] not in ids:
                errs.append(f"panel {i}: speaker {b['speaker_id']} is not in the panel")
        if world_tags:
            unknown = [t for t in p["visual_tags"] if t not in world_tags and " " in t and len(t.split()) > 3]
            if unknown:
                errs.append(f"panel {i}: visual_tags look like sentences, not booru tags: {unknown}")
    return errs


def to_m0(story, style):
    """Lean model output → world.json + storyboard.json exactly as stories_romance.py writes them."""
    chars = []
    for c in story["characters"]:
        chars.append({"id": c["id"], "name": c["name"], "role": "playable",
                      "count_tag": "1girl" if c["gender"] == "f" else "1boy", "human": True,
                      "description": c["photo"], "base": c["base"], "outfits": c["outfits"], "photo": c["photo"],
                      "tag_prompt": c["base"] + ", " + c["outfits"]["default"],
                      "identity_level": "prompt", "reference_images": []})
    locs = [{"id": l["id"], "name": l["name"], "description": l["name"], "tag_prompt": l["tag_prompt"], "mood": ""}
            for l in story["locations"]]
    world = {"id": "w_" + story["id"], "title": story["title"], "synopsis": story["synopsis"],
             "tone": "romantický, něžný, s humorem", "audience": "adult", "language": "cs", "style_id": style,
             "bible": {"rules": ["SFW: polibek ano, nahota ne."], "factions": []},
             "canon": {"nodes": [], "constraints": [story["ending"]]},
             "permissions": {"allowed_locations": [l["id"] for l in locs]},
             "characters": chars, "locations": locs}
    panels = []
    for p in story["panels"]:
        tags = list(p["visual_tags"])
        if len(p["characters"]) == 2:
            tags = ["couple", "hetero"] + tags
        panels.append({"shot": p["shot"], "location_id": p["location_id"], "characters": p["characters"],
                       "visual_tags": tags, "bubbles": p["bubbles"],
                       "sfx": [{"text": s, "style": "bold"} for s in p["sfx"]], "gap_after": p["gap_after"]})
    return world, {"title": story["title"], "fonts": "romance", "panels": panels}


def adapt(args):
    schema = load_json(SKILL / "schema" / "story.schema.json")
    system = (SKILL / "prompts" / "adapt_system.md").read_text().replace("{lang}", "Czech")
    ex_in = (SKILL / "examples" / "santorini.input.md").read_text()
    ex_out = json.dumps(load_json(SKILL / "examples" / "santorini.output.json"), ensure_ascii=False)
    source = Path(args.source).read_text()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"id: rh_01_santorini\n\nSCREENPLAY:\n{ex_in}"},
        {"role": "assistant", "content": ex_out},
        {"role": "user", "content": f"id: {args.id}\n\nSCREENPLAY:\n{source}"},
    ]
    if args.dry_run:
        print(json.dumps(messages, ensure_ascii=False, indent=1)[:4000], "...\n[dry-run] no model call")
        return
    vocab = set(load_json(DATA / "wd14_tags.json")) if (DATA / "wd14_tags.json").exists() else None
    for attempt in range(args.attempts):
        story = chat(messages, schema=schema, temperature=0 if attempt == 0 else 0.5)
        story["id"] = args.id
        errs = check(story, vocab)
        if not errs:
            break
        print(f"attempt {attempt + 1}: {len(errs)} problems", *errs[:8], sep="\n  ")
        messages += [{"role": "assistant", "content": json.dumps(story, ensure_ascii=False)},
                     {"role": "user", "content": "Fix these problems and return the full corrected JSON:\n- " + "\n- ".join(errs)}]
    else:
        sys.exit("gave up: output never passed validation")
    world, sb = to_m0(story, args.style)
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source", nargs="?", help="screenplay text file")
    ap.add_argument("--id", help="story id, e.g. rl_01_santorini")
    ap.add_argument("--style", default="fashion_editorial", help="preset from data/styles.json")
    ap.add_argument("--attempts", type=int, default=3)
    ap.add_argument("--qa", help="rendered story dir (out/<day>/<id>) → visual QA instead of adaptation")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.qa:
        qa(args)
    elif args.source and args.id:
        adapt(args)
    else:
        ap.error("either <source> with --id, or --qa <dir>")


if __name__ == "__main__":
    main()
