"""rules/: every rule the pipeline obeys, as data. One loader (cached, validated), the profiles and the storyboard engine.

    rules/base/<file>.yaml       shared rules (storyboard, prompts, render, animate, compose, shorts, music, pipeline, pack)
    rules/profiles/<name>.yaml   harlequin | kids | free | superhero: deep-merged over base (or over the profile
                                 named by `profile.extends`) — mappings merge key by key, lists and values replace,
                                 {extend: [...]} appends to the inherited list, {replace: ...} replaces a mapping whole

    import rules; rules.load("render")["max_reseed"]; rules.cfg("render", "kids")["rating_limits"]
    python3 m0/rules.py get pipeline.strip.deadline.window_end      # one base value for shell scripts
    python3 m0/rules.py get free:pipeline.strip.prefix              # the same, merged for a profile
    python3 m0/rules.py check                                       # load + validate every file and profile

WEBTOON_RULES=<dir> points at another rules directory (default: <repo>/rules). Needs PyYAML (m0/requirements.txt).
"""

import copy
import functools
import json
import os
import re
import sys
from pathlib import Path

import yaml

RULES = Path(os.environ.get("WEBTOON_RULES") or Path(__file__).resolve().parent.parent / "rules")
BASE, PROFILES = RULES / "base", RULES / "profiles"

# Top-level keys each base file must have: a typo or a lost section fails at load, not mid-render.
REQUIRED = {
    "storyboard": ["regex", "limits", "human_kinds", "age_by_kind", "required", "checks", "to_m0", "adapt", "pick_motion"],
    "prompts": ["regex", "age_anchor", "count_tags", "negative", "close_up_location_tags", "default_size", "color_weight",
                "natural"],
    "render": ["rating_limits", "tag_limits", "design_threshold", "max_reseed", "ip_adapter", "sheet_tags"],
    "animate": ["fps", "size", "negative", "style_tail_tags", "default_motion", "webp_quality"],
    "compose": ["width", "gaps", "default_gap", "bg", "ink", "fonts", "bubble", "sfx", "title", "texts"],
    "shorts": ["frame", "top", "bottom", "fade", "font_scale", "panel_duration", "cards", "zoom", "end"],
    "music": ["length", "window", "model", "prompt_suffix", "seed_base", "moods"],
    "pipeline": ["strip"],
    "pack": ["part_size", "webp_quality", "cover", "forbidden_world_prefix", "dropped_episode_fields"],
}
# What every profile must end up declaring (after merging).
PROFILE_REQUIRED = {
    "profile": ["description", "audience", "free", "styles", "pack"],
    "storyboard": ["fences", "to_m0", "adapt"],
}
PROFILE_KEYS = {"storyboard": ["fences"], "storyboard.to_m0": ["tone", "bible_rules", "couple_tags", "fonts"],
                "storyboard.adapt": ["schema", "system", "example", "addendum", "rewrite"],
                "storyboard.fences": ["fence", "kids_fence", "motion", "allow"],
                "profile.styles": ["pool", "default", "strip_default"], "profile.pack": ["audience", "exported"]}


