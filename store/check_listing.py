#!/usr/bin/env python3
"""Checks store/listing/<locale>/*.txt against the App Store Connect and Google Play limits.

    python3 store/check_listing.py          # exit 1 when anything is over a limit or missing

Characters are counted as Unicode code points after NFC normalization (what both consoles count);
App Store keywords are limited in UTF-8 bytes.
"""
import os
import re
import sys
import unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "listing")
LOCALES = ["cs", "en-US", "de-DE", "it", "fr-FR", "pl", "pt-BR", "ja", "ko", "vi", "ru", "uk"]

# file -> (limit, unit)
LIMITS = {
    "name.txt": (30, "chars"),
    "subtitle.txt": (30, "chars"),
    "keywords.txt": (100, "bytes"),
    "promotional_text.txt": (170, "chars"),
    "description.txt": (4000, "chars"),
    "play_short_description.txt": (80, "chars"),
    "play_full_description.txt": (4000, "chars"),
    "release_notes.txt": (4000, "chars"),
}
SINGLE_LINE = {"name.txt", "subtitle.txt", "keywords.txt", "play_short_description.txt"}
# Play policy: no ranking / superlative claims, no emoji
RANKING = re.compile(r"(#\s?1\b|\bnumber one\b|\bbest\b|\btop\s?\d|\bno\.\s?1\b)", re.I)
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]")
NAME_SPLIT = re.compile(r"[\s:：,&\-–]+")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return unicodedata.normalize("NFC", fh.read().rstrip("\n"))


def main():
    errors, rows = [], []
    for loc in LOCALES:
        texts = {}
        for fname, (limit, unit) in LIMITS.items():
            path = os.path.join(ROOT, loc, fname)
            if not os.path.exists(path):
                errors.append(f"{loc}/{fname}: missing")
                continue
            t = texts[fname] = read(path)
            n = len(t.encode("utf-8")) if unit == "bytes" else len(t)
            ok = 0 < n <= limit
            rows.append((loc, fname, n, limit, unit, ok))
            if not ok:
                errors.append(f"{loc}/{fname}: {n} {unit} (limit {limit})")
            if fname in SINGLE_LINE and "\n" in t:
                errors.append(f"{loc}/{fname}: must be one line")
            if fname.startswith("play_") and RANKING.search(t):
                errors.append(f"{loc}/{fname}: ranking claim {RANKING.search(t).group(0)!r}")
            if EMOJI.search(t):
                errors.append(f"{loc}/{fname}: emoji {EMOJI.search(t).group(0)!r}")

        kw = texts.get("keywords.txt")
        if kw is not None:
            words = kw.split(",")
            if any(w != w.strip() or not w for w in words):
                errors.append(f"{loc}/keywords.txt: empty keyword or space around a comma")
            low = [w.lower() for w in words]
            dup = {w for w in low if low.count(w) > 1}
            if dup:
                errors.append(f"{loc}/keywords.txt: repeated {sorted(dup)}")
            name_words = {w.lower() for w in NAME_SPLIT.split(texts.get("name.txt", "")) if len(w) > 1}
            for w in low:
                hit = name_words & set(w.split())
                if w in name_words or hit:
                    errors.append(f"{loc}/keywords.txt: {w!r} repeats a word of the name")

    width = max(len(f"{r[0]}/{r[1]}") for r in rows)
    for loc, fname, n, limit, unit, ok in rows:
        print(f"{'OK ' if ok else 'BAD'} {f'{loc}/{fname}':<{width}} {n:>5} / {limit} {unit}")
    print()
    if errors:
        print(f"{len(errors)} problem(s):")
        for e in errors:
            print("  " + e)
        return 1
    print(f"all {len(rows)} files within limits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
