"""Runs every rule-bearing function of the m0 modules over tests/cases.py and returns comparable results.

    harness.run(mods) → {section: {case: result}}

`mods` is a namespace of imported modules (adapt, prompts, render, animate, compose, shorts, music); make_goldens.py
passes the original snapshot's, test_golden.py the current ones. Results are JSON-able: big outputs as sha256.
"""

import argparse
import contextlib
import copy
import hashlib
import io
import json
import re
import tempfile
from pathlib import Path

import cases


def norm(v):
    """JSON-able, order-stable view of a value that still tells tuple / list / set / regex apart."""
    if isinstance(v, re.Pattern):
        return {"re": v.pattern, "flags": v.flags}
    if isinstance(v, (set, frozenset)):
        return {"set": sorted(norm(x) for x in v)}
    if isinstance(v, tuple):
        return {"tuple": [norm(x) for x in v]}
    if isinstance(v, list):
        return [norm(x) for x in v]
    if isinstance(v, dict):
        return {"dict": [[norm(k), norm(x)] for k, x in v.items()]}
    if isinstance(v, Path):
        p = str(v)
        for r in PATH_ROOTS:
            p = p.replace(str(r), "<root>")
        return {"path": p}
    return v


PATH_ROOTS = []


def import_mods(m0_dir):
    """Imports the m0 modules from m0_dir (one version per process: they import each other by bare name)."""
    import importlib
    import sys
    import types
    sys.path.insert(0, str(m0_dir))
    names = ["common", "adapt", "prompts", "render", "animate", "compose", "shorts", "music"]
    mods = types.SimpleNamespace(**{n: importlib.import_module(n) for n in names})
    mods.root = Path(m0_dir).resolve().parent
    return mods


def sha(obj):
    if isinstance(obj, bytes):
        return hashlib.sha256(obj).hexdigest()
    return hashlib.sha256(json.dumps(obj, ensure_ascii=False, default=str).encode()).hexdigest()


