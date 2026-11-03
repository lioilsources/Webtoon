package preview

import (
	"bytes"
	"encoding/json"
	"html/template"

	"github.com/ol1n/webtoon/backend/internal/pack"
)

// language names in their own language, for the switcher
var langNames = map[string]string{
	"cs": "Čeština", "de": "Deutsch", "en": "English", "es": "Español", "fr": "Français", "it": "Italiano",
	"ja": "日本語", "ko": "한국어", "pl": "Polski", "pt-BR": "Português (BR)", "ru": "Русский", "sk": "Slovenčina",
	"uk": "Українська", "vi": "Tiếng Việt", "zh": "中文",
}

type pageData struct {
	Title, Lede, Unit, Theme string
	Width                    int
	Panels, Loops, Langs     int
	Acts                     []actHead
	LangButtons              []langButton
	Book                     template.JS
}

type actHead struct {
	N             int
	ID, Title     string
	Panels, Loops int
}

type langButton struct{ Code, Name string }

func page(g *pack.Graph, book bookJSON, opts Options, panels, loops int) ([]byte, error) {
	d := pageData{Title: g.Title, Lede: opts.Lede, Unit: opts.Unit, Theme: opts.Theme, Width: 0,
		Panels: panels, Loops: loops, Langs: len(book.Langs)}
	for i, a := range book.Acts {
		h := actHead{N: i + 1, ID: a.ID, Title: a.Titles[opts.Lang], Panels: len(a.Panels)}
		for _, p := range a.Panels {
			if p.Loop {
				h.Loops++
			}
		}
		d.Acts = append(d.Acts, h)
	}
	for _, l := range book.Langs {
		n := langNames[l]
		if n == "" {
			n = l
		}
		d.LangButtons = append(d.LangButtons, langButton{l, n})
	}
	raw, err := json.Marshal(book)
	if err != nil {
		return nil, err
	}
	d.Book = template.JS(raw)
	var out bytes.Buffer
	err = pageTmpl.Execute(&out, d)
	return out.Bytes(), err
}

