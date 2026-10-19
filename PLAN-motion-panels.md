# PLAN-motion-panels.md — pohyblivá políčka stripu (smyčka 1–3 s)

Stav 2026-10-19. Čísla z `video-stack/reports/phase3_bench.tsv` (Spark, srpen 2026) a z dnešního běhu 60 stripů.

---

## 1. Co to je

Vybraný panel stripu není PNG, ale **bezešvá smyčka 1–3 s** (16 fps → 17 / 33 / 49 snímků), která popisuje děj políčka:
vlasy ve větru, otočení hlavy, úsměv, déšť za oknem, vlny, neon. Ostatní panely zůstanou statické. Čtečka smyčku
přehrává, dokud je panel na obrazovce; bubliny leží nad ní stejně jako dnes.

## 2. Technika

| | Volba | Proč |
|---|---|---|
| Model | **Wan 2.2 I2V 14B fp8 + Lightning LoRA (4 kroky)** — už stažený, workflow `video-stack/workflows/flf2v_lightning_portrait.json` | 5B je pomalejší (215 s vs 155 s na 33 sn.) a horší; LTX-2.3 je na dlouhé klipy, pro 2 s nic nepřidá |
| Smyčka | **WanFirstLastFrameToVideo** se start = end = hotový panel | smyčka se uzavře bez střihu; identita postavy = panel sám, žádný drift |
| Rozlišení | 480×704 (portrét) / 704×480 (krajina), ≈ 0,34 Mpx; panel 832×1216 se pro video zmenší | HD (1 Mpx) stojí 5× víc (806 s / 81 sn.) a zisk na telefonu není vidět |
| Výstup | **animovaný WebP** (ComfyUI `SaveAnimatedWEBP`, q 80) + původní PNG jako poster | Flutter `Image` animovaný WebP přehrává nativně na iOS, Androidu i webu — bez `video_player`; 33 sn. ≈ 1,5–3 MB |
| Doručení | přes nové image API (`POST /v1/image/jobs` s FLF2V grafem, vstupní PNG v base64) nebo LAN ComfyUI | kontrakt už bere libovolný workflow a vrací soubory ze SaveImage/VHS; `SaveAnimatedWEBP` ověřit (fáze 1) |
| SFW | WD14 na 3 snímcích (první, prostřední, poslední) se stejnými prahy jako u panelu; `motion` prompt přes stejný slovník zakázaných slov | pohyb nesmí přidat nic, co statický panel neměl |
| Paměť | Wan 14B high+low + umt5 ≈ 50 GB; vedle SDXL (~7 GB) ≈ 60 GB | nad limit „ComfyUI ≤ 52 GB“ v comfy profilu → **domluvit s Directorem**; audio (25 GB) vedle toho ne |

Pořadí v okně: nejdřív všechny statické panely (SDXL), pak všechny smyčky (Wan) — jeden swap modelů místo stovek.

## 3. O kolik se prodlouží render

Dnes: 646 panelů × 14 s ≈ **2,5 h** na 60 stripů.

| Smyčka | Snímků | s / panel (480×704, Lightning) |
|---|---|---|
| 1 s | 17 | ~100 |
| 2 s | 33 | ~155 (naměřeno 832×480) |
| 3 s | 49 | ~200 |

| Kolik panelů rozhýbat | Navíc | Celkem na 60 stripů | Vejde se do okna 07–13? |
|---|---|---|---|
| 1 na strip (60) | 60 × 155 s ≈ **2,6 h** | ≈ 5 h (2×) | ano |
| 2 na strip (120) | ≈ **5,2 h** | ≈ 7,7 h (3×) | ne, přes dvě okna |
| všechny (646) | ≈ **28 h** | — | ne, 5 oken |

Jeden panel navíc stojí tolik co **11 statických**. Proto výchozí limit **2 pohyblivé panely na díl** (kód), typicky
establishing (prostředí: vlny, déšť, světla) + emocionální vrchol (vítr ve vlasech, otočení, úsměv).

