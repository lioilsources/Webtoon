"""Storyboard panel → positive/negative prompt (§5.4 prompt order).

Order: quality, count tags, character tag_prompt, artist/style preset, scene tags, special.
"""

import re

from common import dedupe, split_tags

# Design attributes owned by the character's tag_prompt; scene tags must not override them.
DESIGN_RE = re.compile(r"\b(hair|eyes|skin|freckles|jacket|shirt|shorts|skirt|pantyhose|footwear|boots|dress|uniform)\b")

COUNT_TAGS = {"1girl", "1boy", "2girls", "2boys", "3girls", "multiple girls", "multiple boys", "solo", "no humans"}


def count_tags(chars):
    girls = sum(1 for c in chars if c.get("count_tag") == "1girl")
    boys = sum(1 for c in chars if c.get("count_tag") == "1boy")
    tags = []
    if girls:
        tags.append("1girl" if girls == 1 else f"{girls}girls")
    if boys:
        tags.append("1boy" if boys == 1 else f"{boys}boys")
    if not chars:
        tags.append("no humans")
    elif len(chars) == 1:
        tags.append("solo")
    return tags


def build(panel, world, styles, preset_id=None, sfw=True):
    preset = styles["presets"][preset_id or world["style_id"]]
    chars_by_id = {c["id"]: c for c in world["characters"]}
    locs = {l["id"]: l for l in world["locations"]}
    chars = [chars_by_id[c["id"]] for c in panel.get("characters", []) if c["id"] in chars_by_id]

    char_tags = []
    for c in chars:
        char_tags += split_tags(c.get("tag_prompt") or "")
    design = set(char_tags)

    scene = [t for t in panel.get("visual_tags", []) if t not in COUNT_TAGS]
    if chars:
        scene = [t for t in scene if t in design or not DESIGN_RE.search(t)]
    loc = locs.get(panel.get("location_id"))
    loc_tags = split_tags(loc["tag_prompt"]) if loc else []
    shot = styles["shot_tags"].get(panel.get("shot"), [])
    if chars:
        shot = [t for t in shot if t != "no humans"]

    pos = dedupe(
        preset["quality_pos"]
        + count_tags(chars)
        + char_tags
        + preset["artist_tags"] + preset["aesthetic_tags"]
        + shot + scene + loc_tags
        + (styles["sfw_positive"] if sfw else [])
    )
    neg = dedupe(preset["quality_neg"] + styles["always_negative"] + (styles["sfw_negative"] if sfw else []))
    # A negative tag the scene needs (e.g. "letters" vs. a letter being delivered) would fight the positive.
    pos_forms = set(pos) | {t + "s" for t in pos}
    neg = [t for t in neg if t not in pos_forms]
    w, h = styles["shot_size"].get(panel.get("shot"), [832, 1216])
    return {"positive": ", ".join(pos), "negative": ", ".join(neg), "width": w, "height": h, "preset": preset}
