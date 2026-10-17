"""Golden outputs from the Python M0 prototype (pure functions only, no network).

    python3 -B internal/testdata/gen_golden.py internal/testdata/golden_m0.json
"""
import copy, json, sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "m0"))
sys.dont_write_bytecode = True
import common, storyboard, prompts, state

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