def _read(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@functools.cache
def load(name):
    """rules/base/<name>.yaml (shared by every profile)."""
    path = BASE / f"{name}.yaml"
    data = _read(path)
    missing = [k for k in REQUIRED.get(name, []) if k not in data]
    if missing:
        raise KeyError(f"{path}: missing {', '.join(missing)}")
    return data


def merge(base, over):
    """Profile deep merge: mappings key by key, {extend: [...]} appends, {replace: x} is x, anything else replaces."""
    if isinstance(over, dict):
        if set(over) == {"replace"}:
            return copy.deepcopy(over["replace"])
        if set(over) == {"extend"}:
            return list(base or []) + list(over["extend"])
        out = dict(base) if isinstance(base, dict) else {}
        for k, v in over.items():
            out[k] = merge(out.get(k), v)
        return out
    return copy.deepcopy(over)


def profiles():
    return sorted(p.stem for p in PROFILES.glob("*.yaml"))


@functools.cache
def profile(name):
    """{file: merged rules, "profile": meta, "lineage": [name, parent, ...]} for rules/profiles/<name>.yaml."""
    path = PROFILES / f"{name}.yaml"
    raw = _read(path)
    parent = raw.get("profile", {}).get("extends")
    if parent:
        base = profile(parent)
        lineage = [name] + base["lineage"]
    else:
        base = {"profile": {}, **{f: load(f) for f in REQUIRED}}
        lineage = [name]
    unknown = set(raw) - set(base)
    if unknown:
        raise KeyError(f"{path}: unknown sections {', '.join(sorted(unknown))}")
    out = {k: merge(base[k], raw[k]) if k in raw else base[k] for k in base if k != "lineage"}
    out["profile"].pop("extends", None)
    out["lineage"] = lineage
    for sec, keys in {**PROFILE_REQUIRED, **PROFILE_KEYS}.items():
        node = out
        for k in sec.split("."):
            node = node[k]
        missing = [k for k in keys if k not in node]
        if missing:
            raise KeyError(f"{path}: {sec} missing {', '.join(missing)}")
    return out


def cfg(name, prof=None):
    """Rules of one file: merged for a profile, or the base file (prof None: e.g. a teen world)."""
    return profile(prof)[name] if prof else load(name)


def profile_of(free=False, audience=None, default=None):
    """Today's audience flags → profile: --free → free, kids → kids, adult → harlequin; anything else → default.
    free is adults only (adapt.main refuses --free with kids)."""
    if free and audience == "kids":
        raise ValueError("free mode is adults only, it cannot be combined with audience kids")
    return "free" if free else {"kids": "kids", "adult": "harlequin"}.get(audience, default)


def world_profile(world):
    """The profile a world.json was written for: its "profile" key (superhero), else from audience / free;
    None for a world no profile describes (audience "teen", world_m0.json). "free" wins over any audience."""
    return world.get("profile") or ("free" if world.get("free") else profile_of(False, world.get("audience")))


def get(key):
    """'file.a.b' → rules/base/file.yaml [a][b]; 'prof:file.a.b' merged for a profile (list indices as numbers)."""
    prof, _, key = key.rpartition(":")
    name, *path = key.split(".")
    v = profile(prof)[name] if prof else load(name)
    for k in path:
        v = v[int(k)] if isinstance(v, list) else v[k]
    return v


def _flat(words):
    for w in words:
        if isinstance(w, list):
            yield from _flat(w)
        else:
            yield str(w)


def regexes(specs):
    """{name: spec} → {name: compiled}. spec: a pattern string, or {pattern | words [+ wrap], ignorecase,
    from: <other name> + drop: [words]}; `words` are alternatives joined by | inside wrap (default \\b(...)\\b)."""
    out, words = {}, {}

    def build(name):
        if name in out:
            return out[name]
        s = specs[name]
        if isinstance(s, str):
            s = {"pattern": s}
        if "from" in s:
            build(s["from"])
            base = {**specs[s["from"]], **{k: v for k, v in s.items() if k not in ("from", "drop")}}
            ws = [w for w in words[s["from"]] if w not in set(_flat(s.get("drop", [])))]
            s = {**base, "words": ws}
        if "words" in s:
            words[name] = list(_flat(s["words"]))
            pattern = s.get("wrap", r"\b({})\b").replace("{}", "|".join(words[name]))
        else:
            pattern = s["pattern"]
        out[name] = re.compile(pattern, re.I if s.get("ignorecase") else 0)
        return out[name]

    for n in specs:
        build(n)
    return out


# --- storyboard rule engine ----------------------------------------------------------------------
#
# rules/base/storyboard.yaml `checks` is a list of groups {scope, rules: [...]}; a rule is {id, profiles, if, message}
# or a nested group; `profiles` (default: all) matches the active profile or one it extends. Scopes: story (once), character (each story character), character_field (each of base, photo
# and the outfits of that character), panel (each panel), panel_character (each character entry of that panel),
# bubble (each bubble of that panel). Rules run in file order, so errors come out in file order.
#
# `if` is the violation: a condition tree of {all|any: [...]}, {not: c}, {truthy|falsy: ref}, {eq|ne|in|not_in|gt|ge:
# [a, b]}, {search|match: {regex, in, mask}}, {contains: [set, item]}, {intersects: [set, items]},
# {long_items: {in, max_words, except}}. A ref is "$name.key.0" (strict: a missing key raises, like the old code);
# "?" after a key makes it optional (None), "|len" takes the length. search / match / long_items bind `m`
# (the matched text / the offending items) for the message, a str.format template over the same names.
# A regex is a name from `regex`, an alias from the profile's `fences` (fence, kids_fence, allow; a list alias like
# `$fences.motion` is a list of names), or a ref to a pattern string. `mask: allow` blanks the profile's allowed
# phrases (superhero: the action vocabulary) before searching; `never` (every other profile) leaves the text as is.


class Ctx(dict):
    """Names a rule may reference; `views` are computed on first use (so they raise only where the old code did)."""

    def __init__(self, parent=None, views=None, **names):
        super().__init__(**names)
        self.parent, self.views = parent, views or {}

    def __missing__(self, k):
        if k in self.views:
            self[k] = self.views[k](self)
            return self[k]
        if self.parent is not None:
            return self.parent[k]
        raise KeyError(k)

    def child(self, views=None, **names):
        return Ctx(self, views, **names)


_OPT = object()


def ref(ctx, v):
    if not (isinstance(v, str) and v.startswith("$")):
        return v
    path, _, pipe = v[1:].partition("|")
    head, *keys = path.split(".")
    x = ctx[head]
    for k in keys:
        opt = k.endswith("?")
        k = k.rstrip("?")
        if isinstance(x, (list, tuple)):
            x = x[int(k)]
        elif opt:
            x = x.get(k)
        else:
            x = x[k]
    if pipe == "len":
        x = len(x)
    elif pipe:
        raise ValueError(f"unknown pipe |{pipe} in {v}")
    return x


class Engine:
    def __init__(self, spec, lineage):
        self.spec, self.lineage = spec, set(lineage)
        self.re = regexes(spec["regex"])
        self.fences = spec["fences"]

    def regex(self, ctx, name):
        if isinstance(name, str) and name.startswith("$"):
            return _compiled(ref(ctx, name))
        alias = self.fences.get(name)
        return self.re[alias if isinstance(alias, str) else name]

    def regex_names(self, ctx, spec):
        if isinstance(spec, str) and spec.startswith("$"):
            v = ref(ctx, spec)
            return v if isinstance(v, list) else [spec]
        return spec if isinstance(spec, list) else [spec]

    def mask(self, text):
        allow = self.re[self.fences["allow"]]
        return text if self.fences["allow"] == "never" else allow.sub(lambda m: " " * len(m.group(0)), text)

    def cond(self, ctx, c):
        (op, a), = c.items()
        if op == "all":
            return all(self.cond(ctx, x) for x in a)
        if op == "any":
            return any(self.cond(ctx, x) for x in a)
        if op == "not":
            return not self.cond(ctx, a)
        if op == "truthy":
            return bool(ref(ctx, a))
        if op == "falsy":
            return not ref(ctx, a)
        if op in ("search", "match"):
            text = ref(ctx, a["in"])
            if a.get("mask") == "allow":
                text = self.mask(text)
            for name in self.regex_names(ctx, a["regex"]):
                m = getattr(self.regex(ctx, name), op)(text)
                if m:
                    ctx["m"] = m.group(0)
                    return True
            return False
        if op == "long_items":
            known, n = ref(ctx, a["except"]), ref(ctx, a["max_words"])
            hits = [t for t in ref(ctx, a["in"]) if t not in known and len(t.split()) > n]
            ctx["m"] = hits
            return bool(hits)
        x, y = (ref(ctx, v) for v in a)
        if op == "eq":
            return x == y
        if op == "ne":
            return x != y
        if op == "in":
            return x in y
        if op == "not_in":
            return x not in y
        if op == "gt":
            return x > y
        if op == "ge":
            return x >= y
        if op == "contains":
            return y in x
        if op == "intersects":
            return bool(x & set(y))
        raise ValueError(f"unknown condition {op}")

    def run(self, rules, ctx, errs):
        for r in rules:
            if "scope" in r:
                for item in self.items(r["scope"], ctx):
                    self.run(r["rules"], item, errs)
            elif ("profiles" not in r or self.lineage & set(r["profiles"])) and self.cond(ctx, r["if"]):
                errs.append(r["message"].format_map(ctx))

    def items(self, scope, ctx):
        story, human = ctx["story"], set(self.spec["human_kinds"])
        if scope == "story":
            yield ctx.child({"animated": lambda x: [i for i, p in enumerate(story["panels"]) if p.get("animate")],
                             "n_animated": lambda x: len(x["animated"])})
        elif scope == "character":
            for c in story["characters"]:
                yield ctx.child({"kind": lambda x: x["c"].get("kind", self.spec["default_kind"]),
                                 "base_tags": lambda x: set(split_tags(x["c"]["base"])),
                                 "base_photo": lambda x: x["c"]["base"] + " " + x["c"]["photo"],
                                 "age": lambda x: self.spec["age_by_kind"].get(x["kind"])}, c=c)
        elif scope == "character_field":
            c = ctx["c"]
            for v in (c["base"], c["photo"], *c["outfits"].values()):
                yield ctx.child(value=v)
        elif scope == "panel":
            chars = ctx["chars"]
            for i, p in enumerate(story["panels"]):
                yield ctx.child({
                    "ids": lambda x: [c["id"] for c in x["p"]["characters"]],
                    "genders": lambda x: [chars[c]["gender"] for c in x["ids"] if c in chars],
                    # kind read without the "adult" default here (kids stories always carry it, missing_fields)
                    "humans": lambda x: [c for c in x["ids"] if c in chars and chars[c].get("kind") in human],
                    "tags_text": lambda x: ", ".join(x["p"]["visual_tags"]),
                    "bubble_text": lambda x: " ".join(b["text"] for b in x["p"]["bubbles"])}, i=i, p=p)
        elif scope == "panel_character":
            for pc in ctx["p"]["characters"]:
                yield ctx.child({"pc_char": lambda x: ctx["chars"].get(x["pc"]["id"])}, pc=pc)
        elif scope == "bubble":
            for b in ctx["p"]["bubbles"]:
                yield ctx.child(b=b)
        else:
            raise ValueError(f"unknown scope {scope}")

    def missing_fields(self, story):
        req, msg = self.spec["required"], self.spec["required"]["messages"]
        errs = [msg["story"].format(k=k) for k in req["story"] if k not in story]
        for c in story.get("characters", []):
            cid = c.get("id", "?")
            errs += [msg["character"].format(id=cid, k=k) for k in req["character"] if k not in c]
            if req["outfit"] not in c.get("outfits", {}):
                errs.append(msg["outfit"].format(id=cid, k=req["outfit"]))
        for l in story.get("locations", []):
            errs += [msg["location"].format(id=l.get("id", "?"), k=k) for k in req["location"] if k not in l]
        for i, p in enumerate(story.get("panels", [])):
            errs += [msg["panel"].format(i=i, k=k) for k in req["panel"] if k not in p]
            for b in p.get("bubbles", []):
                errs += [msg["bubble"].format(i=i, k=k) for k in req["bubble"] if k not in b]
        return errs

    def check(self, story, world_tags=None):
        errs = self.missing_fields(story)
        if errs:  # the schema was not enforced (no guided decoding): report instead of crashing on a missing key
            return errs
        ctx = Ctx(story=story, world_tags=world_tags, limits=self.spec["limits"], fences=self.fences,
                  human_kinds=set(self.spec["human_kinds"]), age_by_kind=self.spec["age_by_kind"],
                  chars={c["id"]: c for c in story["characters"]}, loc_ids={l["id"] for l in story["locations"]})
        self.run(self.spec["checks"], ctx, errs)
        return errs


@functools.cache
def _compiled(pattern):
    return re.compile(pattern)


def split_tags(s):  # common.split_tags, imported late so rules.py stays usable from the shell without m0 on the path
    from common import split_tags as st
    return st(s)


@functools.cache
def storyboard(prof):
    """The storyboard rule engine of a profile (adapt.check(): harlequin, kids, free, superhero)."""
    p = profile(prof)
    return Engine(p["storyboard"], p["lineage"])


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "get":
        v = get(sys.argv[2])
        print(" ".join(map(str, v)) if isinstance(v, list) else json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else v)
    elif sys.argv[1:] == ["check"]:
        for name in REQUIRED:
            load(name)
        for name in profiles():
            storyboard(name)
        print(f"{RULES}: {len(REQUIRED)} base files, profiles {', '.join(profiles())} ok")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
