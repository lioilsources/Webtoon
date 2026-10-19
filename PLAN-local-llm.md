# PLAN-local-llm.md — nahradit Clauda lokálním LLM při tvorbě stripů

Stav 2026-10-19. Navazuje na dvě šedesátky romantických stripů (sady A–K) a na AiStack `PLAN-model-bench.md`
(§6a) a `PLAN-image-api.md`.

---

## 1. Co při tvorbě stripu dělal LLM (Claude) a co ne

| Krok | Kdo to dělá dnes | Nahraditelné lokálním LLM? |
|---|---|---|
| **a) Adaptace scénáře na storyboard** — z volného textu (postavy, scény, dialogy) udělat 8–12 panelů, záběry, lokace s booru tagy, postavy s `base` + pojmenovanými outfity + `photo` větou, české bubliny (verbatim, opravené překlepy), narace, sfx | Claude ručně, 10 příběhů ≈ 3 min práce forku | **Ano.** Je to strukturovaná úloha s jasnými pravidly. Potřebuje model, který zvládne dlouhý český vstup a přísný JSON. |
| **b) Přepis na SFW** — svlékání, prádlo, pozice → polibek + zatmění, plavky → šaty, značky → popis | Claude v rámci (a) | **Ano**, s pravidly v promptu + slovníkem zakázaných slov v kódu jako pojistka. |
| **c) Volba stylu a návrh experimentu** — který preset na který příběh, nové LoRA presety, úpravy `styles.json`, negativní prompty | Claude | **Ne.** Je to návrhářská práce: vyžaduje vidět výsledky, číst metadata LoRA, rozumět modelům. Zůstane na Claude Code / člověku. |
| **d) Vizuální QA panelů** — koláže místo jednoho obrázku, tři postavy místo dvou, klon postavy, prohozené vlasy, odhalené oblečení, dětský vzhled | Claude koukal na kontaktní archy (po 4–7 příbězích), zhruba 25 ručních nálezů na 646 panelů; WD14 chytí jen rating/oblečení | **Částečně.** Multimodální model může třídit panely a navrhnout, co přegenerovat. Dětský vzhled a jemné chyby identity bez ověření nesvěřím jen malému VLM. |
| **e) Opravy a nástroje** — `fix_panels.sh`, změny záběru, úprava tagů, port do Go backendu | Claude Code | **Ne**, to je programování. |
| **f) Moderace vstupu čtenáře, storyboard dalšího dílu, tagy postav** | už dnes **lokální qwen36** (`openclaw-default`) v backendu | Hotovo, LLM-agnostické přes OpenAI API. |

Shrnuto: Claude je v pipeline **scenárista + editor obrazu + programátor**. Lokální model může převzít
scenáristu (a + b) a část editora obrazu (d). Programátor a návrhář stylů zůstávají.

## 2. Který model (podle Directora, PLAN-model-bench §6a)

**Prakticky jen `qwen36`** (Qwen3.6-35B-A3B NVFP4, vLLM na SPARKu):
- alias v LiteLLM: **`openclaw-default`** (`judge` je zatím jen ve větvi feat/model-bench, živý config ho nemá); posílat
  temperature 0, `response_format: json_schema` a `chat_template_kwargs.enable_thinking=false` (reasoning parser jinak
  dá přemýšlení do `reasoning_content`, `content` zůstane JSON);
- kontext 64k, tool calls, **`response_format: json_schema`** (xgrammar) — vynucené schéma je nutné, bez něj dal bench 48 %;
- 80 tok/s na stream, 215 tok/s při 4 souběžných → storyboard ~2 500 tokenů ≈ 30 s;
- okno **llm 13:00–07:00**; comfy 07–13, takže psaní a render se nepotkají;
- přes `https://llm.ol1n.com/v1` se service tokenem, stejně jako dnešní moderace;
- multimodální (vidění přes alias `judge`), na SPARKu zatím neověřeno — kontaktní arch poslat jako **jeden** složený obrázek.

Ostatní (`Gemma-4` 7 tok/s a schéma 20 %, `Nano-30B`, `swarm-director` 120B jen noční, `translate`, `vl` 7B) Director nedoporučuje.

Čeština: bench měřil právní češtinu, ne tvůrčí. Kvalitu bublin a SFW přepisu musí posoudit Ol1n na A/B vzorku (§5).

