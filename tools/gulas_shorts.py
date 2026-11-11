#!/usr/bin/env python3
"""Kulový blesk gamebooks → one 9:16 TikTok video each, named <guláš>-<llm model>.mp4.

    python3 tools/gulas_shorts.py                      # all six  → out/shorts/gulas/
    python3 tools/gulas_shorts.py grok kimi            # just these models
    python3 tools/gulas_shorts.py --music data/music --lang en --api http://localhost:8095
    python3 tools/gulas_shorts.py --music auto --lang en          # each model its own track, data/music/gulas_<model>.mp3
    python3 tools/gulas_shorts.py --music auto --remux --out out/shorts/gulas-en   # just add the tracks to finished videos

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
    ap.add_argument("--music", default=None,
                    help="'auto' = data/music/gulas_<model>.mp3 laid over the whole joined video; "
                         "otherwise an audio file or directory passed to shorts.py per node")
    ap.add_argument("--volume", type=float, default=0.8)
    ap.add_argument("--remux", action="store_true",
                    help="with --music auto: only put the track on the existing <out>/<name>-<model>.mp4, no rendering")
    ap.add_argument("--api", default=os.environ.get("WEBTOON_API", "https://webtoon-api.ol1n.com"), help="backend (JODA via the tunnel)")
    ap.add_argument("--user", default="player", help="X-User-ID that owns the imported episodes")
    ap.add_argument("--out", default=str(ROOT / "out" / "shorts" / "gulas"))
    args = ap.parse_args()
    models = args.models or list(GULAS)
    if bad := [m for m in models if m not in GULAS]:
        sys.exit(f"unknown model {bad}: {', '.join(GULAS)}")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    auto = args.music == "auto"
    if auto and (missing := [m for m in models if not (ROOT / "data/music" / f"gulas_{m}.mp3").exists()]):
        sys.exit(f"no track for {missing}: python3 m0/music.py --only {' '.join('gulas_' + m for m in missing)}")
    if args.remux and not auto:
        sys.exit("--remux needs --music auto")

    for model in models:
        gid, name = GULAS[model]
        target = out / f"{name}-{model}.mp4"
        if args.remux:
            if not target.exists():
                sys.exit(f"{target} missing: render it first (without --remux)")
            add_music(target, ROOT / "data/music" / f"gulas_{model}.mp3", args.volume)
            print(f"{model}: {target} + music")
            continue
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
                if node != nodes[-1]:
                    cmd.append("--no-end")  # "The End" only after the last chapter
                if args.music and not auto:
                    cmd += ["--music", args.music, "--volume", str(args.volume)]
                subprocess.run(cmd, check=True)
                parts.append(part)
            if len(parts) == 1:
                shutil.move(parts[0], target)  # the temp dir may be on another volume (os.replace fails there)
            else:  # same encoder settings for every part, so the streams can be joined without re-encoding
                lst = Path(tmp) / "list.txt"
                lst.write_text("".join(f"file '{p}'\n" for p in parts))
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                                "-c", "copy", "-movflags", "+faststart", str(target)], check=True)
            if auto:
                add_music(target, ROOT / "data/music" / f"gulas_{model}.mp3", args.volume)
            print(f"{model}: {target}")


def add_music(video, track, volume):
    """Replace the audio of video with track: looped to the full length, faded in and out; picture is copied."""
    total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                  str(video)], check=True, capture_output=True, text=True).stdout)
    tmp = video.with_suffix(".music.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-stream_loop", "-1", "-i", str(track),
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-af", f"volume={volume},afade=t=in:d=0.5,afade=t=out:st={max(total - 2, 0):.2f}:d=2",
                    "-t", f"{total:.3f}", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(video)


if __name__ == "__main__":
    main()
