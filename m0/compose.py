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

from common import ROOT, load_json

WIDTH = 800
GAPS = {"small": 40, "medium": 140, "large": 320}
FONTS = ROOT / "assets" / "fonts"
BG = (255, 255, 255)
INK = (20, 20, 24)


def font(kind, size):
    name, weight = {"speech": ("Nunito-Variable.ttf", b"Bold"), "thought": ("Nunito-Italic-Variable.ttf", b"SemiBold"),
                    "shout": ("DynaPuff-Variable.ttf", b"Bold"), "narration": ("Baloo2-Variable.ttf", b"Medium"),
                    "sfx": ("DynaPuff-Variable.ttf", b"Bold"), "ui": ("Nunito-Variable.ttf", b"SemiBold"),
                    "pet": ("DynaPuff-Variable.ttf", b"Bold"), "radio": ("Nunito-Variable.ttf", b"Bold")}[kind]
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


PET_FILL = (255, 244, 214)
RADIO_FILL = (222, 238, 255)


def draw_icon(d, icon, cx, cy, r):
    """Small pictogram for pet bubbles (what the animal is thinking about)."""
    if icon == "bone":
        d.rounded_rectangle((cx - r, cy - r * 0.25, cx + r, cy + r * 0.25), radius=4, fill="white", outline=INK, width=2)
        for sx in (-1, 1):
            for sy in (-1, 1):
                ex, ey = cx + sx * r, cy + sy * r * 0.3
                d.ellipse((ex - r * 0.32, ey - r * 0.32, ex + r * 0.32, ey + r * 0.32), fill="white", outline=INK, width=2)
        d.rectangle((cx - r * 0.85, cy - r * 0.2, cx + r * 0.85, cy + r * 0.2), fill="white")
    elif icon == "fish":
        d.polygon([(cx + r * 0.4, cy), (cx + r, cy - r * 0.55), (cx + r, cy + r * 0.55)], fill=(120, 180, 230), outline=INK)
        d.ellipse((cx - r, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55), fill=(120, 180, 230), outline=INK, width=2)
        d.ellipse((cx - r * 0.62, cy - r * 0.2, cx - r * 0.42, cy), fill=INK)
    elif icon == "pearl":
        d.ellipse((cx - r * 0.8, cy - r * 0.8, cx + r * 0.8, cy + r * 0.8), fill=(150, 210, 255), outline=INK, width=2)
        d.ellipse((cx - r * 0.45, cy - r * 0.5, cx - r * 0.1, cy - r * 0.15), fill="white")
    elif icon == "bolt":
        d.polygon([(cx + r * 0.2, cy - r), (cx - r * 0.6, cy + r * 0.1), (cx - r * 0.05, cy + r * 0.1),
                   (cx - r * 0.3, cy + r), (cx + r * 0.6, cy - r * 0.15), (cx + r * 0.05, cy - r * 0.15)],
                  fill=(255, 210, 40), outline=INK)
    elif icon == "heart":
        d.ellipse((cx - r, cy - r * 0.7, cx, cy + r * 0.3), fill=(240, 90, 110))
        d.ellipse((cx, cy - r * 0.7, cx + r, cy + r * 0.3), fill=(240, 90, 110))
        d.polygon([(cx - r * 0.95, cy - r * 0.05), (cx + r * 0.95, cy - r * 0.05), (cx, cy + r)], fill=(240, 90, 110))
    elif icon == "moon":
        d.ellipse((cx - r * 0.8, cy - r * 0.8, cx + r * 0.8, cy + r * 0.8), fill=(255, 215, 80), outline=INK, width=2)
        d.ellipse((cx - r * 0.35, cy - r * 0.95, cx + r * 1.1, cy + r * 0.6), fill=PET_FILL)
    elif icon == "carrot":
        d.polygon([(cx - r * 0.7, cy - r * 0.55), (cx - r * 0.25, cy - r * 0.85), (cx + r * 0.85, cy + r * 0.85)],
                  fill=(245, 140, 40), outline=INK)
        d.line([(cx - r * 0.55, cy - r * 0.75), (cx - r * 0.95, cy - r * 1.05)], fill=(70, 160, 70), width=4)
        d.line([(cx - r * 0.45, cy - r * 0.8), (cx - r * 0.45, cy - r * 1.15)], fill=(70, 160, 70), width=4)
    elif icon == "cookie":
        d.ellipse((cx - r * 0.85, cy - r * 0.85, cx + r * 0.85, cy + r * 0.85), fill=(215, 160, 90), outline=INK, width=2)
        for ox, oy in ((-0.35, -0.3), (0.3, -0.1), (-0.1, 0.4), (0.35, 0.45)):
            d.ellipse((cx + (ox - 0.1) * r, cy + (oy - 0.1) * r, cx + (ox + 0.1) * r, cy + (oy + 0.1) * r), fill=(90, 50, 30))
    elif icon == "strawberry":
        d.polygon([(cx - r * 0.8, cy - r * 0.35), (cx + r * 0.8, cy - r * 0.35), (cx, cy + r)], fill=(225, 45, 60), outline=INK)
        d.ellipse((cx - r * 0.8, cy - r * 0.75, cx + r * 0.8, cy + r * 0.1), fill=(225, 45, 60))
        d.polygon([(cx - r * 0.5, cy - r * 0.55), (cx, cy - r * 0.95), (cx + r * 0.5, cy - r * 0.55)], fill=(70, 160, 70))
        for ox, oy in ((-0.3, -0.1), (0.3, -0.1), (0, 0.3), (-0.15, 0.6), (0.15, 0.6)):
            d.ellipse((cx + ox * r - 2, cy + oy * r - 2, cx + ox * r + 2, cy + oy * r + 2), fill=(255, 230, 120))
    elif icon == "star":
        import math
        pts = [(cx + (r if k % 2 == 0 else r * 0.45) * math.sin(k * math.pi / 5),
                cy - (r if k % 2 == 0 else r * 0.45) * math.cos(k * math.pi / 5)) for k in range(10)]
        d.polygon(pts, fill=(255, 205, 50), outline=INK)
    else:  # paw
        d.ellipse((cx - r * 0.55, cy - r * 0.1, cx + r * 0.55, cy + r * 0.8), fill=(150, 100, 70))
        for ox, oy in ((-0.7, -0.35), (-0.25, -0.75), (0.25, -0.75), (0.7, -0.35)):
            d.ellipse((cx + (ox - 0.22) * r, cy + (oy - 0.22) * r, cx + (ox + 0.22) * r, cy + (oy + 0.22) * r), fill=(150, 100, 70))


