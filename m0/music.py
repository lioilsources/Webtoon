"""Instrumental music library for shorts.py, rendered by AiStack's audio service (ACE-Step, container audio-music).

    python3 m0/music.py [--only lofi_1]          # WEBTOON_AUDIO overrides the Spark LAN endpoint
    → data/music/<name>.mp3, one per MOODS entry; existing tracks are skipped

Director's rules: only in the comfy window 07:05–12:45 (audio is down while the big LLMs run), one job at a time,
never start the container yourself; if the model is not available, ask Director.
shorts.py --music data/music picks one track per world, so a series keeps its sound.
"""

import argparse
import json
import os
import time
import urllib.request
from datetime import datetime

import rules
from common import DATA, http

AUDIO_URL = os.environ.get("WEBTOON_AUDIO", "http://192.168.88.66:8093")
LIB = DATA / "music"
# Length, window, model and the moods: rules/music.yaml.
R = rules.load("music")
LENGTH = R["length"]  # s: ACE-Step returns 9–19 % short of this; the longest short is ~65 s, and shorts.py loops anyway
MOODS = dict(R["moods"])


def render(name, prompt, seed):
    job = json.loads(http("POST", f"{AUDIO_URL}/v1/audio/music", {
        "prompt": prompt + R["prompt_suffix"], "duration_s": LENGTH, "seed": seed,
        "instrumental": True, "loop": False, "format": "mp3", "variations": 1}))
    while job.get("status") not in ("done", "error"):
        time.sleep(2)
        job = json.loads(http("GET", f"{AUDIO_URL}/v1/audio/jobs/{job['job_id']}"))
    if job["status"] == "error" or not job.get("outputs"):
        raise RuntimeError(f"{name}: {job.get('error') or 'no outputs'}")
    url = job["outputs"][0]["url"]
    data = urllib.request.urlopen(url if url.startswith("http") else AUDIO_URL + url, timeout=120).read()
    (LIB / f"{name}.mp3").write_bytes(data)


def check_ready():
    now = datetime.now().strftime("%H:%M")
    start, end = R["window"]["start"], R["window"]["end"]
    if not start <= now <= end:
        raise SystemExit(f"{now}: audio runs only {start}–{end}")
    models = json.loads(http("GET", f"{AUDIO_URL}/v1/audio/models"))
    ace = [m for m in models if m["name"] == R["model"]]
    if not (ace and ace[0].get("available")):
        raise SystemExit(f"{R['model']} not available: ask Director, never start audio-music yourself")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    args = ap.parse_args()
    check_ready()
    LIB.mkdir(parents=True, exist_ok=True)
    for k, (name, prompt) in enumerate(MOODS.items()):
        if (args.only and name not in args.only) or (LIB / f"{name}.mp3").exists():
            continue
        t = time.time()
        render(name, prompt, R["seed_base"] + k)
        print(f"{name} ok {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()
