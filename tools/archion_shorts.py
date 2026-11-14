#!/usr/bin/env python3
"""Archion gamebooks → one 9:16 TikTok video per variant, named archion-<variant>.mp4 (like tools/gulas_shorts.py).

    python3 tools/archion_shorts.py --ids archion_episodes.txt                  # all eight → out/shorts/archion/
    python3 tools/archion_shorts.py --ids archion_episodes.txt grok kimi oil     # just these
    python3 tools/archion_shorts.py --ids archion_episodes.txt --music auto      # each variant its own track
    python3 tools/archion_shorts.py --music auto --remux                         # just put the tracks on finished videos

--ids: the Director's list, one episode per line: `gb_archion_<model>_<node> <ep_id>` for the six model variants,
`gb_archion_<aN> <oil|semireal> <ep_id>` for the original (one graph, two worlds). The ids are written to
out/local/<key>/episode_id, as an import leaves them, so a second run does not need --ids.
Music (--music auto): data/music/trailers/archion_<model>.mp3, the original's two styles share archion.mp3.
Backend = JODA, export WEBTOON_STUDIO_TOKEN (see tools/gulas_shorts.py).
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gulas_shorts import add_music  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# variant → (graph id, local key prefix, music track)
ARCHION = {
    "claude": ("archion_claude", "gb_archion_claude", "archion_claude"),
    "kimi": ("archion_kimi", "gb_archion_kimi", "archion_kimi"),
    "deepseek": ("archion_deepseek", "gb_archion_deepseek", "archion_deepseek"),
    "chatgpt": ("archion_chatgpt", "gb_archion_chatgpt", "archion_chatgpt"),
    "lechat": ("archion_lechat", "gb_archion_lechat", "archion_lechat"),
    "grok": ("archion_grok", "gb_archion_grok", "archion_grok"),
    "oil": ("archion", "gb_archion_oil", "archion"),  # Gemini's original, oil world
    "semireal": ("archion", "gb_archion_semireal", "archion"),  # Gemini's original, semireal world
}


def write_ids(path):
    """The Director's episode list → out/local/<key>/episode_id."""
    n = 0
    for line in Path(path).read_text().splitlines():
        parts = line.split()
        if len(parts) == 2:
            key, ep = parts
        elif len(parts) == 3:  # gb_archion_a1 oil ep_…
            base, world, ep = parts
            key = base.replace("gb_archion_", f"gb_archion_{world}_")
        else:
            continue
        d = ROOT / "out/local" / key
        d.mkdir(parents=True, exist_ok=True)
        (d / "episode_id").write_text(ep + "\n")
        n += 1
    print(f"{n} episode ids → out/local")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("variants", nargs="*", help=f"any of {', '.join(ARCHION)} (default: all)")
    ap.add_argument("--ids", help="episode list from the Director (written to out/local first)")
    ap.add_argument("--lang", default="cs")
    ap.add_argument("--music", default=None, help="'auto' = data/music/trailers/<track>.mp3 over the whole video")
    ap.add_argument("--volume", type=float, default=0.8)
    ap.add_argument("--remux", action="store_true", help="with --music auto: only put the track on finished videos")
    ap.add_argument("--api", default=os.environ.get("WEBTOON_API", "https://webtoon-api.ol1n.com"))
    ap.add_argument("--user", default="player")
    ap.add_argument("--out", default=str(ROOT / "out" / "shorts" / "archion"))
    args = ap.parse_args()
    if args.ids:
        write_ids(args.ids)
    variants = args.variants or list(ARCHION)
    if bad := [v for v in variants if v not in ARCHION]:
        sys.exit(f"unknown variant {bad}: {', '.join(ARCHION)}")
    auto = args.music == "auto"
    track = {v: ROOT / "data/music/trailers" / f"{ARCHION[v][2]}.mp3" for v in variants}
    if auto and (missing := [str(t) for t in track.values() if not t.exists()]):
        sys.exit(f"no track: {missing} (they are on the fix/gamebook-music branch)")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for v in variants:
        gid, key, _ = ARCHION[v]
        target = out / f"archion-{v}.mp4"
        if args.remux:
            add_music(target, track[v], args.volume)
            print(f"{v}: {target} + music")
            continue
        nodes = list(yaml.safe_load((ROOT / "data/gamebooks" / gid / "graph.yaml").read_text())["nodes"])
        with tempfile.TemporaryDirectory() as tmp:
            parts = []
            for node in nodes:
                f = ROOT / "out/local" / f"{key}_{node}" / "episode_id"
                if not f.exists():
                    sys.exit(f"{v}/{node}: {f.relative_to(ROOT)} missing (pass --ids)")
                part = Path(tmp) / f"{len(parts):02d}.mp4"
                cmd = [sys.executable, str(ROOT / "m0/shorts.py"), f.read_text().strip(), "--lang", args.lang,
                       "--api", args.api, "--user", args.user, "--out", str(part)]
                if node != nodes[-1]:
                    cmd.append("--no-end")
                subprocess.run(cmd, check=True)
                parts.append(part)
            if len(parts) == 1:
                shutil.move(parts[0], target)
            else:
                lst = Path(tmp) / "list.txt"
                lst.write_text("".join(f"file '{p}'\n" for p in parts))
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                                "-c", "copy", "-movflags", "+faststart", str(target)], check=True)
            if auto:
                add_music(target, track[v], args.volume)
            print(f"{v}: {target}")


if __name__ == "__main__":
    main()
