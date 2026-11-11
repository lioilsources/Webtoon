"""Bubbles → spoken lines for shorts.py --dub: TTS from AiStack's audio service (or macOS say), cached per line.

Cast and timing: rules/base/shorts.yaml dub. Every line is a 48 kHz mono wav in out/shorts/_tts/<hash>.wav, so a
rerun (other music, other cut) does not synthesize again. Machine and narration voices get an ffmpeg filter (fx).
"""

import hashlib
import json
import subprocess
import tempfile
import time
import urllib.request
import wave
from pathlib import Path

import numpy as np

import rules
from common import OUT

D = rules.load("shorts")["dub"]
SR = 48000
CACHE = OUT / "shorts" / "_tts"


def voice_for(speaker):
    for v in D["voices"]:
        if v["match"] == "*" or speaker.startswith(v["match"]):
            return v
    raise SystemExit(f"no voice for {speaker!r} in rules/base/shorts.yaml dub.voices")


def is_machine(speaker):
    return voice_for(speaker)["match"] == "*"


def spoken(text):
    """What the TTS reads: ALL-CAPS narration would be spelled out letter by letter."""
    return text[0] + text[1:].lower() if text.isupper() else text


def _post(path, body):
    req = urllib.request.Request(D["url"] + path, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        raise SystemExit(f"TTS {path}: {e.code} {e.read().decode()[:300]}")


def _synth(text, v, dst):
    if v["engine"] == "say":
        subprocess.run(["say", "-v", v["voice"], "-o", str(dst.with_suffix(".aiff")), text], check=True)
        return dst.with_suffix(".aiff")
    job = _post("/v1/audio/tts", {"text": text, "language": "cs", "voice": v["voice"], "engine": v["engine"],
                                  "commercial_only": False, "format": "wav", "seed": 7})
    while job.get("status") not in ("done", "error"):
        time.sleep(0.5)
        job = json.load(urllib.request.urlopen(f"{D['url']}/v1/audio/jobs/{job['job_id']}", timeout=60))
    if job["status"] == "error" or not job.get("outputs"):
        raise SystemExit(f"TTS failed for {text!r}: {job.get('error')}")
    url = job["outputs"][0]["url"]
    dst.write_bytes(urllib.request.urlopen(url if url.startswith("http") else D["url"] + url, timeout=120).read())
    return dst


def line(text, speaker):
    """Path of the line's wav (48 kHz mono, fx applied), synthesized on first use."""
    v = voice_for(speaker)
    text = spoken(text)
    key = hashlib.sha1(json.dumps([text, v["engine"], v["voice"], v.get("fx", "")]).encode()).hexdigest()[:16]
    out = CACHE / f"{key}.wav"
    if out.exists():
        return out
    CACHE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        raw = _synth(text, v, Path(tmp) / "raw.wav")
        af = ["-af", v["fx"]] if v.get("fx") else []
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-ac", "1", "-ar", str(SR), *af,
                        "-ar", str(SR), str(out)], check=True)
    return out


def duration(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def mix(placed, total, dst):
    """placed = [(start s, wav)] → one mono wav of `total` seconds."""
    buf = np.zeros(int((total + 1) * SR), dtype=np.float32)
    for start, path in placed:
        with wave.open(str(path)) as w:
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        i = int(start * SR)
        buf[i:i + len(a)] += a[:len(buf) - i]
    buf = buf[:int(total * SR)]
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf, -1, 1) * 32767).astype(np.int16).tobytes())
