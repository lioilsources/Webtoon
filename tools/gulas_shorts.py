#!/usr/bin/env python3
"""Linear gamebooks (the Kulový blesk guláš and others) → one 9:16 TikTok video each.

    python3 tools/gulas_shorts.py                      # the six guláš → out/shorts/gamebooks/<name>-<model>.mp4
    python3 tools/gulas_shorts.py grok kimi            # just these guláš models
    python3 tools/gulas_shorts.py louka kovovenebe --music auto   # other books → <name>.mp4
    python3 tools/gulas_shorts.py --music data/music --lang en --api http://localhost:8095
    python3 tools/gulas_shorts.py --music auto --lang en          # each book its own track, data/music/trailers/<id>.mp3
    python3 tools/gulas_shorts.py --music auto --remux --out out/shorts/gulas-en   # just put the tracks on finished videos

Every node (chapter) of a gamebook is an episode: m0/shorts.py renders each one (episode id from
out/local/gb_<id>_<node>/episode_id, left by the import), then the chapters are joined in reading order (start → next)
into one file. Only linear books: a node with choices stops the run before anything is rendered.
A book's own track (rules/base/music.yaml gamebooks, m0/music.py) is shared with its trailer and lives outside the
data/music mood pool. It is looped with a crossfade when the video is longer than the track.
Backend = JODA (https://webtoon-api.ol1n.com); its token: export WEBTOON_STUDIO_TOKEN=<STUDIO_TOKEN from JODA ~/deploy/Webtoon/deploy/.env>.
Images and loops are downloaded from /media into out/shorts/_media. Needs ffmpeg and the shorts.py deps.
"""

import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TRACKS = ROOT / "data/music/trailers"
# key → (gamebook id, output file name without .mp4); the guláš keys are the LLM that wrote the book
BOOKS = {
    "chatgpt": ("poslednislovo", "posledni-slovo-chatgpt"),
    "grok": ("gulasspagety", "gulas-a-spagety-grok"),
    "deepseek": ("poslednislovopavilon", "posledni-slovo-pavilon-deepseek"),
    "claude": ("uknedliku", "u-knedliku-2089-claude"),
    "lechat": ("gulasknedlik", "gulas-s-knedlikem-lechat"),
    "kimi": ("knedlikvzakopu", "s-knedlikem-v-zakopu-kimi"),
    "louka": ("louka", "rozkvetla-louka"),
    "kovovenebe": ("kovovenebe", "kovove-nebe"),
    "archion": ("archion", "archion"),
}
GULAS = ["chatgpt", "grok", "deepseek", "claude", "lechat", "kimi"]
CROSSFADE = 3.0  # s between two plays of a looped track


def track_of(key):
    return TRACKS / f"{BOOKS[key][0]}.mp3"


