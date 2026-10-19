---
name: storyboard-writer
description: Převede volný scénář (postavy, scény, dialogy) na webtoon storyboard pro M0 renderer — world.json + storyboard.json, SFW, české bubliny, booru tagy. Pro lokální LLM (qwen36) i Claude Code.
---

# Storyboard writer

Použij, když přijde nový příběh jako text a má z něj vzniknout strip. Výstup je jeden JSON podle
`schema/story.schema.json`, který `m0/adapt.py` rozdělí na `data/stories/<id>/world.json` a `storyboard.json`
a doplní odvozená pole (`tag_prompt`, `count_tag`, `permissions`…).

## Jak spustit

```bash
# lokální model přes LiteLLM na SPARKu (okno llm 13:00–07:00) nebo přes llm.ol1n.com se service tokenem
WEBTOON_LLM=https://llm.ol1n.com/v1 WEBTOON_LLM_MODEL=openclaw-default \
WEBTOON_CF_ACCESS_ID=… WEBTOON_CF_ACCESS_SECRET=… \
python3 m0/adapt.py --id rl_01_santorini --style fashion_editorial scenare/santorini.md

python3 m0/adapt.py --dry-run …      # jen vypíše prompt, nevolá model
python3 m0/adapt.py --qa out/romance/rl_01_santorini   # vizuální QA kontaktního archu (vidění)
```

Pak jako dnes: `m0/run_romance.sh rl_01_santorini` (ComfyUI 07–13, max 1 job, Director dává zelenou).

## Pravidla, která musí výstup splnit (kontroluje kód i prompt)

1. **8–12 panelů.** První je `establishing` bez postav. Poslední má `gap_after: large`.
2. **Postavy**: každá má `gender` (`f`/`m`), `base` (booru tagy: `adult, mature female|mature male, …` povinně), 2–4 pojmenované
   `outfits` (vždy `default`), `photo` (jedna anglická věta: národnost, věk ≥ 23, vlasy, postava — **bez oblečení**).
   Žádné značky (Versace, Calvin Klein…), žádné tagy velikosti těla (`large breasts`, `short stature`), žádné prádlo, plavky, průsvitné látky.
3. **Panel**: `shot` ∈ `establishing|wide|medium|close-up|over-shoulder`; max 2 postavy; nikdy dvě stejného pohlaví v jednom panelu;
   pár nikdy v `close-up` (anime modely z toho dělají koláž); `visual_tags` jen booru tagy akce, pózy, emoce, světla a rekvizit — **ne design postavy**.
4. **Bubliny**: text česky, dialog z předlohy **doslova** (opravit jen překlepy, přeložit cizí jazyk), max 2 bubliny na panel,
   `kind` ∈ `speech|thought|shout|narration`; vnitřní monolog jako `thought`; narace má `speaker_id: ""`.
5. **SFW**: žádná nahota, prádlo, svlékání kromě kabátu/bot/šperků/klobouku, žádné pozice, žádná postel.
   Intimní scéna = objetí/polibek → panel bez lidí (zavřené dveře, zhasnutá lampa, moře) s narací → ráno oba oblečení. Muži v košili.
6. **Konec** podle předlohy (šťastný, hořkosladký, smutný, otevřený) jde do `canon.constraints`.
7. **Lokace**: 3–6, `tag_prompt` začíná `indoors`/`outdoors`, pak místo, denní doba, počasí, orientační body.

## Soubory

| Soubor | Co |
|---|---|
| `prompts/adapt_system.md` | systémový prompt pro adaptaci (anglicky, výstup česky) |
| `prompts/visual_qa.md` | prompt pro kontrolu kontaktního archu (vidění) |
| `schema/story.schema.json` | JSON schema pro `response_format` (vLLM xgrammar) a lokální validaci |
| `examples/santorini.input.md` + `.output.json` | few-shot: předloha ze sady H a výsledný storyboard, který se vykreslil bez oprav |
| `../../m0/adapt.py` | runner: prompt → model → validace → `data/stories/<id>/` |

## Co model nedělá

Volbu stylu (`--style` dává člověk nebo Claude Code podle `data/styles.json`), úpravy presetů, opravy panelů a kód.
Dětský vzhled postav a identitu ve dvojici po renderu vždy ověří člověk nebo Claude, model je jen první síto.
