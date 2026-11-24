# PLAN-pipeline-go.md — `webtoon story --definition <yaml>`: jeden příkaz, celý příběh

Stav 2026-11-13. Zadání od Olina pro Opus: z jedné YAML definice příběhu se na kterémkoli stroji (MacBook, M2),
bez Clauda v smyčce, příběh nakreslí, rozanimuje, vysází, přeloží do všech jazyků, namluví, naimportuje do JODA,
zabalí do in-app balíčku a vyrobí z něj trailer a TikTok video. Jeden Go binárka, jeden příkaz, všechno ostatní jsou
data v `rules/` a v definici.

Dnešní cesta (Louka, Kovové nebe, guláše, Archion): ručně psaný `graph.yaml`, `m0/gamebook.py draft`,
`m0/local_strip.sh` (Python + bash), `sparkctl`, Go backend (`webtoon import-demo / translate / export-pack /
trailer / music`), `tools/gulas_shorts.py`; čtyři stroje, tři Claude session. Tohle to sešívá dohromady.

---

## 1. Cíl

```
webtoon story --definition data/gamebooks/archion/graph.yaml          # celý běh, navazuje na hotové
webtoon story --definition data/stories/rh_01_santorini/story.yaml    # strip
webtoon story --definition x.yaml --until render                      # jen po render
webtoon story --definition x.yaml --status                            # co je hotové, co čeká, na co
webtoon story --definition x.yaml --approve style=painterly_oil       # lidská brána (kap. 7)
webtoon story author --brief Prompts/archion.md --out data/gamebooks/archion/graph.yaml   # zadání → definice (LLM)
```

Druhé spuštění téhož příkazu neudělá nic, co už je hotové. Po pádu, odsunutí ze SPARKu nebo změně definice
přepočítá jen to, co se změnilo (jedna změněná replika = jeden panel, ne uzel). Člověk zasahuje jen ve třech bodech:
schválí definici, vybere styl z testovacích panelů, odklepne finální preview; i ty jdou vypnout (`--no-gates`,
pro definice s `style.chosen`).

Mimo rozsah: čtečka (`app/`), fronta a profily SPARKu (`spark-broker`, Director), publikování do `webtoon-content`
(Director). Pipeline končí hotovým balíčkem, videi a připraveným PR.

## 2. Kterýkoli stroj

Dnes pipeline závisí na tom, kde co leží: `backend/.env` s DB je na M2, faces venv na MacBooku, ComfyUI a LLM na
SPARKu, token studia na JODĚ. Aby `story` běžel odkudkoli, všechno, co není v binárce, je síťová služba:

| Potřeba | Dnes | Nově |
|---|---|---|
| ComfyUI (SDXL, Wan, ACE-Step) | SPARK `:8188`, LAN | beze změny, přes `sparkctl` lease (Go klient) |
| LLM (storyboard z beats, překlady, author) | openclaw SPARK `:8080/v1`; author Opus API | beze změny; `author` přes API, zbytek lokálně |
| TTS (dabing) | Director: AiStack audio `:8093` → chatterbox `:8104` | beze změny, HTTP |
| obličeje | `m0/faces.py`, insightface venv jen na MacBooku | **služba `faces` na SPARKu** (profil comfy, jeden kontejner, `POST /faces` s PNG → boxy); binárka bez venv |
| import do DB, média | `webtoon import-demo` + `.env` jen na M2, pak `deploy.sh` kvůli médiím | **studio API na JODĚ**: `POST /studio/stories` (world + storyboard + panely multipart) s `X-Studio-Token`; backend uloží do DB i do `/media` sám. `import-demo` zůstane pro seed |
| export balíčku | `export-pack` čte DB přes `.env` | `GET /studio/pack?gamebook=<id>` nebo export z lokálních dat (pipeline má všechno, co je v DB) |
| token studia | `STUDIO_TOKEN` v `deploy/.env` na JODĚ, ručně do env | `WEBTOON_STUDIO_TOKEN` v env nebo v `~/.config/webtoon/env` (0600); nikdy v repu ani v logu |
| data | `data/`, `out/` na každém stroji jinak | `out/` je cache a dá se smazat; vše, co pipeline potřebuje znovu, umí stáhnout z JODA (`/media`) |

Při startu `story` zjistí, co je dosažitelné (ComfyUI, LLM, audio, faces, JODA, broker), a fáze, na které něco
chybí, nechá čekat s důvodem ve `--status` místo pádu. Rozdíl mezi MacBookem a M2 tím zmizí; zůstane jen rychlost
LAN vs. tailnet.

