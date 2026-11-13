#!/usr/bin/env python3
"""Story definitions (story.yaml, schema 2) for the strips that already exist, reverse-engineered from their
world.json + storyboard.json. Gamebooks need none: data/gamebooks/<id>/graph.yaml already is their definition.

    python3 tools/story_defs.py            # write data/stories/<id>/story.yaml for every strip, then check them
    python3 tools/story_defs.py --check    # only verify that every story.yaml rebuilds its storyboard panels
    python3 tools/story_defs.py rh_01_santorini lx_k2_01_x   # just these

A strip definition is the `panels` authoring level of PLAN-pipeline-go.md: every panel as the author (or the LLM
that wrote the strip) decided it, so `webtoon story --definition` redraws it without an LLM. Derived data is left
out and comes back from the pipeline: translations (title_i18n, bubbles[].i18n), face boxes (faces), WD14 tags,
the LLM's motion pick (motion_llm). Characters, locations and the bible stay in world.json (as a gamebook's world).
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
STORIES = ROOT / "data/stories"
DERIVED_PANEL = {"faces", "wd14_tags", "motion_llm"}
HEADER = ("schema", "id", "kind", "title", "world", "audience", "language", "style_id", "profile", "fonts", "music")


def flow(d):
    """One panel on one line, as the script lines in graph.yaml."""
    return yaml.safe_dump(d, default_flow_style=True, allow_unicode=True, width=100000, sort_keys=False).strip()


def panel_def(p):
    d = {"shot": p["shot"], "loc": p["location_id"]}
    if p["characters"]:  # who: ids; a character in another outfit than default is {id: outfit}
        d["who"] = [c["id"] if c.get("outfit", "default") == "default" else {c["id"]: c["outfit"]} for c in p["characters"]]
    d["tags"] = list(p["visual_tags"])
    if p["bubbles"]:
        d["bubbles"] = [{k: b[k] for k in ("speaker_id", "text", "kind") if k in b} for b in p["bubbles"]]
    if p["sfx"]:
        d["sfx"] = list(p["sfx"])
    d["gap"] = p["gap_after"]
    if p.get("animate"):
        d["animate"] = p.get("motion") or True
    return d


def panel_back(d):
    """story.yaml panel → storyboard.json panel (what the pipeline's build stage does for `panels`)."""
    p = {"shot": d["shot"], "location_id": d["loc"], "characters": [who_back(c) for c in d.get("who", [])],
         "visual_tags": list(d["tags"]), "bubbles": [dict(b) for b in d.get("bubbles", [])], "sfx": list(d.get("sfx", [])),
         "gap_after": d["gap"]}
    if d.get("animate"):
        p["animate"] = True
        p["motion"] = d["animate"] if isinstance(d["animate"], str) else ""
    return p


def who_back(c):
    if isinstance(c, dict):
        (cid, outfit), = c.items()
        return {"id": cid, "outfit": outfit}
    return {"id": c}


def normalized(p):
    q = {k: v for k, v in p.items() if k not in DERIVED_PANEL}
    q["characters"] = [c if c.get("outfit", "default") != "default" else {"id": c["id"]} for c in q["characters"]]
    q["bubbles"] = [{k: v for k, v in b.items() if k != "i18n"} for b in q["bubbles"]]
    if not q.get("animate"):
        q.pop("animate", None)
        q.pop("motion", None)
    return q


def definition(sid, world, sb):
    d = {"schema": 2, "id": sid, "kind": "strip", "title": sb["title"], "world": world["id"],
         "audience": world["audience"], "language": world["language"], "style_id": world["style_id"]}
    if world.get("profile"):
        d["profile"] = world["profile"]
    if sb.get("fonts"):
        d["fonts"] = sb["fonts"]
    d["music"] = "pool"  # a track from data/music by world hash (m0/shorts.py); gamebooks have their own
    return d


def write(sid):
    d = STORIES / sid
    world, sb = json.load(open(d / "world.json")), json.load(open(d / "storyboard.json"))
    head = yaml.safe_dump(definition(sid, world, sb), allow_unicode=True, sort_keys=False, width=1000)
    lines = [f"# {sb['title']}: strip definition reverse-engineered from world.json + storyboard.json (tools/story_defs.py).",
             "# Characters, locations and the bible: world.json. Translations, faces and WD14 tags are derived and left out.",
             head.rstrip(), "panels:"]
    lines += ["  - " + flow(panel_def(p)) for p in sb["panels"]]
    if sb.get("choices"):
        lines.append("choices:")
        lines += ["  - " + flow(c) for c in sb["choices"]]
    (d / "story.yaml").write_text("\n".join(lines) + "\n")


def check(sid):
    d = STORIES / sid
    sb, y = json.load(open(d / "storyboard.json")), yaml.safe_load((d / "story.yaml").read_text())
    want = [normalized(p) for p in sb["panels"]]
    got = [panel_back(p) for p in y["panels"]]
    if want != got:
        bad = next(i for i, (a, b) in enumerate(zip(want, got)) if a != b) if len(want) == len(got) else "count"
        return f"{sid}: panel {bad} differs"
    if (sb.get("choices") or []) != (y.get("choices") or []):
        return f"{sid}: choices differ"
    if y["world"] != json.load(open(d / "world.json"))["id"]:
        return f"{sid}: world id differs"
    return None


def strips():
    for d in sorted(STORIES.iterdir()):
        if not (d / "storyboard.json").exists():
            continue  # a gamebook's source world (louka, kovove_nebe, archion, …)
        if json.load(open(d / "world.json")).get("gamebook"):
            continue  # a gamebook node: defined by data/gamebooks/<id>/graph.yaml
        yield d.name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    ids = a.ids or list(strips())
    if not a.check:
        for sid in ids:
            write(sid)
    errs = [e for e in (check(sid) for sid in ids) if e]
    print(*errs, sep="\n", file=sys.stderr)
    print(f"{len(ids) - len(errs)}/{len(ids)} story.yaml rebuild their storyboard panels")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
