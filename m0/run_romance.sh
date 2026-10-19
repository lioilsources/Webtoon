#!/bin/bash
# Renders romance stories one after another (one ComfyUI job at a time) and composes each strip.
#   WEBTOON_DAY=romance m0/run_romance.sh r_ny r_pariz ...
# Loops for panels marked animate (PLAN-motion-panels.md) are a separate pass AFTER all stills, so Wan 14B is loaded once:
#   for s in ...; do python3 m0/animate.py --world data/stories/$s/world.json --storyboard data/stories/$s/storyboard.json --run $s --skip-existing; done
set -u
cd "$(dirname "$0")/.."
DAY="${WEBTOON_DAY:-romance}"; export WEBTOON_DAY="$DAY"
for s in "$@"; do
  d="data/stories/$s"
  echo "== $s $(date +%H:%M)"
  python3 m0/render.py --world "$d/world.json" --storyboard "$d/storyboard.json" --run "$s" --skip-existing
  rc=$?
  [ $rc -eq 3 ] && { echo "== deadline, stopping at $s"; exit 3; }
  [ $rc -ne 0 ] && { echo "!! $s render failed"; continue; }
  python3 m0/compose.py --storyboard "$d/storyboard.json" --panels "out/$DAY/$s" --out "out/$DAY/$s/strip.png" || echo "!! $s compose failed"
done
echo "== done $(date +%H:%M)"
