"""Job registry: every rendered panel — kept or not — with model, LoRAs, sampler, seed and prompts.

    kids/runs/jobs.jsonl      one JSON record per render (append-only)
    kids/gallery/<story>/     the images themselves as JPEG (the container is ephemeral; out/ is not committed)

A record is self-contained: it repeats the preset it was rendered with, so later preset edits do not
rewrite history. `selected` says whether the image went into the strip; a later pick appends a
{"event": "pick"} record instead of editing the old line. This is the input for model matchups.
"""

import datetime
import hashlib
import io
import json
from pathlib import Path

from PIL import Image

KIDS = Path(__file__).resolve().parent
JOBS = KIDS / "runs" / "jobs.jsonl"
GALLERY = KIDS / "gallery"


def _append(rec):
    JOBS.parent.mkdir(parents=True, exist_ok=True)
    with open(JOBS, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def save_image(png, story, name):
    """JPEG copy in the gallery; returns its repo-relative path."""
    out = GALLERY / story / f"{name}.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.open(io.BytesIO(png)).convert("RGB").save(out, "JPEG", quality=88)
    return str(out.relative_to(KIDS.parent))


def record(story, panel, variant, meta, png, selected, seconds=None, source="render", note=None):
    rec = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "source": source,  # render | reconstructed
        "story": story, "panel": panel, "variant": variant, "selected": selected,
        **meta,
        "sha256": hashlib.sha256(png).hexdigest(),
        "image": save_image(png, story, f"p{panel:02d}_{'s0' if variant is None else f'v{variant}'}"),
        "seconds": seconds,
    }
    if note:
        rec["note"] = note
    _append(rec)
    return rec


def pick(story, panel, variant, seed):
    _append({"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             "event": "pick", "story": story, "panel": panel, "variant": variant, "seed": seed})


def load():
    if not JOBS.exists():
        return []
    return [json.loads(l) for l in JOBS.read_text(encoding="utf-8").splitlines() if l.strip()]
