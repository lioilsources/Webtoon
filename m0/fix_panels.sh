#!/bin/bash
# Re-renders single panels (0-based) with another seed and recomposes; old panels go to old/.
#   m0/fix_panels.sh rc_02_la:0,3 rd_05_bombaj:7
set -u
cd "$(dirname "$0")/.."
DAY="${WEBTOON_DAY:-romance}"; export WEBTOON_DAY="$DAY"
for a in "$@"; do
  s="${a%%:*}"; d="data/stories/$s"; o="out/$DAY/$s"
  echo "== fix $a $(date +%H:%M)"
  mkdir -p "$o/old"
  p="${a#*:}"; for i in ${p//,/ }; do f=$(printf "p%02d_s0.png" "$i"); [ -f "$o/$f" ] && mv "$o/$f" "$o/old/$f"; done
  python3 m0/render.py --world "$d/world.json" --storyboard "$d/storyboard.json" --run "$s" --skip-existing --seed-base "${SEED:-5100}" || echo "!! $s"
  python3 m0/compose.py --storyboard "$d/storyboard.json" --panels "$o" --out "$o/strip.png" || echo "!! $s compose"
done
echo "== fix done $(date +%H:%M)"
