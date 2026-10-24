"""Shared helpers for the M0 spike: config, HTTP, LLM client, booru tag handling.

Stdlib + Pillow + PyYAML (m0/requirements.txt; the rules live in rules/*.yaml, read by m0/rules.py).
Endpoints default to the Spark LAN addresses and can be overridden via env (WEBTOON_LLM, WEBTOON_COMFY, WEBTOON_WD14).
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"

LLM_URL = os.environ.get("WEBTOON_LLM", "http://192.168.88.66:8080/v1")
LLM_MODEL = os.environ.get("WEBTOON_LLM_MODEL", "openclaw-default")
COMFY_URL = os.environ.get("WEBTOON_COMFY", "http://192.168.88.66:8188")
WD14_URL = os.environ.get("WEBTOON_WD14", "http://192.168.88.66:8097")


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def http(method, url, body=None, headers=None, timeout=300):
    """Returns raw response bytes. body may be bytes or a JSON-serialisable obj."""
    headers = dict(headers or {})
    if body is not None and not isinstance(body, (bytes, bytearray)):
        body = json.dumps(body).encode()
        headers.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {url} → {e.code}: {e.read()[:500]!r}") from None


def http_json(method, url, body=None, timeout=300):
    return json.loads(http(method, url, body, timeout=timeout))


# --- LLM ---------------------------------------------------------------------

def _extract_json(text):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start = text.find("{")
    end = text.rfind("}")
    return json.loads(text[start:end + 1])


def llm_json(system, user, temperature=0.7, max_tokens=6000, retries=2):
    """Chat completion in JSON mode; returns the parsed object."""
    last = None
    for attempt in range(retries + 1):
        resp = http_json("POST", f"{LLM_URL}/chat/completions", {
            "model": LLM_MODEL,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        content = resp["choices"][0]["message"]["content"] or ""
        try:
            return _extract_json(content)
        except (ValueError, json.JSONDecodeError) as e:
            last = e
            time.sleep(1)
    raise RuntimeError(f"LLM did not return valid JSON: {last}")


# --- booru tags --------------------------------------------------------------

_vocab = None

# Tags the WD14 vocabulary lacks but the SDXL booru models understand.
EXTRA_TAGS = {
    "masterpiece", "best quality", "newest", "absurdres", "highres", "very aesthetic",
    "general", "sensitive", "safe", "1girl", "1boy", "2girls", "2boys", "no humans",
    "establishing shot", "wide shot", "close-up", "medium shot", "over-the-shoulder shot",
}


def vocab():
    global _vocab
    if _vocab is None:
        _vocab = set(load_json(DATA / "wd14_tags.json")["general"]) | EXTRA_TAGS
    return _vocab


def norm_tag(t):
    t = t.strip().lower().replace("_", " ")
    t = re.sub(r"\s+", " ", t)
    return t


def split_tags(s):
    if isinstance(s, list):
        items = s
    else:
        items = s.split(",")
    return [norm_tag(t) for t in items if t.strip()]


def filter_tags(tags, keep_unknown=False):
    """Splits tags into (known, unknown) against the WD14 vocabulary.

    Weighted tags like "(red hair:1.2)" and "artist:x" pass through untouched."""
    known, unknown = [], []
    for t in tags:
        bare = re.sub(r"^\((.*?)(:[\d.]+)?\)$", r"\1", t)
        if t.startswith("artist:") or bare in vocab():
            known.append(t)
        else:
            unknown.append(t)
    if keep_unknown:
        known += unknown
    return known, unknown


def dedupe(tags):
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


# --- WD14 --------------------------------------------------------------------

def wd14_tag(png_bytes):
    """→ {"general": {tag: conf}, "character": {...}, "rating": {...}}"""
    return json.loads(http("POST", f"{WD14_URL}/tag", png_bytes,
                           headers={"Content-Type": "application/octet-stream"}, timeout=120))


_rank = None

STOPWORDS = {"a", "an", "the", "of", "in", "on", "at", "with", "and", "to", "from", "is", "girl", "boy"}


def tag_candidates(phrase, limit=8):
    """Vocabulary tags sharing a word with phrase, most frequent first."""
    global _rank
    if _rank is None:
        _rank = load_json(DATA / "wd14_tags.json")["general"]
    words = {w for w in re.findall(r"[a-z]+", phrase.lower()) if w not in STOPWORDS and len(w) > 2}
    words |= {w[:-1] for w in words if w.endswith("s")}
    hits = []
    for t in _rank:
        tw = set(t.split())
        if tw & words:
            hits.append(t)
            if len(hits) >= limit:
                break
    return hits


TRANSLATE = """Map each free-text phrase to EXISTING Danbooru tags for an SDXL anime model.
For each phrase you get candidate tags from the tag dictionary; prefer them, but you may use other very common Danbooru tags.
Drop phrases that are not visual or are already covered (e.g. "teen girl" — counts are added automatically, "vertical composition").
Phrases with candidates:
{items}
Output JSON: {{"map": {{"<phrase>": ["<tag>", ...]}}}}"""


def translate_tags(phrases, llm_system="You are a Danbooru tagging expert."):
    """Free-text phrases → {phrase: [known booru tags]} via LLM + vocabulary candidates."""
    if not phrases:
        return {}
    items = "\n".join(f"- {p!r}: {tag_candidates(p)}" for p in phrases)
    res = llm_json(llm_system, TRANSLATE.format(items=items), temperature=0.2)
    return {p: filter_tags(split_tags(tags))[0] for p, tags in res.get("map", {}).items()}
