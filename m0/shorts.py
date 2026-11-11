"""Episode from the backend → vertical 9:16 video for TikTok / YouTube Shorts.

    python3 m0/shorts.py ep_7ccf0615b49b [--lang en] [--music track.mp3 | data/music] [--out out/shorts/x.mp4]
    → out/shorts/<world>-<title>_<lang>.mp4, e.g. rh_10_kostarika-kostarika-doma_cs.mp4

Panel by panel: portrait panels fill the frame with a slow zoom, landscape panels and Wan loops sit on a blurred
copy of themselves, bubbles (same drawing as compose.py) are lettered big below the app's top bar. Each panel
stays up as long as its text takes to read; panels crossfade. Silent AAC track unless --music: a file, or a
directory (data/music from music.py) where every world gets its own track; looped if short, faded in and out.
SFW app episodes only: free strips (lxf_) are never published.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import unicodedata
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import compose
import dub
import rules
from common import DATA, OUT, ROOT, faces_for

# Frame, timing and end texts with their reasons: rules/base/shorts.yaml.
R = rules.load("shorts")
W, H, FPS = R["frame"]["width"], R["frame"]["height"], R["frame"]["fps"]
TOP = R["top"]                # TikTok/Shorts top bar: no lettering above this
FADE = R["fade"]              # crossfade between panels, seconds
FONT_SCALE = R["font_scale"]  # compose.py letters for an 800 px strip; a phone frame wants them bigger
END = dict(R["end"]["texts"])
DUR = R["panel_duration"]


def api_get(api, path, user=None):
    """GET from the backend. JODA sits behind Caddy: /media is open, everything else needs X-Studio-Token
    (WEBTOON_STUDIO_TOKEN = STUDIO_TOKEN in JODA's deploy/.env). Cloudflare refuses urllib's default agent."""
    h = {"User-Agent": "toonfork-shorts"}
    if user:
        h["X-User-ID"] = user
    if os.environ.get("WEBTOON_STUDIO_TOKEN"):
        h["X-Studio-Token"] = os.environ["WEBTOON_STUDIO_TOKEN"]
    return urllib.request.urlopen(urllib.request.Request(api.rstrip("/") + path, headers=h))


def media_file(rel, api):
    """backend/<rel> when this machine has the media, otherwise downloaded from the API once (out/shorts/_media)."""
    local = ROOT / "backend" / rel.lstrip("/")
    if local.exists():
        return local
    cached = OUT / "shorts" / "_media" / rel.lstrip("/")
    if not cached.exists():
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(api_get(api, "/" + rel.lstrip("/")).read())
    return cached


def slug(title):
    """'Kostarika – Doma' → 'kostarika-doma': readable file names, ASCII for every platform's uploader."""
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def pick_track(music, world):
    """A file as is; from a directory the same track for every episode of a world (stable hash, not random)."""
    m = Path(music)
    if m.is_file():
        return m
    tracks = sorted(t for t in m.iterdir() if t.suffix in (".mp3", ".m4a", ".wav", ".flac", ".ogg"))
    if not tracks:
        raise SystemExit(f"no tracks in {m}")
    return tracks[int(hashlib.sha1(world.encode()).hexdigest(), 16) % len(tracks)]


def text_of(obj, key, lang):
    return (obj.get(f"{key}_i18n") or obj.get("i18n") or {}).get(lang) if lang != "cs" else None


def bubbles_layer(bubbles, lang, faces=()):
    """Transparent full-frame layer with the panel's bubbles, drawn by compose.draw_bubble; faces = face boxes in
    frame pixels, which the bubbles keep off."""
    layer = Image.new("RGBA", (W, H - TOP - R["bottom"]), (0, 0, 0, 0))  # bottom: caption and buttons
    layer._faces = [(x0, y0 - TOP, x1, y1 - TOP) for x0, y0, x1, y1 in faces if y1 > TOP]
    bs = [{**b, "text": (b.get("i18n") or {}).get(lang) or b["text"]} if lang != "cs" else b for b in bubbles]
    narr = [b for b in bs if b.get("kind") == "narration"]
    talk = [b for b in bs if b.get("kind") != "narration"]
    for k, b in enumerate(narr):
        compose.draw_bubble(layer, b, k, len(narr))
    for k, b in enumerate(talk):
        compose.draw_bubble(layer, b, k + (1 if narr else 0), len(talk))
    full = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    full.paste(layer, (0, TOP))
    return full


def cover_box(iw, ih, zoom=1.0, focus_y=0.42):
    """The part of an iw×ih image that cover() shows: (x0, y0, x1, y1) in its pixels."""
    cw = min(iw, ih * W / H) / zoom
    ch = cw * H / W
    x = (iw - cw) / 2
    y = min(max(0, ih * focus_y - ch / 2), ih - ch)
    return x, y, x + cw, y + ch


def cover(img, zoom=1.0, focus_y=0.42):
    """Crop to 9:16 (zoomed in by `zoom`) and scale to the frame; focus_y keeps faces in the upper part."""
    return img.resize((W, H), Image.LANCZOS, box=cover_box(*img.size, zoom, focus_y))


def faces_in_frame(boxes, iw, ih, landscape):
    """Face boxes (normalized to the panel) → frame pixels, for the panel shown by cover() (at its mid zoom) or
    on_blur()."""
    out = []
    for b in boxes:
        if landscape:
            fh = ih * W / iw
            top = (H - round(fh)) // 2 + 120
            out.append((b[0] * W, top + b[1] * fh, b[2] * W, top + b[3] * fh))
        else:
            x0, y0, x1, y1 = cover_box(iw, ih, zoom=1 + R["zoom"]["portrait"] / 2)
            sx, sy = W / (x1 - x0), H / (y1 - y0)
            out.append(((b[0] * iw - x0) * sx, (b[1] * ih - y0) * sy, (b[2] * iw - x0) * sx, (b[3] * ih - y0) * sy))
    return [(max(0, a), max(0, b), min(W, c), min(H, d)) for a, b, c, d in out if c > 0 and d > 0 and a < W and b < H]


def on_blur(img, bg):
    """Landscape image across the frame's width, centred, over a blurred, darkened cover of `bg`."""
    frame = bg.copy()
    fg = img.resize((W, round(img.height * W / img.width)), Image.LANCZOS)
    frame.paste(fg, (0, (H - fg.height) // 2 + 120))  # a little low, so bubbles above sit on the blur
    return frame


def blurred(img):
    b = cover(img).filter(ImageFilter.GaussianBlur(40))
    return Image.blend(b, Image.new("RGB", b.size, (0, 0, 0)), 0.35)


class Segment:
    def __init__(self, dur, frame_at, voice=()):
        self.dur, self.frame_at, self.voice = dur, frame_at, list(voice)  # voice: [(start s in the segment, wav)]


def subtitle_layer(text, kind):
    """Transparent full frame with one subtitle line block just above the bottom bar, on a dark translucent box."""
    S = R["subtitles"]
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    fnt = compose.font("narration" if kind == "narration" else "speech", S["size"])
    lines = compose.wrap(d, text, fnt, W - 4 * S["margin"])
    lh = int(fnt.size * 1.25)
    bottom = H - R["bottom"] - 10
    top = bottom - lh * len(lines) - S["margin"]
    widest = max(d.textlength(t, font=fnt) for t in lines)
    d.rounded_rectangle(((W - widest) / 2 - S["margin"] * 0.75, top, (W + widest) / 2 + S["margin"] * 0.75, bottom),
                        radius=24, fill=(0, 0, 0, S["box_alpha"]))
    color = tuple(S["colors"][kind])
    for i, t in enumerate(lines):
        d.text(((W - d.textlength(t, font=fnt)) / 2, top + S["margin"] / 2 + i * lh), t, font=fnt, fill=color,
               stroke_width=2, stroke_fill=(0, 0, 0))
    return layer


def panel_lines(p, lang):
    """The panel's bubbles in reading order (narration first, as bubbles_layer stacks them): (text, speaker, kind)."""
    bs = p.get("bubbles") or []
    out = []
    for b in [b for b in bs if b.get("kind") == "narration"] + [b for b in bs if b.get("kind") != "narration"]:
        text = ((b.get("i18n") or {}).get(lang) if lang != "cs" else None) or b["text"]
        out.append((text, b.get("speaker_id") or "", b.get("kind") or "speech"))
    return out


def panel_segment(p, api, lang, subs=False, voiced=False):
    src = media_file(p["image_url"], api)
    img = Image.open(src).convert("RGB")
    words = sum(len(t) for t, _, _ in panel_lines(p, lang))
    dur = min(DUR["max"], max(DUR["min"], DUR["base"] + DUR["per_char"] * words))
    landscape = img.width > img.height
    voice, cues = [], []  # cues: (start s, subtitle layer)
    if voiced:  # the panel stays up while its lines are spoken, one after another
        D = dub.D
        t = D["lead"]
        for text, speaker, kind in panel_lines(p, lang):
            muted = text in D["mute"]
            d = DUR["base"] if muted else dub.duration(wav := dub.line(text, speaker))
            if not muted:
                voice.append((t, wav))
            cues.append((t, subtitle_layer(text, "machine" if kind != "narration" and dub.is_machine(speaker) else kind)))
            t += d + D["gap"]
        dur = max(DUR["min"], t - D["gap"] + D["tail"]) if cues else DUR["min"]
    elif subs:  # silent: each line gets a share of the reading time by its length
        t = 0.0
        for text, speaker, kind in panel_lines(p, lang):
            cues.append((t, subtitle_layer(text, kind)))
            t += dur * len(text) / max(words, 1)
    if subs or voiced:
        layer = None
    else:
        boxes = p["faces"] if p.get("faces") is not None else faces_for([src])[str(src)]
        layer = bubbles_layer(p.get("bubbles") or [], lang, faces_in_frame(boxes, img.width, img.height, landscape))
    bg = blurred(img) if landscape else None

    frames = []
    if p.get("video_url") and p.get("video_status", "ready") == "ready":
        v = Image.open(media_file(p["video_url"], api))
        for i in range(v.n_frames):
            v.seek(i)
            f = v.convert("RGB")
            frames.append(on_blur(f, blurred(f)) if f.width > f.height else cover(f))
        dur = max(dur, R["loop"]["min_duration"])  # at least two passes of a 2 s loop

    def frame_at(t):
        if frames:
            base = frames[int(t * R["loop"]["fps"]) % len(frames)]  # Wan loops are 16 fps
        elif landscape:
            z = 1 + R["zoom"]["landscape"] * t / dur
            fg = img.resize((round(img.width * z), round(img.height * z)), Image.LANCZOS)
            fg = fg.crop(((fg.width - img.width) // 2, (fg.height - img.height) // 2,
                          (fg.width + img.width) // 2, (fg.height + img.height) // 2))
            base = on_blur(fg, bg)
        else:
            base = cover(img, zoom=1 + R["zoom"]["portrait"] * t / dur)
        out = base.convert("RGBA")
        if layer is not None:
            out.alpha_composite(layer)
        elif cues:  # the line being spoken; before the first one already the first, so it never flashes empty
            out.alpha_composite(next(c for s, c in reversed(cues) if s <= t) if t >= cues[0][0] else cues[0][1])
        return out.convert("RGB")

    return Segment(dur, frame_at, voice)


def card_segment(text, under, dur, size=R["cards"]["title"]["size"]):
    bg = blurred(under)
    d = ImageDraw.Draw(bg)
    fnt = compose.font("narration", size)
    lines = compose.wrap(d, text, fnt, W - 160)
    lh = int(size * 1.3)
    y0 = (H - lh * len(lines)) // 2
    for i, line in enumerate(lines):
        d.text(((W - d.textlength(line, font=fnt)) / 2, y0 + i * lh), line, font=fnt, fill="white",
               stroke_width=4, stroke_fill=(0, 0, 0))
    return Segment(dur, lambda t: bg)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("episode")
    ap.add_argument("--lang", default="cs")
    ap.add_argument("--music", default=None, help="audio file or directory of tracks (one per world)")
    ap.add_argument("--volume", type=float, default=0.8)
    ap.add_argument("--api", default=os.environ.get("WEBTOON_API", "https://webtoon-api.ol1n.com"), help="backend; default JODA via the tunnel")
    ap.add_argument("--user", default="player", help="X-User-ID of the episode's owner")
    ap.add_argument("--out", default=None)
    ap.add_argument("--no-end", action="store_true", help="no end card (a chapter that is followed by another one)")
    ap.add_argument("--subtitles", action="store_true", help="the bubbles' text as subtitles at the bottom, no bubbles")
    ap.add_argument("--dub", action="store_true", help="every line spoken (rules/base/shorts.yaml dub); implies --subtitles")
    args = ap.parse_args()
    if args.dub and args.lang != "cs":
        raise SystemExit("--dub has Czech voices only")

    ep = json.load(api_get(args.api, f"/episodes/{args.episode}", args.user))
    world = json.load(api_get(args.api, f"/campaigns/{ep['campaign_id']}", args.user))["world_id"]
    if world.startswith(rules.get("pack.forbidden_world_prefix")):
        raise SystemExit("free strips are never published")
    sb = DATA / "stories" / world.removeprefix("w_") / "storyboard.json"
    compose.FONT_SET = json.loads(sb.read_text()).get("fonts") if sb.exists() else "romance"
    base_font = compose.font
    compose.font = lambda kind, size: base_font(kind, round(size * FONT_SCALE))

    panels = [p for p in ep["panels"] if p.get("image_url")]
    subs = args.subtitles or args.dub
    if not subs:
        faces_for([media_file(p["image_url"], args.api) for p in panels if p.get("faces") is None])  # one detector run
    first = Image.open(media_file(panels[0]["image_url"], args.api)).convert("RGB")
    last = Image.open(media_file(panels[-1]["image_url"], args.api)).convert("RGB")
    title = text_of(ep, "title", args.lang) or ep["title"]
    C = R["cards"]
    segs = [card_segment(title, first, C["title"]["duration"])] + \
        [panel_segment(p, args.api, args.lang, subs=subs, voiced=args.dub) for p in panels]
    if not args.no_end:
        segs.append(card_segment(END.get(args.lang, R["end"]["default"]), last, C["end"]["duration"], size=C["end"]["size"]))

    out = Path(args.out or OUT / "shorts" / f"{world.removeprefix('w_')}-{slug(ep['title'])}_{args.lang}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    total = sum(s.dur for s in segs) - FADE * (len(segs) - 1)
    music = pick_track(args.music, world) if args.music else None
    tmp = tempfile.TemporaryDirectory()
    if args.dub:  # one voice track: every line at its segment's start (segments overlap by FADE)
        placed, at = [], 0.0
        for s in segs:
            placed += [(at + t, w) for t, w in s.voice]
            at += s.dur - FADE
        voice_wav = Path(tmp.name) / "voice.wav"
        dub.mix(placed, total, voice_wav)
    fade = f"afade=t=in:d=0.5,afade=t=out:st={max(total - 1.5, 0):.2f}:d=1.5"
    if args.dub and music:
        audio = ["-i", str(voice_wav), "-stream_loop", "-1", "-i", str(music)]
        afilter = ["-filter_complex", f"[2:a]volume={dub.D['music_duck']},{fade}[m];[1:a]aformat=channel_layouts=stereo[v];"
                                      f"[v][m]amix=inputs=2:duration=first:normalize=0[a]", "-map", "[a]"]
    elif args.dub:
        audio, afilter = ["-i", str(voice_wav)], ["-map", "1:a"]
    elif music:
        audio = ["-stream_loop", "-1", "-i", str(music)]
        afilter = ["-af", f"volume={args.volume},{fade}", "-map", "1:a"]
    else:
        audio, afilter = ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"], ["-map", "1:a"]
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", *audio, *afilter,
                           "-map", "0:v", "-ac", "2", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest",
                           "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)
    for k, s in enumerate(segs):
        start = FADE if k else 0  # the first FADE seconds were already shown blended into the previous segment
        nxt = segs[k + 1] if k + 1 < len(segs) else None
        for n in range(round(start * FPS), round(s.dur * FPS)):
            t = n / FPS
            f = s.frame_at(t)
            if nxt and t > s.dur - FADE:
                tn = t - (s.dur - FADE)
                f = Image.blend(f, nxt.frame_at(tn), tn / FADE)
            ff.stdin.write(f.tobytes())
    ff.stdin.close()
    if ff.wait():
        raise SystemExit("ffmpeg failed")
    tmp.cleanup()
    print(f"{out}  {total:.1f} s, {len(panels)} panels" + (f", music {music.name}" if music else ""))


if __name__ == "__main__":
    main()