## 3. Architektura

```
scénář.md ──► m0/adapt.py ──► qwen36 (judge, json_schema) ──► validace (kód) ──► data/stories/<id>/{world,storyboard}.json
                  │  SKILL.md + prompts/adapt_system.md + schema/story.schema.json + examples/
                  └─ opakování s chybovou zpětnou vazbou (max 3×), pak odmítnout

render (ComfyUI 07–13, image API) ──► kontaktní arch ──► m0/adapt.py --qa ──► qwen36 vidění ──► seznam panelů k přegenerování
                                                                                 └─ Claude/člověk potvrdí (dětský vzhled, identita)
```

- **Rozhraní**: OpenAI chat completions, žádná závislost na konkrétním modelu. `WEBTOON_LLM`, `WEBTOON_LLM_MODEL`,
  `WEBTOON_CF_ACCESS_ID/SECRET` (stejné proměnné jako backend).
- **Pojistky v kódu, ne v promptu**: slovník zakázaných slov (prádlo, nahota, plavky, značky, `short stature` bez
  `mature female`…), enumy záběrů, 1 girl + 1 boy max v panelu, pár nikdy v `close-up`, zakázaná dvě stejná pohlaví
  v panelu, 8–12 panelů, `visual_tags` jen booru tagy (ověření proti `data/wd14_tags.json` jako u postav).
- **Skill** = `skills/storyboard-writer/` (SKILL.md, prompty, schéma, příklady). Stejný SKILL.md může číst Claude Code
  i OpenClaw agent; promptům rozumí qwen36 v angličtině, výstup je český.

## 4. Fáze

| Fáze | Co | Kde | Ověření |
|---|---|---|---|
| 1 | `skills/storyboard-writer/` + `m0/adapt.py` (hotovo v tomto commitu) | Webtoon | `--dry-run` sestaví prompt bez volání |
| 2 | **A/B na 10 scénářích** ze sady H (nejkratší předlohy): qwen36 vs. dnešní výstup Clauda, stejné předlohy | SPARK, okno llm (po 13:00) | tabulka: validace prošla / počet oprav / Ol1nův úsudek češtiny |
| 3 | Render A/B stripů ve stejném stylu, srovnání vedle sebe v reportu | ComfyUI 07–13 | kolik panelů z qwen36 storyboardů jsem musel opravit vs. Claude |
| 4 | `--qa`: ověřit vidění qwen36 na kontaktním archu se známými chybami (koláže, 3 postavy, klon) | okno llm | recall na 25 známých nálezech z dnešního běhu |
| 5 | Backend: `storyboard.Generate` pro „adaptaci z textu“ (nový endpoint `POST /worlds/import-script`) se stejným promptem; `response_format` do `internal/llm` | Webtoon backend | golden test proti `adapt.py` |
| 6 | Agent v OpenClaw / cron: scénář do složky → storyboard → fronta do image API → QA → návrh oprav do Telegramu | AiStack / PromoClown vzor | — |

## 5. Co rozhodne, jestli to stačí

1. **Validace**: kolik % výstupů projde kódovou validací napoprvé (cíl > 80 %, Claude ≈ 100 %).
2. **Čeština**: bubliny verbatim z předlohy, opravené překlepy, přirozená narace — posoudí Ol1n na A/B.
3. **SFW přepis**: žádný zakázaný prvek v tazích ani textu (kód to ohlídá; otázka je, jestli model zachová náladu scény).
4. **Panely k opravě po renderu**: dnes ~4 % ručních oprav (25/646). Když qwen36 storyboardy vyžadují > 10 %, nestačí.
5. **QA recall**: z 25 známých chyb kolik model najde; false positives pod 20 %.

## 6. Rizika

- Model dodrží schéma, ale zploští dialog (parafráze místo verbatim). Prompt to zakazuje, kód neověří. → A/B.
- Vidění qwen36 na SPARKu neověřené; vLLM výchozí `limit-mm-per-prompt`. → jeden složený obrázek ≤ 2048 px.
- Dětský vzhled postav: žádný automat ho spolehlivě nepozná. → `mature female`/`mature male` povinné v `base` (kód),
  QA jen jako filtr, poslední slovo člověk.
- Okno: psaní jen 13–07. Scénáře přijaté dopoledne čekají. Pro dávky to nevadí, pro interaktivní editor ano.
