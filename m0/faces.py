"""Face boxes of panel images, so bubbles can stay off faces (compose.py strips, shorts.py, the app via storyboard).

    ~/.venvs/webtoon-faces/bin/python m0/faces.py out/local/<id>/p*_s0.png      # fill the cache
    ~/.venvs/webtoon-faces/bin/python m0/faces.py --storyboard data/stories/<id>/storyboard.json --panels out/local/<id>
        # also writes panels[i].faces into the storyboard (import-demo carries it to the app)

Detector: ADetailer's face_yolov8m (anime + real faces; copied from Spark's ComfyUI models), run locally on the
Mac (MPS), no Spark lease. It misses animal and robot faces; those panels keep the old placement.
Cache: out/faces/<sha1 of the image bytes>.json = [[x0, y0, x1, y1, conf], ...], normalized 0..1, origin top-left,
so a panel copied into the backend's media dir hits the same entry. The renderers run on the system python and
only read the cache: common.faces_for() calls this script in the venv for misses.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "out" / "faces"
MODEL = Path(os.environ.get("WEBTOON_FACE_MODEL", Path.home() / ".cache/webtoon-faces/face_yolov8m.pt"))
MIN_CONF = 0.3


def key(path):
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def detect(paths):
    """→ {path: boxes}; reads the cache, runs the model only on misses."""
    out, todo = {}, []
    for p in paths:
        c = CACHE / f"{key(p)}.json"
        if c.exists():
            out[p] = json.loads(c.read_text())
        else:
            todo.append(p)
    if todo:
        import torch
        from ultralytics import YOLO
        model = YOLO(str(MODEL))
        dev = "mps" if torch.backends.mps.is_available() else "cpu"
        CACHE.mkdir(parents=True, exist_ok=True)
        for p in todo:
            r = model.predict(str(p), conf=MIN_CONF, device=dev, verbose=False)[0]
            h, w = r.orig_shape
            boxes = [[round(b[0] / w, 4), round(b[1] / h, 4), round(b[2] / w, 4), round(b[3] / h, 4), round(float(c), 3)]
                     for b, c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist())]
            (CACHE / f"{key(p)}.json").write_text(json.dumps(boxes))
            out[p] = boxes
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="*")
    ap.add_argument("--storyboard", help="write panels[i].faces into this storyboard.json")
    ap.add_argument("--panels", help="panel dir of the storyboard (pNN_s<variant>.png)")
    ap.add_argument("--variant", type=int, default=0)
    args = ap.parse_args()
    paths = list(args.images)
    if args.storyboard:
        sb = json.loads(Path(args.storyboard).read_text())
        pan = [str(Path(args.panels) / f"p{i:02d}_s{args.variant}.png") for i in range(len(sb["panels"]))]
        paths += [p for p in pan if Path(p).exists()]
    found = detect(paths)
    if args.storyboard:
        for i, p in enumerate(sb["panels"]):
            boxes = found.get(pan[i])
            if boxes is not None:
                p["faces"] = [b[:4] for b in boxes]
        tmp = Path(args.storyboard).with_suffix(".json.tmp")
        tmp.write_text(json.dumps(sb, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, args.storyboard)
    print(f"faces: {len(paths)} images, {sum(len(v) for v in found.values())} faces", file=sys.stderr)


if __name__ == "__main__":
    main()