def chapters(gid):
    """The nodes of a linear gamebook in reading order; exits on a branching one."""
    g = yaml.safe_load((ROOT / "data/gamebooks" / gid / "graph.yaml").read_text())
    nodes, order, node = g["nodes"], [], g["start"]
    while node:
        if node in order:
            sys.exit(f"{gid}: {node} loops back")
        if nodes[node].get("choices"):
            sys.exit(f"{gid}: {node} has choices; only linear gamebooks become one video")
        order.append(node)
        node = nodes[node].get("next")
    return order


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("books", nargs="*", help=f"any of {', '.join(BOOKS)} (default: the six guláš)")
    ap.add_argument("--lang", default="cs")
    ap.add_argument("--music", default=None,
                    help="'auto' = the book's own track, data/music/trailers/<gamebook id>.mp3, over the whole video; "
                         "otherwise an audio file or directory passed to shorts.py per chapter")
    ap.add_argument("--volume", type=float, default=0.8)
    ap.add_argument("--remux", action="store_true",
                    help="with --music auto: only put the track on the existing <out>/<name>.mp4, no rendering")
    ap.add_argument("--dub", action="store_true", help="Czech voices + subtitles instead of bubbles (shorts.py --dub)")
    ap.add_argument("--subtitles", action="store_true", help="subtitles instead of bubbles, silent (shorts.py --subtitles)")
    ap.add_argument("--api", default=os.environ.get("WEBTOON_API", "https://webtoon-api.ol1n.com"), help="backend (JODA via the tunnel)")
    ap.add_argument("--user", default="player", help="X-User-ID that owns the imported episodes")
    ap.add_argument("--out", default=str(ROOT / "out" / "shorts" / "gamebooks"))
    args = ap.parse_args()
    books = args.books or GULAS
    if bad := [b for b in books if b not in BOOKS]:
        sys.exit(f"unknown {bad}: {', '.join(BOOKS)}")
    out = Path(args.out)
    auto = args.music == "auto"
    if args.remux and not auto:
        sys.exit("--remux needs --music auto")

    # everything that can be missing is checked before the first (minutes long) render
    if auto and (missing := [b for b in books if not track_of(b).exists()]):
        sys.exit(f"no track for {missing}: python3 m0/music.py --only {' '.join(BOOKS[b][0] for b in missing)}")
    plan = {}
    for b in books:
        gid, name = BOOKS[b]
        if args.remux:
            if not (out / f"{name}.mp4").exists():
                sys.exit(f"{out / f'{name}.mp4'} missing: render it first (without --remux)")
            continue
        ids = []
        for node in chapters(gid):
            f = ROOT / "out/local" / f"gb_{gid}_{node}" / "episode_id"
            if not f.exists():
                sys.exit(f"{gid}/{node}: {f.relative_to(ROOT)} missing (the gamebook is not imported on this machine)")
            ids.append(f.read_text().strip())
        plan[b] = ids
    out.mkdir(parents=True, exist_ok=True)
    # under the voices the music is quieter (rules/base/shorts.yaml dub.music_duck) and the voice track is kept
    volume = yaml.safe_load((ROOT / "rules/base/shorts.yaml").read_text())["dub"]["music_duck"] if args.dub else args.volume

    for b in books:
        target = out / f"{BOOKS[b][1]}.mp4"
        if args.remux:
            add_music(target, track_of(b), volume, keep_voice=args.dub)
            print(f"{b}: {target} + music")
            continue
        ids = plan[b]
        with tempfile.TemporaryDirectory() as tmp:
            parts = []
            for i, episode in enumerate(ids):
                part = Path(tmp) / f"{i:02d}.mp4"
                cmd = [sys.executable, str(ROOT / "m0/shorts.py"), episode, "--lang", args.lang,
                       "--api", args.api, "--user", args.user, "--out", str(part)]
                if i < len(ids) - 1:
                    cmd.append("--no-end")  # "The End" only after the last chapter
                if args.dub:
                    cmd.append("--dub")
                elif args.subtitles:
                    cmd.append("--subtitles")
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
                add_music(target, track_of(b), volume, keep_voice=args.dub)
            print(f"{b}: {target}")


def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                 str(path)], check=True, capture_output=True, text=True).stdout)


def add_music(video, music_file, volume, keep_voice=False):
    """Put music_file under video: repeated with a crossfade to the full length (no hard cut back to its intro),
    faded in and out; picture is copied. keep_voice mixes it under the video's own audio (the dub) instead of
    replacing that."""
    total, length = duration(video), duration(music_file)
    plays = 1 if length >= total else math.ceil((total - CROSSFADE) / (length - CROSSFADE))
    inputs = [x for _ in range(plays) for x in ("-i", str(music_file))]
    chain, last = [], "1:a"
    for k in range(2, plays + 1):
        chain.append(f"[{last}][{k}:a]acrossfade=d={CROSSFADE}[x{k}]")
        last = f"x{k}"
    chain.append(f"[{last}]atrim=0:{total:.3f},volume={volume},afade=t=in:d=0.5,"
                 f"afade=t=out:st={max(total - 2, 0):.2f}:d=2[m]")
    if keep_voice:
        chain.append("[0:a][m]amix=inputs=2:duration=first:normalize=0[a]")
    tmp = video.with_suffix(".music.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), *inputs,
                    "-filter_complex", ";".join(chain), "-map", "0:v", "-map", "[a]" if keep_voice else "[m]",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                    "-t", f"{total:.3f}", "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(video)


if __name__ == "__main__":
    main()
