"""Golden outputs from the Python M0 prototype (pure functions only, no network).

    python3 -B internal/testdata/gen_golden.py internal/testdata/golden_m0.json
"""
import copy, json, sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "m0"))
sys.dont_write_bytecode = True
import common, storyboard, prompts, state, comfy, render, gen_character

world = common.load_json(common.DATA / "world_m0.json")
styles = common.load_json(common.DATA / "styles.json")
ep1 = common.load_json(common.ROOT / "out/dev/storyboard_ep1.json")
ep2 = common.load_json(common.ROOT / "out/dev/storyboard_ep2.json")

def raw_sb(sb):
    sb = copy.deepcopy(sb)
    for k in list(sb):
        if k.startswith("_"):
            del sb[k]
    for p in sb["panels"]:
        p.pop("visual_tags", None); p.pop("unmapped_phrases", None)
    return sb

out = {}
out["system_prompt_empty"] = storyboard.system_prompt(world, {})
out["system_prompt_c1"] = storyboard.system_prompt(world, {"canon_progress": ["c1"]})

# validate with a stubbed translator
calls = []
def fake_translate(phrases, llm_system=None):
    calls.append(list(phrases))
    # deterministic: map each phrase to its first two candidates
    return {p: common.filter_tags(common.split_tags(common.tag_candidates(p)[:2]))[0] for p in phrases}
storyboard.translate_tags = fake_translate
raw1 = raw_sb(ep1)
out["ep1_raw"] = copy.deepcopy(raw1)
v = copy.deepcopy(raw1)
out["ep1_validate_errors"] = storyboard.validate(v, world)
out["ep1_validated"] = v
out["ep1_translate_phrases"] = calls[0] if calls else []
out["ep1_translate_prompt"] = common.TRANSLATE.format(items="\n".join(f"- {p!r}: {common.tag_candidates(p)}" for p in calls[0]))
out["candidates"] = {p: common.tag_candidates(p) for p in calls[0]}

# broken storyboard
bad = copy.deepcopy(raw1)
bad["panels"] = bad["panels"][:3]
bad["panels"][0]["shot"] = "aerial"
bad["panels"][1]["location_id"] = "l_moon"
bad["panels"][1]["characters"] = [{"id": "c_nobody", "emotion": "smile", "action": "standing"}]
bad["panels"][2]["bubbles"] = [{"speaker_id": "c_ghost", "text": "Ahoj", "kind": "whisper"}]
bad["panels"][2]["gap_after"] = "huge"
bad["choices"] = [{"kind": "closed", "text": "A"}]
calls.clear()
out["bad_raw"] = copy.deepcopy(bad)
out["bad_errors"] = storyboard.validate(bad, world)
out["bad_validated_panel2"] = bad["panels"][2]

# rule check prompt
captured = {}
def fake_llm(system, user, temperature=0.7, **kw):
    captured["system"], captured["user"] = system, user
    return {"violations": [
        {"rule": "Kurýři nikdy neotevírají cizí dopisy.", "panel": 3, "evidence": "opens it", "certain": True},
        {"rule": "x", "panel": "choices", "evidence": "maybe", "certain": False},
        {"rule": "y", "panel": None, "evidence": "z", "certain": "true"},
    ]}
storyboard.llm_json = fake_llm
out["rule_violations"] = storyboard.rule_check(v, world)
out["rule_check_prompt"] = captured["user"]
out["user_prompt"] = f"STORY STATE: {json.dumps(ep2['_campaign'].get('state', {}), ensure_ascii=False)}\n\nEPISODE PREMISE / PLAYER CHOICE:\nhello"

# prompt builder
out["prompts"] = [prompts.build(p, world, styles) for p in ep1["panels"]]
for p in out["prompts"]:
    p.pop("preset")
out["prompts_nosfw"] = [prompts.build(p, world, styles, "hassaku_soft", sfw=False) for p in ep1["panels"][:2]]
for p in out["prompts_nosfw"]:
    p.pop("preset")

