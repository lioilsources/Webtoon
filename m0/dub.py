"""Bubbles → spoken lines for shorts.py --dub: TTS from AiStack's audio service (or macOS say), cached per line.

Cast and timing: rules/base/shorts.yaml dub. Every line is a 48 kHz mono wav in out/shorts/_tts/<hash>.wav, so a
rerun (other music, other cut) does not synthesize again. Machine and narration voices get an ffmpeg filter (fx).
"""

import difflib
import hashlib
import json
import os
import re
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


def _synth(text, v, dst, seed=7):
    if v["engine"] == "say":
        subprocess.run(["say", "-v", v["voice"], "-o", str(dst.with_suffix(".aiff")), text], check=True)
        return dst.with_suffix(".aiff")
    job = _post("/v1/audio/tts", {"text": text, "language": "cs", "voice": v["voice"], "engine": v["engine"],
                                  "commercial_only": False, "format": "wav", "seed": seed})
    while job.get("status") not in ("done", "error"):
        time.sleep(0.5)
        job = json.load(urllib.request.urlopen(f"{D['url']}/v1/audio/jobs/{job['job_id']}", timeout=60))
    if job["status"] == "error" or not job.get("outputs"):
        raise SystemExit(f"TTS failed for {text!r}: {job.get('error')}")
    url = job["outputs"][0]["url"]
    dst.write_bytes(urllib.request.urlopen(url if url.startswith("http") else D["url"] + url, timeout=120).read())
    return dst


def _take(text, v, key, k):
    """Raw take k of a line (48 kHz mono, fx applied): take 0 is seed 7, the next ones seed 7 + k."""
    path = CACHE / (f"{key}.wav" if k == 0 else f"{key}_v{k}.wav")
    if not path.exists():
        with tempfile.TemporaryDirectory() as tmp:
            raw = _synth(text, v, Path(tmp) / "raw.wav", seed=7 + k)
            af = ["-af", v["fx"]] if v.get("fx") else []
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-ac", "1", "-ar", str(SR), *af,
                            "-ar", str(SR), str(path)], check=True)
    return path


def line(text, speaker):
    """Path of the line's wav (48 kHz mono, fx applied, tail cleaned), synthesized on first use.

    A voice with `takes` (XTTS) is checked by Whisper: up to that many takes until one is heard as the text, the
    best one is cut right after its last word (XTTS garbles the end of a line or babbles on after it)."""
    v = voice_for(speaker)
    text = spoken(text)
    key = hashlib.sha1(json.dumps([text, v["engine"], v["voice"], v.get("fx", "")]).encode()).hexdigest()[:16]
    out = CACHE / f"{key}_t.wav"
    if out.exists():
        return out
    CACHE.mkdir(parents=True, exist_ok=True)
    if not (v.get("takes") and asr_available()):
        _write(out, clean_tail(_read(_take(text, v, key, 0)), len(text), v.get("tail_rate")))
        return out
    best = None
    for k in range(v["takes"]):
        path = _take(text, v, key, k)
        heard = asr(path)
        score, end = match(text, heard)
        if best is None or score > best[0]:
            best = (score, k, end, heard["text"])
        if score >= D["asr_accept"]:
            break
    score, k, end, heard = best
    a = _read(_take(text, v, key, k))
    if end is not None:
        a = a[:min(len(a), int((end + D["asr_margin"]) * SR))]
        a = clean_tail(a)
    else:
        a = clean_tail(a, len(text), v.get("tail_rate"))
    _write(out, a)
    (CACHE / f"{key}_pick.json").write_text(json.dumps({"text": text, "take": k, "score": round(score, 3),
                                                        "heard": heard}, ensure_ascii=False))
    return out


_ASR = None


def asr_available():
    return bool(os.environ.get("WEBTOON_ASR_PYTHON"))


def asr(path):
    """{"text", "words": [[word, start, end]]} from m0/asr_words.py, started once in WEBTOON_ASR_PYTHON."""
    global _ASR
    if _ASR is None:
        _ASR = subprocess.Popen([os.environ["WEBTOON_ASR_PYTHON"], str(Path(__file__).parent / "asr_words.py")],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    _ASR.stdin.write(f"{path}\n")
    _ASR.stdin.flush()
    return json.loads(_ASR.stdout.readline())


def _norm(s):
    return " ".join(re.sub(r"[^\w\s]", " ", s.lower()).split())


def match(text, heard):
    """(similarity 0–1 of what Whisper heard to the text, end s of the last word that matches the text's end)."""
    want = _norm(text)
    words = [(_norm(w), e) for w, _, e in heard["words"] if _norm(w)]
    got = " ".join(w for w, _ in words)
    sm = difflib.SequenceMatcher(None, want, got, autojunk=False)
    score = sm.ratio()
    blocks = [b for b in sm.get_matching_blocks() if b.size]
    if not blocks or not words:
        return score, None
    last = blocks[-1].b + blocks[-1].size - 1  # last character of the take that matches the text
    pos = 0
    for w, e in words:
        if pos + len(w) > last:
            return score, e
        pos += len(w) + 1
    return score, words[-1][1]


def _read(path):
    with wave.open(str(path)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768


def _write(path, a):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype(np.int16).tobytes())


def clean_tail(a, chars=0, rate=None, gap=0.08, quiet=0.05, step=0.02, fade=0.04, pad=0.12):
    """XTTS often babbles on after the sentence (a garbled syllable, click or breath; on one-word lines up to a
    second) and the service trims the silence after it, so the line seems to end broken. With `rate` (s per
    character, a slow estimate of the voice), cut at the first pause (≥ gap s below quiet × peak) that starts after
    the text can have been said; a pause or a quiet sibilant inside the sentence comes earlier and is kept.
    Every line then fades out and gets a little silence."""
    if rate:
        n = int(step * SR)
        rms = np.sqrt(np.array([np.mean(a[i:i + n] ** 2) for i in range(0, len(a) - n + 1, n)]) + 1e-12)
        lo = rms < quiet * rms.max() if len(rms) else rms
        need, k = int(gap / step), int(chars * rate / step)
        while k < len(rms):
            if lo[k] and lo[k:k + need].all() and k + need <= len(rms):
                a = a[:(k + 2) * n]  # keep a little of the pause, so the last phoneme decays naturally
                break
            k += 1
    f = min(len(a), int(fade * SR))
    a = a.copy()
    a[len(a) - f:] *= np.linspace(1, 0, f, dtype=np.float32)
    return np.concatenate([a, np.zeros(int(pad * SR), dtype=np.float32)])


def duration(path):
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def mix(placed, total, dst):
    """placed = [(start s, wav)] → one mono wav of `total` seconds."""
    buf = np.zeros(int((total + 1) * SR), dtype=np.float32)
    for start, path in placed:
        a = _read(path)
        i = int(start * SR)
        buf[i:i + len(a)] += a[:len(buf) - i]
    _write(dst, buf[:int(total * SR)])