def guard(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except SystemExit as e:
        return {"exit": str(e.code)}
    except Exception as e:  # noqa: BLE001 — the exception type is part of the behaviour
        return {"raises": type(e).__name__}


def consts(mod, names):
    return {n: norm(getattr(mod, n)) for n in names}


# --- adapt ---------------------------------------------------------------------------------------

def run_check(m):
    vocab = m.common.vocab()
    out = {}
    for cid, story in cases.check_cases():
        for aud, free in cases.MODES:
            for wt in (False, True):
                out[f"{cid}|{aud}|{'vocab' if wt else 'none'}"] = guard(m.adapt.check, copy.deepcopy(story),
                                                                         vocab if wt else None, free=free,
                                                                         audience="kids" if aud == "kids" else "adult")
    for cid, story in cases.check_cases():
        for kids in (False, True):
            out[f"missing|{cid}|{kids}"] = guard(m.adapt.missing_fields, copy.deepcopy(story), kids)
    return out


def run_to_m0(m):
    out = {}
    for cid, story in cases.check_cases():
        if m.adapt.missing_fields(story, True) and m.adapt.missing_fields(story, False):
            continue
        for aud, free in cases.MODES:
            r = guard(m.adapt.to_m0, copy.deepcopy(story), "style_x", free=free, audience="kids" if aud == "kids" else "adult")
            out[f"{cid}|{aud}"] = r if isinstance(r, dict) else sha(r)
    return out


class FakeChat:
    def __init__(self, answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, messages, schema=None, temperature=0.4, max_tokens=6000):
        self.calls.append({"messages": copy.deepcopy(messages), "schema": schema, "temperature": temperature})
        a = self.answers.pop(0) if self.answers else {}
        if isinstance(a, Exception):
            raise a
        return copy.deepcopy(a)


def run_adapt(m):
    ad = m.adapt
    ex = cases.examples()
    saved = {}
    orig = ad.chat, ad.save_json
    out = {}
    broken = copy.deepcopy(ex["santorini"])
    broken["panels"][-1]["gap_after"] = "small"
    scen = {
        "adult": ("adult", False, [ex["santorini"]]),
        "adult_retry": ("adult", False, [ValueError("bad json"), broken, ex["santorini"]]),
        "adult_gaveup": ("adult", False, [broken, broken, broken]),
        "kids": ("kids", False, [ex["kids_park"]]),
        "free": ("adult", False, []),
        "free_gaveup": ("adult", True, [ex["santorini"]] * 3),
        "free_ok": ("adult", True, [cases.M(lambda s: [c.update(base=c["base"].replace("petite, ", "") if "adult" in c["base"]
                                                           else "adult, " + c["base"]) for c in s["characters"]])(ex["santorini"])]),
    }
    try:
        ad.save_json = lambda path, obj: saved.__setitem__(str(Path(path).relative_to(ad.DATA)), copy.deepcopy(obj))
        for name, (aud, free, answers) in scen.items():
            for dry in ((True, False) if name in ("adult", "kids", "free_gaveup") else (False,)):
                fake = FakeChat(answers)
                ad.chat = fake
                saved.clear()
                example = "kids_park" if aud == "kids" else "santorini"
                args = argparse.Namespace(id="lt_test_" + name, style=None, audience=aud, free=free, attempts=3, dry_run=dry,
                                          source=str(cases.EXAMPLES / f"{example}.input.md"))
                args.style = "clean_webtoon_noartist" if aud == "kids" else "fashion_editorial"
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    res = guard(ad.adapt, args)
                out[f"{name}|dry={dry}"] = {"result": res, "stdout": buf.getvalue(), "calls": fake.calls, "saved": dict(saved)}
        # pick_motion over a real storyboard with a scripted model
        sid = "r_bombaj"
        n = len(cases.load(cases.ROOT / "data" / "stories" / sid / "storyboard.json")["panels"])
        for name, answers in {
            "ok": [{"panels": [{"n": 0, "motion": "clouds drifting, static camera"}, {"n": 3, "motion": "hair swaying"}]}],
            "retry": [{"panels": [{"n": 99, "motion": "x"}, {"n": 2, "motion": "kissing slowly"}]}, KeyError("panels"),
                      {"panels": [{"n": 1, "motion": "nude"}, {"n": 4, "motion": "they dance"}, {"n": 5, "motion": "x"}]},
                      {"panels": [{"n": n - 1, "motion": "rain, ambient only"}]}],
            "gaveup": [{"panels": [{"n": -1, "motion": "x"}]}] * 3,
        }.items():
            fake = FakeChat(answers)
            ad.chat = fake
            saved.clear()
            args = argparse.Namespace(pick_motion=sid, attempts=3, dry_run=False)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                res = guard(ad.pick_motion, args)
            out[f"pick_{name}"] = {"result": res, "stdout": buf.getvalue(), "calls": fake.calls, "saved": dict(saved)}
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ad.pick_motion(argparse.Namespace(pick_motion=sid, attempts=3, dry_run=True))
        out["pick_dry"] = buf.getvalue()
    finally:
        ad.chat, ad.save_json = orig
    system = (ad.SKILL / "prompts" / "adapt_system.md").read_text().replace("{lang}", "Czech")
    out["free_prompt"] = ad.free_prompt(system)
    out["consts"] = consts(ad, ["SHOTS", "KINDS", "GAPS", "BANNED", "AGE_BANNED", "FREE_AUDIENCE", "KIDS_SFW", "KIDS_BANNED",
                                "HUMAN_KINDS", "AGE_BY_KIND", "PICK_SCHEMA"])
    return out


# --- prompts / render ----------------------------------------------------------------------------

PROMPT_VARIANTS = [  # (world override, preset, sfw, regional)
    ({}, None, True, False), ({}, None, True, True), ({}, None, False, False),
    ({}, "webtoon_romance", True, True), ({}, "photo_juggernaut", True, False), ({}, "clean_webtoon", False, True),
    ({"free": True}, None, False, True), ({"audience": "kids"}, "clean_webtoon_noartist", True, False),
    ({"audience": "teen"}, "fashion_editorial", True, False),
]


def run_prompts(m):
    styles = cases.load(cases.ROOT / "data" / "styles.json")
    out = {}
    for sid, w, sb in cases.stories():
        for k, (over, preset, sfw, regional) in enumerate(PROMPT_VARIANTS):
            world = {**w, **over}
            res = [guard(m.prompts.build, p, world, styles, preset, sfw=sfw, regional=regional) for p in sb["panels"]]
            res += [guard(m.prompts.build, m.render.sheet_panel(c), world, styles, preset, sfw=sfw) for c in w["characters"]]
            out[f"{sid}|{k}"] = sha(res)
    # one full sample per path, readable in a diff
    sid, w, sb = cases.stories()[0]
    out["sample"] = [m.prompts.build(sb["panels"][1], w, styles, p, regional=True) for p in ("webtoon_romance", "photo_juggernaut")]
    girl, boy, pet = {"count_tag": "1girl"}, {"count_tag": "1boy"}, {"count_tag": ""}
    for combo in ([], [pet], [pet, pet], [girl], [boy], [girl, boy], [girl, girl], [boy, boy, boy], [girl, pet], [girl, girl, boy, pet]):
        out["count|" + ",".join(c["count_tag"] or "-" for c in combo)] = m.prompts.count_tags(combo)
    out["weight"] = m.prompts.weight(["red hair", "dark brown eyes", "long hair", "blue hair, x", "aqua eyes", "Red hair"])
    for aud in ("kids", "adult", "teen", None):
        for free in (False, True):
            out[f"aud|{aud}|{free}"] = m.prompts.audience_negative({"audience": aud, **({"free": True} if free else {})}, styles)
    out["consts"] = consts(m.prompts, ["DESIGN_RE", "EXPRESSION_RE", "LOWER_RE", "FEET_RE", "COLOR_RE", "AGE_ANCHOR",
                                       "COUNT_TAGS", "AGE_NEGATIVE"])
    return out


TAG_SETS = [
    {},
    {"rating": {"general": 0.9, "sensitive": 0.4, "questionable": 0.1, "explicit": 0.01}},
    {"rating": {"sensitive": 0.6, "questionable": 0.31, "explicit": 0.2}, "general": {"cleavage": 0.81, "bed": 0.7, "child": 0.36}},
    {"rating": {"explicit": 0.21}, "general": {"shirtless": 0.51, "underwear": 0.31, "covered nipples": 0.29, "large breasts": 0.9}},
    {"general": {"loli": 0.35, "shota": 0.351, "flat chest": 0.6, "school uniform": 0.49, "serafuku": 0.51,
                 "randoseru": 0.4, "kindergarten uniform": 0.9, "aged down": 0.1}},
    {"rating": {"sensitive": 0.5}, "general": {"long hair": 0.9, "brown hair": 0.36, "brown eyes": 0.35, "dress": 0.2}},
]


def run_render(m):
    out = {}
    for k, t in enumerate(TAG_SETS):
        for aud in ("teen", "adult", "kids", None):
            for free in (False, True):
                out[f"safety|{k}|{aud}|{free}"] = m.render.safety(t, aud, free=free)
    for sid, w, sb in cases.stories()[:40]:
        for c in w["characters"]:
            for shot in (None, "close-up", "medium", "over-shoulder", "wide", "sheet"):
                for k, t in enumerate(TAG_SETS):
                    out[f"identity|{sid}|{c['id']}|{shot}|{k}"] = m.render.identity(t, c, shot)
    out["sheet"] = m.render.sheet_panel({"id": "x"})
    out["consts"] = consts(m.render, ["UNSAFE", "UNSAFE_KIDS", "DESIGN_THRESHOLD", "MAX_RESEED", "ADULT_TAG_LIMITS", "AGE_TAG_LIMITS"])
    return out


# --- animate / compose / shorts / music ----------------------------------------------------------

def run_animate(m):
    from PIL import Image
    a = m.animate
    styles = cases.load(cases.ROOT / "data" / "styles.json")
    out = {"frames": [a.frames(s) for s in (1, 2, 3)],
           "tails": {k: a.style_tail(p) for k, p in styles["presets"].items()}}
    for k, p in list(styles["presets"].items())[:6]:
        for free in (False, True):
            out[f"graph|{k}|{free}"] = a.graph("in.png", " hair swaying in the wind. ", p, 480, 704, a.frames(2), 9100, "pfx", free=free)
    out["graph|empty"] = a.graph("in.png", "x", {}, 704, 480, 17, 1, "p")
    for sid, w, sb in cases.stories():
        for explicit, force in ((None, False), ("0,1,2", False), ("0,1,2", True), ("3", False)):
            out[f"select|{sid}|{explicit}|{force}"] = guard(a.select_panels, sb["panels"], explicit, force)
    with tempfile.TemporaryDirectory() as d:
        for wh in ((832, 1216), (1216, 832), (900, 900)):
            f = Path(d) / f"{wh[0]}x{wh[1]}.png"
            Image.new("RGB", wh).save(f)
            out[f"size|{wh}"] = norm(a.size_for(f))
    out["consts"] = consts(a, ["FPS", "MAX_ANIMATED", "SIZE", "NEGATIVE", "NEGATIVE_FREE", "STYLE_TAIL_TAGS"])
    return out


def run_compose(m):
    from PIL import Image
    c = m.compose
    out = {}
    pick = ["halloween", "les", "r_bombaj", "ra_01_santorini", "rq_10_kostarika"]
    for sid, w, sb in cases.stories():
        if sid in pick or sb.get("choices"):
            img = c.compose(sb, use_placeholder=True)
            out[f"strip|{sid}"] = [img.size, sha(img.tobytes())]
    sb = cases.stories()[0][2]
    sb = {**sb, "choices": [{"text": "Zůstat"}, {"text": "Odejít", "kind": "free"}]}
    for fonts in (None, "romance"):
        img = c.compose({**sb, "fonts": fonts}, use_placeholder=True)
        out[f"choices|{fonts}"] = [img.size, sha(img.tobytes())]
        c.FONT_SET = fonts
        for kind in ("speech", "thought", "shout", "narration", "sfx", "ui"):
            img = Image.new("RGB", (800, 1100), "white")
            for k, txt in enumerate(["Krátce.", "Tohle je dlouhá bublina, která se musí zalomit do více řádků, aby se vešla.", "Ještě?"]):
                c.draw_bubble(img, {"kind": kind, "text": txt}, k, 3)
            c.draw_sfx(img, {"text": "BUM"}, 0)
            c.draw_sfx(img, {"text": "ŠUM"}, 1)
            out[f"bubble|{fonts}|{kind}"] = sha(img.tobytes())
        out[f"end|{fonts}"] = sha(c.end_block().tobytes())
    c.FONT_SET = None
    out["consts"] = consts(c, ["WIDTH", "GAPS", "FONTS", "BG", "INK", "SYSTEM_FONTS", "ROMANCE"])
    return out


def run_shorts(m):
    from PIL import Image
    s, c = m.shorts, m.compose
    out = {"consts": consts(s, ["W", "H", "FPS", "TOP", "FADE", "FONT_SCALE", "END"])}
    out["slug"] = [s.slug(t) for t in ("Kostarika – Doma", "Ánò, ne!", "  x  ")]
    base_font, base_set = c.font, c.FONT_SET
    try:
        c.FONT_SET = "romance"
        c.font = lambda kind, size: base_font(kind, round(size * s.FONT_SCALE))
        with tempfile.TemporaryDirectory() as d:
            media = Path(d)
            Image.linear_gradient("L").convert("RGB").resize((300, 450)).save(media / "port.png")
            Image.linear_gradient("L").convert("RGB").resize((450, 300)).save(media / "land.png")
            fr = [Image.new("RGB", (240, 352), (k * 60, 20, 90)) for k in range(4)]
            fr[0].save(media / "loop.webp", save_all=True, append_images=fr[1:], duration=62, loop=0)
            for t in ("a.mp3", "b.ogg", "c.txt", "d.wav"):
                (media / t).write_text("x")
            out["track"] = [s.pick_track(str(media), w).name for w in ("w_a", "w_b", "w_rl_01")]
            bub = [{"kind": "narration", "text": "Ráno.", "speaker_id": ""},
                   {"kind": "speech", "text": "Ahoj, jak se máš? " * 4, "i18n": {"en": "Hi"}}]
            panels = {"port": {"image_url": "/port.png", "bubbles": bub}, "land": {"image_url": "/land.png", "bubbles": bub[:1]},
                      "empty": {"image_url": "/port.png"}, "long": {"image_url": "/port.png", "bubbles": [{"kind": "speech", "text": "x" * 200}]},
                      "loop": {"image_url": "/port.png", "video_url": "/loop.webp", "bubbles": bub},
                      "loop_pending": {"image_url": "/land.png", "video_url": "/loop.webp", "video_status": "pending"}}
            for name, p in panels.items():
                for lang in ("cs", "en"):
                    seg = s.panel_segment(p, media, lang)
                    out[f"seg|{name}|{lang}"] = [seg.dur] + [sha(seg.frame_at(t).tobytes()) for t in (0, seg.dur / 2)]
            seg = s.card_segment("Konec dlouhého příběhu o lásce", Image.open(media / "port.png").convert("RGB"), 2.0, size=120)
            out["card"] = [seg.dur, sha(seg.frame_at(0).tobytes())]
            out["text_of"] = [s.text_of({"title_i18n": {"en": "T"}}, "title", lang) for lang in ("cs", "en", "de")]
    finally:
        c.font, c.FONT_SET = base_font, base_set
    return out


def run_music(m):
    mu = m.music
    out = {"consts": consts(mu, ["LENGTH", "MOODS", "LIB"])}
    import datetime as dt
    calls = []

    class FakeDT:
        now_s = "07:05"

        @classmethod
        def now(cls):
            return dt.datetime.strptime("2026-10-24 " + cls.now_s, "%Y-%m-%d %H:%M")

    orig = mu.datetime, mu.http
    try:
        mu.datetime = FakeDT
        for models in ([{"name": "acestep-v15-turbo", "available": True}], [{"name": "acestep-v15-turbo"}], []):
            mu.http = lambda method, url, *a, **kw: (calls.append(url), json.dumps(models).encode())[1]
            for t in ("07:04", "07:05", "10:00", "12:45", "12:46", "00:00"):
                FakeDT.now_s = t
                out[f"ready|{t}|{len(models)}|{models[0].get('available') if models else None}"] = guard(mu.check_ready)
    finally:
        mu.datetime, mu.http = orig
    out["calls"] = calls
    return out


SECTIONS = {"check": run_check, "to_m0": run_to_m0, "adapt": run_adapt, "prompts": run_prompts, "render": run_render,
            "animate": run_animate, "compose": run_compose, "shorts": run_shorts, "music": run_music}


def run(mods, only=None):
    PATH_ROOTS[:] = [mods.root]
    # the old code runs from a temp copy: its absolute paths (printed or stored) are compared as <root>/...
    return {k: json.loads(json.dumps(fn(mods), ensure_ascii=False, default=norm).replace(str(mods.root), "<root>"))
            for k, fn in SECTIONS.items() if not only or k in only}
