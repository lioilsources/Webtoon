"""Gamebook graph (data/gamebooks/<id>/graph.yaml, docs/gamebook.md) → one story per node, drawn like any strip.

    python3 m0/gamebook.py scripts data/gamebooks/sara/graph.yaml   # node screenplays → data/gamebooks/sara/scripts/<node>.md
    python3 m0/gamebook.py write   data/gamebooks/sara/graph.yaml   # adapt.py per node (LLM) → data/stories/gb_sara_<node>/
    python3 m0/gamebook.py unify   data/gamebooks/sara/graph.yaml   # the source world's characters and locations in every node
    m0/local_strip.sh -I -a kids gb_sara_n0 gb_sara_n1a ...          # render, loops, import (ids: `ids` below)
    python3 m0/gamebook.py ids     data/gamebooks/sara/graph.yaml

Every node is its own story gb_<id>_<node> (world w_gb_<id>_<node>), so render.py / local_strip.sh / import-demo work
unchanged. `unify` is what keeps the gamebook one book: the LLM invents characters per node, unify swaps them for the
source world's (same tag prompts, so Sára looks like Sára in every node) and gives each new location the same
tag prompt everywhere (the first node that drew it wins; kept in data/gamebooks/<id>/locations.json).
"""
import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import yaml

from common import DATA, ROOT, load_json, save_json


def load(graph):
    g = yaml.safe_load(Path(graph).read_text())
    g["_dir"] = Path(graph).resolve().parent
    return g


def story_id(g, node):
    return f"gb_{g['id']}_{node}"


def source_world(g):
    return load_json(DATA / "stories" / g["world"].removeprefix("w_") / "world.json")


def fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()


def script(g, node_id, world):
    """The node as a screenplay in the shape of data/scripts/kids*/: characters, then one line per beat."""
    n = g["nodes"][node_id]
    chars = {c["id"]: c for c in world["characters"]}
    locs = {l["id"]: l["name"] for l in world["locations"]} | {l["id"]: l["name"] for l in g.get("locations", [])}
    out = [f"# {n['title'].upper()}", "", f"(Gamebook „{g['title']}“, uzel {node_id}. {g['premise'].strip()})", "", "POSTAVY", ""]
    for cid in g["characters"]:
        out += [f"{chars[cid]['name'].upper()} – {chars[cid]['description']}.", ""]
    out += [f"SCÉNA – {locs.get(n['location'], n['location']).upper()}", ""]
    for b in n["beats"]:
        m = re.match(r"^([^:]{2,40}?)(?: \(([^)]*)\))?: (.+)$", b)
        who = m and next((c["name"] for c in chars.values() if fold(c["name"]).startswith(fold(m.group(1)))), None)
        if who:
            out += [f"{who.upper()}:" + (f" ({m.group(2)})" if m.group(2) else ""), f"„{m.group(3).strip(chr(34))}“", ""]
        else:
            out += [b, ""]
    if n.get("choices"):
        out += ["(Konec uzlu: čtenář volí — " + " / ".join(c["text"] for c in n["choices"]) + ". Volbu nekresli.)"]
    elif n.get("ending"):
        out += ["(Konec gamebooku.)" if n["ending"] == "good" else "(Konec této cesty — čtenář to zkusí znovu.)"]
    return "\n".join(out) + "\n"


def cmd_scripts(g):
    world = source_world(g)
    d = g["_dir"] / "scripts"
    d.mkdir(exist_ok=True)
    for node_id in g["nodes"]:
        (d / f"{node_id}.md").write_text(script(g, node_id, world), encoding="utf-8")
    print(f"{len(g['nodes'])} scripts → {d}")