def draw_pet(img, bubble, slot, placed):
    """Pet bubble: pictogram + the animal's sound, with the 'translation' small underneath."""
    d = ImageDraw.Draw(img)
    W, H = img.size
    fs, ft = font("pet", 28), font("thought", 21)
    icon_w, pad = 52, 18
    max_w = int(W * 0.6)
    sound = wrap(d, bubble["text"], fs, max_w - icon_w - 2 * pad)
    trans = wrap(d, bubble["translation"], ft, max_w - icon_w - 2 * pad) if bubble.get("translation") else []
    lhs, lht = int(fs.size * 1.2), int(ft.size * 1.25)
    tw = max([d.textlength(l, font=fs) for l in sound] + [d.textlength(l, font=ft) for l in trans])
    bw = int(tw) + icon_w + 2 * pad
    bh = max(lhs * len(sound) + lht * len(trans) + 2 * pad - 6, icon_w + 12)
    right = slot % 2 == 1
    x = W - bw - 22 if right else 22
    y = 22 + (slot // 2) * (bh + 30) + (40 if right else 0)
    for px0, py0, px1, py1 in sorted(placed or [], key=lambda b: b[1]):
        if x < px1 and px0 < x + bw and y < py1 + 12 and py0 < y + bh:
            y = py1 + 60
    if placed is not None:
        placed.append((x, y, x + bw, y + bh))
    cx, cy = x + bw / 2, y + bh
    tx, ty = cx + (40 if cx < W / 2 else -40), min(H - 20, y + bh + 44)
    for r, f in ((9, 0.4), (6, 0.75)):  # bubbly tail, like a thought: animals do not quite speak
        px, py = cx + (tx - cx) * f, cy + (ty - cy) * f
        d.ellipse((px - r, py - r, px + r, py + r), fill=PET_FILL, outline=INK, width=2)
    d.rounded_rectangle((x, y, x + bw, y + bh), radius=min(bh // 2, 30), fill=PET_FILL, outline=(150, 100, 60), width=4)
    draw_icon(d, bubble.get("icon", "paw"), x + pad + icon_w / 2 - 4, y + bh / 2, 20)
    ty0 = y + (bh - (lhs * len(sound) + lht * len(trans))) / 2
    for i, line in enumerate(sound):
        d.text((x + pad + icon_w, ty0 + i * lhs), line, font=fs, fill=INK)
    for i, line in enumerate(trans):
        d.text((x + pad + icon_w, ty0 + lhs * len(sound) + i * lht), line, font=ft, fill=(95, 85, 80))


def draw_bubble(img, bubble, slot, n_slots, placed=None):
    d = ImageDraw.Draw(img)
    W, H = img.size
    kind = bubble.get("kind", "speech")
    if kind == "pet":
        return draw_pet(img, bubble, slot, placed)
    fnt = font(kind, 26 if kind != "shout" else 30)
    max_w = int(W * (0.62 if kind != "narration" else 0.8))
    lines = wrap(d, bubble["text"], fnt, max_w - 40)
    lh = int(fnt.size * 1.25)
    tw = max(d.textlength(l, font=fnt) for l in lines)
    bw, bh = int(tw) + 44, lh * len(lines) + 30
    margin = 22
    if kind == "narration":
        x, y = margin, margin + slot * (bh + 12)
    else:
        right = slot % 2 == 1
        x = W - bw - margin if right else margin
        y = margin + (slot // 2) * (bh + 30) + (40 if right else 0)
    # Wide panels are short: push the bubble below any already placed one it would overlap.
    for px0, py0, px1, py1 in sorted(placed or [], key=lambda b: b[1]):
        if x < px1 and px0 < x + bw and y < py1 + 12 and py0 < y + bh:
            y = py1 + (60 if kind != "narration" else 12)
    box = (x, y, x + bw, y + bh)
    if placed is not None:
        placed.append(box)

    if kind == "narration":
        d.rectangle(box, fill=(255, 248, 225), outline=INK, width=3)
    else:
        cx, cy = x + bw / 2, y + bh
        tx, ty = cx + (40 if cx < W / 2 else -40), min(H - 20, y + bh + 48)
        if kind == "thought":
            for r, f in ((10, 0.35), (7, 0.65), (5, 0.9)):
                px, py = cx + (tx - cx) * f, cy + (ty - cy) * f
                d.ellipse((px - r, py - r, px + r, py + r), fill="white", outline=INK, width=2)
        else:
            d.polygon([(cx - 22, cy - 4), (cx + 10, cy - 4), (tx, ty)], fill=RADIO_FILL if kind == "radio" else "white", outline=INK, width=3)
        if kind == "radio":  # voice from a speaker/radio: square box, blue tint
            d.rectangle(box, fill=RADIO_FILL, outline=INK, width=3)
            d.line([(x + bw - 30, y + 8), (x + bw - 14, y + 8)], fill=INK, width=2)
        elif kind == "shout":
            d.rectangle(box, fill="white", outline=INK, width=5)
        else:
            d.rounded_rectangle(box, radius=min(bh // 2, 40), fill="white", outline=INK, width=3)
        if kind != "thought":
            d.polygon([(cx - 19, cy - 6), (cx + 7, cy - 6), (tx - 1, ty - 9)], fill=RADIO_FILL if kind == "radio" else "white")
    for i, line in enumerate(lines):
        lw = d.textlength(line, font=fnt)
        d.text((x + (bw - lw) / 2, y + 15 + i * lh), line, font=fnt, fill=INK)


def draw_sfx(img, sfx, i):
    d = ImageDraw.Draw(img)
    W, H = img.size
    fnt = font("sfx", 64)
    x, y = int(W * (0.55 if i % 2 == 0 else 0.1)), int(H * 0.68)
    d.text((x, y), sfx["text"], font=fnt, fill=(255, 220, 60), stroke_width=6, stroke_fill=INK)


def choices_block(choices, title):
    img = Image.new("RGB", (WIDTH, 120 + 110 * len(choices)), (245, 243, 250))
    d = ImageDraw.Draw(img)
    d.text((40, 40), "Co udělá dál?", font=font("narration", 40), fill=INK)
    for i, c in enumerate(choices):
        y = 120 + i * 110
        free = c.get("kind") == "free"
        d.rounded_rectangle((40, y, WIDTH - 40, y + 86), radius=24, fill="white" if not free else (235, 235, 240),
                            outline=(120, 90, 200), width=3)
        d.text((70, y + 26), c["text"], font=font("ui", 28), fill=INK if not free else (110, 110, 120))
    return img


def end_block(text):
    """Closing card for a finished story (no reader choices)."""
    img = Image.new("RGB", (WIDTH, 200), (245, 243, 250))
    d = ImageDraw.Draw(img)
    fnt = font("narration", 48)
    d.text(((WIDTH - d.textlength(text, font=fnt)) / 2, 70), text, font=fnt, fill=INK)
    return img


def placeholder(panel, i):
    w, h = (1216, 832) if panel["shot"] in ("wide", "establishing") else (832, 1216)
    img = Image.new("RGB", (w, h), (200 + i * 6 % 50, 210, 225))
    d = ImageDraw.Draw(img)
    d.text((30, h - 80), f"#{i} {panel['shot']} @ {panel['location_id']}", font=font("ui", 40), fill=INK)
    return img


def compose(sb, panel_dir=None, variant=0, use_placeholder=False):
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
        placed = []
        for k, b in enumerate(narr):
            draw_bubble(img, b, k, len(narr), placed)
        for k, b in enumerate(talk):
            draw_bubble(img, b, k + (1 if narr else 0), len(talk), placed)
        for k, s in enumerate(p.get("sfx", [])):
            draw_sfx(img, s, k)
        parts.append((img, GAPS.get(p.get("gap_after"), 140)))

    title = Image.new("RGB", (WIDTH, 160), BG)
    ImageDraw.Draw(title).text((40, 50), sb["title"], font=font("narration", 54), fill=INK)
    end = choices_block(sb["choices"], sb["title"]) if sb.get("choices") else end_block(sb.get("end", "Konec"))
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
