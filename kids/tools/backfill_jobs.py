"""One-off: job records for strips rendered before kids/jobs.py existed (stories 01–15).

Parameters are recomputed with make_strips.build_job from the storyboard (pinned seeds included) and
the preset — so they are `source: reconstructed`, not logged at render time. Animagine panels drawn
before the preset lost its literal 'storybook' tag get that older preset back, so the record matches
what was actually sent. Rejected variants of earlier rounds were deleted and are not recoverable.
"""
import copy
import sys
from pathlib import Path

KIDS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIDS))
import jobs  # noqa: E402
import make_strips as M  # noqa: E402
from common import DATA, OUT, load_json  # noqa: E402

# Panels re-rendered after the Animagine preset fix; every other Animagine panel used the old preset.
AFTER_FIX = {"07_majak": {2, 5, 18}, "09_klarka": {2, 5, 9, 11, 13, 14, 15, 16},
             "10_anicka_les": {1, 6, 9, 10, 12, 14, 15, 18, 22}}
OLD_ANIMAGINE = {"aesthetic_tags": ["watercolor (medium)", "storybook", "soft lighting"]}

styles = load_json(DATA / "styles.json")
old = copy.deepcopy(styles)
old["presets"]["animagine_storybook"].update(OLD_ANIMAGINE)
old["presets"]["animagine_storybook"]["quality_neg"] = [
    t for t in styles["presets"]["animagine_storybook"]["quality_neg"] if "book" not in t]

done = {(r["story"], r["panel"], r.get("variant")) for r in jobs.load() if "event" not in r}
n = 0
for path in sorted((KIDS / "stories").glob("*.json")):
    data = load_json(path)
    world, panels = data["world"], data["storyboard"]["panels"]
    preset = world.get("style_id", "clean_webtoon")
    for i, panel in enumerate(panels):
        f = OUT / "kids" / path.stem / "comfy" / f"p{i:02d}_s0.png"
        if not f.exists() or (path.stem, i, None) in done:
            continue
        use = old if preset == "animagine_storybook" and i not in AFTER_FIX.get(path.stem, set()) else styles
        _, meta = M.build_job(panel, world, use, preset, panel.get("seed", 7000 + i * 100))
        jobs.record(path.stem, i, None, meta, f.read_bytes(), selected=True, source="reconstructed",
                    note="parameters recomputed from storyboard + preset after the fact")
        n += 1
print(n, "records")
