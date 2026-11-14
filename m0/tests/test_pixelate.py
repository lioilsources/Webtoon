"""m0/pixelate.py: pixel-art post-process of presets with a `pixelate` block."""

import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PIL import Image, ImageDraw  # noqa: E402

import pixelate  # noqa: E402

PX = {"factor": 6, "colors": 32}


def picture(shift=0):
    im = Image.new("RGB", (240, 360))
    d = ImageDraw.Draw(im)
    for y in range(360):
        d.line([(0, y), (239, y)], fill=(y % 256, 80, 255 - y % 256))
    d.ellipse((40 + shift, 80, 160 + shift, 220), fill=(230, 190, 150))
    return im


def frames_of(data):
    im, out = Image.open(io.BytesIO(data)), []
    for k in range(im.n_frames):
        im.seek(k)
        im.load()
        out.append((im.convert("RGB").copy(), im.info.get("duration")))
    return out


class PixelateTest(unittest.TestCase):
    def test_spec(self):
        self.assertIsNone(pixelate.spec({"checkpoint": "x"}))
        self.assertEqual(pixelate.spec({"pixelate": {}}), PX)

    def test_png_same_size_limited_colours_blocky(self):
        b = io.BytesIO()
        picture().save(b, "PNG")
        out = Image.open(io.BytesIO(pixelate.png(b.getvalue(), PX))).convert("RGB")
        self.assertEqual(out.size, (240, 360))
        self.assertLessEqual(len(out.getcolors(1 << 16)), 32)
        self.assertEqual(out.getpixel((0, 0)), out.getpixel((5, 5)))  # one 6×6 block, one colour

    def test_webp_keeps_frames_durations_and_one_palette(self):
        src = [picture(k * 8) for k in range(4)]
        b = io.BytesIO()
        src[0].save(b, "WEBP", save_all=True, append_images=src[1:], duration=[62] * 4, loop=0)
        out = frames_of(pixelate.webp(b.getvalue(), PX))
        self.assertEqual([d for _, d in out], [62] * 4)
        colours = set()
        for im, _ in out:
            colours |= {c for _, c in im.getcolors(1 << 16)}
        self.assertLessEqual(len(colours), 32)  # every frame on the first frame's palette: no flicker


if __name__ == "__main__":
    unittest.main()