## 3. Definice příběhu

Jeden YAML. Pro gamebooky **už existuje**: `data/gamebooks/<id>/graph.yaml` (schema 1, 12 knih) je definice beze
změny, `story` ho bere přímo. Pro stripy je nově `data/stories/<id>/story.yaml` (schema 2), vyrobený zpětně z
`world.json` + `storyboard.json` nástrojem `tools/story_defs.py` (236 stripů, kontrola: každá definice postaví
původní panely 1:1). Obě schémata sdílejí stejné bloky; schema 2 jen přidává to, co graph.yaml nemá (hudba, dabing,
trailer, úroveň autorství) a dovoluje `kind: strip`.

**Úrovně autorství** (co v definici je, tím pipeline začne; čím výš, tím víc dělá LLM):

| `panels` | hotové panely: záběr, lokace, kdo, tagy, bubliny, sfx, smyčka | deterministické; všech 236 stripů dnes |
| `script` | divadelní hra: `say` (jedna replika = jeden panel mluvčího) a `see` (scénická poznámka jako obraz) | deterministické; 10 gamebooků (`m0/gamebook.py draft`) |
| `beats` | odstavec děje na uzel + postavy; LLM napíše panely podle `rules/base/storyboard.yaml` | Sára, Učit se mlčet; stripy z `local_strip.sh` |
| `brief` | lidsky řečené zadání v `.md`; `story author` z něj napíše celou definici na úrovni `script` nebo `beats` a čeká na schválení | nové |

Příklad schema 2 (gamebook; strip má jednu scénu a `kind: strip`):

```yaml
schema: 2
id: archion
kind: gamebook                 # gamebook | strip | series
title: "Archion: Konec jednoho přátelství"
title_i18n: {}                 # prázdné = přeloží pipeline
author: {screenplay: Ol1n, model: Gemini}
audience: adult                # kids | teen | adult → profil a SFW prahy
language: cs
languages: all                 # nebo seznam; all = jazyky appky (rules/base/pack.yaml)
profile: noir                  # rules/profiles/<name>.yaml; chybí-li, odvodí se (děti v příběhu, romance, …)
product: {id: gamebook_archion, price_tier: pack, free: false}
world: w_archion               # data/stories/archion/world.json: postavy, lokace, bible (jako dnes); nebo inline:
# characters: [...]  locations: [...]   (inline forma pro author a nové příběhy; build z ní world.json vyrobí)
style:
  candidates: [noir_graphic, painterly_oil, semireal_25d]   # testovací panely, vybere člověk
  chosen: null                 # po schválení zapíše pipeline; pak už se nemění
  palette_by_location: true    # paleta v promptu nese lokace (akvarel_louka), preset jen techniku
music: {prompt: "minimal techno, hypnotic four-on-the-floor kick, …", seed: 4221}   # nebo `pool` (data/music podle hashe světa)
dub:
  enabled: true
  voices: {kosmo: {ref: voices/kosmo.wav}, ol1n: {clone: player}}   # ref = vzorek, clone = hlas hráče (voice_clone)
  music_duck: 0.35
trailer: {shots: auto}         # nebo seznam jako dnes data/gamebooks/<id>/trailer.yaml
start: a1
draft: {speakers: {...}, faces: {...}, speaking: [...]}            # jako graph.yaml
nodes:
  a1: {title: "Jaro", location: l_zahrada_1, cast: {kosmo: kosmo, ol1n: ol1n_jaro}, next: a2,
       script: [{see: "…", shot: establishing, loc: l_bunkr_1, tags: [...], animate: "…"}, {say: kosmo, text: "…"}]}
```

Strip (`story.yaml`, výstup `tools/story_defs.py`):

```yaml
schema: 2
id: rh_01_santorini
kind: strip
title: Santorini – Ta, která se nedá přehlédnout
world: w_rh_01_santorini
audience: adult
language: cs
style_id: photo_juggernaut
fonts: romance
music: pool
panels:
  - {shot: establishing, loc: l_terrace, tags: [...], gap: medium}
  - {shot: close-up, loc: l_terrace, who: [elena], tags: [sad, looking down], bubbles: [{speaker_id: elena, text: "…", kind: thought}], gap: small}
  - {shot: wide, loc: l_cabin, who: [{erik: cabin}, sofia], tags: [...], gap: medium}   # {id: outfit} = jiné oblečení než default
```

