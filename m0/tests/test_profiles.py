"""rules/profiles: merge semantics, every profile valid, today's flags ↔ profiles, and the new superhero profile."""

import argparse
import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import adapt  # noqa: E402
import animate  # noqa: E402
import cases  # noqa: E402
import prompts  # noqa: E402
import render  # noqa: E402
import rules  # noqa: E402

STYLES = cases.load(cases.ROOT / "data" / "styles.json")
FLAGS = {"harlequin": (False, "adult"), "kids": (False, "kids"), "free": (True, "adult")}


class Merge(unittest.TestCase):
    def test_semantics(self):
        base = {"a": {"x": 1, "y": [1, 2]}, "l": [1], "keep": 3}
        over = {"a": {"y": [9], "z": 2}, "l": {"extend": [2, 3]}, "r": {"replace": {"q": 1}}}
        self.assertEqual(rules.merge(base, over), {"a": {"x": 1, "y": [9], "z": 2}, "l": [1, 2, 3], "keep": 3, "r": {"q": 1}})
        self.assertEqual(rules.merge({"a": {"x": 1}}, {"a": {"replace": {}}}), {"a": {}})
        self.assertEqual(base["l"], [1])  # inputs untouched


class Profiles(unittest.TestCase):
    def test_all_valid(self):
        self.assertEqual(rules.profiles(), ["free", "harlequin", "kids", "superhero"])
        for name in rules.profiles():
            p = rules.profile(name)
            st = p["profile"]["styles"]
            pool = list(STYLES["presets"]) if st["pool"] == "all" else st["pool"]
            self.assertTrue(set(pool) <= set(STYLES["presets"]), name)
            self.assertIn(st["default"], pool, name)
            self.assertIn(st["strip_default"], pool, name)
            for f in ("schema", "system", "example"):
                self.assertTrue(p["storyboard"]["adapt"][f], name)
            rules.storyboard(name)

    def test_flags_map_to_profiles(self):
        for name, (free, aud) in FLAGS.items():
            self.assertEqual(rules.profile_of(free, aud), name)
        self.assertIsNone(rules.profile_of(False, "teen"))
        self.assertEqual(rules.world_profile({"audience": "kids", "profile": "superhero"}), "superhero")
        self.assertEqual(rules.world_profile({"audience": "kids", "free": True}), "free")

    def test_profile_equals_flags(self):  # check()/to_m0() by --profile give exactly what the old flags give
        for cid, story in cases.mutants():
            for name, (free, aud) in FLAGS.items():
                a = harness_guard(adapt.check, copy.deepcopy(story), {"smile"}, free=free, audience=aud)
                b = harness_guard(adapt.check, copy.deepcopy(story), {"smile"}, profile=name)
                self.assertEqual(a, b, f"{cid} {name}")
                if not adapt.missing_fields(story, aud == "kids"):
                    self.assertEqual(adapt.to_m0(copy.deepcopy(story), "s", free=free, audience=aud),
                                     adapt.to_m0(copy.deepcopy(story), "s", profile=name), f"{cid} {name}")


def harness_guard(fn, *a, **kw):
    try:
        return fn(*a, **kw)
    except Exception as e:  # noqa: BLE001
        return type(e).__name__


def hero_story():
    s = copy.deepcopy(cases.examples()["kids_park"])
    s["panels"][2]["visual_tags"] = ["energy blast", "punch", "sword clash", "explosion", "motion lines"]
    return s


