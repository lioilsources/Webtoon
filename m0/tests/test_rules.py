"""rules/*.yaml loader, the shell helper and local_strip.sh values (the shell script has no golden run: it calls the LLM)."""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "m0"))

import rules  # noqa: E402


def get(key):
    return subprocess.run([sys.executable, "m0/rules.py", "get", key], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()


class Rules(unittest.TestCase):
    def test_all_files_load(self):
        for name in rules.REQUIRED:
            self.assertTrue(rules.load(name))

    def test_missing_key_fails(self):
        rules.REQUIRED["music"].append("no_such_key")
        rules.load.cache_clear()
        try:
            with self.assertRaises(KeyError):
                rules.load("music")
        finally:
            rules.REQUIRED["music"].remove("no_such_key")
            rules.load.cache_clear()

    def test_free_kids_refused(self):  # adapt.main() refuses --free --audience kids; the profile mapping does too
        with self.assertRaises(ValueError):
            rules.profile_of(True, "kids")

    def test_local_strip_values(self):  # the literals local_strip.sh had before it read rules (base pipeline + profiles)
        want = {"harlequin:pipeline.strip.prefix": "lx_", "free:pipeline.strip.prefix": "lxf_",
                "kids:pipeline.strip.prefix": "lx_", "harlequin:pipeline.strip.day": "local",
                "free:pipeline.strip.day": "local_free", "kids:pipeline.strip.day": "local",
                "harlequin:profile.styles.strip_default": "webtoon_romance", "free:profile.styles.strip_default": "webtoon_romance",
                "kids:profile.styles.strip_default": "clean_webtoon_noartist",
                "free:profile.free": "True", "harlequin:profile.free": "False", "kids:profile.audience": "kids",
                "pipeline.strip.wait_seconds": "300", "pipeline.strip.deadline.window_end_hour": "13",
                "pipeline.strip.deadline.window_end": "13:00", "pipeline.strip.deadline.late_slot_minutes": "60",
                "pipeline.strip.deadline.no_wrap": "23:59"}
        self.assertEqual({k: get(k) for k in want}, want)
        subprocess.run(["bash", "-n", "m0/local_strip.sh"], cwd=ROOT, check=True)

    def test_shorts_free_prefix(self):  # shorts.py and the Go pack share it
        self.assertEqual(get("pack.forbidden_world_prefix"), "w_lxf_")


if __name__ == "__main__":
    unittest.main()
