"""Word timestamps for m0/dub.py: Whisper (mlx-whisper, Apple silicon) as a small stdin/stdout server.

    python3 m0/asr_words.py            # reads one wav path per line, answers one JSON line each:
    → {"text": "...", "words": [["slovo", start s, end s], ...]}

Runs in its own interpreter (WEBTOON_ASR_PYTHON, e.g. a venv with `pip install mlx-whisper`), so shorts.py
needs no ML packages. The model is loaded once, on the first file.
"""

import json
import os
import sys

import mlx_whisper

MODEL = os.environ.get("WEBTOON_ASR_MODEL", "mlx-community/whisper-large-v3-turbo")

for path in sys.stdin:
    path = path.strip()
    if not path:
        continue
    try:
        r = mlx_whisper.transcribe(path, path_or_hf_repo=MODEL, language="cs", word_timestamps=True,
                                   condition_on_previous_text=False)
        words = [[w["word"].strip(), round(w["start"], 3), round(w["end"], 3)] for s in r["segments"] for w in s["words"]]
        out = {"text": r["text"].strip(), "words": words}
    except Exception as e:  # one bad file must not stop the render
        out = {"text": "", "words": [], "error": str(e)}
    print(json.dumps(out, ensure_ascii=False), flush=True)
