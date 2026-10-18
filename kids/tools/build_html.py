"""All finished strips → one browsable page (index + one section per story, versions stacked).

    python3 kids/tools/build_html.py OUTDIR

Writes OUTDIR/index.html, OUTDIR/strips/<story>.jpg (600 px wide) and OUTDIR/thumbs/<story>.jpg.
Stories that are the same script on another model (world.remake_of) share one section, versions
one under another, so the A/B reads top to bottom.
"""
import html
import json
import sys
from pathlib import Path

from PIL import Image

KIDS = Path(__file__).resolve().parent.parent
ROOT = KIDS.parent
OUT_STRIPS = ROOT / "out" / "kids"
notes = json.loads((KIDS / "runs" / "matrix_notes.json").read_text(encoding="utf-8"))["presets"]
styles = json.loads((ROOT / "data" / "styles.json").read_text(encoding="utf-8"))["presets"]
dest = Path(sys.argv[1])
(dest / "strips").mkdir(parents=True, exist_ok=True)
(dest / "thumbs").mkdir(parents=True, exist_ok=True)

SETS = [(1, 5, "Sada 1 · NoobAI webtoon"), (6, 10, "Sada 2 · Illustrious a Animagine"), (11, 15, "Sada 3 · Juggernaut, FLUX, Pony + LoRA"),
        (16, 20, "Sada 4 · postapokalyptický svět"), (21, 25, "Sada 5"), (26, 30, "Sada 6"),
        (31, 35, "Sada 7 · remake sady 6"), (36, 40, "Sada 8 · remake sady 5")]


def set_of(n):
    return next((label for a, b, label in SETS if a <= n <= b), "")


