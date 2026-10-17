"""Character description → fixed booru tag_prompt (§5.4 level 1).

    python3 m0/gen_character.py [--world data/world_m0.json] [--force]

Writes tag_prompt (and unknown_tags for review) back into the world file.
"""

import argparse

from common import DATA, dedupe, filter_tags, llm_json, load_json, save_json, split_tags

SYSTEM = """You convert a character description into a FIXED Danbooru tag list for an SDXL anime model (NoobAI-XL / Illustrious).
Rules:
- Output JSON: {"tags": ["...", ...], "notes": "..."}
- Only real Danbooru general tags, lowercase, spaces instead of underscores.
- Describe the DESIGN only: hair color + length + style, eye color, face marks, every clothing item separately (with color), accessories, body marks.
- 12-25 tags, ordered: hair, eyes, face, top, bottom, legwear, footwear, accessories.
- NO count tags (1girl), NO pose, NO emotion, NO background, NO camera, NO quality tags, NO character/copyright names.
- Use the most common Danbooru spelling (e.g. "short hair", "messy hair", "green eyes", "freckles", "goggles on head", "black pantyhose", "cross-laced footwear").
- Colors must use standard Danbooru color words (orange hair, brown hair, aqua eyes...), never "copper", "auburn" etc.
- Hair color and eye color are MANDATORY.
"""

REPAIR = """These Danbooru tags do not exist: {unknown}
For each, give the closest EXISTING Danbooru general tag(s) that keep the visual meaning (e.g. "copper hair" -> "orange hair", "brown boots" -> "brown footwear", "boots"; "leather bracelet" -> "bracelet"). Drop it only if nothing fits.
Output JSON: {{"replace": {{"<bad tag>": ["<tag>", ...]}}}}"""


def make_tag_prompt(ch):
    user = f"Name: {ch['name']}\nDescription: {ch['description']}"
    best = None
    for _ in range(3):
        res = llm_json(SYSTEM, user, temperature=0.3)
        tags = dedupe(split_tags(res.get("tags", [])))
        known, unknown = filter_tags(tags)
        if unknown:
            rep = llm_json(SYSTEM, REPAIR.format(unknown=unknown), temperature=0.2).get("replace", {})
            fixed = [t for u in unknown for t in split_tags(rep.get(u, []))]
            k2, unknown = filter_tags(fixed)
            known = dedupe(known + k2)
        if best is None or len(unknown) < len(best[1]):
            best = (known, unknown)
        if not unknown:
            break
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default=str(DATA / "world_m0.json"))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    world = load_json(args.world)
    for ch in world["characters"]:
        if ch.get("tag_prompt") and not args.force:
            print(f"{ch['id']}: keeping existing tag_prompt")
            continue
        known, unknown = make_tag_prompt(ch)
        ch["tag_prompt"] = ", ".join(known)
        ch["unknown_tags"] = unknown
        print(f"{ch['id']}: {ch['tag_prompt']}")
        if unknown:
            print(f"  dropped (not in WD14 vocab): {unknown}")
    save_json(args.world, world)


if __name__ == "__main__":
    main()