var pageTmpl = template.Must(template.New("page").Parse(`<!doctype html>
<html lang="cs" data-book-theme="{{.Theme}}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="claude:viewport-fit-sides" content="cover">
<title>{{.Title}}</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Nunito:ital,wght@0,700;1,600&family=Baloo+2:wght@500&family=DynaPuff:wght@700&family=Cormorant+Garamond:wght@600;700&family=Oswald:wght@500;700&family=IBM+Plex+Sans:wght@400;500&display=swap">
<style>
/* One narrow reading column like the phone reader. Panels are images (or the Wan loops), bubbles an SVG per panel
   drawn from the page data in the chosen language (webtoon preview, backend/internal/preview). One look per book:
   dark (noir) or light (watercolour paper). */
:root { --display:"Oswald","Arial Narrow",sans-serif; --body:"IBM Plex Sans",system-ui,sans-serif;
  --bg:#0d0f12; --panel:#15181d; --fg:#e4e6ea; --muted:#9aa1ad; --accent:#3fb8b0; --hot:#c45ad6; --line:#2a2f37; color-scheme:dark }
:root[data-book-theme="light"] { --display:"Cormorant Garamond",Georgia,serif;
  --bg:#f7f3ec; --panel:#ece6dc; --fg:#2d2a33; --muted:#6a6372; --accent:#2f6f96; --hot:#a8437e; --line:#d9d1c4; color-scheme:light }
body { background:var(--bg); color:var(--fg); font-family:var(--body); font-size:15px; line-height:1.55; margin:0 }
.wrap { max-width:560px; margin:0 auto; padding-block:28px 48px; padding-left:max(16px,env(safe-area-inset-left,0px)); padding-right:max(16px,env(safe-area-inset-right,0px)); display:grid; gap:20px }
.eyebrow { font-family:var(--display); font-weight:500; letter-spacing:.14em; text-transform:uppercase; color:var(--accent); font-size:12px }
h1 { font-family:var(--display); font-weight:700; font-size:clamp(30px,8vw,44px); line-height:1.05; margin:4px 0 0; text-wrap:balance }
.meta { color:var(--muted); font-size:14px; max-width:62ch; margin:0 }
dl { display:grid; grid-template-columns:auto 1fr; gap:6px 14px; margin:0; font-size:14px }
dt { color:var(--muted) } dd { margin:0 }
.toc { display:flex; flex-wrap:wrap; gap:8px }
.toc a { color:var(--fg); text-decoration:none; font-family:var(--display); font-size:14px; letter-spacing:.04em; border:1px solid var(--line); border-radius:3px; padding:5px 9px }
.toc a:hover, .toc a:focus-visible { border-color:var(--hot); color:var(--hot); outline:none }
.langbar { position:sticky; top:0; z-index:5; background:var(--bg); padding:10px 0; display:flex; gap:6px; overflow-x:auto; scrollbar-width:none; border-bottom:1px solid var(--line) }
.langbar::-webkit-scrollbar { display:none }
.langbar button { flex:none; font:500 13px var(--body); color:var(--muted); background:var(--panel); border:1px solid var(--line); border-radius:999px; padding:5px 11px; cursor:pointer }
.langbar button[aria-pressed="true"] { color:var(--bg); background:var(--accent); border-color:var(--accent) }
.langbar button:focus-visible { outline:2px solid var(--hot); outline-offset:2px }
.act { display:grid; gap:12px; scroll-margin-top:60px }
.acthead { display:flex; flex-wrap:wrap; gap:4px 10px; align-items:baseline; border-top:1px solid var(--line); padding-top:14px }
.acthead b { font-family:var(--display); font-size:21px; font-weight:700 }
.acthead i { font-style:normal; color:var(--muted); font-size:13px }
.strip { background:#fff; border-radius:6px; overflow:hidden }
.frame { position:relative }
.frame img { display:block; width:100%; height:100%; object-fit:cover; background:var(--panel) }
.frame svg { position:absolute; inset:0; width:100%; height:100%; pointer-events:none; overflow:visible }
.foot { color:var(--muted); font-size:13px; border-top:1px solid var(--line); padding-top:14px; margin:0 }
</style>
</head>
<body>
<div class="wrap">
  <div>
    <div class="eyebrow">Gamebook · náhled celé knihy</div>
    <h1 id="title">{{.Title}}</h1>
  </div>
  {{if .Lede}}<p class="meta">{{.Lede}}</p>{{end}}
  <dl>
    <dt>Rozsah</dt><dd>{{len .Acts}} × {{.Unit}}, {{.Panels}} panelů, {{.Loops}} animovaných</dd>
    <dt>Jazyky</dt><dd>{{.Langs}}, přepínač níž</dd>
  </dl>
  <nav class="toc">{{range .Acts}}<a href="#{{.ID}}">{{.N}}. <span class="t" data-act="{{.ID}}">{{.Title}}</span></a>{{end}}</nav>
  <div class="langbar" role="group" aria-label="Jazyk bublin">{{range .LangButtons}}<button type="button" data-l="{{.Code}}">{{.Name}}</button>{{end}}</div>
  {{range .Acts}}<section class="act" id="{{.ID}}">
    <div class="acthead"><b>{{.N}}. {{$.Unit}} · <span class="t" data-act="{{.ID}}">{{.Title}}</span></b><i>{{.Panels}} panelů · {{.Loops}} smyček</i></div>
    <div class="strip" data-act="{{.ID}}"></div>
  </section>
  {{end}}
  <p class="foot">Náhled ze zpracování, ne čtečka: appka si bubliny rozmístí sama. Animované panely tu hrají pořád; appka je pouští, až když je panel vidět, a při omezení pohybu nechá stát. Překlady jsou strojové.</p>
</div>
<script>
const BOOK = {{.Book}};
const W = 800, INK = '#141418', NS = 'http://www.w3.org/2000/svg';
const FONT = { speech:'"Nunito",system-ui,sans-serif', thought:'"Nunito",system-ui,sans-serif', shout:'"DynaPuff","Nunito",sans-serif', narration:'"Baloo 2","Nunito",sans-serif' };
const el = (n, a, p) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (p) p.appendChild(e); return e; };

function drawBubble(svg, b, L) {
  const g = el('g', {}, svg);
  const kind = b.kind;
  if (kind === 'narration') {
    el('rect', { x:L.x, y:L.y, width:L.w, height:L.h, fill:'#fff8e1', stroke:INK, 'stroke-width':3 }, g);
  } else {
    const [cx, cy, tx, ty, s] = L.tail;
    if (kind === 'thought') {
      [[10,.35],[7,.65],[5,.9]].forEach(([r,f]) => el('circle', { cx:cx+(tx-cx)*f, cy:cy+(ty-cy)*f, r, fill:'#fff', stroke:INK, 'stroke-width':2 }, g));
    } else {
      el('polygon', { points:` + "`${cx-22},${cy-4*s} ${cx+10},${cy-4*s} ${tx},${ty}`" + `, fill:'#fff', stroke:INK, 'stroke-width':3, 'stroke-linejoin':'round' }, g);
    }
    el('rect', { x:L.x, y:L.y, width:L.w, height:L.h, rx: kind === 'shout' ? 0 : Math.min(L.h/2, 40), fill:'#fff', stroke:INK, 'stroke-width': kind === 'shout' ? 5 : 3 }, g);
    if (kind !== 'thought') el('polygon', { points:` + "`${cx-19},${cy-6*s} ${cx+7},${cy-6*s} ${tx-1},${ty-9*s}`" + `, fill:'#fff' }, g);
  }
  const t = el('text', { 'text-anchor':'middle', fill:INK, 'font-size':L.fs, 'font-family':FONT[kind] || FONT.speech,
    'font-weight': kind === 'narration' ? 500 : 700, 'font-style': kind === 'thought' ? 'italic' : 'normal' }, g);
  L.lines.forEach((line, i) => { const s = el('tspan', { x:L.x + L.w/2, y:L.y + 15 + i*L.lh + L.fs*0.92 }, t); s.textContent = line; });
}

function render(lang) {
  for (const act of BOOK.acts) {
    const strip = document.querySelector(` + "`.strip[data-act=\"${act.id}\"]`" + `);
    if (!strip.dataset.built) {
      strip.dataset.built = '1';
      for (const p of act.panels) {
        const pn = document.createElement('div');
        pn.style.paddingBottom = p.gap + '%';
        const fr = document.createElement('div');
        fr.className = 'frame'; fr.style.aspectRatio = ` + "`${W} / ${Math.round(W*p.ratio)}`" + `;
        const img = document.createElement('img');
        img.loading = 'lazy'; img.alt = ''; img.src = p.src;
        fr.appendChild(img);
        const svg = el('svg', { viewBox:` + "`0 0 ${W} ${W*p.ratio}`" + `, 'aria-hidden':'true' }, fr);
        pn.appendChild(fr); strip.appendChild(pn);
        p._svg = svg;
      }
    }
    for (const p of act.panels) {
      p._svg.replaceChildren();
      for (const b of p.bubbles || []) drawBubble(p._svg, b, b.layout[lang]);
      if (p._svg.parentElement) p._svg.parentElement.setAttribute('aria-label', (p.bubbles || []).map(b => b.text[lang]).join(' '));
    }
    document.querySelectorAll(` + "`.t[data-act=\"${act.id}\"]`" + `).forEach(t => { t.textContent = act.titles[lang] || act.titles[BOOK.langs[0]]; });
  }
  document.getElementById('title').textContent = BOOK.titles[lang] || BOOK.titles[BOOK.langs[0]];
  document.querySelectorAll('.langbar button').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.l === lang)));
  document.documentElement.lang = lang;
  try { localStorage.setItem('preview-lang', lang); } catch (e) {}
}

document.querySelector('.langbar').addEventListener('click', e => { const b = e.target.closest('button'); if (b) render(b.dataset.l); });
let start = BOOK.langs[0];
try { const l = localStorage.getItem('preview-lang'); if (l && BOOK.langs.includes(l)) start = l; } catch (e) {}
(document.fonts ? document.fonts.ready : Promise.resolve()).then(() => render(start));
render(start);
</script>
</body>
</html>
`))
