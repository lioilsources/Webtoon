"""Paragraph / player choice → storyboard JSON (§5.1–5.3), validated.

    python3 m0/storyboard.py --text "Vesna dostane svítící dopis…" --out out/<run>/storyboard.json
"""

import argparse
import json

from common import DATA, dedupe, filter_tags, llm_json, load_json, save_json, split_tags, translate_tags

SHOTS = ["close-up", "medium", "wide", "over-shoulder", "establishing"]
BUBBLE_KINDS = ["speech", "thought", "shout", "narration"]
GAPS = ["small", "medium", "large"]
MIN_PANELS, MAX_PANELS = 6, 8

SYSTEM = """You are the storyboard writer of an interactive vertical webtoon. You write ONE episode as strict JSON.

WORLD (static bible):
{world}

CHARACTERS (use only these ids):
{characters}

LOCATIONS (use only these ids):
{locations}

CANON NODES not yet reached (the episode may advance at most one): {canon}
CONSTRAINTS (never break): {constraints}

OUTPUT JSON schema:
{{
  "title": "<episode title in {lang}>",
  "panels": [
    {{
      "shot": one of {shots},
      "location_id": "<location id>",
      "characters": [{{"id": "<character id>", "emotion": "<booru emotion tag>", "action": "<booru pose/action tags>"}}],
      "visual_prompt": "<comma separated Danbooru tags: pose, action, expression, props, lighting, camera angle. NO character design tags (hair/clothes are added automatically), NO names, NO text>",
      "bubbles": [{{"speaker_id": "<character id or null for narration>", "text": "<{lang}>", "kind": one of {kinds}}}],
      "sfx": [{{"text": "<onomatopoeia>", "style": "bold|shaky|soft"}}],
      "gap_after": one of {gaps}
    }}
  ],
  "choices": [
    {{"kind": "closed", "text": "<{lang}>"}},
    {{"kind": "closed", "text": "<{lang}>"}},
    {{"kind": "free", "text": "Nebo napiš, co uděláš…"}}
  ],
  "state_diff": {{"current_location": "<location id>", "open_threads_add": [], "open_threads_remove": [], "facts_add": [], "timeline_add": "<one sentence>", "mood": "<word>"}},
  "canon_nodes_reached": ["<canon node id>"]
}}

Rules:
- {min_p}-{max_p} panels. Start with an establishing or wide shot. Vary shots. End on a hook that sets up the choices.
- An "establishing" panel has NO characters.
- Max 2 bubbles per panel, max ~12 words per bubble. Text in {lang}, fits the speech style of the character.
- visual_prompt uses ONLY real Danbooru tags (e.g. "standing, holding letter, looking at viewer, surprised, open mouth, glowing, from side, wind, hair blowing").
- 2-3 closed choices + exactly 1 free choice.
"""


def _world_ctx(world):
    w = {k: world[k] for k in ("title", "synopsis", "tone", "audience") if k in world}
    w["rules"] = world.get("bible", {}).get("rules", [])
    chars = [{"id": c["id"], "name": c["name"], "role": c["role"], "personality": c.get("personality"),
              "speech_style": c.get("speech_style")} for c in world["characters"]]
    locs = [{"id": l["id"], "name": l["name"], "description": l["description"]} for l in world["locations"]]
    return w, chars, locs


def system_prompt(world, campaign_state):
    w, chars, locs = _world_ctx(world)
    reached = set(campaign_state.get("canon_progress", []))
    canon = [n for n in world.get("canon", {}).get("nodes", []) if n["id"] not in reached]
    return SYSTEM.format(
        world=json.dumps(w, ensure_ascii=False), characters=json.dumps(chars, ensure_ascii=False),
        locations=json.dumps(locs, ensure_ascii=False), canon=json.dumps(canon, ensure_ascii=False),
        constraints=json.dumps(world.get("canon", {}).get("constraints", []), ensure_ascii=False),
        lang=world.get("language", "cs"), shots=SHOTS, kinds=BUBBLE_KINDS, gaps=GAPS,
        min_p=MIN_PANELS, max_p=MAX_PANELS)


