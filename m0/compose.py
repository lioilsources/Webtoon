"""Panels + storyboard bubbles → one vertical webtoon strip PNG (M0 stand-in for the Flutter overlay).

    python3 m0/compose.py --storyboard out/dev/storyboard_ep1.json --panels out/<day>/<run> [--variant 0] --out strip.png
    python3 m0/compose.py --storyboard ... --placeholder --out strip.png   # layout test without images

Bubble placement heuristic (no bboxes in M0): alternate top corners, narration as a box at the top-left,
tails point toward the panel centre.
"""

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import rules
from common import ROOT, load_json

# Layout rules (gaps, font sets, bubble sizing) with their reasons: rules/base/compose.yaml.
R = rules.load("compose")
WIDTH = R["width"]
GAPS = dict(R["gaps"])
FONTS = ROOT / R["fonts"]["default"]["dir"]
BG = tuple(R["bg"])
INK = tuple(R["ink"])
B = R["bubble"]

# Grown-up lettering for the romance stories (storyboard "fonts": "romance"); macOS system fonts, M0 is local.
SYSTEM_FONTS = Path(R["fonts"]["romance"]["dir"])
ROMANCE = {k: tuple(v) for k, v in R["fonts"]["romance"]["faces"].items()}
DEFAULT_FACES = {k: (name, weight.encode()) for k, (name, weight) in R["fonts"]["default"]["faces"].items()}
FONT_SET = None