## 4. Co napíše lokální LLM (ne Claude)

Storyboard writer (`skills/storyboard-writer`, qwen36 přes `m0/adapt.py`) dostane do schématu dvě pole na panel:

- `animate: bool` — nejvýš 2 panely na příběh (kód ořízne na první dva);
- `motion: string` — anglický Wan prompt ≤ 15 slov: pohyb subjektu + okolí + „static camera“
  („her hair moves in the sea breeze, she slowly turns her head and smiles, static camera“).

Pravidla v promptu: vybírat panely **bez lidí nebo s jednou postavou** (Wan ve dvojici míchá oblečení a tváře,
viz `video-stack/ANIME_STORY_PLAN.md`), malý pohyb, žádná mluva (lip-sync nedává smysl pod bublinou), žádný střih
kamery, žádný pohyb, který by odhalil oblečení. Stejné pole přidáme do backendového `storyboard.SystemPrompt`
(díl 2+ v interaktivním světě), takže to píše tentýž lokální model jako dnes storyboardy.

## 5. Editor

Na panelu nový přepínač **„Rozhýbat“**: zapne `animate`, pole „Pohyb“ (předvyplněné z LLM), délka 1 / 2 / 3 s.
Uložení → `PATCH /episodes/{id}/panels/{n}` → job `panel_video` → stav „Rozhýbává se…“ → po dokončení smyčka
v náhledu, tlačítka „Znovu“ (nový seed) a „Statický“ (smaže video, PNG zůstane). Odhad ceny ukázat: „≈ 2,5 min renderu“.
Mimo okno ComfyUI job čeká (image API `waiting_window`).

Čtečka: smyčka hraje, když je panel aspoň z poloviny vidět; respektuje systémové „omezit pohyb“ (pak poster PNG);
klepnutí pauzne.

## 6. Fáze

| Fáze | Co | Čas | Ověření |
|---|---|---|---|
| 1 | Schéma + prompt (`animate`, `motion`), `m0/animate.py`: FLF2V graf (port z video-stacku), SaveAnimatedWEBP, WD14 na 3 snímcích; smoke na 3 panelech z dnešní sady (zítra 07–13, po OK Directora k paměti) | ½ dne + okno | 3 smyčky bez švu, čas na panel, velikost WebP |
| 2 | Backend: `Panel.VideoURL/Motion/Animate/LoopSeconds`, migrace, PATCH, job `panel_video` (graf stejný jako m0), worker přes image API i LAN | 1 den | testy s fake ComfyUI |
| 3 | App: `PanelView` přehrává WebP s posterem, viditelnost, reduce-motion; editor přepínač + pole + délka + cena | 1 den | flutter test, ruční na telefonu |
| 4 | `adapt.py` A/B: nechat qwen36 vybrat panely a napsat `motion` pro 10 scénářů sady H, vykreslit, posoudit | okno | kolik smyček drží identitu a SFW |
| 5 | Report: strip s pohyblivými panely na olin.now (WebP přehraje i prohlížeč) | ½ dne | — |

## 7. Rizika

- **Dvě postavy v pohybu** se rozpadnou (známé z video-stacku) → kód povolí `animate` jen pro panely s ≤ 1 postavou,
  dvojice jen jako „ambient“ (světla, déšť) se silným `static camera` a malou intenzitou.
- **Rozlišení**: video 480×704 pod 832×1216 panelem — ve stripu se škáluje nahoru, na telefonu to projde, na desktopu změkne.
- **Paměť a okno**: Wan + SDXL ≈ 60 GB; Director musí posunout limit nebo smyčky jedou až po statických panelech
  s uvolněným SDXL (`/free`).
- **Velikost dílu**: 2 smyčky × 2,5 MB na díl je přijatelné; 10 smyček ne — limit zůstává.
- **SFW v pohybu**: šaty ve větru, naklonění — WD14 na 3 snímcích chytí totéž co u panelu, ne víc; ruční kontrola vzorku.
