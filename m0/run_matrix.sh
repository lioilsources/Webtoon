#!/bin/bash
# Style matrix: one key panel of a story rendered in every preset (same seed) → out/romance/matrix/<story>/<preset>/
#   m0/run_matrix.sh r_ny:13 r_pariz:12 r_sanghaj:16
set -u
cd "$(dirname "$0")/.."
export WEBTOON_DAY=romance
PRESETS=$(python3 -c "import json;print(' '.join(json.load(open('data/styles.json'))['presets']))")
for sp in "$@"; do
  s=${sp%%:*}; p=${sp##*:}; d="data/stories/$s"
  for pr in $PRESETS; do
    python3 m0/render.py --world "$d/world.json" --storyboard "$d/storyboard.json" --run "matrix/$s/$pr" \
      --preset "$pr" --panels "$p" --seed-base 7000 --skip-existing | grep -v "^mean" || echo "!! $s $pr"
  done
done
echo "== matrix done $(date +%H:%M)"