# shot-aware prompts: every shot on the M0 character (close-ups drop lower-body tags, medium/over-shoulder footwear)
shot_panels = [{"shot": shot, "location_id": "l_market", "characters": [{"id": "c_vesna"}],
                "visual_tags": ["1girl", "smile", "long hair", "brown shorts", "boots", "holding letter"]}
               for shot in ["close-up", "medium", "over-shoulder", "wide", "establishing", "sheet"]]
out["shot_panels"] = shot_panels
out["shot_prompts"] = [prompts.build(p, world, styles) for p in shot_panels]
for p in out["shot_prompts"]:
    p.pop("preset")
out["sheet_panel"] = render.sheet_panel(world["characters"][0])
# romance worlds: outfits per panel, photoreal presets in sentences (natural), adult negative,
# expression tags that mention hair/eyes; a 3-person panel for the group case
rworld = common.load_json(common.DATA / "stories/rb_06_la/world.json")
rpanels = common.load_json(common.DATA / "stories/rb_06_la/storyboard.json")["panels"]
rworld["characters"].append({"id": "friend", "name": "Friend", "role": "npc", "count_tag": "1girl",
                             "tag_prompt": "adult, short hair, black hair"})  # no base/photo: falls back to tag_prompt
a, b = rworld["characters"][0]["id"], rworld["characters"][1]["id"]
rpanels = rpanels + [dict(rpanels[-1], characters=[{"id": a, "outfit": "pink sundress"}, {"id": b, "outfit": "dinner"},
                                                   {"id": "friend", "outfit": "dinner"}],
                          visual_tags=["closed eyes", "wet hair", "red hair", "laughing"])]
out["romance_world"] = rworld
out["romance_panels"] = rpanels
out["romance_prompts"] = [prompts.build(p, rworld, styles) for p in rpanels]
out["romance_prompts_anime"] = [prompts.build(p, rworld, styles, "webtoon_romance") for p in rpanels]
for p in out["romance_prompts"] + out["romance_prompts_anime"]:
    p.pop("preset")

out["sheet_prompt"] = prompts.build(render.sheet_panel(world["characters"][0]), world, styles)
out["sheet_prompt"].pop("preset")

# identity scoring on in-frame design tags
char = world["characters"][0]
seen = {"short hair": 0.9, "orange hair": 0.8, "green eyes": 0.5, "freckles": 0.34, "white shirt": 0.36,
        "brown shorts": 0.7, "boots": 0.6, "smile": 0.9}
out["identity"] = [{"shot": shot, "general": seen, "identity": render.identity({"general": seen}, char, shot or None)}
                   for shot in ["", "close-up", "medium", "over-shoulder", "wide", "sheet"]]

# ComfyUI workflow graphs (prompt-only, IP-Adapter defaults, configured IP-Adapter)
wf = []
for args in [
    dict(positive="a, b", negative="c", width=832, height=1216, seed=1000, preset="clean_webtoon", prefix="webtoon/x/p00_s0"),
    dict(positive="a", negative="c", width=1216, height=832, seed=7, preset="hassaku_soft", prefix="x", ref="ref.png"),
    dict(positive="a", negative="c", width=832, height=1216, seed=9, preset="clean_webtoon", prefix="x", ref="face.png",
         ip_weight=0.35, ip_preset="PLUS FACE (portraits)", ip_end=0.6),
    dict(positive="a", negative="c", width=832, height=1216, seed=11, preset="fashion_editorial", prefix="x"),
    dict(positive="a", negative="c", width=832, height=1216, seed=12, preset="anime_screencap", prefix="x", ref="ref.png"),
]:
    kw = dict(ref_image=args.get("ref"))
    for k in ("ip_weight", "ip_preset", "ip_end"):
        if k in args:
            kw[k] = args[k]
    g = comfy.workflow(args["positive"], args["negative"], args["width"], args["height"], args["seed"],
                       styles["presets"][args["preset"]], args["prefix"], **kw)
    wf.append({"args": args, "graph": g})
