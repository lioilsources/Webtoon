"""Panels + storyboard bubbles → one vertical webtoon strip PNG (M0 stand-in for the Flutter overlay).

    python3 m0/compose.py --storyboard out/dev/storyboard_ep1.json --panels out/<day>/<run> [--variant 0] --out strip.png
    python3 m0/compose.py --storyboard ... --placeholder --out strip.png   # layout test without images

Bubble placement: with face boxes (storyboard panels[].faces or m0/faces.py's cache) each bubble takes the spot
that covers the least of the faces, tail toward the nearest face; without faces the old heuristic: alternate top
corners, narration as a box at the top-left, tails point toward the panel centre.
"""

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import rules
from common import ROOT, faces_for, load_json

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


def place_off_faces(W, H, bw, bh, kind, slot, faces, placed, margin, sfx=()):
    """Top-left corner for a bw×bh bubble that covers as little of the faces (pixel boxes, from m0/faces.py) as
    possible. Candidates: the left and right column (and centre for talk) at every 12 px, never over an earlier
    bubble and not above the previous one (reading order). Cost: covered share of each face (padded) dominates,
    then of the panel's sound effects (sfx boxes), then height (higher is better) and the usual left/right alternation."""
    F = R["faces"]
    pad = F["pad"] * W
    zones = [(f[0] - pad, f[1] - pad, f[2] + pad, f[3] + pad, F["cost"]["face"]) for f in faces]
    zones += [(*b, F["cost"]["sfx"]) for b in sfx]
    right_first = kind != "narration" and slot % 2 == 1
    other = F["cost"]["other_side"]
    xs = [(margin, 0 if not right_first else other), (W - bw - margin, other if not right_first else 0)]
    if kind != "narration":
        xs.append(((W - bw) // 2, F["cost"]["centre"]))
    y0 = max(margin, placed[-1][1]) if placed else margin
    best = None
    for y in range(int(y0), int(max(y0, H - bh - margin)) + 1, F["step"]):
        for x, side_cost in xs:
            gap = F["bubble_gap"]
            if any(x < p[2] + gap and p[0] - gap < x + bw and y < p[3] + gap and p[1] - gap < y + bh for p in placed):
                continue
            covered = 0.0
            for z in zones:
                ix = min(x + bw, z[2]) - max(x, z[0])
                iy = min(y + bh, z[3]) - max(y, z[1])
                if ix > 0 and iy > 0:
                    covered += z[4] * ix * iy / ((z[2] - z[0]) * (z[3] - z[1]))
            cost = covered + F["cost"]["height"] * y / H + side_cost
            if best is None or cost < best[0]:
                best = (cost, x, y)
    if best is None:  # no free spot left: the caller's overlap rule stacks it below the previous bubble
        return (margin, y0)
    return best[1], best[2]


def nearest_face(faces, x, y):
    if not faces:
        return None
    return min(faces, key=lambda f: ((f[0] + f[2]) / 2 - x) ** 2 + ((f[1] + f[3]) / 2 - y) ** 2)


def set_faces(img, boxes, crop=None):
    """Attach face boxes (normalized to the source image) to img for draw_bubble, in img's pixels. crop =
    (x0, y0, x1, y1) of the source shown in img, normalized (shorts.py zooms/crops panels)."""
    cx0, cy0, cx1, cy1 = crop or (0, 0, 1, 1)
    W, H = img.size
    out = []
    for b in boxes:
        x0, y0 = (b[0] - cx0) / (cx1 - cx0) * W, (b[1] - cy0) / (cy1 - cy0) * H
        x1, y1 = (b[2] - cx0) / (cx1 - cx0) * W, (b[3] - cy0) / (cy1 - cy0) * H
        if x1 > 0 and y1 > 0 and x0 < W and y0 < H:
            out.append((max(0, x0), max(0, y0), min(W, x1), min(H, y1)))
    img._faces = out


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
    faces = getattr(img, "_faces", [])
    if faces:
        x, y = place_off_faces(W, H, bw, bh, kind, slot, faces, getattr(img, "_bubbles", []), margin,
                               getattr(img, "_sfx", []))
    elif kind == "narration":
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
        face = nearest_face(faces, cx, y + bh / 2)
        if face is not None:
            # Tail toward the nearest face: from the edge facing it, stopping short of it so it doesn't cover it.
            fx, fy = (face[0] + face[2]) / 2, (face[1] + face[3]) / 2
            below = fy > y + bh / 2
            cy = y + bh if below else y
            edge = face[1] if below else face[3]
            dx, dy = fx - cx, edge - cy
            dist = max(1.0, (dx * dx + dy * dy) ** 0.5)
            T = R["faces"]["tail"]
            length = min(T["max"], max(T["min"], dist - T["short_of_face"]))
            tx, ty = cx + dx / dist * length, cy + dy / dist * length
            if (ty > cy) != below:  # face level with the bubble: a short tail down/up toward its side
                ty = cy + (T["min"] if below else -T["min"])
        s = 1 if ty >= cy else -1  # tail leaves the bottom edge (1) or the top edge (-1)
        if kind == "thought":
            for r, f in ((10, 0.35), (7, 0.65), (5, 0.9)):
                px, py = cx + (tx - cx) * f, cy + (ty - cy) * f
                d.ellipse((px - r, py - r, px + r, py + r), fill="white", outline=INK, width=2)
        else:
            d.polygon([(cx - 22, cy - 4 * s), (cx + 10, cy - 4 * s), (tx, ty)], fill="white", outline=INK, width=3)
        if kind == "shout":
            d.rectangle(box, fill="white", outline=INK, width=5)
        else:
            d.rounded_rectangle(box, radius=min(bh // 2, 40), fill="white", outline=INK, width=3)
        if kind != "thought":
            d.polygon([(cx - 19, cy - 6 * s), (cx + 7, cy - 6 * s), (tx - 1, ty - 9 * s)], fill="white")
    for i, line in enumerate(lines):
        lw = d.textlength(line, font=fnt)
        d.text((x + (bw - lw) / 2, y + 15 + i * lh), line, font=fnt, fill=INK)


def sfx_box(img, sfx, i):
    """Where draw_sfx letters sfx: (x, y, box) with box = its bounding box in img's pixels."""
    W, H = img.size
    x, y = int(W * (0.55 if i % 2 == 0 else 0.1)), int(H * 0.68)
    return x, y, ImageDraw.Draw(img).textbbox((x, y), sfx["text"], font=font("sfx", R["sfx"]["size"]),
                                              stroke_width=R["sfx"]["stroke"])


def draw_sfx(img, sfx, i):
    x, y, _ = sfx_box(img, sfx, i)
    ImageDraw.Draw(img).text((x, y), sfx["text"], font=font("sfx", R["sfx"]["size"]), fill=tuple(R["sfx"]["fill"]),
                             stroke_width=R["sfx"]["stroke"], stroke_fill=INK)


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
    # face boxes of every panel in one detector run (faces.py loads its model once)
    found = {} if use_placeholder else faces_for(
        [Path(panel_dir) / f"p{i:02d}_s{variant}.png" for i, p in enumerate(sb["panels"]) if "faces" not in p])
    for i, p in enumerate(sb["panels"]):
        if use_placeholder:
            img = placeholder(p, i)
        else:
            src = Path(panel_dir) / f"p{i:02d}_s{variant}.png"
            img = Image.open(src).convert("RGB")
        img = img.resize((WIDTH, round(img.height * WIDTH / img.width)), Image.LANCZOS)
        if not use_placeholder:
            set_faces(img, p["faces"] if "faces" in p else found.get(str(src), []))
            img._sfx = [sfx_box(img, x, k)[2] for k, x in enumerate(p.get("sfx", []))]
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
