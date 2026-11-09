#!/usr/bin/env python3
"""Kulový blesk gamebooks → one 9:16 TikTok video each, named <guláš>-<llm model>.mp4.

    python3 tools/gulas_shorts.py                      # all six  → out/shorts/gulas/
    python3 tools/gulas_shorts.py grok kimi            # just these models
    python3 tools/gulas_shorts.py --music data/music --lang en --api http://localhost:8095

Every node (chapter) of a gamebook is an episode: m0/shorts.py renders each one (episode id from
out/local/gb_<id>_<node>/episode_id, left by the import), then the nodes are joined in graph order into one file.
Backend = JODA (https://webtoon-api.ol1n.com); its token: export WEBTOON_STUDIO_TOKEN=<STUDIO_TOKEN from JODA ~/deploy/Webtoon/deploy/.env>.
Images and loops are downloaded from /media into out/shorts/_media. Needs ffmpeg and the shorts.py deps.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
# model → (gamebook id, file name without the model)
GULAS = {
    "chatgpt": ("poslednislovo", "posledni-slovo"),
    "grok": ("gulasspagety", "gulas-a-spagety"),
    "deepseek": ("poslednislovopavilon", "posledni-slovo-pavilon"),
    "claude": ("uknedliku", "u-knedliku-2089"),
    "lechat": ("gulasknedlik", "gulas-s-knedlikem"),
    "kimi": ("knedlikvzakopu", "s-knedlikem-v-zakopu"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models", nargs="*", help=f"any of {', '.join(GULAS)} (default: all)")
    ap.add_argument("--lang", default="cs")
    ap.add_argument("--music", default=None, help="audio file or directory, passed to shorts.py")
    ap.add_argument("--api", default=os.environ.get("WEBTOON_API", "https://webtoon-api.ol1n.com"), help="backend (JODA via the tunnel)")
    ap.add_argument("--user", default="player", help="X-User-ID that owns the imported episodes")
    ap.add_argument("--out", default=str(ROOT / "out" / "shorts" / "gulas"))
    args = ap.parse_args()
    models = args.models or list(GULAS)
    if bad := [m for m in models if m not in GULAS]:
        sys.exit(f"unknown model {bad}: {', '.join(GULAS)}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    for model in models:
        gid, name = GULAS[model]
        nodes = list(yaml.safe_load((ROOT / "data/gamebooks" / gid / "graph.yaml").read_text())["nodes"])
        with tempfile.TemporaryDirectory() as tmp:
            parts = []
            for node in nodes:
                f = ROOT / "out/local" / f"gb_{gid}_{node}" / "episode_id"
                if not f.exists():
                    sys.exit(f"{gid}/{node}: {f.relative_to(ROOT)} missing (the gamebook is not imported on this machine)")
                part = Path(tmp) / f"{len(parts):02d}.mp4"
                cmd = [sys.executable, str(ROOT / "m0/shorts.py"), f.read_text().strip(), "--lang", args.lang,
                       "--api", args.api, "--user", args.user, "--out", str(part)]
                if args.music:
                    cmd += ["--music", args.music]
                subprocess.run(cmd, check=True)
                parts.append(part)
            target = out / f"{name}-{model}.mp4"
            if len(parts) == 1:
                shutil.move(parts[0], target)  # the temp dir may be on another volume (os.replace fails there)
            else:  # same encoder settings for every part, so the streams can be joined without re-encoding
                lst = Path(tmp) / "list.txt"
                lst.write_text("".join(f"file '{p}'\n" for p in parts))
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                                "-c", "copy", "-movflags", "+faststart", str(target)], check=True)
            print(f"{model}: {target}")


if __name__ == "__main__":
    main()
