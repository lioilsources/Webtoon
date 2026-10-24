"""Captures golden results from the ORIGINAL m0 code (a git revision) for test_golden.py.

    python3 m0/tests/make_goldens.py [--rev 4940354] [--only check,prompts]

The revision's m0/ is extracted into a temp dir next to symlinks of data/, skills/, assets/, so the old modules
read exactly the same inputs; results go to m0/tests/golden/golden.json.
"""

import argparse
import json
import subprocess
import sys
import tarfile
import io
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE_REV = "4940354"  # "WIP snapshot for YAML rules refactor": the last commit with the rules in code


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", default=BASE_REV)
    ap.add_argument("--only", default=None)
    ap.add_argument("--out", default=str(HERE / "golden" / "golden.json"))
    args = ap.parse_args()
    with tempfile.TemporaryDirectory() as d:
        t = Path(d)
        tar = subprocess.run(["git", "-C", str(ROOT), "archive", args.rev, "m0"], capture_output=True, check=True).stdout
        tarfile.open(fileobj=io.BytesIO(tar)).extractall(t, filter="data")
        for name in ("data", "skills", "assets", "backend"):
            (t / name).symlink_to(ROOT / name)
        sys.path.insert(0, str(HERE))
        import harness
        mods = harness.import_mods(t / "m0")
        res = harness.run(mods, args.only.split(",") if args.only else None)
    out = Path(args.out)
    old = json.loads(out.read_text()) if args.only and out.exists() else {}
    old.update(res)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"rev": args.rev, **{k: v for k, v in old.items() if k != "rev"}}, ensure_ascii=False, indent=0))
    print(f"{out}: " + ", ".join(f"{k} {len(v)}" for k, v in res.items()))


if __name__ == "__main__":
    main()
