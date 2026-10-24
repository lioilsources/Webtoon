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
import re
import subprocess
import unicodedata
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import compose
import rules
from common import DATA, OUT, ROOT

# Frame, timing and end texts with their reasons: rules/shorts.yaml.
R = rules.load("shorts")
W, H, FPS = R["frame"]["width"], R["frame"]["height"], R["frame"]["fps"]
TOP = R["top"]                # TikTok/Shorts top bar: no lettering above this
FADE = R["fade"]              # crossfade between panels, seconds
FONT_SCALE = R["font_scale"]  # compose.py letters for an 800 px strip; a phone frame wants them bigger
END = dict(R["end"]["texts"])
DUR = R["panel_duration"]


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


def bubbles_layer(bubbles, lang):
    """Transparent full-frame layer with the panel's bubbles, drawn by compose.draw_bubble."""
    layer = Image.new("RGBA", (W, H - TOP - R["bottom"]), (0, 0, 0, 0))  # bottom: caption and buttons
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


def cover(img, zoom=1.0, focus_y=0.42):
    """Crop to 9:16 (zoomed in by `zoom`) and scale to the frame; focus_y keeps faces in the upper part."""
    iw, ih = img.size
    cw = min(iw, ih * W / H) / zoom
    ch = cw * H / W
    x = (iw - cw) / 2
    y = min(max(0, ih * focus_y - ch / 2), ih - ch)
    return img.resize((W, H), Image.LANCZOS, box=(x, y, x + cw, y + ch))


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
    def __init__(self, dur, frame_at):
        self.dur, self.frame_at = dur, frame_at


def panel_segment(p, media, lang):
    img = Image.open(media / p["image_url"].lstrip("/")).convert("RGB")
    words = sum(len(((b.get("i18n") or {}).get(lang) if lang != "cs" else None) or b["text"]) for b in p.get("bubbles") or [])
    dur = min(DUR["max"], max(DUR["min"], DUR["base"] + DUR["per_char"] * words))
    layer = bubbles_layer(p.get("bubbles") or [], lang)
    landscape = img.width > img.height
    bg = blurred(img) if landscape else None

    frames = []
    if p.get("video_url") and p.get("video_status", "ready") == "ready":
        v = Image.open(media / p["video_url"].lstrip("/"))
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
        out.alpha_composite(layer)
        return out.convert("RGB")

    return Segment(dur, frame_at)


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
    ap.add_argument("--api", default="http://localhost:8095")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    req = urllib.request.Request(f"{args.api}/episodes/{args.episode}", headers={"X-User-ID": "player"})
    ep = json.load(urllib.request.urlopen(req))
    world = subprocess.run(["docker", "exec", "webtoon-db-1", "sh", "-c",
                            'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "select c.world_id from episodes e '
                            f"join campaigns c on c.id=e.campaign_id where e.id='{args.episode}'\""],
                           capture_output=True, text=True).stdout.strip()
    if world.startswith(rules.get("pack.forbidden_world_prefix")):
        raise SystemExit("free strips are never published")
    sb = DATA / "stories" / world.removeprefix("w_") / "storyboard.json"
    compose.FONT_SET = json.loads(sb.read_text()).get("fonts") if sb.exists() else "romance"
    base_font = compose.font
    compose.font = lambda kind, size: base_font(kind, round(size * FONT_SCALE))

    media = ROOT / "backend"
    panels = [p for p in ep["panels"] if p.get("image_url")]
    first = Image.open(media / panels[0]["image_url"].lstrip("/")).convert("RGB")
    last = Image.open(media / panels[-1]["image_url"].lstrip("/")).convert("RGB")
    title = text_of(ep, "title", args.lang) or ep["title"]
    C = R["cards"]
    segs = [card_segment(title, first, C["title"]["duration"])] + [panel_segment(p, media, args.lang) for p in panels] \
        + [card_segment(END.get(args.lang, R["end"]["default"]), last, C["end"]["duration"], size=C["end"]["size"])]

    out = Path(args.out or OUT / "shorts" / f"{world.removeprefix('w_')}-{slug(ep['title'])}_{args.lang}.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    total = sum(s.dur for s in segs) - FADE * (len(segs) - 1)
    music = pick_track(args.music, world) if args.music else None
    audio = ["-stream_loop", "-1", "-i", str(music)] if music else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
    afilter = ["-af", f"volume={args.volume},afade=t=in:d=0.5,afade=t=out:st={total - 1.5:.2f}:d=1.5"] if music else []
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", *audio, *afilter,
                           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
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
    print(f"{out}  {total:.1f} s, {len(panels)} panels" + (f", music {music.name}" if music else ""))


if __name__ == "__main__":
    main()