**Co v definici není a nikdy nebude:** překlady (`*_i18n`, `bubbles[].i18n`), boxy obličejů, WD14 tagy, seedy
panelů, episode id. To všechno je výstup a žije v `out/` a v DB. `storyboard.json` se stává odvozeným souborem:
build ho z definice vyrobí vždy stejně (pro `panels` a `script`), pro `beats` jednou přes LLM a pak ho drží v
`out/` jako hotový artefakt s hashem vstupu.

**Ze zadání do definice.** `story author --brief x.md` nechá LLM napsat definici podle `schema/story.schema.json`
(schéma je v promptu, výstup se validuje, chyba se posílá zpět, nejvýš 3×). Divadelní hra jde doslova do `script`,
popis postav do `look`, scénické poznámky do `see`. Co autor neřekl (jazyky, profil, hudba), doplní pipeline z
pravidel, ne LLM. Pravidlo v promptu: jména skutečných osob, citace zpráv, částky a data nahradit smyšlenými
(Archion: Kosmo, Nebulon). Výsledek je diff ke schválení.

## 4. Architektura

```
backend/cmd/webtoon            story {--definition|author|--status|--approve}
backend/internal/
  story/        definice: načtení schema 1 a 2, validace, odvození world.json + storyboardů
                (port gamebook.py draft + adapt.check/to_m0; `panels` = tools/story_defs.py panel_back)
  pipeline/     DAG fází, stav, hashe, navazování, lidské brány; Stage interface
  stage/        build, styletest, render, faces, animate, compose, translate, dub, music, importdb, pack, trailer, shorts, publish
  spark/        klient fronty (lease, heartbeat, prodloužení, odsunutí, profily comfy|llm|audio)
  qa/           kontroly kap. 6, Verdict{ok|regenerate|human, reason}
  media/        ffmpeg, WebP, sazba bublin (sdílí compose, trailer, shorts)
  comfy/ wd14/ llm/ translate/ pack/ trailer/ prompt/ tags/   existují, rozšíří se
  api/          + studio endpointy (import, pack) pro JODA
```

**Stav.** `out/story/<id>/state.json` + adresář na fázi. Artefakt má klíč z hashe vstupů (prompt + seed + preset +
verze grafu ComfyUI + verze pravidel); shodný klíč = hotovo. Logy per fáze.

**DAG.** Fáze deklarují vstupy/výstupy; co nezávisí, běží vedle sebe (překlady vedle renderu, hudba vedle smyček,
dabing po překladu nezávisle na obrázcích). Na GPU pořadí po profilech: všechny SDXL panely, pak všechny Wan smyčky,
pak audio: jeden swap modelů na běh (PLAN-motion-panels.md). SPARK dostane jednu `lease` na skupinu fází se stejným
profilem.

**Gates místo hodin.** Fáze čeká, dokud služba neodpoví, a končí v deadline z `rules/base/pipeline.yaml`
(`WEBTOON_DEADLINE` zůstává).

**Konfigurace.** Jen `rules/*.yaml` a env (`WEBTOON_API`, `WEBTOON_COMFY`, `WEBTOON_LLM`, `WEBTOON_AUDIO`,
`WEBTOON_FACES`, `WEBTOON_STUDIO_TOKEN`, `SPARK_BROKER`). Nové klíče pravidel do `rules/README.md`.

## 5. Fáze

| # | Fáze | Dělá | Lidská brána |
|---|---|---|---|
| 0 | author | brief → definice (LLM, validace) | **schválit definici** |
| 1 | build | definice → world.json, storyboardy; slovník tagů, fences profilu, délky bublin, „nikdy dva lidé v jednom obraze“ u `script` | ne |
| 2 | styletest | 3 panely (interiér, exteriér, close-up) × kandidát stylu, kontaktní list | **vybrat styl** (přeskočeno, je-li `chosen` nebo `style_id`) |
| 3 | render | panel po panelu (preset + lokace + postava + tagy, seed), QA 6.2–6.5, reseed/varianta, skip hotových | ne |
| 4 | faces | boxy do storyboardu (služba faces) | ne |
| 5 | animate | `animate` panely → Wan smyčka, QA 6.6; smyčky zapsané autorem vždy | ne |
| 6 | compose | bubliny mimo obličeje, QA 6.7; strip PNG pro preview | ne |
| 7 | translate | `bubbles[].i18n`, `title_i18n`, `synopsis_i18n` pro všechny jazyky, QA 6.8 | ne |
| 8 | dub | replika × jazyk → WAV (AiStack), hlasy per postava, QA 6.9 | ne |
| 9 | music | skladba z `music` (ACE-Step) nebo výběr z poolu; `data/music/trailers/<id>.mp3` | ne |
| 10 | importdb | studio API JODA: world + storyboard + panely + smyčky → episode id do `state.json` | ne |
| 11 | pack | balíček `gamebook-<id>-v<N>.zip` / `<pack>-v<N>.zip`, QA 6.10 | ne |
| 12 | trailer, shorts | trailer 20–30 s; TikTok celý příběh 9:16 (větvené knihy: nejdelší cesta), bubliny i dabing+titulky, každý jazyk; hudba s crossfade smyčkou, ducking | **finální preview** |
| 13 | publish | PR do `webtoon-content` (zip, catalog diff, cover) a do Webtoon (data/…), store texty (`tools/gen_products.py`) | ne; merge Director |