out["workflows"] = wf

# character tag_prompt generation (m0/gen_character.py) with a scripted LLM
gc_calls = []
gc_replies = [
    {"tags": ["Short_Hair", "orange hair", "copper braid", "green eyes", "leather bracelet", "orange hair", "brown boots"], "notes": "n"},
    {"replace": {"copper braid": ["braid", "orange hair"], "leather bracelet": ["bracelet"], "brown boots": ["brown footwear", "bootz"]}},
    {"tags": ["short hair", "green eyes", "glowy aura"]},
    {"replace": {"glowy aura": ["qqq", "zzz"]}},
    {"tags": ["short hair", "green eyes", "zzz unknown", "yyy unknown"]},
    {"replace": {"zzz unknown": ["qqq"], "yyy unknown": ["freckles"]}},
]
def gc_llm(system, user, temperature=0.7, **kw):
    gc_calls.append({"system": system, "user": user, "temperature": temperature})
    return gc_replies[len(gc_calls) - 1]
gen_character.llm_json = gc_llm
ch = {"name": "Vesna", "description": "Mladá kurýrka s krátkými zrzavými vlasy."}
out["gen_character_system"] = gen_character.SYSTEM
out["gen_character_replies"] = gc_replies
known, unknown = gen_character.make_tag_prompt(ch)
out["gen_character_result"] = {"known": known, "unknown": unknown}
out["gen_character_calls"] = gc_calls
# second scenario: first attempt leaves an unknown tag, the second is clean
gc_calls2 = []
gc_replies2 = [
    {"tags": ["short hair", "glowy aura"]},
    {"replace": {"glowy aura": "qqq, sparkle"}},
    {"tags": ["short hair", "green eyes"]},
]
def gc_llm2(system, user, temperature=0.7, **kw):
    gc_calls2.append({"system": system, "user": user, "temperature": temperature})
    return gc_replies2[len(gc_calls2) - 1]
gen_character.llm_json = gc_llm2
known2, unknown2 = gen_character.make_tag_prompt(ch)
out["gen_character2_replies"] = gc_replies2
out["gen_character2_result"] = {"known": known2, "unknown": unknown2}
out["gen_character2_calls"] = gc_calls2

# filter
sample = ["red hair", "(red hair:1.2)", "artist:foo", "copper hair", "1girl", "establishing shot", "(nonsense tag)", "smile"]
out["filter_sample"] = sample
out["filter_result"] = list(common.filter_tags(sample))
out["split_sample"] = common.split_tags("  Red_Hair,  green   eyes ,, ,Smile ")

# state
s0 = state.empty_state(world)
out["empty_state"] = s0
s1 = state.apply_diff(s0, ep1["state_diff"], 1)
out["ep1_state_diff"] = ep1["state_diff"]
out["state_after_ep1"] = s1
diff2 = {"current_location": "", "open_threads_add": ["a", "b"], "open_threads_remove": [s1["open_threads"][0]] if s1["open_threads"] else [], "facts_add": ["f1", "f1"], "timeline_add": "", "mood": "klid"}
out["diff2"] = diff2
out["state_after_2"] = state.apply_diff(s1, diff2, 2)

# continuation premise
last = ep1["panels"][-1]
out["premise"] = (f"Previous episode: \"{ep1['title']}\". It ended with: "
                  f"{[b['text'] for b in last.get('bubbles', [])]} at {last.get('location_id')}.\n"
                  f"The player chose: \"Jdu za Strážci\". Continue directly from that moment.")
json.dump(out, open(sys.argv[1], "w"), ensure_ascii=False, indent=1)
print("ok", len(out["prompts"]), out["ep1_validate_errors"], out["bad_errors"])
