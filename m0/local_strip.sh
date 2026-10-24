#!/bin/bash
# Screenplay → finished strip with no Claude in the loop: the local LLM writes the storyboard (and picks the loops),
# ComfyUI draws it, the backend imports and translates it. Strips get the id prefix lx_ (their own reader category).
#
#   m0/local_strip.sh [-s style] scenar.md [jiny.md:noir_mono ...]      # whole run, waits for each Spark window
#   m0/local_strip.sh -p write|render|import|translate ...              # one phase only
#   m0/local_strip.sh -p sbtranslate scenar.md ...                      # translate storyboard.json before render (not in all)
#   m0/local_strip.sh -f scenar.md                                      # free: experiment outside the app (below)
#   m0/local_strip.sh -r scenar.md                                      # own prompt per character in two-shots
#   m0/local_strip.sh -c scenar.md                                      # reference sheet per character (IP-Adapter)
#   m0/local_strip.sh -a kids scenar.md                                 # kids adventure: adapt --audience kids, style clean_webtoon_noartist
#
# Gates instead of the clock: LLM phases wait until a 1-token chat to openclaw-default answers; ComfyUI phases wait
# until ComfyUI answers AND the LLM does not (never both at once). Render stops at WEBTOON_DEADLINE (default 13:00).
# Every phase skips what is already done, so a rerun resumes. Log: out/local/<id>.log
# -f: no SFW rules for the LLM, no SFW negatives, no WD14 rating check; adults only stays enforced (adapt.py AGE_BANNED,
# prompts.AGE_NEGATIVE, render.AGE_TAG_LIMITS). Ids lxf_, output out/local_free/, never imported, translated or published.
set -u
cd "$(dirname "$0")/.."
ROOT=$PWD
LLM=${WEBTOON_LLM:-http://192.168.88.66:8080/v1}; MODEL=${WEBTOON_LLM_MODEL:-openclaw-default}
COMFY=${WEBTOON_COMFY:-http://192.168.88.66:8188}
# the CLI build; /tmp/claude-501/webtoon is also the running `webtoon serve`, never overwrite that one
if [ -x /tmp/claude-501/webtoon-cli ]; then BIN=${WEBTOON_BIN:-/tmp/claude-501/webtoon-cli}; else BIN=${WEBTOON_BIN:-/tmp/claude-501/webtoon}; fi
STYLE=; PHASE=all; FREE=; REGIONS=; REFS=; AUD=
while getopts "s:p:a:frc" o; do case $o in s) STYLE=$OPTARG ;; p) PHASE=$OPTARG ;; a) AUD=$OPTARG ;; f) FREE=1 ;; r) REGIONS=1 ;; c) REFS=1 ;; *) exit 2 ;; esac; done
shift $((OPTIND - 1))
[ $# -eq 0 ] && { sed -n 2,17p "$0"; exit 2; }
# -a kids: adapt.py --audience kids; the kids preset unless -s says otherwise
if [ -z "$STYLE" ]; then if [ "$AUD" = kids ]; then STYLE=clean_webtoon_noartist; else STYLE=webtoon_romance; fi; fi
if [ -n "$FREE" ]; then export WEBTOON_DAY=local_free; PREFIX=lxf_; else export WEBTOON_DAY=local; PREFIX=lx_; fi
OUTD=out/$WEBTOON_DAY
mkdir -p "$OUTD"

llm_up() { curl -s -m 60 "$LLM/chat/completions" -H 'Content-Type: application/json' \
  -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ok\"}],\"max_tokens\":1}" | grep -q '"choices"'; }
comfy_up() { curl -s -m 5 -o /dev/null -w '%{http_code}' "$COMFY/system_stats" | grep -q 200; }
wait_llm() { until llm_up; do echo "$(date +%H:%M) čekám na LLM"; sleep 300; done; }
wait_comfy() { until comfy_up && ! llm_up; do echo "$(date +%H:%M) čekám na ComfyUI (a vypnuté LLM)"; sleep 300; done; }

# "path/scenar.md[:style]" → id lx_<slug> (lxf_<slug> with -f)
ids=(); srcs=(); styles=()
for a in "$@"; do
  f=${a%%:*}; st=$STYLE; [[ $a == *:* ]] && st=${a#*:}
  [ -f "$f" ] || { echo "!! $f neexistuje"; exit 2; }
  slug=$(python3 -c 'import re,sys,unicodedata as u; s=u.normalize("NFKD",sys.argv[1]).encode("ascii","ignore").decode().lower(); print(re.sub(r"[^a-z0-9]+","_",s).strip("_"))' "$(basename "${f%.*}")")
  ids+=("$PREFIX$slug"); srcs+=("$(cd "$(dirname "$f")" && pwd)/$(basename "$f")"); styles+=("$st")
done

phase_write() {
  wait_llm
  for i in "${!ids[@]}"; do
    id=${ids[$i]}; [ -f "data/stories/$id/storyboard.json" ] && continue
    echo "== píše LLM: $id (${styles[$i]}) $(date +%H:%M)"
    python3 m0/adapt.py --id "$id" --style "${styles[$i]}" ${FREE:+--free} ${AUD:+--audience "$AUD"} "${srcs[$i]}" >> "$OUTD/$id.log" 2>&1 \
      || echo "!! $id: LLM storyboard nevalidní, viz $OUTD/$id.log"
  done
}

phase_render() {
  wait_comfy
  # morning window ends at 13:00; a slot Director grants later gets an hour (override: WEBTOON_DEADLINE=HH:MM)
  if [ -z "${WEBTOON_DEADLINE:-}" ]; then
    if [ "$(date +%H)" -lt 13 ]; then WEBTOON_DEADLINE=13:00; else WEBTOON_DEADLINE=$(date -v+60M +%H:%M); fi
    [[ $WEBTOON_DEADLINE < $(date +%H:%M) ]] && WEBTOON_DEADLINE=23:59  # no wrap past midnight (string compare)
  fi
  export WEBTOON_DEADLINE; echo "== render do $WEBTOON_DEADLINE"
  for id in "${ids[@]}"; do
    d=data/stories/$id; [ -f "$d/storyboard.json" ] || continue
    [ -f "$OUTD/$id/strip.png" ] && continue
    echo "== kreslí ComfyUI: $id $(date +%H:%M)"
    python3 m0/render.py --world "$d/world.json" --storyboard "$d/storyboard.json" --run "$id" --skip-existing ${REGIONS:+--regions} ${REFS:+--char-refs} >> "$OUTD/$id.log" 2>&1
    rc=$?; [ $rc -eq 3 ] && { echo "== konec okna ComfyUI, pokračuj zítra stejným příkazem"; exit 3; }
    [ $rc -ne 0 ] && { echo "!! $id render selhal"; continue; }
    python3 m0/compose.py --storyboard "$d/storyboard.json" --panels "$OUTD/$id" --out "$OUTD/$id/strip.png" >> "$OUTD/$id.log" 2>&1
  done
  # loops after all stills, so Wan is loaded once; SDXL out of VRAM first
  curl -s -m 30 -X POST "$COMFY/free" -H 'Content-Type: application/json' -d '{"unload_models":true,"free_memory":true}' >/dev/null
  for id in "${ids[@]}"; do
    d=data/stories/$id; [ -f "$OUTD/$id/strip.png" ] || continue
    grep -q '"animate": *true' "$d/storyboard.json" || continue
    echo "== hýbe: $id $(date +%H:%M)"
    python3 m0/animate.py --world "$d/world.json" --storyboard "$d/storyboard.json" --run "$id" --skip-existing >> "$OUTD/$id.log" 2>&1 \
      || echo "!! $id smyčky selhaly (okýnka zůstanou statická)"
  done
}

phase_import() {
  [ -n "$FREE" ] && { echo "== -f: free stripy se do backendu neimportují"; return; }
  for id in "${ids[@]}"; do
    d=data/stories/$id; o=$OUTD/$id
    grep -q '"free": *true' "$d/world.json" 2>/dev/null && { echo "!! $id je free svět, do aplikace nesmí"; continue; }
    [ -f "$o/strip.png" ] && [ ! -f "$o/episode_id" ] || continue
    # render.py keeps a panel that stayed unsafe after the reseeds (status "failed"); such a strip never goes in
    bad=$(python3 -c 'import json,sys; print(" ".join(r["file"] for r in json.load(open(sys.argv[1]))["images"] if r["status"] != "ok"))' "$o/meta.json")
    [ -n "$bad" ] && { echo "!! $id neprošel SFW kontrolou ($bad), neimportuju; přegeneruj: m0/fix_panels.sh"; continue; }
    (cd backend && "$BIN" seed -world "../$d/world.json" -owner author -visibility public >> "$ROOT/$o.log" 2>&1 \
      && "$BIN" import-demo -world "w_$id" -player player "../$d/storyboard.json" "../$o" 2>&1 | tee -a "$ROOT/$o.log" \
      | grep -o '"episode":"[^"]*"' | cut -d'"' -f4 > "$ROOT/$o/episode_id")
    [ -s "$o/episode_id" ] && echo "== v backendu: $id → $(cat "$o/episode_id")" || { rm -f "$o/episode_id"; echo "!! $id import selhal"; }
  done
}

# bubbles/title/choices translated into storyboard.json itself (bubbles[].i18n, title_i18n), so import-demo brings
# them along and phase_translate has nothing left to do. Run after write, before render: -p sbtranslate
phase_sbtranslate() {
  [ -n "$FREE" ] && return
  wait_llm
  for id in "${ids[@]}"; do
    sb=data/stories/$id/storyboard.json; [ -f "$sb" ] && [ ! -f "$OUTD/$id.sbtranslated" ] || continue
    echo "== překládá storyboard LLM: $id $(date +%H:%M)"
    (cd backend && "$BIN" translate -storyboard "../$sb" >> "$ROOT/$OUTD/$id.log" 2>&1) \
      && touch "$OUTD/$id.sbtranslated" || echo "!! $id překlad storyboardu selhal"
  done
}

phase_translate() {
  [ -n "$FREE" ] && return
  # storyboard translated before import → the episode came in translated, no LLM needed
  for id in "${ids[@]}"; do
    o=$OUTD/$id; [ -s "$o/episode_id" ] && [ -f "$OUTD/$id.sbtranslated" ] && touch "$o/translated"
  done
  for id in "${ids[@]}"; do [ -s "$OUTD/$id/episode_id" ] && [ ! -f "$OUTD/$id/translated" ] && { wait_llm; break; }; done
  for id in "${ids[@]}"; do
    o=$OUTD/$id; [ -s "$o/episode_id" ] && [ ! -f "$o/translated" ] || continue
    echo "== překládá LLM: $id $(date +%H:%M)"
    (cd backend && "$BIN" translate -episode "$(cat "$ROOT/$o/episode_id")" -inline >> "$ROOT/$o.log" 2>&1) \
      && touch "$o/translated" || echo "!! $id překlad selhal"
  done
}

case $PHASE in
  all) phase_write; phase_render; phase_import; phase_translate ;;
  write|render|import|translate|sbtranslate) "phase_$PHASE" ;;
  *) echo "neznámá fáze $PHASE"; exit 2 ;;
esac
echo "== hotovo $(date +%H:%M):"
for id in "${ids[@]}"; do
  o=$OUTD/$id; st="bez storyboardu (LLM znovu)"; [ -f "data/stories/$id/storyboard.json" ] && st="storyboard hotový, nenakresleno"
  [ -f "$o/strip.png" ] && st="nakresleno"; [ -s "$o/episode_id" ] && st="v backendu $(cat "$o/episode_id")"
  [ -f "$o/translated" ] && st="$st, přeloženo"; echo "   $id: $st ($(ls "$o"/p*_video.webp 2>/dev/null | wc -l | tr -d ' ') smyček)"
done