Fáze 12 bere obrázky z `out/`, ne z `/media`: video nesmí záviset na importu a musí jít vyrobit i pro styl, který
do appky nepůjde (Archion oil vs. semireal).

## 6. Quality gates a přegenerování

Každá kontrola vrací `ok | regenerate | human`. Politika: `seed+1` až 3×, pak jedna změna promptu (jiná `faces`
varianta mluvčího, bez `animate`, kratší tagy), pak `human` se zdůvodněním a kontaktním listem. Limity v
`rules/base/qa.yaml` (nový, per profil přepsatelný).

| # | Kontrola | Fáze | Měří | Neprojde |
|---|---|---|---|---|
| 6.1 | schéma a slovník | build | JSON schema, booru tagy ne věty, id lokací/postav existují, graf bez sirot a smyček, bubliny ≤ 150 zn., skutečná jména (`qa.yaml: real_names`) | odmítnout s řádkem a důvodem |
| 6.2 | SFW | render, animate | WD14 rating a `tag_limits` profilu; u smyček 3 snímky | regenerate |
| 6.3 | počet lidí | render | WD14 `1boy/1girl/2girls/multiple people` vs. `who` panelu (0 u `see` bez `who`) | regenerate |
| 6.4 | identita | render | podobnost s referenčním panelem postavy (první schválený close-up; ArcFace přes službu faces) ≥ práh; jiná věková varianta = jiná reference | regenerate; po 3× human |
| 6.5 | text v obraze | render | WD14 `text`/`speech bubble` nad prahem, případně OCR | regenerate |
| 6.6 | smyčka | animate | první ≈ poslední snímek (PSNR), žádný nový obličej, SFW | regenerate; po 2× panel zůstane statický |
| 6.7 | bubliny | compose | mimo obličeje, uvnitř panelu, text se vejde fontem appky, bubliny se nepřekrývají | jiný slot → kratší `split_line` → human |
| 6.8 | překlad | translate | zpětný překlad a „stejný význam?“ (LLM), žádné prázdné i18n, délka ≤ 1,6× | znovu s poznámkou → human |
| 6.9 | dabing | dub | WAV existuje, délka v mezích, −16 LUFS ± 2, žádné ticho > 1 s, detekovaný jazyk = cílový | jiný seed TTS → titulky bez hlasu |
| 6.10 | balíček | pack | `node_ids` úplné, `languages` = všechny, každý panel má WebP, žádný `status != ok`, velikost | zastavit |
| 6.11 | video | shorts | ≤ 10 min, zvuk bez výpadků na švech (RMS v okně 1 s), „Konec“ na posledním snímku, 1080×1920, faststart | regenerate audio → human |

Dnes chybí úplně: 6.3, 6.4, 6.5, 6.7, 6.8, 6.9, 6.11. Nejvíc zvednou 6.4 a 6.5 (dnes vybírá panely Olin ručně).

## 7. Lidské brány

`--status` ukáže, co čeká; `--approve definition | style=<preset> | preview` pustí dál; `--reject --note "…"`
vrátí fázi s poznámkou. Tři brány: definice (diff, počet panelů, odhad času: panely × 14 s + smyčky × 155 s, odhad
ceny LLM), styl (kontaktní list; po volbě se `style.chosen` zapíše do definice), finální preview (strip PNG každého
uzlu, trailer, jedno video v cs). `human` verdikty z QA se hromadí a ukážou u nejbližší brány, pipeline na ně
nečeká u každého panelu. Hotová definice s `style.chosen` a `--no-gates` projde bez člověka celá.

## 8. SPARK a běh

