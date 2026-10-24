#!/bin/bash
# Re-draw an existing story in another style: copy data/stories/<id> to data/stories/<id>__<style> with the new
# style_id (storyboard.json and its translations untouched), then render, animate, import and translate the copy
# through m0/local_strip.sh -I (phases render, import, translate). Made for the starter showcase
# (data/starter_showcase.yaml): the kids/superhero picks are drawn in clean_webtoon_noartist today.
#
#   m0/restyle.sh w_lx_k2_01_lia_planeta_tisice_mesicu:pixar_3d w_lx_k4_06_toby_pavouci_rytir:western_comic:superhero
#   m0/restyle.sh -n …     dry run: make the copies, print the local_strip.sh commands, run nothing
#   m0/restyle.sh -f …     replace an existing copy (its storyboard/world.json; out/ renders are kept)
#
# <world-id>:<style>[:<profile>]  world id with or without w_; style = a data/styles.json preset in the profile's
# pool; profile (optional) is written into the copy's world.json (`profile` key, e.g. superhero for the k3/k4
# worlds that have none today), else the world's own (rules.world_profile). Free worlds are refused (never in the
# app). The render needs the ComfyUI window (local_strip.sh waits for it): ask Director for the go.
# WEBTOON_ROOT=<dir> works on another checkout's data/ (tests); default the repo of this script.
set -u
cd "$(dirname "$0")/.."
ROOT=${WEBTOON_ROOT:-$PWD}
M0=$PWD/m0
DRY=; FORCE=
while getopts "nf" o; do case $o in n) DRY=1 ;; f) FORCE=1 ;; *) exit 2 ;; esac; done
shift $((OPTIND - 1))
[ $# -eq 0 ] && { sed -n 2,17p "$0"; exit 2; }

declare -a new_ids=() new_profiles=()
for a in "$@"; do
  IFS=: read -r world style profile <<< "$a"
  [ -n "$world" ] && [ -n "$style" ] || { echo "!! $a: čekám <world-id>:<style>[:<profile>]"; exit 2; }
  id=${world#w_}; src=$ROOT/data/stories/$id; new=${id}__$style; dst=$ROOT/data/stories/$new
  [ -f "$src/world.json" ] && [ -f "$src/storyboard.json" ] || { echo "!! $src: chybí world.json / storyboard.json"; exit 2; }
  # checks + the profile the copy is drawn with; prints it
  prof=$(python3 - "$src/world.json" "$style" "$profile" "$M0" <<'EOF'
import json, sys
world_path, style, profile, m0 = sys.argv[1:]
sys.path.insert(0, m0)
import rules
w = json.load(open(world_path, encoding="utf-8"))
if w.get("free"):
    sys.exit(f"!! {w['id']} je free svět: do aplikace nesmí, nepřekresluje se")
presets = json.load(open(rules.RULES.parent / "data" / "styles.json", encoding="utf-8"))["presets"]
if style not in presets:
    sys.exit(f"!! styl {style} není v data/styles.json")
p = profile or rules.world_profile(w)
if p not in rules.profiles():
    sys.exit(f"!! {w['id']}: profil {p!r} neznám ({', '.join(rules.profiles())})")
if p == "free":
    sys.exit(f"!! {w['id']}: profil free se do aplikace nepřekresluje")
pool = rules.cfg("profile", p)["styles"]["pool"]
if pool != "all" and style not in pool:
    sys.exit(f"!! styl {style} není v poolu profilu {p} (rules/profiles/{p}.yaml styles.pool)")
print(p)
EOF
  ) || exit 2
  if [ -e "$dst" ] && [ -z "$FORCE" ]; then echo "!! $dst už existuje (-f přepíše)"; exit 2; fi
  mkdir -p "$dst"
  cp "$src/storyboard.json" "$dst/storyboard.json"
  # everything else of the story dir comes along too (character sheets, notes), world.json is rewritten below
  for f in "$src"/*; do b=$(basename "$f"); [ "$b" = storyboard.json ] || [ "$b" = world.json ] || cp -R "$f" "$dst/"; done
  python3 - "$src/world.json" "$dst/world.json" "w_$new" "$style" "$profile" <<'EOF'
import json, sys
src, dst, wid, style, profile = sys.argv[1:]
w = json.load(open(src, encoding="utf-8"))
w["id"], w["style_id"] = wid, style
if profile:
    w["profile"] = profile
with open(dst, "w", encoding="utf-8") as f:
    json.dump(w, f, ensure_ascii=False, indent=2)
    f.write("\n")
EOF
  # the storyboard already carries its translations (bubbles[].i18n, title_i18n): mark it translated, so the
  # translate phase finds the imported episode translated and never calls the LLM
  day=$(python3 m0/rules.py get "$prof:pipeline.strip.day")
  if grep -q '"i18n"' "$dst/storyboard.json"; then mkdir -p "$ROOT/out/$day"; touch "$ROOT/out/$day/$new.sbtranslated"; fi
  echo "== kopie: $id → $new (styl $style, profil $prof)"
  new_ids+=("$new"); new_profiles+=("$prof")
done

# one local_strip.sh run per profile (render thresholds, negatives and loops follow the profile)
for prof in $(printf '%s\n' "${new_profiles[@]}" | sort -u); do
  batch=()
  for i in "${!new_ids[@]}"; do [ "${new_profiles[$i]}" = "$prof" ] && batch+=("${new_ids[$i]}"); done
  for phase in render import translate; do
    cmd=(m0/local_strip.sh -I -P "$prof" -p "$phase" "${batch[@]}")
    if [ -n "$DRY" ]; then echo "${cmd[*]}"; continue; fi
    "${cmd[@]}"; rc=$?
    # render exit 3 = the ComfyUI window closed: rerun the same restyle.sh -f … tomorrow, every phase resumes
    [ $rc -eq 3 ] && { echo "== konec okna ComfyUI; pokračuj zítra: m0/local_strip.sh -I -P $prof -p render ${batch[*]}"; exit 3; }
  done
done