def font(kind, size):
    if FONT_SET == "romance" and (SYSTEM_FONTS / ROMANCE[kind][0]).exists():
        return ImageFont.truetype(str(SYSTEM_FONTS / ROMANCE[kind][0]), size, index=ROMANCE[kind][1])
    name, weight = DEFAULT_FACES[kind]
    f = ImageFont.truetype(str(FONTS / name), size)
    try:
        f.set_variation_by_name(weight)
    except (OSError, ValueError):
        pass
    return f


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_bubble(img, bubble, slot, n_slots):
    d = ImageDraw.Draw(img)
    W, H = img.size
    kind = bubble.get("kind", "speech")
    fnt = font(kind, B["font_size"] if kind != "shout" else B["shout_font_size"])
    max_w = int(W * (B["max_width"] if kind != "narration" else B["narration_max_width"]))
    lines = wrap(d, bubble["text"], fnt, max_w - B["text_inset"])
    lh = int(fnt.size * B["line_height"])
    tw = max(d.textlength(l, font=fnt) for l in lines)
    bw, bh = int(tw) + B["pad"][0], lh * len(lines) + B["pad"][1]
    margin = B["margin"]
    if kind == "narration":
        x, y = margin, margin + slot * (bh + 12)
    else:
        right = slot % 2 == 1
        x = W - bw - margin if right else margin
        y = margin + (slot // 2) * (bh + 30) + (40 if right else 0)
    # Two long bubbles would overlap side by side: put the later one below the previous.
    for px0, py0, px1, py1 in getattr(img, "_bubbles", []):
        if x < px1 and px0 < x + bw and y < py1 + 30 and py0 < y + bh:
            y = py1 + 50
    img._bubbles = getattr(img, "_bubbles", []) + [(x, y, x + bw, y + bh)]
    box = (x, y, x + bw, y + bh)

    if kind == "narration":
        d.rectangle(box, fill=tuple(B["narration_fill"]), outline=INK, width=3)
    else:
        cx, cy = x + bw / 2, y + bh
        tx, ty = cx + (40 if cx < W / 2 else -40), min(H - 20, y + bh + 48)
        if kind == "thought":
            for r, f in ((10, 0.35), (7, 0.65), (5, 0.9)):
                px, py = cx + (tx - cx) * f, cy + (ty - cy) * f
                d.ellipse((px - r, py - r, px + r, py + r), fill="white", outline=INK, width=2)
        else:
            d.polygon([(cx - 22, cy - 4), (cx + 10, cy - 4), (tx, ty)], fill="white", outline=INK, width=3)
        if kind == "shout":
            d.rectangle(box, fill="white", outline=INK, width=5)
        else:
            d.rounded_rectangle(box, radius=min(bh // 2, 40), fill="white", outline=INK, width=3)
        if kind != "thought":
            d.polygon([(cx - 19, cy - 6), (cx + 7, cy - 6), (tx - 1, ty - 9)], fill="white")
    for i, line in enumerate(lines):
        lw = d.textlength(line, font=fnt)
        d.text((x + (bw - lw) / 2, y + 15 + i * lh), line, font=fnt, fill=INK)


def draw_sfx(img, sfx, i):
    d = ImageDraw.Draw(img)
    W, H = img.size
    fnt = font("sfx", R["sfx"]["size"])
    x, y = int(W * (0.55 if i % 2 == 0 else 0.1)), int(H * 0.68)
    d.text((x, y), sfx["text"], font=fnt, fill=tuple(R["sfx"]["fill"]), stroke_width=R["sfx"]["stroke"], stroke_fill=INK)


def end_block():
    img = Image.new("RGB", (WIDTH, 200), (245, 243, 250))
    d = ImageDraw.Draw(img)
    fnt = font("narration", 48)
    end = R["texts"]["end"]
    d.text(((WIDTH - d.textlength(end, font=fnt)) / 2, 70), end, font=fnt, fill=INK)
    return img


def choices_block(choices, title):
    img = Image.new("RGB", (WIDTH, 120 + 110 * len(choices)), (245, 243, 250))
    d = ImageDraw.Draw(img)
    d.text((40, 40), R["texts"]["choices"], font=font("narration", 40), fill=INK)
    for i, c in enumerate(choices):
        y = 120 + i * 110
        free = c.get("kind") == "free"
        d.rounded_rectangle((40, y, WIDTH - 40, y + 86), radius=24, fill="white" if not free else (235, 235, 240),
                            outline=(120, 90, 200), width=3)
        d.text((70, y + 26), c["text"], font=font("ui", 28), fill=INK if not free else (110, 110, 120))
    return img


def placeholder(panel, i):
    w, h = (1216, 832) if panel["shot"] in ("wide", "establishing") else (832, 1216)
    img = Image.new("RGB", (w, h), (200 + i * 6 % 50, 210, 225))
    d = ImageDraw.Draw(img)
    d.text((30, h - 80), f"#{i} {panel['shot']} @ {panel['location_id']}", font=font("ui", 40), fill=INK)
    return img


def compose(sb, panel_dir=None, variant=0, use_placeholder=False):
    global FONT_SET
    FONT_SET = sb.get("fonts")
    parts = []
    for i, p in enumerate(sb["panels"]):
        if use_placeholder:
            img = placeholder(p, i)
        else:
            img = Image.open(Path(panel_dir) / f"p{i:02d}_s{variant}.png").convert("RGB")
        img = img.resize((WIDTH, round(img.height * WIDTH / img.width)), Image.LANCZOS)
        bubbles = p.get("bubbles", [])
        narr = [b for b in bubbles if b.get("kind") == "narration"]
        talk = [b for b in bubbles if b.get("kind") != "narration"]
        for k, b in enumerate(narr):
            draw_bubble(img, b, k, len(narr))
        for k, b in enumerate(talk):
            draw_bubble(img, b, k + (1 if narr else 0), len(talk))
        for k, s in enumerate(p.get("sfx", [])):
            draw_sfx(img, s, k)
        parts.append((img, GAPS.get(p.get("gap_after"), R["default_gap"])))

    tf = font("narration", R["title"]["size"])
    tlines = wrap(ImageDraw.Draw(Image.new("RGB", (1, 1))), sb["title"], tf, WIDTH - 80)
    tl = R["title"]["line"]
    title = Image.new("RGB", (WIDTH, 100 + tl * len(tlines)), BG)
    for k, line in enumerate(tlines):
        ImageDraw.Draw(title).text((40, 50 + tl * k), line, font=tf, fill=INK)
    end = choices_block(sb["choices"], sb["title"]) if sb.get("choices") else end_block()
    total = title.height + sum(im.height + g for im, g in parts) + end.height
    strip = Image.new("RGB", (WIDTH, total), BG)
    y = 0
    strip.paste(title, (0, y)); y += title.height
    for im, g in parts:
        strip.paste(im, (0, y)); y += im.height + g
    strip.paste(end, (0, y))
    return strip


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--storyboard", required=True)
    ap.add_argument("--panels")
    ap.add_argument("--variant", type=int, default=0)
    ap.add_argument("--placeholder", action="store_true")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    strip = compose(load_json(args.storyboard), args.panels, args.variant, args.placeholder)
    strip.save(args.out, optimize=True)
    print(f"{args.out}: {strip.width}x{strip.height}")


if __name__ == "__main__":
    main()