stories = []
for f in sorted((KIDS / "stories").glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    strip = OUT_STRIPS / f"{f.stem}.png"
    if not strip.exists():
        continue
    w = d["world"]
    pre = w.get("style_id", "")
    pdef = styles.get(pre, {})
    model = (pdef.get("unet") or pdef.get("checkpoint") or "").rsplit(".", 1)[0]
    loras = [l["name"].split("/")[-1].rsplit(".", 1)[0] for l in pdef.get("loras", [])]
    n = notes.get(pre, {})
    im = Image.open(strip).convert("RGB")
    small = im.resize((600, round(im.height * 600 / im.width)), Image.LANCZOS)
    small.save(dest / "strips" / f"{f.stem}.jpg", "JPEG", quality=74, optimize=True, progressive=True)
    first = Image.open(OUT_STRIPS / f.stem / "comfy" / "p01_s0.png").convert("RGB")
    first.thumbnail((360, 360))
    first.save(dest / "thumbs" / f"{f.stem}.jpg", "JPEG", quality=78)
    stories.append({"id": f.stem, "num": int(f.stem[:2]), "title": d["storyboard"]["title"], "base": w.get("remake_of", f.stem),
                    "preset": pre, "model": model, "loras": loras, "style": n.get("style", pre), "verdict": n.get("verdict", "–"),
                    "panels": len(d["storyboard"]["panels"]), "height": small.height, "setting": w.get("setting", "")})

groups = {}
for s in stories:
    groups.setdefault(s["base"], []).append(s)
order = sorted(groups.values(), key=lambda g: min(x["num"] for x in g if x["id"] == x["base"]) if any(x["id"] == x["base"] for x in g) else g[0]["num"])

E = html.escape


def version(s):
    lora = f'<span class="tag">LoRA {E(", ".join(s["loras"]))}</span>' if s["loras"] else ""
    return f'''<figure class="version" id="{E(s["id"])}">
  <figcaption><span class="num">{s["num"]:02d}</span><span class="style">{E(s["style"])}</span>
    <span class="tag">{E(s["model"])}</span>{lora}<span class="tag v v{E(s["verdict"])}" title="verdikt v paměťové matici">{E(s["verdict"])}</span>
    <span class="meta">{s["panels"]} panelů · {E(set_of(s["num"]))}</span></figcaption>
  <img src="strips/{E(s["id"])}.jpg" width="600" height="{s["height"]}" loading="lazy" alt="Komiksový strip: {E(s["title"])} ({E(s["style"])})">
</figure>'''


cards, sections = [], []
for g in order:
    g = sorted(g, key=lambda x: x["num"])
    head = g[0]
    anchor = f"s{head['num']:02d}"
    vers = " · ".join(f"{x['num']:02d}" for x in g)
    cards.append(f'''<a class="card" href="#{anchor}"><img src="thumbs/{E(head["id"])}.jpg" alt="" loading="lazy">
  <span class="ct">{E(head["title"])}</span><span class="cm">{"verze " if len(g) > 1 else "příběh "}{vers}</span></a>''')
    note = f'<p class="lede">{len(g)} verze téhož scénáře a seedů, liší se jen model a styl.</p>' if len(g) > 1 else ""
    setting = f'<p class="lede">Prostředí: {E(head["setting"])}</p>' if head["setting"] else ""
    sections.append(f'''<section class="story" id="{anchor}">
  <h2>{E(head["title"])}</h2>{note}{setting}
  <div class="versions">{"".join(version(x) for x in g)}</div>
  <a class="top" href="#index">↑ zpět na přehled</a>
</section>''')

page = f'''<title>Webtoony pro děti</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Baloo+2:wght@600;800&family=Nunito:wght@400;600;700&display=swap">
<style>
/* Layout: comic-shelf index on top, then one reading column per story with versions stacked like strips on a phone. */
:root {{
  --paper: #fbf7f0; --ink: #23201d; --muted: #6d655c; --line: #e4dccf; --accent: #e8573c; --card: #ffffff;
  --a: #2f8f5b; --b: #3c74c9; --c: #c98a1c; --d: #b9473b;
  --display: "Baloo 2", "Nunito", system-ui, sans-serif; --body: "Nunito", system-ui, sans-serif;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{ --paper: #1b1917; --ink: #f1ebe2; --muted: #a99f93; --line: #3a352f; --accent: #ff7a5c; --card: #24211e; --a: #5cc48a; --b: #7aa6ee; --c: #e7b14f; --d: #ee7a6c; color-scheme: dark }} }}
:root[data-theme="dark"] {{ --paper: #1b1917; --ink: #f1ebe2; --muted: #a99f93; --line: #3a352f; --accent: #ff7a5c; --card: #24211e; --a: #5cc48a; --b: #7aa6ee; --c: #e7b14f; --d: #ee7a6c; color-scheme: dark }}
body {{ background: var(--paper); color: var(--ink); font: 16px/1.55 var(--body); padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); padding-block: 24px 64px; }}
main {{ max-width: 1100px; margin: 0 auto; display: grid; gap: 56px; }}
header h1 {{ font: 800 clamp(2rem, 6vw, 3.2rem)/1.05 var(--display); margin: 0 0 8px; text-wrap: balance; }}
header p {{ margin: 0; color: var(--muted); max-width: 65ch; }}
.stats {{ display: flex; flex-wrap: wrap; gap: 8px 20px; margin-top: 14px; font-size: .9rem; color: var(--muted); font-variant-numeric: tabular-nums; }}
.stats b {{ color: var(--ink); }}
h2 {{ font: 800 clamp(1.5rem, 4vw, 2.1rem)/1.1 var(--display); margin: 0; text-wrap: balance; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 14px; }}
.card {{ display: grid; gap: 4px; text-decoration: none; color: inherit; background: var(--card); border: 1px solid var(--line); border-radius: 10px; overflow: hidden; padding-bottom: 10px; }}
.card img {{ aspect-ratio: 4/3; object-fit: cover; width: 100%; background: var(--line); }}
.card:hover, .card:focus-visible {{ border-color: var(--accent); outline: none; }}
.ct {{ font: 700 .95rem/1.25 var(--body); padding: 0 10px; }}
.cm {{ font-size: .78rem; color: var(--muted); padding: 0 10px; font-variant-numeric: tabular-nums; }}
.story {{ display: grid; gap: 14px; border-top: 3px solid var(--ink); padding-top: 18px; }}
.lede {{ margin: 0; color: var(--muted); }}
.versions {{ display: grid; gap: 28px; justify-items: center; }}
.version {{ margin: 0; display: grid; gap: 8px; width: 100%; max-width: 600px; min-width: 0; }}
.version img {{ width: 100%; height: auto; border: 1px solid var(--line); border-radius: 6px; background: #fff; }}
figcaption {{ display: flex; flex-wrap: wrap; gap: 6px 8px; align-items: baseline; font-size: .85rem; }}
.num {{ font: 800 1.1rem var(--display); color: var(--accent); font-variant-numeric: tabular-nums; }}
.style {{ font-weight: 700; }}
.tag {{ border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px; color: var(--muted); font-size: .78rem; overflow-wrap: anywhere; }}
.v {{ font-weight: 700; color: var(--paper); border: 0; }}
.vA {{ background: var(--a); }} .vB {{ background: var(--b); }} .vC {{ background: var(--c); }} .vD {{ background: var(--d); }}
.meta {{ color: var(--muted); font-size: .78rem; width: 100%; }}
.top {{ justify-self: center; color: var(--muted); font-size: .9rem; }}
.legend {{ display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: .82rem; color: var(--muted); margin-top: 10px; }}
.legend .v {{ padding: 1px 7px; border-radius: 999px; margin-right: 4px; }}
a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 2px; }}
</style>
<main>
<header id="index">
  <h1>Webtoony pro děti</h1>
  <p>Každý příběh je vertikální komiksový strip s bublinami v češtině. Obrázky kreslil ComfyUI na ol1n.com, každý příběh jiným modelem nebo stylem. Kde existují dvě verze téhož scénáře, jsou pod sebou.</p>
  <div class="stats"><span><b>{len(stories)}</b> stripů</span><span><b>{len(order)}</b> scénářů</span><span><b>{sum(s["panels"] for s in stories)}</b> panelů</span><span><b>{len({s["model"] for s in stories})}</b> modelů</span></div>
  <div class="legend"><span><span class="v vA">A</span>výchozí volba</span><span><span class="v vB">B</span>dobré se známými opravami</span><span><span class="v vC">C</span>jen na některé záběry</span><span><span class="v vD">D</span>nepoužívat</span><span>(verdikt presetu v paměťové matici)</span></div>
</header>
<nav class="grid" aria-label="Příběhy">{"".join(cards)}</nav>
{"".join(sections)}
</main>
'''
(dest / "index.html").write_text(page, encoding="utf-8")
total = sum(p.stat().st_size for p in dest.rglob("*") if p.is_file())
print(f"{len(stories)} strips in {len(order)} sections → {dest}/index.html ({total / 1e6:.1f} MB with images)")
