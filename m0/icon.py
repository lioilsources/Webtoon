"""App icon: two noir manga portraits (man, woman) composed as comic panels across a diagonal gutter.

Renders 2 seeds per character with the noir_mono preset (one ComfyUI job each, run serially), then composes
candidate icons at 1024x1024. Director's rules: check system_stats/queue first, POST /free at the end."""

import json
import sys
from pathlib import Path

sys.path.insert(0, "/Volumes/YOTTA/Dev/Webtoon/m0")
import comfy  # noqa: E402
from common import COMFY_URL, DATA, http, http_json, load_json  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "app" / "assets" / "icon" / "src"  # portraits + composed candidates
STYLES = load_json(DATA / "styles.json")
PRESET = STYLES["presets"]["noir_mono"]
SIZE = 1024
STYLE = ["manga style", "ink", "screentone", "clean lineart", "close-up", "face focus", "portrait"] + PRESET["aesthetic_tags"]

CHARS = {
    "woman": ["1girl", "solo", "adult", "mature female", "beautiful", "long hair", "sharp eyes", "lips",
              "looking to the side", "serious", "intense", "rain"],
    "man": ["1boy", "solo", "adult", "mature male", "handsome", "short hair", "stubble", "sharp eyes",
            "looking to the side", "looking up", "from below", "serious", "intense"],
}
EXTRA_NEG = {"woman": ["1boy", "male"], "man": ["1girl", "female"]}


def prompt(char):
    pos = PRESET["quality_pos"] + CHARS[char] + STYLE + STYLES["sfw_positive"]
    neg = PRESET["quality_neg"] + STYLES["always_negative"] + STYLES["adult_negative"] + STYLES["sfw_negative"] + EXTRA_NEG[char]
    return ", ".join(pos), ", ".join(neg)


def check_ready():
    stats = http_json("GET", f"{COMFY_URL}/system_stats", timeout=5)
    devs = [d.get("type", d.get("name", "")) for d in stats["devices"]]
    if not any("cuda" in str(d).lower() for d in devs):
        raise SystemExit(f"ComfyUI device not cuda: {devs}")
    import time
    for _ in range(120):  # someone else's jobs run mornings: wait up to 10 min for an empty queue
        q = http_json("GET", f"{COMFY_URL}/queue", timeout=5)
        busy = q["queue_running"] + q["queue_pending"]
        if not busy:
            return
        pref = [v["inputs"].get("filename_prefix") for it in busy for v in it[2].values() if "filename_prefix" in v.get("inputs", {})]
        print("queue busy:", len(busy), pref[:3], flush=True)
        time.sleep(5)
    raise SystemExit("ComfyUI queue still not empty after 10 min")


def render(char, seed):
    pos, neg = prompt(char)
    g = comfy.workflow(pos, neg, SIZE, SIZE, seed, PRESET, f"icon_{char}_{seed}")
    outs = comfy.run_outputs(g, timeout=600)
    files = [f for fs in outs.values() for f in fs]
    p = OUT / f"{char}_{seed}.png"
    p.write_bytes(files[0]["bytes"])
    return p


def compose(woman, man, out, gutter=0.035):
    """Woman top-left panel, man bottom-right, diagonal from bottom-left to top-right, white gutter between."""
    W = SIZE
    from PIL import ImageFilter, ImageEnhance
    def place(src, cx, cy, scale=0.8):
        im = Image.open(src).convert("L")
        bg = im.resize((round(W * 1.4), round(W * 1.4)), Image.LANCZOS).filter(ImageFilter.GaussianBlur(18))
        bg = ImageEnhance.Brightness(bg).enhance(0.45)
        canvas = Image.new("L", (W, W), 0)
        canvas.paste(bg, (round(-W * 0.2), round(-W * 0.2)))
        fg = im.resize((round(W * scale), round(W * scale)), Image.LANCZOS)
        feather = Image.new("L", fg.size, 0)   # soft edges so the smaller copy melts into the blurred fill
        ImageDraw.Draw(feather).rectangle((60, 60, fg.width - 60, fg.height - 60), fill=255)
        feather = feather.filter(ImageFilter.GaussianBlur(40))
        canvas.paste(fg, (round(cx * W - W * scale / 2), round(cy * W - W * scale / 2)), feather)
        return canvas
    a = place(woman, 0.33, 0.33, 0.85)        # face at the top-left triangle's centroid
    b = place(man, 0.68, 0.68, 0.85)          # face at the bottom-right triangle's centroid
    mask = Image.new("L", (W, W), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (W, 0), (0, W)], fill=255)   # top-left triangle
    icon = Image.composite(a, b, mask).convert("RGB")
    d = ImageDraw.Draw(icon)
    g = gutter * W
    d.line([(0, W), (W, 0)], fill=(245, 245, 245), width=round(g))
    d.line([(0, W), (W, 0)], fill=(20, 20, 20), width=round(g * 0.25))  # thin ink line in the gutter
    icon.save(out, "PNG")


def main():
    only_compose = "--compose" in sys.argv
    wseeds, mseeds = [21, 22, 23], [11, 12]
    if not only_compose:
        check_ready()
        try:
            for s in wseeds:
                p = render("woman", s)
                print("rendered", p.name)
        finally:
            http("POST", f"{COMFY_URL}/free", {"unload_models": True, "free_memory": True}, timeout=30)
            print("ComfyUI /free sent")
    k = 0
    for sw in wseeds:
        for sm in mseeds:
            k += 1
            compose(OUT / f"woman_{sw}.png", OUT / f"man_{sm}.png", OUT / f"icon_{k}.png")
    print("icons:", k)


if __name__ == "__main__":
    main()
