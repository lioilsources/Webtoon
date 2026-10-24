"""Inputs for the golden tests: lean stories rebuilt from data/stories/*, the skill examples, and broken mutants.

Stdlib only and independent of the m0 modules, so make_goldens.py (original code) and test_golden.py (current code)
feed both versions exactly the same cases.
"""

import copy
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "skills" / "storyboard-writer" / "examples"


def load(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


# The stories the goldens were recorded on (data/stories of the snapshot revision); stories added later are new
# data, not a change of behaviour, so they stay out of the comparison.
GOLDEN_STORIES = set((Path(__file__).parent / "golden" / "stories.txt").read_text().split())


def stories():
    """[(id, world, storyboard)] for every data/stories/<id> of the golden set, sorted."""
    out = []
    for d in sorted(glob.glob(str(ROOT / "data" / "stories" / "*"))):
        if Path(d).name in GOLDEN_STORIES:
            out.append((Path(d).name, load(Path(d) / "world.json"), load(Path(d) / "storyboard.json")))
    return out


def examples():
    return {"santorini": load(EXAMPLES / "santorini.output.json"), "kids_park": load(EXAMPLES / "kids_park.output.json")}


def lean(world, sb, base_from_tags=False):
    """m0 world + storyboard → the lean model form adapt.check() reads (inverse of to_m0, as far as it goes)."""
    kids = world.get("audience") == "kids"
    chars = []
    for c in world["characters"]:
        lc = {"id": c["id"], "name": c["name"]}
        if kids:
            lc["kind"] = ("adult" if "adult" in (c.get("base") or c.get("tag_prompt", "")) else "child") if c.get("human") else "creature"
        lc["gender"] = {"1girl": "f", "1boy": "m"}.get(c.get("count_tag"), "m")
        for k in ("base", "outfits", "photo"):
            if k in c:
                lc[k] = c[k]
        if base_from_tags:
            lc.setdefault("base", c.get("tag_prompt", ""))
            lc.setdefault("outfits", {"default": ""})
            lc.setdefault("photo", c.get("description", ""))
        chars.append(lc)
    panels = []
    for p in sb["panels"]:
        tags = list(p["visual_tags"])
        if not kids and len(p["characters"]) == 2 and tags[:2] == ["couple", "hetero"]:
            tags = tags[2:]
        lp = {"shot": p["shot"], "location_id": p["location_id"], "characters": p["characters"], "visual_tags": tags,
              "bubbles": [{k: b[k] for k in ("speaker_id", "text", "kind") if k in b} for b in p["bubbles"]],
              "sfx": [s["text"] if isinstance(s, dict) else s for s in p["sfx"]], "gap_after": p["gap_after"]}
        if "animate" in p:
            lp["animate"] = p["animate"]
        if "motion" in p:
            lp["motion"] = p["motion"]
        panels.append(lp)
    return {"id": world["id"].removeprefix("w_"), "title": world["title"], "synopsis": world["synopsis"],
            "ending": (world.get("canon", {}).get("constraints") or [""])[0],
            "characters": chars,
            "locations": [{"id": l["id"], "name": l["name"], "tag_prompt": l["tag_prompt"]} for l in world["locations"]],
            "panels": panels}


# --- mutants: each breaks (or probes) one rule of adapt.check() / missing_fields() ------------------------------

def _first_with(s, n):
    """Index of the first panel with exactly n characters (or None)."""
    return next((i for i, p in enumerate(s["panels"]) if len(p["characters"]) == n), None)


def _set_base(s, k, v):
    s["characters"][k]["base"] = v


def _human_ids(s):
    return [c["id"] for c in s["characters"] if c.get("kind", "adult") in ("child", "adult")]


def M(fn):
    def run(s):
        s = copy.deepcopy(s)
        fn(s)
        return s
    run.__name__ = fn.__name__
    return run


MUTANTS = []


def mutant(fn):
    MUTANTS.append((fn.__name__, M(fn)))
    return fn


def _drop(path):
    def fn(s):
        obj = s
        for k in path[:-1]:
            obj = obj[k]
        obj.pop(path[-1], None)
    fn.__name__ = "drop_" + "_".join(map(str, path))
    MUTANTS.append((fn.__name__, M(fn)))


for k in ("id", "title", "synopsis", "ending", "characters", "locations", "panels"):
    _drop([k])
for k in ("id", "name", "kind", "gender", "base", "outfits", "photo"):
    _drop(["characters", 0, k])
for k in ("id", "name", "tag_prompt"):
    _drop(["locations", 0, k])
for k in ("shot", "location_id", "characters", "visual_tags", "bubbles", "sfx", "gap_after"):
    _drop(["panels", 1, k])
for k in ("speaker_id", "text", "kind"):
    _drop(["panels", 1, "bubbles", 0, k])


@mutant
def outfits_no_default(s):
    o = s["characters"][0]["outfits"]
    o["other"] = o.pop("default")


@mutant
def outfits_and_ids_missing(s):
    for c in s["characters"]:
        c.pop("id")
        c["outfits"] = {}


@mutant
def banned_base_nude(s):
    s["characters"][0]["base"] += ", nude"


@mutant
def banned_photo_bikini(s):
    s["characters"][0]["photo"] += " in a bikini"


@mutant
def banned_outfit_lingerie(s):
    s["characters"][0]["outfits"]["default"] = "black lingerie, " + s["characters"][0]["outfits"]["default"]


@mutant
def banned_all_fields(s):
    c = s["characters"][-1]
    c["base"] = "Teenager, " + c["base"]
    c["photo"] = "a school girl " + c["photo"]
    c["outfits"] = {k: v + ", Gucci bag, kissing" for k, v in c["outfits"].items()}


@mutant
def banned_child_word(s):
    s["characters"][0]["base"] = s["characters"][0]["base"].replace("female", "child female")


@mutant
def banned_czech(s):
    s["characters"][0]["photo"] += ", dítě, holčička, školák"


@mutant
def banned_kids_words(s):
    s["characters"][0]["outfits"]["default"] += ", blood stains, wine glass, zabil"


@mutant
def banned_petite(s):
    s["characters"][0]["base"] = "petite, " + s["characters"][0]["base"]


@mutant
def banned_long_field(s):
    s["characters"][0]["photo"] = "x" * 80 + " bra " + "y" * 30


@mutant
def base_no_adult(s):
    for c in s["characters"]:
        c["base"] = ", ".join(t for t in c["base"].split(", ") if t != "adult")


@mutant
def base_no_mature(s):
    for c in s["characters"]:
        c["base"] = c["base"].replace("mature female", "woman").replace("mature male", "man")


@mutant
def base_free_ok(s):
    for c in s["characters"]:
        if "adult" not in c["base"]:
            c["base"] = "adult, " + c["base"]
        c["base"] = c["base"].replace("petite, ", "")


@mutant
def base_tag_case(s):
    s["characters"][0]["base"] = "Adult , MATURE_FEMALE, " + s["characters"][0]["base"]


@mutant
def kids_child_prefix(s):
    for c in s["characters"]:
        if c.get("kind") == "child":
            c["base"] = c["base"].replace("female child, ", "girl, female child, ").replace("male child, ", "child male, ")


@mutant
def kids_adult_prefix(s):
    for c in s["characters"]:
        if c.get("kind") == "adult":
            c["base"] = "mature female, adult, " + c["base"]


@mutant
def kids_creature_human(s):
    for c in s["characters"]:
        if c.get("kind") not in ("child", "adult"):
            c["photo"] += " like a little person"
            c["kind"] = "robot"


@mutant
def kids_creature_girl(s):
    s["characters"][-1].update(kind="spirit", base="1girl, ghost, glowing")


@mutant
def kids_gender_bad(s):
    for c in s["characters"]:
        c["gender"] = "x"


@mutant
def kind_dropped_all(s):
    for c in s["characters"]:
        c.pop("kind", None)


@mutant
def photo_clothing(s):
    s["characters"][0]["photo"] += ", wearing a Coat"


@mutant
def photo_age_young(s):
    for c in s["characters"]:
        c["photo"] = c["photo"].replace("aged ", "aged 1")[:-0 or None].replace("aged 12", "aged 19")


@mutant
def photo_no_age(s):
    for c in s["characters"]:
        c["photo"] = c["photo"].replace("aged", "about")


@mutant
def photo_age_15_child(s):
    for c in s["characters"]:
        if c.get("kind") == "child":
            c["photo"] = c["photo"].replace("aged 8", "aged 15").replace("aged 9", "aged 5")


@mutant
def photo_adult_20(s):
    for c in s["characters"]:
        if c.get("kind", "adult") == "adult":
            c["photo"] = "a person aged 20"


@mutant
def panel0_not_establishing(s):
    s["panels"][0]["shot"] = "wide"


@mutant
def panel0_with_char(s):
    s["panels"][0]["characters"] = [{"id": s["characters"][0]["id"]}]


@mutant
def last_gap_small(s):
    s["panels"][-1]["gap_after"] = "small"


@mutant
def animate_three(s):
    for p in s["panels"][1:4]:
        p.update(animate=True, motion="hair swaying, ambient only, static camera")


@mutant
def animate_no_motion(s):
    s["panels"][2]["animate"] = True
    s["panels"][2].pop("motion", None)


@mutant
def animate_empty_motion(s):
    s["panels"][2].update(animate=True, motion="")


@mutant
def animate_empty_motion_two(s):
    i = _first_with(s, 2)
    s["panels"][i].update(animate=True, motion="")


@mutant
def animate_missing_motion_two(s):  # original code raises KeyError here
    i = _first_with(s, 2)
    s["panels"][i]["animate"] = True
    s["panels"][i].pop("motion", None)


@mutant
def motion_kiss(s):
    s["panels"][2].update(animate=True, motion="they kiss slowly")


@mutant
def motion_kissing(s):
    s["panels"][2].update(animate=True, motion="kissing, static camera")


@mutant
def motion_remove(s):
    s["panels"][2].update(animate=True, motion="she removes her scarf, Unbuttons")


@mutant
def motion_child(s):
    s["panels"][2].update(animate=True, motion="a child waving, static")


@mutant
def motion_blood(s):
    s["panels"][2].update(animate=True, motion="blood dripping, static camera")


@mutant
def motion_nude(s):
    s["panels"][2].update(animate=True, motion="nude figure, ambient only")


@mutant
def motion_two_people(s):
    i = _first_with(s, 2)
    s["panels"][i].update(animate=True, motion="they dance together")


@mutant
def motion_two_people_ok(s):
    i = _first_with(s, 2)
    s["panels"][i].update(animate=True, motion="hair moving, Ambient Only")


@mutant
def motion_without_animate(s):
    s["panels"][3].update(animate=False, motion="kiss, nude")


@mutant
def unknown_location(s):
    s["panels"][2]["location_id"] = "l_nowhere"


@mutant
def unknown_character(s):
    s["panels"][2]["characters"] = [{"id": "ghost"}] + s["panels"][2]["characters"]


@mutant
def unknown_outfit(s):
    s["panels"][2]["characters"] = [{**c, "outfit": "tuxedo"} for c in s["panels"][2]["characters"]]


@mutant
def known_outfit(s):
    c = s["characters"][0]
    s["panels"][2]["characters"] = [{"id": c["id"], "outfit": next(iter(c["outfits"]))}]


@mutant
def empty_outfit(s):
    s["panels"][2]["characters"] = [{"id": s["characters"][0]["id"], "outfit": ""}]


@mutant
def panel_char_no_id(s):  # original code raises KeyError here
    s["panels"][2]["characters"] = [{"outfit": "default"}]


@mutant
def three_humans(s):
    ids = _human_ids(s)[:3] or [c["id"] for c in s["characters"][:3]]
    s["panels"][3]["characters"] = [{"id": i} for i in ids]
    s["panels"][3]["shot"] = "wide"


@mutant
def three_closeup(s):
    s["panels"][3]["characters"] = [{"id": c["id"]} for c in s["characters"][:3]]
    s["panels"][3]["shot"] = "close-up"


@mutant
def couple_closeup(s):
    i = _first_with(s, 2)
    s["panels"][i]["shot"] = "close-up"


@mutant
def same_gender(s):
    for c in s["characters"]:
        c["gender"] = "f"


@mutant
def same_gender_three(s):
    for c in s["characters"]:
        c["gender"] = "m"
    s["panels"][3]["characters"] = [{"id": c["id"]} for c in s["characters"][:3]]


@mutant
def same_gender_unknown(s):
    s["characters"][0]["gender"] = s["characters"][1]["gender"]
    s["panels"][3]["characters"] = [{"id": s["characters"][0]["id"]}, {"id": "nobody"}, {"id": s["characters"][1]["id"]}]


@mutant
def establishing_mid(s):
    s["panels"][4]["shot"] = "establishing"


@mutant
def banned_tag(s):
    s["panels"][2]["visual_tags"] = s["panels"][2]["visual_tags"] + ["cleavage", "blood"]


@mutant
def banned_tag_age(s):
    s["panels"][2]["visual_tags"] = ["loli"] + s["panels"][2]["visual_tags"]


@mutant
def banned_tag_child(s):
    s["panels"][2]["visual_tags"] = ["child", "kiss"] + s["panels"][2]["visual_tags"]


@mutant
def bubble_age(s):
    s["panels"][2]["bubbles"].append({"speaker_id": "", "text": "Byla jsem ještě dítě.", "kind": "narration"})


@mutant
def bubble_kids(s):
    s["panels"][2]["bubbles"].append({"speaker_id": "", "text": "Všude byla krev a pak ho políbila.", "kind": "narration"})


@mutant
def bubble_banned_sfw(s):
    s["panels"][2]["bubbles"].append({"speaker_id": "", "text": "nude bikini teen", "kind": "narration"})


@mutant
def narration_speaker(s):
    s["panels"][2]["bubbles"].append({"speaker_id": s["characters"][0]["id"], "text": "Hm.", "kind": "narration"})


@mutant
def speaker_absent(s):
    s["panels"][0]["bubbles"].append({"speaker_id": s["characters"][0]["id"], "text": "Ahoj.", "kind": "speech"})
    s["panels"][2]["bubbles"].append({"speaker_id": "", "text": "...", "kind": "thought"})


@mutant
def sentence_tags(s):
    s["panels"][2]["visual_tags"] += ["she is looking at the sea with a sad face", "taking off her earrings gently",
                                      "one two three four five six seven", "1 2 3 4 5 6"]


@mutant
def sentence_tag_known(s):
    s["panels"][3]["visual_tags"] += ["a b c d e f g h"]


@mutant
def empty_panels(s):  # original code raises IndexError here
    s["panels"] = []


@mutant
def everything(s):
    for name, fn in MUTANTS:
        if name in ("banned_all_fields", "base_no_adult", "kids_gender_bad", "photo_clothing", "panel0_with_char",
                    "last_gap_small", "animate_three", "motion_kiss", "unknown_location", "unknown_outfit",
                    "couple_closeup", "same_gender", "establishing_mid", "banned_tag", "bubble_age", "bubble_kids",
                    "narration_speaker", "speaker_absent", "sentence_tags", "three_humans"):
            s.update(fn(s))


def mutants():
    """[(name, story)] for every mutant of every example (a mutant that does not apply is skipped)."""
    out = []
    for ex_name, ex in examples().items():
        out.append((f"{ex_name}/orig", ex))
        for name, fn in MUTANTS:
            try:
                out.append((f"{ex_name}/{name}", fn(ex)))
            except (TypeError, IndexError, KeyError, AttributeError):
                pass
    return out


def check_cases():
    """[(case id, lean story)] for check(): data/stories (two lean forms), examples, mutants."""
    out = []
    for sid, w, sb in stories():
        out.append((f"stories/{sid}", lean(w, sb)))
        if any("base" not in c for c in w["characters"]):
            out.append((f"stories/{sid}/tags", lean(w, sb, base_from_tags=True)))
    return out + mutants()


MODES = [("adult", False), ("free", True), ("kids", False)]  # (audience, free) as adapt.main() can call check()
