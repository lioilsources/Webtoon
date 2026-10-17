#!/usr/bin/env bash
# M0 spike image run (§8). Needs ComfyUI up (Spark window 07–13, Director's go).
# Storyboard must exist already (LLM is down 07–13): out/dev/storyboard_ep1.json
#
#   m0/run_m0.sh            # full run (~38 images)
#   DRY=1 m0/run_m0.sh      # print the plan only
set -euo pipefail
cd "$(dirname "$0")/.."
SB=${SB:-out/dev/storyboard_ep1.json}
DAY=$(date +%F)
R="python3 m0/render.py"
[[ -n "${DRY:-}" ]] && R="$R --dry-run"

# Panels that contain the character (IP-Adapter only matters there).
CHAR_PANELS=$(python3 -c "import json;d=json.load(open('$SB'));print(','.join(str(i) for i,p in enumerate(d['panels']) if p.get('characters')))")

# 1) character sheet, 4 seeds → reference for IP-Adapter
$R --sheet --run sheet_vesna --seeds 4
# 2) prompt-only identity test, main preset, 2 seeds per panel
$R --storyboard "$SB" --run ep1_noob_artist --preset clean_webtoon --seeds 2
# 3) style comparison: no artist tags / Hassaku
$R --storyboard "$SB" --run ep1_noob_plain --preset clean_webtoon_noartist
$R --storyboard "$SB" --run ep1_hassaku --preset hassaku_soft
[[ -n "${DRY:-}" ]] && exit 0

# 4) IP-Adapter from the best sheet (highest WD14 design recall)
REF=$(python3 -c "
import json;m=json.load(open('out/$DAY/sheet_vesna/meta.json'))
best=max((r for r in m['images'] if r['status']=='ok'),key=lambda r:r['identity']['recall'])
print('out/$DAY/sheet_vesna/'+best['file'])")
echo "IP-Adapter reference: $REF"
$R --storyboard "$SB" --run ep1_ipa06 --preset clean_webtoon --ref "$REF" --ip-weight 0.6 --panels "$CHAR_PANELS"
$R --storyboard "$SB" --run ep1_ipa08 --preset clean_webtoon --ref "$REF" --ip-weight 0.8 --panels "$CHAR_PANELS"

# 5) strips
for run in ep1_noob_artist ep1_noob_plain ep1_hassaku; do
  python3 m0/compose.py --storyboard "$SB" --panels "out/$DAY/$run" --out "out/$DAY/strip_$run.png"
done
python3 m0/summary.py "out/$DAY"