def validate(sb, world):
    """Returns a list of problems (empty = ok). Normalises tags in place."""
    errs = []
    char_ids = {c["id"] for c in world["characters"]}
    allowed = set(world.get("permissions", {}).get("allowed_locations") or [l["id"] for l in world["locations"]])
    panels = sb.get("panels")
    if not isinstance(panels, list):
        return ["panels missing"]
    if not MIN_PANELS <= len(panels) <= MAX_PANELS:
        errs.append(f"panel count {len(panels)} not in {MIN_PANELS}-{MAX_PANELS}")
    for i, p in enumerate(panels):
        if p.get("shot") not in SHOTS:
            errs.append(f"panel {i}: bad shot {p.get('shot')!r}")
        if p.get("location_id") not in allowed:
            errs.append(f"panel {i}: location {p.get('location_id')!r} not allowed")
        for c in p.get("characters", []):
            if c.get("id") not in char_ids:
                errs.append(f"panel {i}: unknown character {c.get('id')!r}")
        if p.get("shot") == "establishing" and p.get("characters"):
            p["shot"] = "wide"  # cheap fix rather than a regeneration
        for b in p.get("bubbles", []):
            if b.get("kind") not in BUBBLE_KINDS:
                b["kind"] = "speech"
            if b.get("speaker_id") not in char_ids and b["kind"] != "narration":
                errs.append(f"panel {i}: bubble speaker {b.get('speaker_id')!r} unknown")
        if p.get("gap_after") not in GAPS:
            p["gap_after"] = "medium"
        tags = split_tags(p.get("visual_prompt", ""))
        for c in p.get("characters", []):
            tags += split_tags(c.get("emotion", "")) + split_tags(c.get("action", ""))
        known, unknown = filter_tags(dedupe(tags))
        p["visual_tags"] = known
        p["unmapped_phrases"] = unknown
    # One LLM call for the whole episode instead of one per panel.
    phrases = dedupe([u for p in panels for u in p["unmapped_phrases"]])
    if phrases:
        mapped = translate_tags(phrases)
        for p in panels:
            extra = [t for u in p["unmapped_phrases"] for t in mapped.get(u, [])]
            p["visual_tags"] = dedupe(p["visual_tags"] + extra)
    choices = sb.get("choices", [])
    closed = [c for c in choices if c.get("kind") == "closed"]
    free = [c for c in choices if c.get("kind") == "free"]
    if not 2 <= len(closed) <= 3 or len(free) != 1:
        errs.append(f"choices: {len(closed)} closed / {len(free)} free")
    return errs


RULE_CHECK = """You check a webtoon episode against the world rules and constraints.
RULES: {rules}
CONSTRAINTS: {constraints}
AUDIENCE: {audience}
Episode JSON:
{episode}
Report ONLY violations that actually HAPPEN on-panel (a character explicitly does the forbidden thing, or content unfit for the audience).
Also check the offered choices: a choice suggesting self-harm or suicide, or content unfit for the audience, IS a violation (panel = "choices").
Intentions, hints, mysteries, moving toward a place or mere mentions are NOT violations. Doing something adjacent is NOT a violation (delivering a letter is not opening it).
Output JSON: {{"violations": [{{"rule": "<quoted rule>", "panel": <index>, "evidence": "<what exactly happens>", "certain": true|false}}]}}
Empty list if none. When in doubt, do not report."""


def rule_check(sb, world):
    slim = {"title": sb.get("title"),
            "panels": [{"visual_prompt": p.get("visual_prompt"), "bubbles": p.get("bubbles")} for p in sb["panels"]],
            "choices": sb.get("choices"), "state_diff": sb.get("state_diff")}
    res = llm_json("You are a strict continuity editor.", RULE_CHECK.format(
        rules=world.get("bible", {}).get("rules", []), constraints=world.get("canon", {}).get("constraints", []),
        audience=world.get("audience"), episode=json.dumps(slim, ensure_ascii=False)), temperature=0.1)
    out = []
    for v in res.get("violations", []):
        if isinstance(v, dict) and v.get("certain") is True:
            out.append(f"panel {v.get('panel')}: {v.get('rule')} — {v.get('evidence')}")
    return out


def generate(world, user_text, campaign_state=None, attempts=3):
    campaign_state = campaign_state or {}
    system = system_prompt(world, campaign_state)
    user = f"STORY STATE: {json.dumps(campaign_state.get('state', {}), ensure_ascii=False)}\n\nEPISODE PREMISE / PLAYER CHOICE:\n{user_text}"
    feedback, log, soft = "", [], None
    for attempt in range(attempts):
        sb = llm_json(system, user + feedback, temperature=0.8)
        errs = validate(sb, world)
        rule_only = False
        if not errs:
            errs = [f"rule violation: {v}" for v in rule_check(sb, world)]
            rule_only = bool(errs)
        log.append({"attempt": attempt, "errors": errs})
        if not errs:
            sb["_validation"] = log
            return sb
        if rule_only:
            soft = sb
        feedback = "\n\nYOUR PREVIOUS ATTEMPT WAS REJECTED. Fix these problems:\n- " + "\n- ".join(errs)
    if soft is not None:
        # Schema-valid but the rule checker still objects: accept, flag for review.
        soft["_validation"] = log
        soft["_warnings"] = log[-1]["errors"]
        return soft
    raise RuntimeError(f"storyboard failed validation: {log}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", default=str(DATA / "world_m0.json"))
    ap.add_argument("--text", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    world = load_json(args.world)
    sb = generate(world, args.text)
    save_json(args.out, sb)
    print(f"{sb['title']}: {len(sb['panels'])} panels, attempts={len(sb['_validation'])}")
    for w in sb.get("_warnings", []):
        print(f"  WARNING {w}")
    for i, p in enumerate(sb["panels"]):
        print(f"  {i} {p['shot']:<14} {p['location_id']:<9} {', '.join(p['visual_tags'])[:110]}")
        if p["unmapped_phrases"]:
            print(f"     from phrases: {p['unmapped_phrases']}")


if __name__ == "__main__":
    main()
