"""Ambient-only loops (2026-10-24, a deliberate behaviour change): the 2+ character motion rule, the WD14 tags in
meta.json and the tag-built loop prompt of animate.py."""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import adapt  # noqa: E402
import animate  # noqa: E402
import cases  # noqa: E402
import render  # noqa: E402
import rules  # noqa: E402

A = rules.load("animate")["ambient"]
PREFIX = "ambient only, characters still"


def two_shot(motion, profile="harlequin"):
    ex = cases.examples()["kids_park" if profile in ("kids", "superhero") else "santorini"]
    s = copy.deepcopy(ex)
    i = next(i for i, p in enumerate(s["panels"]) if len(p["characters"]) == 2)
    for p in s["panels"]:
        p.pop("animate", None), p.pop("motion", None)
    s["panels"][i].update(animate=True, motion=motion)
    return s, i


class Rule(unittest.TestCase):
    def test_loophole_closed(self):  # before: any "static camera" passed
        for prof in rules.profiles():
            s, i = two_shot("they dance slowly, static camera", prof)
            errs = adapt.check(s, profile=prof)
            self.assertIn(f"panel {i}: two people may only get ambient motion (write 'ambient only, characters still, "
                          f"<ambient>, static camera')", errs, prof)
            self.assertIn(f"panel {i}: ambient motion must not move a character ('dance')", errs, prof)

    def test_template_passes(self):
        for prof in rules.profiles():
            s, i = two_shot(A["template"].format(ambient="rain falling, clouds drifting slowly"), prof)
            self.assertEqual([e for e in adapt.check(s, profile=prof) if "motion" in e], [], prof)

    def test_verbs_after_prefix(self):
        s, i = two_shot(PREFIX + ", she turns to him, waving, static camera")
        errs = adapt.check(s)
        self.assertEqual(errs, [f"panel {i}: ambient motion must not move a character ('turns')"])

    def test_vocabulary_clear_of_verbs(self):
        eng = rules.storyboard("harlequin")
        for phrase in [e["phrase"] for e in A["from_tags"]] + [A["default"]]:
            self.assertIsNone(eng.re["character_motion"].search(phrase), phrase)
            self.assertIsNone(eng.re["banned"].search(phrase), phrase)
        self.assertTrue(eng.re["ambient_prefix"].match(A["template"]))

    def test_single_character_unchanged(self):
        s = copy.deepcopy(cases.examples()["santorini"])
        self.assertEqual(adapt.check(s), [])  # the few-shot's one-person loop ("she slowly turns her head") still passes

    def test_prompts_carry_template(self):
        for f in ("adapt_system.md", "adapt_system_kids.md"):
            text = (adapt.SKILL / "prompts" / f).read_text()
            self.assertIn('"ambient only, characters still, <1–3 ambient phrases>, static camera"', text, f)
        free = adapt.free_prompt((adapt.SKILL / "prompts" / "adapt_system.md").read_text())
        self.assertIn(PREFIX, free)  # the free rewrite keeps it

    def test_pick_motion_same_rule(self):
        p = {"characters": [{"id": "a"}, {"id": "b"}]}
        ok = A["template"].format(ambient="water rippling")
        self.assertTrue(adapt.ENGINE.re["ambient_prefix"].match(ok))
        self.assertIsNone(adapt.ENGINE.re["character_motion"].search(ok))
        self.assertTrue(p)


class Tags(unittest.TestCase):
    def test_top_tags(self):
        got = render.top_tags({"general": {"sky": 0.5, "rain": 0.9, "cloud": 0.34, "tree": 0.35}})
        self.assertEqual(list(got.items()), [("rain", 0.9), ("sky", 0.5), ("tree", 0.35)])
        many = render.top_tags({"general": {f"t{k}": 0.5 + k / 1000 for k in range(100)}})
        self.assertEqual(len(many), rules.load("render")["wd14_tags"]["max"])
        self.assertEqual(next(iter(many)), "t99")

    def test_phrases(self):
        f = animate.ambient_phrases
        self.assertEqual(f({"rain": 0.9, "cloudy sky": 0.8, "tree": 0.7, "fire": 0.6}),
                         ["rain falling", "clouds drifting slowly", "leaves swaying"])
        self.assertEqual(f({"night sky": 0.9, "sky": 0.8}), ["stars twinkling", "clouds drifting slowly"])
        self.assertEqual(f({"torch": 0.4, "magic": 0.9, "1girl": 0.99}), ["soft glow pulsing", "flames flickering"])
        self.assertEqual(f({"1girl": 0.9, "smile": 0.8}), [A["default"]])
        self.assertEqual(f({}), [A["default"]])
        self.assertEqual(f({"skyline": 0.9}), [A["default"]])  # whole words only

    def test_loop_motion(self):
        two = {"shot": "medium", "characters": [{"id": "a"}, {"id": "b"}]}
        one = {"shot": "medium", "characters": [{"id": "a"}]}
        est = {"shot": "establishing", "characters": []}
        tags = {"ocean": 0.9, "sky": 0.6}
        self.assertEqual(animate.loop_motion(two, "they dance", None), "they dance")  # an old run: unchanged
        self.assertEqual(animate.loop_motion(two, "they dance", tags),
                         "ambient only, characters still, water rippling, clouds drifting slowly, static camera")
        self.assertEqual(animate.loop_motion(est, "x", tags), "ambient only, water rippling, clouds drifting slowly, static camera")
        self.assertEqual(animate.loop_motion(one, "her hair moves in the wind, static camera.", tags),
                         "her hair moves in the wind, water rippling, clouds drifting slowly, static camera")
        self.assertEqual(animate.loop_motion(one, "water rippling, clouds drifting slowly, static camera", tags),
                         "water rippling, clouds drifting slowly, static camera")

    def test_built_motion_passes_check(self):
        s, i = two_shot("x")
        s["panels"][i]["motion"] = animate.loop_motion(s["panels"][i], "x", {"rain": 0.9, "lights": 0.5})
        self.assertEqual(adapt.check(s), [])

    def test_meta_reading(self):
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "meta.json"
            self.assertEqual(animate.wd14_by_panel(m), {})
            m.write_text(json.dumps({"images": [{"panel": 0, "variant": 0, "wd14_tags": {"rain": 0.9}},
                                                {"panel": 0, "variant": 1, "wd14_tags": {"fire": 0.9}},
                                                {"panel": 1, "variant": 0}]}))
            self.assertEqual(animate.wd14_by_panel(m), {0: {"rain": 0.9}})


if __name__ == "__main__":
    unittest.main()
