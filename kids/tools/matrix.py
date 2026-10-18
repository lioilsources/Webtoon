"""Memory matrix: kids/runs/matrix.md from the job registry + kids/runs/matrix_notes.json.

    python3 kids/tools/matrix.py

Per preset: model, LoRAs, style, verdict, stories, renders (strip / variants / tests), rerolls per strip
panel, median seconds, and the notes. A second table maps every story to its preset, so the same
storyboard on two presets (e.g. 26 vs 31) reads as an A/B row.
"""
import json
import statistics
from collections import defaultdict
from pathlib import Path

KIDS = Path(__file__).resolve().parent.parent
ROOT = KIDS.parent
recs = [json.loads(l) for l in (KIDS / "runs" / "jobs.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
notes = json.loads((KIDS / "runs" / "matrix_notes.json").read_text(encoding="utf-8"))
styles = json.loads((ROOT / "data" / "styles.json").read_text(encoding="utf-8"))["presets"]

jobs = [r for r in recs if "event" not in r]
stat = defaultdict(lambda: {"strip": 0, "variant": 0, "test": 0, "secs": [], "stories": set()})
for r in jobs:
    s = stat[r["preset"]]
    v = r.get("variant")
    kind = "strip" if v is None else ("test" if isinstance(v, str) else "variant")
    s[kind] += 1
    if r.get("seconds"):
        s["secs"].append(r["seconds"])
    if kind != "test":
        s["stories"].add(r["story"][:2])

order = {"A": 0, "B": 1, "C": 2, "D": 3, "-": 4}
rows = sorted(set(stat) | set(notes["presets"]), key=lambda p: (order.get(notes["presets"].get(p, {}).get("verdict", "-"), 4), p))

out = ["# Paměťová matice — modely a styly pro dětské webtoony", "",
       "Generováno `kids/tools/matrix.py` z `kids/runs/jobs.jsonl` (čísla) a `kids/runs/matrix_notes.json` (poznatky).",
       "Verdikt: **A** výchozí volba · **B** dobré se známými opravami · **C** jen na některé záběry · **D** nepoužívat.", "",
       "Výhrady k číslům: příběhy 01–15 jsou v registru zpětně (`reconstructed`) a jejich zamítnuté varianty se nezachovaly, "
       "takže „přegenerování na panel“ je u nich podhodnocené (Juggernaut i Pony měly ve skutečnosti best-of-3 na ~40 % panelů). "
       "Sekundy jsou čas od odeslání po stažení, včetně čekání ve sdílené frontě ComfyUI — srovnávat jen v rámci jednoho běhu.", "",
       "## Obecná poučení", ""] + [f"- {l}" for l in notes["lessons"]] + ["",
       "## Presety", "",
       "| verdikt | preset | model | LoRA | styl | příběhy | rendery strip / varianty / test | přegenerování na panel | medián s/panel |",
       "|---|---|---|---|---|---|---|---|---|"]
for p in rows:
    n = notes["presets"].get(p, {})
    pre = styles.get(p, {})
    s = stat.get(p, {"strip": 0, "variant": 0, "test": 0, "secs": [], "stories": set()})
    model = pre.get("unet") or pre.get("checkpoint") or "?"
    loras = ", ".join(f"{l['name'].split('/')[-1].rsplit('.', 1)[0]} {l.get('strength', 1)}" for l in pre.get("loras", [])) or "—"
    reroll = f"{s['variant'] / s['strip']:.2f}" if s["strip"] else "—"
    secs = f"{statistics.median(s['secs']):.0f}" if s["secs"] else "—"
    out.append(f"| {n.get('verdict', '-')} | `{p}` | {model.rsplit('.', 1)[0]} | {loras} | {n.get('style', '')} | "
               f"{', '.join(sorted(s['stories'])) or '—'} | {s['strip']} / {s['variant']} / {s['test']} | {reroll} | {secs} |")
out += ["", "## Poznámky k presetům", ""]
for p in rows:
    n = notes["presets"].get(p)
    if not n or n.get("verdict") == "-":
        continue
    out += [f"### `{p}` — {n['verdict']}", f"- **funguje:** {n['good']}", f"- **chyby:** {n['bad']}", f"- **opravy:** {n['fixes']}", ""]

# story → preset (strip renders), A/B pairs via world.remake_of
out += ["## Příběhy", "", "| příběh | preset | remake of |", "|---|---|---|"]
for f in sorted((KIDS / "stories").glob("*.json")):
    w = json.loads(f.read_text(encoding="utf-8"))["world"]
    out.append(f"| {f.stem} | `{w.get('style_id')}` | {w.get('remake_of', '')} |")
(KIDS / "runs" / "matrix.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"{len(rows)} presets, {len(jobs)} renders → kids/runs/matrix.md")