class Superhero(unittest.TestCase):
    def test_inherits_kids(self):
        hero, kids = rules.profile("superhero"), rules.profile("kids")
        self.assertEqual(hero["lineage"], ["superhero", "kids"])
        self.assertEqual(hero["profile"]["audience"], "kids")
        for f in ("render", "prompts", "animate"):
            self.assertEqual(hero[f], kids[f], f)
        self.assertEqual(hero["storyboard"]["fences"]["fence"], "kids_sfw")
        self.assertEqual(hero["storyboard"]["fences"]["allow"], "action")
        self.assertEqual(hero["storyboard"]["required"], kids["storyboard"]["required"])
        self.assertEqual(hero["profile"]["styles"]["default"], "western_comic")

    def test_kids_rules_apply(self):  # every kids rule runs for superhero too (profiles: [kids] matches the lineage)
        for cid, story in cases.mutants():
            if cid.startswith("kids_park/"):
                self.assertEqual(harness_guard(adapt.check, copy.deepcopy(story), None, profile="superhero"),
                                 harness_guard(adapt.check, copy.deepcopy(story), None, profile="kids"), cid)

    def test_action_allowed(self):
        self.assertEqual(adapt.check(hero_story(), profile="superhero"), [])

    def test_still_no_blood_death_kiss(self):
        s = hero_story()
        s["panels"][2]["visual_tags"] += ["blood"]
        s["panels"][3]["bubbles"].append({"speaker_id": "", "text": "A pak ho líbá.", "kind": "narration"})
        s["panels"][4].update(animate=True, motion="punch, villain dead on the ground")
        errs = adapt.check(s, profile="superhero")
        self.assertIn("panel 2: banned tag 'blood'", errs)
        self.assertIn("panel 3: banned term 'líbá' in a bubble (reword it without violence or romance)", errs)
        self.assertIn("panel 4: motion prompt contains a banned action", errs)

    def test_mask(self):
        eng = rules.storyboard("superhero")
        self.assertEqual(eng.mask("Energy Blast, blood"), " " * 12 + ", blood")
        self.assertEqual(rules.storyboard("kids").mask("energy blast"), "energy blast")

    def test_to_m0(self):
        world, sb = adapt.to_m0(hero_story(), "western_comic", profile="superhero")
        self.assertEqual((world["audience"], world["profile"], world["tone"]), ("kids", "superhero", "akční, hrdinský, laskavý"))
        self.assertNotIn("fonts", sb)
        self.assertNotIn("free", world)
        self.assertEqual(rules.world_profile(world), "superhero")
        k_world, _ = adapt.to_m0(hero_story(), "x", profile="kids")
        self.assertNotIn("profile", k_world)

    def test_adapt_prompt(self):
        calls = []
        orig = adapt.chat, adapt.save_json
        try:
            adapt.chat = lambda messages, **kw: (calls.append(messages), copy.deepcopy(hero_story()))[1]
            adapt.save_json = lambda path, obj: None
            args = argparse.Namespace(id="lx_hero", style="western_comic", audience="kids", free=False, attempts=1,
                                      dry_run=False, profile="superhero", source=str(cases.EXAMPLES / "kids_park.input.md"))
            adapt.adapt(args)
        finally:
            adapt.chat, adapt.save_json = orig
        system = calls[0][0]["content"]
        kids = (adapt.SKILL / "prompts" / "adapt_system_kids.md").read_text().replace("{lang}", "Czech")
        self.assertTrue(system.startswith(kids))
        self.assertIn("SUPERHERO ADDENDUM", system)
        self.assertIn('"energy blast", "punch", "sword clash", "explosion", "motion lines"', system)

    def test_render_animate_prompts_like_kids(self):
        w = {"audience": "kids", "profile": "superhero"}
        self.assertEqual(prompts.audience_negative(w, STYLES), STYLES["kids_negative"])
        tags = {"rating": {"sensitive": 0.6}}
        self.assertEqual(render.safety(tags, profile="superhero"), render.safety(tags, "kids"))
        self.assertEqual(animate.negative("superhero"), animate.NEGATIVE)

    def test_style_pool_enforced(self):
        out = __import__("subprocess").run([sys.executable, "m0/adapt.py", "--profile", "superhero", "--style", "photo_glossy",
                                            "--id", "x", "--dry-run", "skills/storyboard-writer/examples/kids_park.input.md"],
                                           cwd=cases.ROOT, capture_output=True, text=True)
        self.assertEqual(out.returncode, 2)
        self.assertIn("not in the profile's pool", out.stderr)


if __name__ == "__main__":
    unittest.main()
