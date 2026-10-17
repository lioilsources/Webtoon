#!/usr/bin/env bash
# M0 follow-up: stronger close-ups + second IP-Adapter attempt (face crop, low weight).
set -euo pipefail
cd "$(dirname "$0")/.."
SB=${SB:-out/dev/storyboard_ep1.json}
R="python3 m0/render.py"
[[ -n "${DRY:-}" ]] && R="$R --dry-run"
FACE=out/2026-10-17/sheet_vesna/face_ref.png
CHAR_PANELS=$(python3 -c "import json;d=json.load(open('$SB'));print(','.join(str(i) for i,p in enumerate(d['panels']) if p.get('characters')))")
CLOSE=$(python3 -c "import json;d=json.load(open('$SB'));print(','.join(str(i) for i,p in enumerate(d['panels']) if p['shot']=='close-up'))")

$R --storyboard "$SB" --run closeup_fix --preset clean_webtoon --panels "$CLOSE" --seeds 3
$R --storyboard "$SB" --run ipa_face04 --preset clean_webtoon --ref "$FACE" --ip-preset "PLUS FACE (portraits)" --ip-weight 0.4 --ip-end 0.6 --panels "$CHAR_PANELS"
$R --storyboard "$SB" --run ipa_plus03 --preset clean_webtoon --ref "$FACE" --ip-weight 0.3 --ip-end 0.6 --panels "$CHAR_PANELS"
[[ -n "${DRY:-}" ]] || python3 m0/summary.py "out/$(date +%F)"
