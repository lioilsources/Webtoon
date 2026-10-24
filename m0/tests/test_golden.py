"""Golden identity: the rules moved to rules/*.yaml must give exactly what the code-only snapshot gave.

    python3 -m unittest discover m0/tests

golden/golden.json comes from make_goldens.py run against the snapshot revision (rules still in code).
"""

import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import harness  # noqa: E402

GOLDEN = json.loads((HERE / "golden" / "golden.json").read_text())

# Deliberate behaviour changes since the snapshot, each with its own tests; the goldens are compared with them
# taken out of both sides, so everything else is still proven identical.
# 2026-10-24 ambient-only loops (test_ambient.py): the 2+ character motion rule and its prompt sentences.
AMBIENT_ERR = re.compile(r"two people may only get ambient motion|ambient motion must not move a character")
AMBIENT_PROMPT = [
    ' A panel with two or more people gets ambient motion only, written exactly as "ambient only, characters still, '
    '<1–3 ambient phrases>, static camera" (e.g. "ambient only, characters still, water rippling, clouds drifting slowly, '
    'static camera"); no word moves a person (dancing, running, jumping, turning, waving, walking, fades, rises…).',
    ', written exactly as "ambient only, characters still, <1–3 ambient phrases>, static camera" (e.g. "ambient only, '
    'characters still, leaves swaying, soft glow pulsing, static camera"); no word moves a character (dancing, running, '
    'jumping, turning, waving, walking, flapping, rises…)',
    "; a panel with 2+ characters: 'ambient only, characters still, <ambient>, static camera'",  # schema motion description
]


def without_changes(section, v):
    if section == "check" and isinstance(v, list):
        return [e for e in v if not AMBIENT_ERR.search(e)]
    if section == "adapt":
        t = json.dumps(v, ensure_ascii=False)
        for sentence in AMBIENT_PROMPT:
            esc = json.dumps(sentence, ensure_ascii=False)[1:-1]
            t = t.replace(esc, "").replace(json.dumps(esc, ensure_ascii=False)[1:-1], "")  # dry-run prints the JSON
        return json.loads(t)
    return v


def dry_prefix(a, b):
    """A dry run prints the first 4000 characters of the messages: after taking a sentence out, compare what both printed."""
    a, b = ((x["stdout"] if isinstance(x, dict) else x).split(" ...\n[dry-run]")[0].rstrip("\n") for x in (a, b))
    n = min(len(a), len(b))
    for sentence in AMBIENT_PROMPT:  # cut off where a (truncated) new sentence starts: the full prompts are compared in `calls`
        head = json.dumps(sentence, ensure_ascii=False)[1:41]
        if head in b:
            n = min(n, b.index(head))
    return a[:n], b[:n]
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
        norm = {k: (without_changes(section, want[k]), without_changes(section, got[k])) for k in want}
        for k, (w, g) in norm.items():
            if section == "adapt" and (k.endswith("dry=True") or k == "pick_dry"):
                norm[k] = dry_prefix(w, g)
        bad = [k for k, (w, g) in norm.items() if w != g]
        if bad:
            k = bad[0]
            self.assertEqual(*norm[k], f"{section}: {len(bad)} cases differ, first {k!r}")

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
