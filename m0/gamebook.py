"""Gamebook graph (data/gamebooks/<id>/graph.yaml, docs/gamebook.md) → one story per node, drawn like any strip.

    python3 m0/gamebook.py scripts data/gamebooks/sara/graph.yaml   # node screenplays → data/gamebooks/sara/scripts/<node>.md
    python3 m0/gamebook.py write   data/gamebooks/sara/graph.yaml   # adapt.py per node (LLM) → data/stories/gb_sara_<node>/
    python3 m0/gamebook.py draft   data/gamebooks/mlceni/graph.yaml # no LLM, word for word: lines → bubbles, directions → pictures
    python3 m0/gamebook.py unify   data/gamebooks/sara/graph.yaml   # the source world's characters and locations in every node
    m0/local_strip.sh -I -a kids gb_sara_n0 gb_sara_n1a ...          # render, loops, import (ids: `ids` below)
    python3 m0/gamebook.py ids     data/gamebooks/sara/graph.yaml
    python3 m0/gamebook.py import-branch data/gamebooks/sara/graph.yaml vetev.json --name t1   # a reader's branch → nodes

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
    g["_path"] = str(Path(graph).resolve())
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


# stage direction → what the panel shows: first matching pattern wins (shot, location, who: "" / a / p / ap, tags, gap)
DIRECTIONS = [
    (r"Zhasnutí|Zhasne se", ("wide", "l_poradna", "", ["dark room", "lights off", "darkness", "night", "no humans", "empty armchairs"], "large")),
    (r"zvuk hodin|^Hodiny|na hodiny", ("close-up", "l_poradna", "", ["wall clock", "clock hands", "no humans", "still life"], "medium")),
    (r"Prázdný pohled z okna", ("wide", "l_poradna_okno", "", ["no humans", "scenery"], "medium")),
    (r"z okna", ("medium", "l_poradna", "a", ["looking away", "from side", "window light"], "medium")),
    (r"Prázdné křeslo", ("wide", "l_poradna", "", ["empty armchair", "no humans"], "large")),
    (r"Detail sklenice|Sklenice se zastaví", ("close-up", "l_poradna", "", ["holding glass", "hand", "long sleeves", "glass of water"], "small")),
    (r"podívá na sklenici", ("medium", "l_poradna", "p", ["looking down", "calm expression"], "small")),
    (r"vrátí sklenici|Sklenici nechá|^Sklenice vody", ("close-up", "l_poradna", "", ["glass of water", "low table", "no humans", "still life"], "small")),
    (r"nalévá vodu", ("medium", "l_poradna", "p", ["pouring water", "glass of water"], "small")),
    (r"Obraz|obraz|stěně", ("medium", "l_poradna_obraz", "a", ["upper body", "from side", "standing", "looking at painting"], "medium")),
    (r"První stránka", ("close-up", "l_poradna", "", ["blank notebook", "empty white pages", "white paper", "minimalist", "no humans", "still life"], "medium")),
    (r"knihu na stolku|Kniha na stolku|ji pozoruje|zavře knihu|Položí knihu", ("close-up", "l_poradna", "", ["closed book", "book cover", "hardcover", "plain cover", "no humans", "still life"], "small")),
    (r"s knihou", ("medium", "l_poradna", "a", ["standing", "holding book"], "small")),
    (r"odejde|kabát", ("medium", "l_poradna", "a", ["long coat", "standing", "upper body", "from side"], "medium")),
    (r"rukávy", ("close-up", "l_poradna", "", ["hands", "long sleeves", "sleeves past fingers"], "small")),
    (r"kapesník", ("close-up", "l_poradna", "", ["hands", "long sleeves", "holding handkerchief"], "small")),
    (r"pero", ("close-up", "l_poradna", "", ["hand", "pen", "notebook", "low table"], "small")),
    (r"poznámky", ("medium", "l_poradna", "p", ["upper body", "sitting", "holding notebook", "looking down"], "small")),
    (r"brýle", ("medium", "l_poradna", "p", ["holding eyewear", "tired", "looking down"], "medium")),
    (r"ruce", ("close-up", "l_poradna", "", ["hands", "long sleeves", "looking at own hands"], "small")),
    (r"rozrušená", ("medium", "l_poradna", "a", ["standing", "upset", "coat"], "small")),
    (r"usměje", ("medium", "l_poradna", "p", ["upper body", "sitting", "slight smile"], "small")),
    (r"^Psycholog", ("medium", "l_poradna", "p", ["closed mouth", "looking down", "calm expression"], "medium")),
    (r"^Anna", ("medium", "l_poradna", "a", ["closed mouth", "serious", "looking down"], "medium")),
    (r"Pauza|ticho", ("wide", "l_poradna", "", ["no humans", "scenery", "two armchairs", "low table", "small room"], "medium")),
]
FACES = {"anna": [["serious", "looking away"], ["looking down", "serious"], ["looking at another", "guarded"]],
         "psycholog": [["calm expression", "looking at another"], ["tired", "slight smile"], ["looking at another", "thinking"]]}


def node_lines(n):
    """Beats → (speaker id or "" for narration, text) / (None, stage direction), in the order of the play."""
    who = {"Psycholog": "psycholog", "Anna": "anna", "Vyprávění": ""}
    for b in n["beats"]:
        m = re.match(r"(Psycholog|Anna|Vyprávění): (.*)", b)
        yield (who[m[1]], m[2].strip()) if m else (None, b)


def direction_panel(text, alone, default_loc):
    for pat, (shot, loc, cast, tags, gap) in DIRECTIONS:
        if re.search(pat, text):
            if alone:  # the last scene: he is alone in the room
                cast = cast.replace("a", "")
            if loc == "l_poradna":
                loc = default_loc
            return {"shot": shot, "location_id": loc, "characters": [{"id": {"a": "anna", "p": "psycholog"}[x]} for x in cast],
                    "visual_tags": tags, "bubbles": [], "sfx": [], "gap_after": gap, "animate": False, "motion": ""}
    sys.exit(f"no panel for the stage direction: {text}")


def draft_story(g, node_id, src):
    """Storyboard with no LLM: every line of the play is a bubble, word for word and in order; only the pictures are chosen."""
    n, panels, turn = g["nodes"][node_id], [], 0
    loc = n.get("location") or g["locations"][0]["id"]
    if loc != "l_poradna" and node_id not in ("o3a", "o6e"):
        loc = "l_poradna"
    lines = list(node_lines(n))
    alone = not any(s == "anna" for s, _ in lines)
    bubble = lambda s, t: {"speaker_id": s, "text": t, "kind": "speech" if s else "narration"}

    def spoken(chars, shot, tags, bubbles):
        cast = [{"id": c} for c in chars]
        # "l_poradna": the painting's tags end up printed on their clothes
        panels.append({"shot": shot, "location_id": "l_poradna", "characters": cast, "visual_tags": tags, "bubbles": bubbles,
                       "sfx": [], "gap_after": "small", "animate": False, "motion": ""})

    panels.append({"shot": "establishing", "location_id": "l_poradna", "characters": [], "visual_tags": ["no humans", "scenery", "two armchairs", "low table", "small room"],
                   "bubbles": [], "sfx": [], "gap_after": "medium", "animate": False, "motion": ""})
    i = 0
    while i < len(lines):
        s, t = lines[i]
        if s is None:
            if re.match(r"Malá poradna|Další setkání|Jiné odpoledne|Další týden", t) and len(panels) == 1:
                i += 1  # the establishing panel is this direction
                continue
            panels.append(direction_panel(t, alone, "l_poradna"))
            i += 1
        elif s == "":
            if panels[-1]["characters"] or panels[-1]["bubbles"]:
                panels.append(direction_panel("Pauza", alone, "l_poradna") if not alone else {**panels[0], "shot": "wide"})
                panels[-1] = {**panels[-1], "bubbles": []}
            panels[-1]["bubbles"] = panels[-1]["bubbles"] + [bubble("", t)]
            i += 1
        else:
            nxt = lines[i + 1] if i + 1 < len(lines) else (None, "")
            turn += 1  # every line in its speaker's own panel: never two people in one picture (Hassaku XL makes a couple of any two-shot)
            shot = "close-up" if turn % 2 else "medium"
            same = nxt[0] == s and len(t) + len(nxt[1]) < 110
            spoken([s], shot, ["upper body", "from front", "sitting"] + FACES[s][turn % 3], [bubble(s, t)] + ([bubble(s, nxt[1])] if same else []))
            i += 2 if same else 1
    for p in panels:  # at most one ambient loop per node, and only in an empty picture
        if not p["characters"] and "wall clock" not in p["visual_tags"] and p["shot"] == "wide" and "dark room" not in p["visual_tags"]:
            p["animate"], p["motion"] = True, "ambient only, soft light slowly moving, thin curtain swaying, static camera"
            break
    panels[-1]["gap_after"] = "large"
    locs = [l for l in src["locations"]]
    return {"id": story_id(g, node_id), "title": n["title"], "synopsis": g["premise"].strip()[:230], "ending": src["canon"]["constraints"][0],
            "characters": [{"id": c["id"], "name": c["name"], "gender": c["gender"], "base": c["base"], "outfits": c["outfits"], "photo": c["photo"]}
                           for c in src["characters"]],
            "locations": [{"id": l["id"], "name": l["name"], "tag_prompt": l["tag_prompt"]} for l in locs], "panels": panels}


def split_line(t, limit=150):
    """A long line → bubbles of whole sentences, word for word and in order (one speaker, one panel)."""
    if len(t) <= limit:
        return [t]
    parts, cur = [], ""
    for s in re.split(r"(?<=[.!?…])\s+", t):
        if cur and len(cur) + 1 + len(s) > limit:
            parts.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    return parts + ([cur] if cur else [])


def script_story(g, node_id, src):
    """Storyboard from a node's structured `script` (graph `draft` section): `say` = a line in its speaker's own panel,
    `see` = a stage direction as a picture. Every line word for word, never two people in one picture."""
    n, d = g["nodes"][node_id], g["draft"]
    cast, loc0, panels, turn = n["cast"], n["location"], [], 0
    bubble = lambda s, t: {"speaker_id": s, "text": t, "kind": "speech" if s else "narration"}
    for e in n["script"]:
        loc = e.get("loc", loc0)
        if "say" in e:
            turn += 1
            cid = cast[e["say"]]
            shot = e.get("shot") or ("close-up" if turn % 2 else "medium")
            tags = d["speaking"] + e.get("tags", d["faces"][e["say"]][turn % 3])
            panels.append({"shot": shot, "location_id": loc, "characters": [{"id": cid}], "visual_tags": tags,
                           "bubbles": [bubble(cid, t) for t in split_line(e["text"])], "sfx": [], "gap_after": e.get("gap", "small"),
                           "animate": bool(e.get("animate")), "motion": e.get("animate", "")})
        else:
            who = [{"id": cast[e["who"]]}] if e.get("who") else []
            tags = e.get("tags", []) + ([] if who else ["no humans"] if "hand" not in " ".join(e.get("tags", [])) else [])
            panels.append({"shot": e.get("shot", "medium"), "location_id": loc, "characters": who, "visual_tags": tags,
                           "bubbles": [], "sfx": [], "gap_after": e.get("gap", "medium"),
                           "animate": bool(e.get("animate")), "motion": e.get("animate", "")})
    panels[-1]["gap_after"] = "large"
    used = {c["id"] for p in panels for c in p["characters"]}
    chars = [c for c in src["characters"] if c["id"] in used]
    return {"id": story_id(g, node_id), "title": n["title"], "synopsis": g["premise"].strip()[:230], "ending": src["canon"]["constraints"][0],
            "characters": [{"id": c["id"], "name": c["name"], "gender": c["gender"], "base": c["base"], "outfits": c["outfits"], "photo": c["photo"]}
                           for c in chars],
            "locations": [{"id": l["id"], "name": l["name"], "tag_prompt": l["tag_prompt"]} for l in src["locations"]
                          if l["id"] in {p["location_id"] for p in panels}], "panels": panels}


def cmd_draft(g):
    """`write` for a text that must stay word for word (profile drama): no LLM, then `unify` as usual.
    Nodes with a `script` are complete here (their world uses the source world's characters by id; no unify)."""
    sys.path.insert(0, str(ROOT / "m0"))
    import adapt
    src, style, failed = source_world(g), g["style_id"], False
    for node_id, n in g["nodes"].items():
        if "script" in n:
            story = script_story(g, node_id, src)
            # max_animated guards the LLM's picks; loops written into the script are the author's choice
            # (animate.py --force draws them all)
            unlooped = {**story, "panels": [{**p, "animate": False} for p in story["panels"]]}
            errs = adapt.check(unlooped, adapt.common_vocab(), profile=g["profile"])
            if errs:
                failed = True
                print(node_id, *errs[:8], sep="\n  ")
                continue
            world, sb = adapt.to_m0(story, style, profile=g["profile"])
            used_c = {c["id"] for p in sb["panels"] for c in p["characters"]}
            used_l = sorted({p["location_id"] for p in sb["panels"]})
            world = {**src, "id": "w_" + story["id"], "title": f"{g['title']} — {n['title']}",
                     "characters": [c for c in src["characters"] if c["id"] in used_c],
                     "locations": [l for l in src["locations"] if l["id"] in used_l],
                     "permissions": {**src.get("permissions", {}), "allowed_locations": used_l},
                     "gamebook": {"id": g["id"], "node": node_id}}
            sb["title"] = n["title"]
            d = DATA / "stories" / story["id"]
            save_json(d / "world.json", world)
            save_json(d / "storyboard.json", sb)
            print(f"{node_id}: {len(sb['panels'])} panels, {sum(len(p['bubbles']) for p in sb['panels'])} bubbles")
            continue
        story = draft_story(g, node_id, src)
        errs = adapt.check(story, adapt.common_vocab(), profile=g["profile"])
        if errs:
            failed = True
            print(node_id, *errs[:6], sep="\n  ")
            continue
        world, sb = adapt.to_m0(story, style, profile=g["profile"])
        d = DATA / "stories" / story["id"]
        save_json(d / "world.json", world)
        save_json(d / "storyboard.json", sb)
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


def episode_nodes(g):
    """Exported episode id → (node, its storyboard): local_strip.sh leaves out/local/<story>/episode_id."""
    out = {}
    for node_id in g["nodes"]:
        sid = story_id(g, node_id)
        f = ROOT / "out" / "local" / sid / "episode_id"
        sb = DATA / "stories" / sid / "storyboard.json"
        if f.exists() and sb.exists():
            out[f.read_text().strip()] = (node_id, load_json(sb))
    return out


def branch_beats(bn, eps, names):
    """One beat per panel of a reader's branch node: the picture it reuses, then its bubbles."""
    beats, loc = [], None
    for bp in bn.get("panels", []):
        src = eps.get(bp["episode"])
        if src is None:
            beats.append("(obraz z neznámé epizody) " + " / ".join(b["text"] for b in bp.get("bubbles", [])))
            continue
        node_id, sb = src
        p = sb["panels"][bp["panel"]] if bp["panel"] < len(sb["panels"]) else {}
        loc = loc or p.get("location_id")
        who = ", ".join(names.get(c["id"], c["id"]) for c in p.get("characters", []))
        pic = f"(obraz jako {node_id} p{bp['panel']:02d}: {p.get('shot', '')}; {who}; {', '.join(p.get('visual_tags', []))})"
        said = [(f"{names.get(b.get('speaker_id'), b.get('speaker_id'))}: " if b.get("speaker_id") and b.get("kind") != "narration" else "")
                + b["text"] for b in bp.get("bubbles", [])]
        beats.append(pic + (" " + " / ".join(said) if said else ""))
    return beats, loc


def cmd_import_branch(g, path, name, out):
    """A reader's "Odeslat autorovi" JSON → new nodes appended to graph.yaml (ids <name>_<n>), and the reader's
    hooks as new choices of the official nodes. Each node keeps `origin` (review: true) until the author has read
    it: the text comes from a reader and is drawn for children only after that review."""
    br = json.loads(Path(path).read_text())
    if br.get("gamebook") != g["id"]:
        sys.exit(f"{path} is for gamebook {br.get('gamebook')!r}, not {g['id']!r}")
    if not re.fullmatch(r"[a-z][a-z0-9]{0,7}", name):
        sys.exit("--name: a short lowercase tag, e.g. t1")
    names = {c["id"]: c["name"] for c in source_world(g)["characters"]}
    eps = episode_nodes(g)
    ids = {}
    for i, bn in enumerate(br.get("nodes", []), 1):
        nid = f"{name}_{i}"
        if nid in g["nodes"]:
            sys.exit(f"node {nid} exists already: pick another --name")
        ids[bn["id"]] = nid
    new = {}
    for bn in br.get("nodes", []):
        beats, loc = branch_beats(bn, eps, names)
        node = {"title": bn.get("title") or ids[bn["id"]], "location": loc or g["nodes"][g["start"]].get("location"),
                "panels": max(8, len(beats)), "beats": beats or ["(prázdný uzel)"],
                "origin": {"kind": "reader-branch", "file": Path(path).name, "review": True}}
        choices = [{"id": f"{ids[bn['id']]}_{k}", "text": c["text"], "to": ids.get(c["to"], c["to"])}
                   for k, c in enumerate(bn.get("choices", []), 1)]
        if choices:
            node["choices"] = choices
        else:
            node["ending"] = "good"
        new[ids[bn["id"]]] = node
    hooks = []
    for h in br.get("hooks", []):
        to = ids.get(h["choice"]["to"], h["choice"]["to"])
        if h["from"] in g["nodes"]:
            hooks.append((h["from"], {"id": f"{to}_in", "text": h["choice"]["text"], "to": to}))
    text = Path(g["_path"]).read_text()
    for frm, ch in hooks:
        text = add_choice(text, frm, ch)
    text = text.rstrip("\n") + "\n\n  # větve čtenáře " + Path(path).name + " (" + name + "): před kreslením přečíst, pak smazat origin.review\n"
    for nid, node in new.items():
        block = yaml.safe_dump({nid: node}, allow_unicode=True, sort_keys=False, width=110)
        text += "".join("  " + l + "\n" for l in block.splitlines())
    yaml.safe_load(text)  # still YAML
    Path(out or g["_path"]).write_text(text, encoding="utf-8")
    print(f"{len(new)} nodes ({', '.join(new)}), {len(hooks)} hooks → {out or g['_path']}")
    print("next: read the new nodes (they are a reader's text), drop origin.review, then write/unify/render as usual")


def add_choice(text, node_id, choice):
    """Inserts a flow-style choice into node_id's choices (a `next` becomes the choice "Pokračovat")."""
    flow = "{" + ", ".join(f"{k}: {json.dumps(v, ensure_ascii=False) if k == 'text' else v}" for k, v in choice.items()) + "}"
    lines = text.split("\n")
    start = next(i for i, l in enumerate(lines) if l == f"  {node_id}:")
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^  \S", lines[i])), len(lines))
    body = lines[start + 1:end]
    if any(l.strip() == "choices:" for l in body):
        c = start + 1 + next(i for i, l in enumerate(body) if l.strip() == "choices:")
        last = c
        while last + 1 < end and lines[last + 1].startswith("      - "):
            last += 1
        lines.insert(last + 1, f"      - {flow}")
    else:
        n = start + 1 + next(i for i, l in enumerate(body) if l.startswith("    next: "))
        target = lines[n].split(":", 1)[1].strip()
        lines[n:n + 1] = ["    choices:", f"      - {{id: next, text: Pokračovat, to: {target}}}", f"      - {flow}"]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scripts", "write", "draft", "unify", "ids", "import-branch"])
    ap.add_argument("graph")
    ap.add_argument("branches", nargs="?", help="import-branch: the JSON a reader sent (Odeslat autorovi)")
    ap.add_argument("--name", default="r1", help="import-branch: id prefix of the new nodes")
    ap.add_argument("--out", help="import-branch: write the graph here instead of over it")
    a = ap.parse_args()
    g = load(a.graph)
    if a.cmd == "import-branch":
        if not a.branches:
            ap.error("import-branch needs the branches JSON")
        return cmd_import_branch(g, a.branches, a.name, a.out)
    if a.cmd == "ids":
        print(" ".join(story_id(g, n) for n in g["nodes"]))
        return 0
    return {"scripts": cmd_scripts, "write": cmd_write, "draft": cmd_draft, "unify": cmd_unify}[a.cmd](g) or 0


if __name__ == "__main__":
    sys.exit(main())
