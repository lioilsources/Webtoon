"""Golden identity: the rules moved to rules/*.yaml must give exactly what the code-only snapshot gave.

    python3 -m unittest discover m0/tests

golden/golden.json comes from make_goldens.py run against the snapshot revision (rules still in code).
"""

import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402

GOLDEN = json.loads((HERE / "golden" / "golden.json").read_text())
MODS = harness.import_mods(HERE.parent)
_cache = {}


def current(section):
    if section not in _cache:
        _cache.update(harness.run(MODS, [section]))
    return _cache[section]


class Golden(unittest.TestCase):
    maxDiff = 4000

    def same(self, section):
        want, got = GOLDEN[section], current(section)
        self.assertEqual(sorted(want), sorted(got), f"{section}: case set differs")
        bad = [k for k in want if want[k] != got[k]]
        if bad:
            k = bad[0]
            self.assertEqual(want[k], got[k], f"{section}: {len(bad)} cases differ, first {k!r}")

    def test_check(self):  # adapt.check() + missing_fields(): data/stories, examples, mutants × adult/free/kids
        self.same("check")

    def test_to_m0(self):
        self.same("to_m0")

    def test_adapt(self):  # prompt/schema/example selection, retries, free_prompt, pick_motion
        self.same("adapt")

    def test_prompts(self):  # prompts.build() for every panel of every storyboard (9 variants)
        self.same("prompts")

    def test_render(self):
        self.same("render")

    def test_animate(self):
        self.same("animate")

    def test_compose(self):
        self.same("compose")

    def test_shorts(self):
        self.same("shorts")

    def test_music(self):
        self.same("music")


if __name__ == "__main__":
    unittest.main()