def cmd_write(g):
    cmd_scripts(g)
    style = g.get("style_id") or source_world(g)["style_id"]
    failed = []
    for node_id in g["nodes"]:
        sid = story_id(g, node_id)
        if (DATA / "stories" / sid / "storyboard.json").exists():
            continue
        print(f"== {sid}", flush=True)
        r = subprocess.run([sys.executable, str(ROOT / "m0" / "adapt.py"), "--id", sid, "--style", style, "--audience", "kids",
                            "--profile", g.get("profile", "kids"), str(g["_dir"] / "scripts" / f"{node_id}.md")])
        if r.returncode:
            failed.append(sid)
    print("failed: " + " ".join(failed) if failed else "all nodes written")
    return 1 if failed else 0


def cmd_unify(g):
    src = source_world(g)
    by_name = {fold(c["name"]): c for c in src["characters"]}
    loc_file = g["_dir"] / "locations.json"
    locs = {l["id"]: l for l in src["locations"]}
    if loc_file.exists():
        locs |= {l["id"]: l for l in load_json(loc_file)}
    graph_locs = {fold(l["name"]): l for l in g.get("locations", [])} | {fold(l["name"]): l for l in src["locations"]}
    report = []
    for node_id, n in g["nodes"].items():
        d = DATA / "stories" / story_id(g, node_id)
        if not (d / "storyboard.json").exists():
            report.append(f"{node_id}: not written")
            continue
        world, sb = load_json(d / "world.json"), load_json(d / "storyboard.json")
        cmap, lmap, unknown = {}, {}, []
        for c in world["characters"]:
            hit = by_name.get(fold(c["name"])) or next((s for k, s in by_name.items() if k in fold(c["name"]) or fold(c["name"]) in k), None)
            if hit:
                cmap[c["id"]] = hit["id"]
            else:
                unknown.append(c["name"])
        for l in world["locations"]:
            hit = graph_locs.get(fold(l["name"]))
            lid = hit["id"] if hit else l["id"]
            lmap[l["id"]] = lid
            if lid not in locs:  # first node to draw a new location fixes its look for the whole book
                locs[lid] = {"id": lid, "name": hit["name"] if hit else l["name"], "description": hit.get("description", l["name"]) if hit else l["name"],
                             "tag_prompt": l["tag_prompt"], "mood": ""}
        if unknown:  # an invented character would be drawn differently in every node: write it again
            report.append(f"{node_id}: characters not in the source world: {', '.join(unknown)} — delete {d} and rerun write")
            continue
        for p in sb["panels"]:
            p["characters"] = [{**c, "id": cmap[c["id"]]} for c in p["characters"]]
            for b in p["bubbles"]:
                if b.get("speaker_id"):
                    b["speaker_id"] = cmap.get(b["speaker_id"], b["speaker_id"])
            p["location_id"] = lmap.get(p["location_id"], p["location_id"])
        used_c = {c["id"] for p in sb["panels"] for c in p["characters"]} | set(g["characters"])
        used_l = {p["location_id"] for p in sb["panels"]}
        world = {**src, "id": "w_" + story_id(g, node_id), "title": f"{g['title']} — {n['title']}",
                 "characters": [c for c in src["characters"] if c["id"] in used_c],
                 "locations": [locs[l] for l in sorted(used_l)],
                 "permissions": {**src.get("permissions", {}), "allowed_locations": sorted(used_l)},
                 "gamebook": {"id": g["id"], "node": node_id}}
        sb["title"] = n["title"]
        save_json(d / "world.json", world)
        save_json(d / "storyboard.json", sb)
        report.append(f"{node_id}: {len(sb['panels'])} panels, characters {sorted(set(cmap.values()))}, locations {sorted(used_l)}")
    save_json(loc_file, [l for l in locs.values() if l["id"] not in {s["id"] for s in src["locations"]}])
    print("\n".join(report))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scripts", "write", "unify", "ids"])
    ap.add_argument("graph")
    a = ap.parse_args()
    g = load(a.graph)
    if a.cmd == "ids":
        print(" ".join(story_id(g, n) for n in g["nodes"]))
        return 0
    return {"scripts": cmd_scripts, "write": cmd_write, "unify": cmd_unify}[a.cmd](g) or 0


if __name__ == "__main__":
    sys.exit(main())