Profily `comfy` (SDXL, Wan), `llm` (openclaw), `audio` (ACE-Step, chatterbox), služba `faces` v profilu comfy. Fáze
se seskupí po profilech; `lease` s prioritou z pravidel (webtoon 20) a názvem `<id>: <fáze>`. Odsunutí: klient
dostane `preempted`, fáze uloží stav, po návratu pokračuje od posledního panelu. Ve frontě ComfyUI max. 4 úlohy, aby
šlo odsunutí rychle. Odhad gamebooku 60 panelů + 15 smyček + 40 replik × 12 jazyků: ≈ 15 min SDXL + 40 min Wan +
30 min TTS.

## 9. Etapy pro Opus

Každá etapa končí commitem, zelenými testy a zápisem do sekce Stav.

| Etapa | Obsah | Hotovo, když |
|---|---|---|
| E1 řízení | `internal/pipeline`, `internal/spark`, `internal/story` čte schema 1 i 2 (`panels`, `script`), `story --definition` volá dnešní Python/bash kroky jako subprocess | Archion i `rh_01_santorini` projdou `story` od definice po video, druhý běh neudělá nic |
| E2 odkudkoli | služba faces na SPARKu, studio API (import, pack) na JODĚ, token z env/konfigu, zjišťování dostupnosti | stejný příkaz dojede na MacBooku i M2; `local_strip.sh -p import` smazán |
| E3 autorství | `schema/story.schema.json`, `beats` přes LLM v Go, `story author` s validační smyčkou | z `Prompts/archion.md` vznikne definice, jejíž build dá bit-shodné storyboardy s `gb_archion_*` |
| E4 render v Go | port `render.py`, `comfy.py`, WD14 reseed, QA 6.2–6.5, styletest | guláš `uknedliku` v Go se liší jen seedem; 6.4 odhalí podstrčený cizí obličej |
| E5 obraz a video | `media/` bubliny (shodné s `compose.py` na pixel ± AA), port `animate.py`, shorts + trailer v Go, 6.6, 6.7, 6.11 | `gulas_shorts.py`, `shorts.py` smazané, stejné délky a bubliny |
| E6 jazyky a zvuk | translate v pipeline + 6.8, dub přes AiStack + 6.9, music v Go, ducking, titulky | Archion ve 12 jazycích s dabingem |
| E7 balíček a publish | pack přes studio API + 6.10, PR do webtoon-content a Webtoon, store texty | PR vznikne samo, Director mergne beze změn |
| E8 úklid | smazat nahrazené `m0/*.py`, `local_strip.sh`, `tools/story_defs.py`; `storyboard.json` ven z gitu (odvozený); `docs/pipeline.md` | v `m0/` zbývají jen testy |

E1 první: od ní běží celá cesta a každá další etapa jen nahrazuje jeden subprocess.

## 10. Rozhodnutí a rizika

- **Vlastnictví.** Import, katalog a `webtoon-content` jsou Directorovy. Studio API dává pipeline právo zapisovat do
  DB tokenem studia; to je změna, kterou musí Director odsouhlasit (jinak fáze 10 běží jen u něj).
- **Dabing.** chatterbox-cs není komerčně ověřený (rozhodnutí: na riziko firmy). `dub.enabled: false` a verze
  videa jen s titulky musí fungovat vždy.
- **LLM pro author.** Opus API dá nejlepší definici, ale stojí a není na SPARKu; openclaw zdarma a slabší. Author
  přes API (jednou na příběh), opakované věci lokálně.
- **Wan paměť.** 14B vedle SDXL ≈ 60 GB, nad strop profilu comfy; řeší pořadí fází, i při navazování po pádu.
- **Identita (6.4).** Bez referenčních obrázků bude práh volný; pro série `reference_images` z prvního schváleného
  renderu (IP-Adapter už `render.py -c` umí).
- **Odvozené soubory v gitu.** 236 `storyboard.json` dnes nese i překlady a faces. Dokud E8 neproběhne, build je
  přepisuje jen tam, kde se definice změnila (hash), aby se překlady neztratily.
- **Větvení.** Gamebooky s `choices` nejdou do jednoho videa; shorts vezme nejdelší cestu od `start`
  (`_main-path`), trailer bez omezení.

## Stav

- 2026-11-13: plán napsán. `tools/story_defs.py` vyrobil `story.yaml` pro všechny stripy (schema 2, `panels`),
  každý postaví původní panely 1:1. Gamebooky mají definici v `graph.yaml`. Nic z E1–E8 nezačalo.
