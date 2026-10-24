"""Storyboard panel → positive/negative prompt (§5.4 prompt order).

Order: quality, count tags, character tag_prompt, artist/style preset, scene tags, special.
"""

import rules
from common import dedupe, split_tags

# The rules (and why) live in rules/base/prompts.yaml and the profiles; data/styles.json holds the presets they pick from.
R = rules.load("prompts")
_RE = rules.regexes(R["regex"])
DESIGN_RE, EXPRESSION_RE, LOWER_RE, FEET_RE, COLOR_RE = (_RE[k] for k in ("design", "expression", "lower", "feet", "color"))
AGE_ANCHOR = set(R["age_anchor"])
COUNT_TAGS = set(R["count_tags"])
AGE_NEGATIVE = list(rules.cfg("prompts", "free")["negative"]["tags"])
NATURAL = R["natural"]


def count_tags(chars):
    girls = sum(1 for c in chars if c.get("count_tag") == "1girl")
    boys = sum(1 for c in chars if c.get("count_tag") == "1boy")
    tags = []
    if girls:
        tags.append("1girl" if girls == 1 else f"{girls}girls")
    if boys:
        tags.append("1boy" if boys == 1 else f"{boys}boys")
    if not girls and not boys:
        tags.append("no humans")  # empty panel, or animals only: keep the model from adding a girl
        if len(chars) == 1:
            tags.append("solo")  # one pet, not a litter
    elif len(chars) == 1:
        tags.append("solo")
    return tags


def build(panel, world, styles, preset_id=None, sfw=True, regional=False):
    preset = styles["presets"][preset_id or world["style_id"]]
    chars_by_id = {c["id"]: c for c in world["characters"]}
    locs = {l["id"]: l for l in world["locations"]}
    chars = [chars_by_id[c["id"]] for c in panel.get("characters", []) if c["id"] in chars_by_id]

    outfits = {c["id"]: c.get("outfit") for c in panel.get("characters", [])}

    def design_of(c):
        o = outfits.get(c["id"])
        if o and "base" in c:
            return c["base"] + ", " + c.get("outfits", {}).get(o, o)  # a named outfit, or tags given inline
        return c.get("tag_prompt") or ""

    if preset.get("natural"):
        return _natural(panel, chars, design_of, locs, styles, preset, world, sfw)

    def tags_of(c):
        tags = split_tags(design_of(c))
        if panel.get("shot") == "close-up":
            tags = [t for t in tags if not LOWER_RE.search(t)]
        elif panel.get("shot") in ("medium", "over-shoulder"):
            tags = [t for t in tags if not FEET_RE.search(t)]
        return tags

    design = set(split_tags(" , ".join(design_of(c) for c in chars)))
    scene = [t for t in panel.get("visual_tags", []) if t not in COUNT_TAGS]
    if chars:
        scene = [t for t in scene if t in design or EXPRESSION_RE.search(t) or not DESIGN_RE.search(t)]
    loc = locs.get(panel.get("location_id"))
    loc_tags = split_tags(loc["tag_prompt"]) if loc else []
    if panel.get("shot") == "close-up":
        loc_tags = loc_tags[:R["close_up_location_tags"]]  # a full scene description pulls the camera back to a medium shot
    shot = styles["shot_tags"].get(panel.get("shot"), [])
    if chars:
        shot = [t for t in shot if t != "no humans"]
    style = preset["artist_tags"] + preset["aesthetic_tags"]

    # One flat tag list lets SDXL swap hair, eyes and clothes between two people (the blonde turns brunette):
    # with regional=True (render.py --regions) each character gets its own prompt over its strip of the frame (comfy.workflow regions).
    regions = []
    if regional and len(chars) > 1:
        regions = [dedupe(preset["quality_pos"] + [c["count_tag"]] * bool(c.get("count_tag")) + weight(tags_of(c)) + style)
                   for c in chars]
        char_tags = [t for c in chars for t in tags_of(c) if t in AGE_ANCHOR]  # the shared prompt still says who is adult
        scene = [t for t in scene if EXPRESSION_RE.search(t) or not DESIGN_RE.search(t)]  # design lives in the regions
    else:
        char_tags = [t for c in chars for t in tags_of(c)]

    pos = dedupe(
        preset["quality_pos"]
        + count_tags(chars)
        + char_tags
        + style
        + shot + scene + loc_tags
        + (styles["sfw_positive"] if sfw else [])
    )
    neg = dedupe(preset["quality_neg"] + styles["always_negative"] + (styles["sfw_negative"] if sfw else [])
                 + audience_negative(world, styles))
    # A negative tag the scene needs (e.g. "letters" vs. a letter being delivered) would fight the positive.
    pos_forms = {t for tags in [pos, *regions] for t in tags} | {t + "s" for t in pos}
    neg = [t for t in neg if t not in pos_forms]
    w, h = styles["shot_size"].get(panel.get("shot"), R["default_size"])
    return {"positive": ", ".join(pos), "negative": ", ".join(neg), "width": w, "height": h, "preset": preset,
            "regions": [", ".join(r) for r in regions]}


def weight(tags):
    return [R["color_weight"].format(t=t) if COLOR_RE.match(t) else t for t in tags]


def audience_negative(world, styles):
    if world.get("free"):
        return AGE_NEGATIVE
    # the world's profile: free worlds (local_strip.sh -f) lose the SFW negatives, never the age ones; teen: none
    neg = rules.cfg("prompts", rules.world_profile(world))["negative"]
    return list(neg["tags"]) if "tags" in neg else styles.get(neg["styles"], []) if "styles" in neg else []


def _natural(panel, chars, design_of, locs, styles, preset, world, sfw):
    """Photoreal checkpoints (Juggernaut, RealVis, …) read sentences better than booru tags:
    each character is its `photo` description plus the panel's outfit."""
    people = []
    for c in chars:
        o = {p["id"]: p.get("outfit") for p in panel.get("characters", [])}.get(c["id"])
        desc = c.get("photo") or design_of(c)
        wear = c.get("outfits", {}).get(o, o) if o else c.get("outfits", {}).get("default")
        people.append(desc + (NATURAL["wearing"].format(wear=wear) if wear else ""))
    loc = locs.get(panel.get("location_id"))
    shot = styles.get("natural_shot", {}).get(panel.get("shot"), [])
    action = [t for t in panel.get("visual_tags", []) if t not in COUNT_TAGS and t not in NATURAL["drop_tags"]]
    if len(people) == 2:
        # Photoreal models drop the second person unless the pair leads the prompt.
        lead = [NATURAL["couple_lead"]] + action + [NATURAL["couple_person"].format(p=p) for p in people]
    elif len(people) == 1:
        lead = [NATURAL["one_lead"], NATURAL["one_person"].format(p=people[0])] + action
    elif people:
        lead = [NATURAL["group_lead"].format(n=len(people))] + action + [NATURAL["group_person"].format(p=p) for p in people]
    else:
        lead = [NATURAL["empty"]] + action
    pos = dedupe(preset["quality_pos"] + shot + lead
                 + (split_tags(loc["tag_prompt"]) if loc else []) + preset["aesthetic_tags"])
    neg = dedupe(preset["quality_neg"] + styles["always_negative"] + (styles["sfw_negative"] if sfw else [])
                 + audience_negative(world, styles))
    w, h = styles["shot_size"].get(panel.get("shot"), R["default_size"])
    return {"positive": ", ".join(pos), "negative": ", ".join(neg), "width": w, "height": h, "preset": preset}
