"""Prints the M0 comparison table (identity recall, safety, most-missed design tags) for a day's runs.

    python3 m0/summary.py out/<YYYY-MM-DD>
"""

import collections
import sys
from pathlib import Path

from common import load_json, save_json


def main():
    day = Path(sys.argv[1])
    rows = []
    for meta_path in sorted(day.glob("*/meta.json")):
        m = load_json(meta_path)
        imgs = m["images"]
        scored = [r["identity"]["recall"] for r in imgs if "identity" in r]
        missed = collections.Counter(t for r in imgs if "identity" in r for t in r["identity"]["missing"])
        rows.append({
            "run": m["run"], "preset": m["preset"], "ip_weight": m.get("ip_weight"),
            "images": len(imgs), "failed": sum(r["status"] == "failed" for r in imgs),
            "reseeds": sum(len(r["attempts"]) - 1 for r in imgs),
            "identity_mean": round(sum(scored) / len(scored), 3) if scored else None,
            "identity_min": min(scored) if scored else None,
            "most_missed": missed.most_common(6),
        })
    for r in rows:
        print(f"{r['run']:<18} {r['preset']:<24} ip={r['ip_weight']!s:<5} n={r['images']:<3} "
              f"failed={r['failed']} reseeds={r['reseeds']} identity={r['identity_mean']} (min {r['identity_min']})")
        print(f"   most missed: {r['most_missed']}")
    save_json(day / "summary.json", rows)


if __name__ == "__main__":
    main()
