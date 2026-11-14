"""Post-process for pixel-art presets (`"pixelate": {"factor": 6, "colors": 32}` in data/styles.json).

Illustrious will not draw real 16-bit pixel art from the prompt: a heavy weight breaks the image into mosaic, a light
one gives plain anime (L40S, Archion test 2, 2026-11-14). So the preset draws its anime-with-pixel-background image
and this turns it into pixel art: shrink to 1/factor (box filter = each pixel the mean of its block), reduce to
`colors` with Floyd–Steinberg, scale back up with nearest neighbour to the original size.

Loops: every frame of the WebP gets the palette of the first frame, so colours do not flicker between frames.
"""

import io

from PIL import Image

DITHER = Image.Dither.FLOYDSTEINBERG


def spec(preset):
    """The preset's pixelate block, or None."""
    px = (preset or {}).get("pixelate")
    if px is None or px is False:
        return None
    px = px if isinstance(px, dict) else {}
    return {"factor": int(px.get("factor", 6)), "colors": int(px.get("colors", 32))}


def _small(img, factor):
    w, h = img.size
    return img.convert("RGB").resize((max(1, w // factor), max(1, h // factor)), Image.Resampling.BOX)


def frame(img, factor, colors, palette=None):
    """One image → pixel art of the same size. `palette`: a P-mode image whose palette to reuse (loops)."""
    small = _small(img, factor)
    q = small.quantize(palette=palette, dither=DITHER) if palette else small.quantize(colors=colors, dither=DITHER)
    return q.convert("RGB").resize(img.size, Image.Resampling.NEAREST), q


def png(data, px):
    """PNG bytes → pixelated PNG bytes."""
    out, _ = frame(Image.open(io.BytesIO(data)), px["factor"], px["colors"])
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return buf.getvalue()


def webp(data, px):
    """Animated WebP bytes → pixelated animated WebP bytes (same frame durations, loops forever, lossless)."""
    src = Image.open(io.BytesIO(data))
    frames, durations, palette = [], [], None
    for k in range(getattr(src, "n_frames", 1)):
        src.seek(k)
        src.load()  # WebP fills info["duration"] only once the frame is decoded
        out, q = frame(src, px["factor"], px["colors"], palette)
        palette = palette or q
        frames.append(out)
        durations.append(src.info.get("duration") or 62)
    buf = io.BytesIO()
    frames[0].save(buf, "WEBP", save_all=True, append_images=frames[1:], duration=durations, loop=0, lossless=True)
    return buf.getvalue()
