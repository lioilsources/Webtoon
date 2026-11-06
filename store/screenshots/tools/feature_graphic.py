#!/usr/bin/env python3
"""Google Play feature graphic (1024×500): app icon, the name, a short tagline and four real
panels from the starter pack (app/assets/packs/starter.zip).

    python3 store/screenshots/tools/feature_graphic.py
"""
import io
import os
import zipfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
ICON = os.path.join(ROOT, 'app/ios/Runner/Assets.xcassets/AppIcon.appiconset/'
                    'Icon-App-1024x1024@1x.png')
FONTS = os.path.join(ROOT, 'app/assets/fonts')
OUT = os.path.join(ROOT, 'store/screenshots/play-feature-graphic.png')
W, H = 1024, 500
BG = (18, 18, 18)
ACCENT = (124, 77, 255)
# kids panels: Halloween night, forest mystery, the beach bunny, the park dog
PANELS = ['media/ep_9d9ea7c6f678/p00.webp', 'media/ep_3b0b3ad059ae/p00.webp',
          'media/ep_287e28ad2209/p01.webp', 'media/ep_17db32e2b07a/p01.webp']
TAGLINE = 'Comics where you choose'


def font(name, size, weight=None):
    f = ImageFont.truetype(os.path.join(FONTS, name), size)
    if weight is not None:
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
    return f


def panel(img, w, h, border=6):
    """Cover-crop to w×h with a white comic border and a hard drop shadow."""
    s = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    img = img.crop((x, y, x + w, y + h))
    out = Image.new('RGBA', (w + 2 * border + 10, h + 2 * border + 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((10, 10, w + 2 * border + 9, h + 2 * border + 9), 16, fill=(0, 0, 0, 255))
    d.rounded_rectangle((0, 0, w + 2 * border - 1, h + 2 * border - 1), 16, fill=(255, 255, 255, 255))
    mask = Image.new('L', (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), 11, fill=255)
    out.paste(img, (border, border), mask)
    return out


def main():
    z = zipfile.ZipFile(os.path.join(ROOT, 'app/assets/packs/starter.zip'))
    imgs = [Image.open(io.BytesIO(z.read(p))).convert('RGB') for p in PANELS]
    canvas = Image.new('RGBA', (W, H), BG + (255,))

    # soft violet glow behind the panels
    glow = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((540, 40, 1120, 520), fill=ACCENT + (110,))
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))

    # panels: a loose, tilted webtoon strip on the right
    spots = [  # (image, w, h, x, y, angle)
        (imgs[0], 300, 205, 470, 30, 4),
        (imgs[2], 180, 255, 790, 22, -5),
        (imgs[1], 290, 200, 520, 265, -3),
        (imgs[3], 170, 205, 805, 270, 6),
    ]
    for img, w, h, x, y, a in spots:
        p = panel(img, w, h).rotate(a, resample=Image.BICUBIC, expand=True)
        canvas.alpha_composite(p, (x, y))

    # left: icon, name, tagline
    icon = Image.open(ICON).convert('RGBA').resize((150, 150), Image.LANCZOS)
    m = Image.new('L', icon.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, 149, 149), 34, fill=255)
    canvas.paste(icon, (56, 92), m)
    d = ImageDraw.Draw(canvas)
    d.text((52, 262), 'Toonfork', font=font('DynaPuff-Variable.ttf', 84, 700), fill='white')
    d.text((58, 370), TAGLINE, font=font('Nunito-Variable.ttf', 34, 800), fill=(214, 200, 255))

    canvas.convert('RGB').save(OUT)
    print(OUT, canvas.size)


if __name__ == '__main__':
    main()
