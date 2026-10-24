# Webtoon backend (M1–M3)

Go služba pro interaktivní webtoon (WEBTOON_PLAN §2, §3, §5, §7): HTTP API a worker pool nad Postgres
job tabulkou. Pipeline je port ověřeného Python prototypu `../m0/`. Systémové prompty, validace, filtr tagů
proti WD14 slovníku, prompt builder, WD14 safety a merge `state_diff` jsou stejné. Testy to kontrolují
golden výstupy, které vznikly spuštěním Python funkcí (`internal/testdata/golden_m0.json`).

## Spuštění

```sh
docker compose up -d db                       # Postgres 16 na localhost:5434
go run ./cmd/webtoon seed                     # import data/world_m0.json + styles.json (owner "seed")
go run ./cmd/webtoon serve                    # API :8095 + 2 workery (MODE=all)
# nebo všechno v Dockeru (seed při startu, owner "author"):
docker compose up --build
```

Příkazy binárky: `serve` (výchozí), `migrate`, `seed [-world f.json] [-styles f.json] [-owner id] [-visibility public]`,
`import-demo [-campaign id | -world w_skyisles -player player] [-character id] [-variant 0] <storyboard.json> <panel_dir>`,
`translate [...]`, `export-pack [...]` (viz níže).

`import-demo` vloží hotový díl z výstupů M0 bez volání LLM/ComfyUI (pro vývoj čtečky): storyboard →
epizoda `ready` s panely `ready`, obrázky `pNN_s<variant>.png` (+ seed/prompt z `meta.json`, pokud je)
se zkopírují do `MEDIA_DIR/episodes/<ep>/`, `state_diff` se aplikuje na kampaň. Bez `-campaign` založí
novou kampaň hráče `-player`; s `-campaign` přidá další díl (kampaň nesmí mít díl ve frontě).

```sh
go run ./cmd/webtoon import-demo -player player ../out/dev/storyboard_ep1.json ../out/2026-10-17/ep1_noob_plain
```
Migrace (embedded, golang-migrate) běží při každém startu `serve` i `seed`.

### Export balíčků (`export-pack`)

`webtoon export-pack` postaví offline balíček obsahu podle `../PACK_FORMAT.md` z DB + `MEDIA_DIR`
(DB jen čte, migrace nespouští). Panely PNG převede na WebP q85 (`cwebp`, musí být v PATH:
`brew install webp`), smyčky zkopíruje jako `pNN_loop.webp`, obálka příběhu je p00 prvního dílu
oříznutý na střed a zmenšený na 416×608. Díly bere v pořadí `idx` a končí u prvního, který není
`ready` nebo má panel bez obrázku; příběh bez hotového dílu vynechá; svět `w_lxf_*` odmítne.
JSON dílu je přesně `GET /episodes/{id}` (`internal/episodejson`, sdílené s API) bez polí
`seed`, `identity_score`, `error`, `video_error`, `estimate_seconds`, `created_at`, `updated_at`.
`languages` příběhu = zdrojový jazyk světa + průnik překladů všech dílů; `title_i18n` příběhu se
bere z prvního dílu, pokud má kampaň stejný název.

```sh
# výběr příběhů: -campaigns cp_a,cp_b | -worlds w_x,w_y | -world-prefix w_rb_,w_rc_ (lze kombinovat worlds + prefix)
#                | -starter-pick ../data/starter_showcase.yaml (jen starter: svět → jeho první kampaň, kontrola stylu)
# starter: jeden zip (bez dělení), katalogu se nedotkne; 15 příběhů výkladní skříně stylů
go run ./cmd/webtoon export-pack -starter ../app/assets/packs/starter.zip -starter-pick ../data/starter_showcase.yaml
# placený balíček do checkoutu webtoon-content: id kids-1, produkt pack_kids_1, release pack-kids-1-v1,
# zipy releases/pack-kids-1-v1/kids-1-a.zip + -b.zip, covers/, catalog.json (schema 2, version++)
go run ./cmd/webtoon export-pack -out ../../webtoon-content -type kids -n 1 -world-prefix w_lx_k2_
# → vypíše (nespouští):
#   gh release create 'pack-kids-1-v1' '…/releases/pack-kids-1-v1/kids-1-a.zip' '…/kids-1-b.zip' \
#     --repo 'lioilsources/webtoon-content' --title 'Pro děti 1 v1' --notes 'kids-1 v1: 50 stories in 2 part(s), …'
# bundly / typy / base_urls z ../rules/base/pack.yaml do katalogu (bez DB)
go run ./cmd/webtoon catalog-bundles -out ../../webtoon-content
```

Typ balíčku (`-type`, `../rules/base/pack.yaml types`) je jinak typ vybraných světů: klíč `profile` ve
`data/stories/<id bez w_>/world.json` (superhero), jinak `audience` (kids → kids, adult → harlequin); světy
různých typů bez `-type` export odmítne. `-n` odvodí id, produkt, název a release tag z `naming` v pack.yaml
(explicitní `-pack`, `-product`, `-title`, `-release-tag` mají přednost). V katalogu se části jmenují vždy
`a`, `b`, … po `part_size` (25) příběhů (každá je samostatný zip se svým `pack.json`, stejné `id`, pole `part`);
placený balíček má `pack_size` (50) příběhů. Zipy jdou do `<out>/releases/<tag>/` — necommitují se, nahraje je
vypsaný `gh release create` (export ho nikdy nespouští). Existující zip se nepřepisuje (nová verze =
`-version N+1` = nový release tag; `-force` přepíše). Další volby: `-free` místo produktu, `-base-url`
(přepíše `base_urls.pages`), `-workers` (výchozí počet CPU). Na konci vypíše za každou část počty
příběhů/dílů/panelů/smyček, bajty a sha256, na stderr poznámky o zkrácených a vynechaných příbězích.

### Konfigurace (env)

| proměnná | výchozí | |
|---|---|---|
| `WEBTOON_LLM` | `http://192.168.88.66:8080/v1` | OpenAI-kompatibilní endpoint (LiteLLM/vLLM) |
| `WEBTOON_LLM_MODEL` | `openclaw-default` | |
| `WEBTOON_COMFY` | `http://192.168.88.66:8188` | ComfyUI. Služba ho **nikdy nespouští**, jen se ptá `/system_stats` |
| `WEBTOON_WD14` | `http://192.168.88.66:8097` | WD14 tagger (`POST /tag`) |
| `WEBTOON_IMAGE_API` | – | AiStack Image API (`https://llm.ol1n.com`); nastavené = místo `WEBTOON_COMFY` a `WEBTOON_WD14` |
| `WEBTOON_CF_ACCESS_ID`, `WEBTOON_CF_ACCESS_SECRET` | – | service token Cloudflare Access pro Image API i LLM za `llm.ol1n.com` |
| `WEBTOON_LANGS` | 12 jazyků Lexify | cílové jazyky překladu bublin (`en,de,…`, `none` = vypnuto); zdrojový jazyk světa se přeskočí |
| `DATABASE_URL` | `postgres://webtoon:webtoon@localhost:5434/webtoon?sslmode=disable` | |
| `MEDIA_DIR` | `./media` | sem se ukládají PNG panelů, servíruje `GET /media/...` |
| `MEDIA_BASE_URL` | `/media` | prefix `image_url` v odpovědích (např. `https://webtoon.ol1n.com/media`) |
| `WORKERS` | `2` | počet worker goroutin (0 = bez workeru) |
| `MODE` | `all` | `all` / `api` / `worker` (víc procesů nad stejnou DB je OK, SKIP LOCKED) |
| `LISTEN_ADDR` | `:8095` | |
| `WEBTOON_BACKOFF` | `5m` | odklad jobu, když LLM / ComfyUI / WD14 neodpovídá |
| `WEBTOON_MAX_ATTEMPTS` | `3` | pokusy při běžné chybě (exponenciální backoff od 30 s) |
| `WEBTOON_CORS_ORIGINS` | – | origins pro Flutter web, čárkami (`http://localhost:8096`, `*`); prázdné = bez CORS |
| `WEBTOON_SEED`, `WEBTOON_SEED_OWNER` | `false`, `seed` | seed při startu |

Mimo domácí síť nastav `WEBTOON_IMAGE_API`: worker pak posílá grafy do sdílené fronty ComfyUI na SPARKu
(`internal/imageq`, kontrakt `AiStack/services/gen-queue/IMAGE-API.md`) a WD14 volá přes `/v1/image/tag`.
Referenční obrázky jdou s jobem v base64. Job zadaný mimo okno comfy ve frontě počká; worker mezitím
dostane „unavailable“ a po `WEBTOON_BACKOFF` se přes stejný `client_ref` (hash grafu) připojí k témuž jobu.

## Pipeline (worker)

1. **episode job**: free text projde nejdřív moderací (LLM, JSON verdikt; `kids` = přísnější instrukce, fail-closed).
   Pak storyboard (LLM) → validátor (schéma, id postav/lokací, 6–8 panelů, 2–3 closed + 1 free volba) →
   tagy filtrované proti `data/wd14_tags.json` + EXTRA_TAGS → neznámé fráze jedním LLM voláním přeložené na tagy
   (kandidáti ze slovníku) → rule check (počítá se jen `certain: true`). Po 3 pokusech se přijme schema-valid
   storyboard s `warnings`. Pak se uloží panely a pro každý se zařadí panel job (+ id voleb `c1..c3`, `free`).
2. **panel job**: prompt (pořadí quality → count → character tag_prompt → artist/style → shot → scene → location → SFW,
   odstranění negativů, které koliduje s pozitivem) → ComfyUI (eps/v-pred, IP-Adapter, pokud má postava
   `identity_level=ip_adapter` a referenci v `MEDIA_DIR`) → WD14 safety podle `audience` světa (teen: `explicit>0.2`, `questionable>0.3`;
   kids navíc `sensitive>0.5`, tj. přiléhavé/odhalující oblečení; adult má prahy teen a navíc reseed na WD14 tagy `cleavage`/`large breasts` > 0.8, `shirtless` > 0.5, `bed` > 0.7 apod. (`wd14.AdultTagLimits`), svět pro dospělé je taky SFW), max 2 reseedy, pak panel `failed`, obrázek se neuloží) → PNG do `MEDIA_DIR/episodes/<ep>/pNN_<seed>.png` →
   `panels_ready++`, identity recall per postava.
   - **Záběr řídí tagy postavy** (port `m0/prompts.py`): close-up vynechá design tagy spodní poloviny
     (`LOWER_RE`: shorts, skirt, pants, pantyhose, thighhighs, legwear, socks, footwear, boots, shoes) a nechá
     jen první 3 tagy lokace; medium a over-shoulder vynechají obuv (`FEET_RE`). Filtr scénických tagů pořád
     zná celý design. Shot tagy close-upu jsou vážené: `(close-up:1.3), (portrait:1.2), face focus`.
     Identity recall počítá jen tagy, které jsou v záběru vidět.
   - **Šatník** (romantické světy): postava má `base` (tagy bez oblečení), `outfits` (`{"default": …, "dinner": …}`)
     a `photo` (popis větou). Panel vybere oblečení přes `characters[].outfit` (jméno z `outfits`, nebo tagy přímo).
     Bez `outfit` platí `tag_prompt`. Publikum `kids`/`adult` přidá `kids_negative`/`adult_negative` ze styles.json.
     Preset může mít stylové LoRA `"loras": [[soubor, síla], …]`, workflow je řetězí za checkpoint (model i CLIP), stejně jako `m0/comfy.py`.
   - **Fotorealistické presety** (`"natural": true`, Juggernaut, RealVis, CyberRealistic) dostanou prompt větami:
     dvojice jde na začátek s vahou 1.3 („a romantic couple … together in frame“), každá postava je `photo` + „wearing <outfit>“,
     záběr z `natural_shot`. Jinak modely druhou postavu vynechávají.
   - **IP-Adapter** jen u postav s `identity_level=ip_adapter` (výchozí je `prompt`, výsledek M0). Postava
     může mít `ip_adapter: {preset, weight, end_at}`. Výchozí hodnoty jsou z prototypu
     (`PLUS (high strength)`, 0.6, 0.8). Pro výřez obličeje funguje `PLUS FACE (portraits)` s vahou 0.3–0.4.
     Použije se první obrázek z `reference_images` první takové postavy v panelu.
3. Když jsou všechny panely hotové, `state_diff` se aplikuje na kampaň (+ `canon_progress`), uloží se snapshot
   stavu u epizody a epizoda je `ready`. Pokud selžou všechny panely, epizoda je `failed`.

4. **sheet job** (character sheet, port `render.py --sheet`): panel `sheet` (celá postava, bílé pozadí, bez
   lokace, bez IP-Adapteru) → N seedů (výchozí 4, max 8; seed = deterministický základ + k), každý s WD14
   safety reseedy jako panel → bezpečné PNG do `MEDIA_DIR/characters/<world>/<char>/sheet_<id>_<k>_<seed>.png`.
   Nejlepší kandidát (nejvyšší identity recall) se přidá na konec `reference_images` postavy. Kandidáti se
   ukládají průběžně, takže job přerušený výpadkem ComfyUI pokračuje tam, kde skončil. Když jsou všichni
   kandidáti unsafe, sheet je `failed`.

Výpadek LLM (běží 13–07) nebo ComfyUI/WD14 (07–13): job dostane `run_after = now + 5 min`, attempt se nepočítá,
epizoda zůstává `queued`/`generating` a v `error` je "waiting: …". Epizoda kvůli rozvrhu nikdy neselže.

### Překlady bublin

Jako Lexify: každý text je v obsahu ve všech jazycích a čtečka jen přepíná. Hotový díl dostane job
`translate_episode`: jedno volání LLM (`response_format: json_schema`, thinking vypnutý) na každý cílový
jazyk, v něm titulek, všechny bubliny a volby, aby jména a tón seděly. Překlady leží vedle originálu
(`bubbles[].i18n`, `choices[].i18n`, `episodes.title_i18n`), originál zůstává zdrojem pravdy. Úprava textu
bubliny v editoru zahodí překlady té bubliny a zařadí díl k přeložení znovu; nezměněné texty si je
nechají. LLM běží jen v okně 13–07, mimo něj job čeká (backoff), nic neselže. `GET /episodes/{id}` vrací
`source_language` a `languages` (jazyky, do kterých je přeložený celý díl).

    webtoon translate -all                  # zařadí překlad všech hotových dílů (hotové jazyky přeskočí)
    webtoon translate -episode ep_… -langs en,ja -force -inline   # přeloží hned tady, bez workeru

### Pohyblivá políčka (smyčka 1–3 s)

`PLAN-motion-panels.md`. Storyboard (LLM) smí označit nejvýš 2 panely `"animate": true` s `"motion"`
(anglický Wan prompt ≤ 15 slov, „subject motion + ambient + static camera“; validátor smyčku bez varování zruší
u dvojic, polibků a zakázaných akcí, `storyboard.CheckMotion`). Instrukce je k systémovému promptu připojená
až v `Generate`, takže `SystemPrompt` dál sedí na prototyp. Po hotovém stillu zařadí panel job
`panel_video`: still se nahraje do ComfyUI a `comfy.VideoWorkflow` ho pustí přes **Wan 2.2 I2V 14B + Lightning**
jako `WanFirstLastFrameToVideo` se stejným prvním i posledním snímkem (smyčka bez střihu), 480×704 / 704×480,
16 fps, 17/33/49 snímků. Výstup je animovaný WebP (`SaveAnimatedWEBP`) + tři snímky (první, prostřední, poslední)
pro WD14 se stejnými prahy jako still; unsafe → reseed, po `MaxReseed` `video_status=failed`, still zůstává.
WebP leží v `MEDIA_DIR/episodes/<ep>/pNN_video_<seed>.webp` a API ho vrací jako `video_url` vedle `image_url`.
Editor: `PATCH /episodes/{id}/panels/{n}` s `{"animate", "motion", "loop_seconds", "reseed_video"}`
(`estimate_seconds` ≈ 100/155/200 s), `animate: false` smyčku zapomene (soubor zůstane). Přegenerovaný still
dostane novou smyčku. ComfyUI mimo okno → backoff jako u panelů.

## API

Auth je zatím stub: hlavička `X-User-ID` (placeholder pro Ol1nLLM účty). Bez ní mutace vrací 401.

```
POST   /worlds                          {title, style_id, synopsis, tone, audience, language, visibility, bible, canon, permissions, characters[], locations[]}
GET    /worlds?visibility=public        veřejné + vlastní
GET    /worlds/{id}                     vč. characters, locations
PATCH  /worlds/{id}                     jen owner
GET    /worlds?owner=me                 jen vlastní světy (záložka „Tvořit“)
POST   /worlds/{id}/characters          owner; ostatní jen když permissions.can_create_character (role player_created)
POST   /worlds/{id}/locations           jen owner
GET    /worlds/{id}/stats               jen owner (dashboard), viz níže
GET    /style_presets                   presety stylu pro picker (+ preview_url, pokud existuje MEDIA_DIR/styles/<id>.png|jpg|webp)

PATCH  /worlds/{id}/characters/{cid}    owner (hráč jen svou player_created postavu, bez změny role); libovolná podmnožina
                                        name, role, count_tag, description, personality, speech_style, tag_prompt,
                                        reference_images (jen přeřadit/odebrat), identity_level, identity_asset, ip_adapter (null = smazat)
DELETE /worlds/{id}/characters/{cid}    204; 409, když je to hráčská postava nějaké kampaně
POST   /worlds/{id}/characters/{cid}/tag_prompt   {description?} → {tags, tag_prompt, dropped, unknown, replaced, notes}; NEukládá
POST   /worlds/{id}/characters/{cid}/sheet        {seeds?=4} → 202 sheet; 409, když se jiný sheet ještě kreslí
GET    /worlds/{id}/characters/{cid}/sheets       {sheets: [...]} nejnovější první
GET    /sheets/{id}                     owner světa nebo kdo sheet zadal: status, done/seeds, images[{seed, image_url, recall, missing, status}], best, best_image_url
POST   /worlds/{id}/characters/{cid}/references   multipart, pole "file", PNG/JPEG ≤ 8 MiB → 201 postava
PATCH  /worlds/{id}/locations/{lid}     jen owner; name, description, tag_prompt, reference_images, mood
DELETE /worlds/{id}/locations/{lid}     204; odebere ji i z permissions.allowed_locations
POST   /worlds/{id}/locations/{lid}/tag_prompt    jako u postav (vlastní system prompt pro scenérii)
POST   /worlds/{id}/locations/{lid}/references    jako u postav
POST   /campaigns                       {world_id, player_character_id?, title?, start?=true} → 201 + first_episode_id
GET    /campaigns?world_id=             vlastní kampaně (world_title, počet dílů, stav posledního dílu), nejnovější aktivita první
GET    /campaigns/{id}                  hráč nebo owner světa; state, canon_progress, seznam epizod
POST   /campaigns/{id}/episodes         jen hráč; {choice_id} | {free_text} → 202 {episode_id}
GET    /episodes/{id}                   status, panels_ready/total, panels[] (image_url, bubbles, sfx, gap_after…), choices
PATCH  /episodes/{id}/panels/{n}        jen hráč; {"bubbles": [...]} (bez regenerace) | {"regenerate": true} → 202
GET    /media/{path}                    soubory z MEDIA_DIR
GET    /health
```

Postavy a lokace v odpovědích mají navíc `reference_urls` (URL k `reference_images`). `tag_prompt` se při
uložení normalizuje (booru zápis, bez prázdných a duplicitních tagů).

**Generování `tag_prompt`** (port `m0/gen_character.py`): až 3 pokusy LLM (teplota 0.3), po každém repair pass
(0.2), který neznámé tagy (mimo WD14 slovník + EXTRA_TAGS) přeloží na existující. Vyhrává pokus s nejmenším
počtem neznámých tagů. `dropped` jsou tagy z LLM, které po opravě zmizely úplně (UI je ukáže šedě),
`replaced` je mapa původní tag → náhrady, `unknown` je druhá hodnota `make_tag_prompt` (paritní test).
LLM mimo rozvrh → 503 `llm unavailable: …`. Autor výsledek doladí a uloží přes `PATCH … {tag_prompt}`.

**Kánon editor**: `PATCH /worlds/{id} {canon: {nodes: [{id, text}], constraints: [...]}}` nahradí celý kánon
v daném pořadí. Uzly si nechávají id (odkazuje na ně `canon_progress`), nové bez id dostanou `n1`, `n2`, …;
prázdný text nebo duplicitní id = 400, prázdné constraints se zahodí. `permissions.allowed_locations` musí
obsahovat existující lokace, `max_episodes ≥ 0`. `bible` je volný objekt (editor upravuje `rules` a `factions`,
oba seznamy textů). Do storyboard promptu jde z bible jen `rules` (parita s prototypem).

**Stats** (`GET /worlds/{id}/stats`): `campaigns, players, episodes, episodes_ready, episodes_failed,
panels_ready, player_created_characters`, `choices {by_kind, by_choice}`, `campaign_depth [{episodes, campaigns}]`,
`canon_reached {node: campaigns}`, `stopped_at [{episode, campaigns}]` (index posledního dílu každé kampaně,
0 = zatím bez dílu), `choices_by_episode [{episode, total, choices {c1, c2, free…}}]` (volba na konci dílu
`episode`), `player_created [{id, name, owner_id, description, created_at}]`.

První epizoda kampaně má jako premisu první kanonický uzel světa (jinak synopsis). Další epizody navazují
na poslední `ready` epizodu stejným textem premisy jako `m0/state.py`. Když epizoda selže (např. moderace),
hráč může poslat novou volbu.

## Testy

```sh
go vet ./... && go test ./...                 # unit + e2e worker (in-memory store, httptest fakes)
docker compose up -d db
WEBTOON_TEST_DATABASE_URL='postgres://webtoon:webtoon@localhost:5434/webtoon?sslmode=disable' \
  go test ./internal/integration/             # API + worker + Postgres (vlastní dočasná DB)
WEBTOON_LLM_SMOKE=1 go test -run Smoke -v ./internal/storyboard/   # 1 pokus proti reálnému LLM (≤3 volání)
```

Testy nikdy nevolají reálné ComfyUI/WD14. Fakes jsou v `internal/fakes`.
`internal/testdata/golden_m0.json` generuje `python3 -B internal/testdata/gen_golden.py internal/testdata/golden_m0.json`
(čisté funkce z `m0/*.py`: prompty všech záběrů vč. sheetu, `render.identity`, `comfy.workflow` s IP-Adapterem,
`gen_character.make_tag_prompt` se skriptovaným LLM); při změně promptů v prototypu je potřeba ho
vygenerovat znovu. `data/styles.json` je kopie `../data/styles.json` (musí být shodná).

## Struktura

```
cmd/webtoon/            main: serve | migrate | seed | import-demo | translate | export-pack | catalog-bundles
data/                   kopie ../data (world_m0, styles, wd14_tags), embedded
internal/api/           HTTP handlery, auth stub, /media; authoring.go = nástroje autora (M3)
internal/chargen/       tag_prompt postavy/lokace z popisu (port m0/gen_character.py)
internal/comfy/         ComfyUI klient + workflow (port m0/comfy.py)
internal/config/        env
internal/demo/          import-demo: hotový díl z výstupů M0 (storyboard + PNG)
internal/episodejson/   tvar GET /episodes/{id}, sdílený API a balíčky
internal/pack/          export-pack: výběr příběhů, pack.json, cwebp, zip, catalog.json (PACK_FORMAT.md)
internal/db/            migrace (embedded) + queries.sql; dbq/ = vygenerované sqlc (`sqlc generate`)
internal/domain/        typy světa, stylů, storyboardu
internal/llm/           OpenAI-kompatibilní JSON klient
internal/prompt/        prompt builder (port m0/prompts.py)
internal/state/         story state + apply_diff (port m0/state.py)
internal/storyboard/    system prompt, validátor, rule check, generate, moderace, premisa (port m0/storyboard.py)
internal/store/         Postgres store (implementuje worker.Store)
internal/tags/          booru tagy, WD14 slovník, překlad frází (port m0/common.py)
internal/wd14/          WD14 klient, safety, identity recall
internal/worker/        job loop, episode/panel joby, backoff
internal/fakes/, testutil/, testdata/, integration/   testy
```

## Co není hotové

- Export (`GET /episodes/{id}/export?fmt=png|pdf`), push notifikace, kredity (jen `credits_cost = počet panelů`).
- Skutečná auth (Ol1nLLM účty). `X-User-ID` se bere tak, jak přijde.
- `director: {...}` v POST episodes (přidat/odebrat postavu, změnit lokaci). `permissions` se zatím vynucuje
  jen pro tvorbu postav, `allowed_locations` (validátor) a `max_episodes`.
- `reference_images` jsou cesty relativní k `MEDIA_DIR`. Smazání postavy/lokace nebo odebrání reference
  nemaže soubory. Upload nemá antivir ani přepočet velikosti obrázku.
- LoRA (`identity_level=lora`, `identity_asset`) se jen ukládá, worker ji nepoužívá. Reference lokací se
  zatím do ComfyUI neposílají (IP-Adapter/img2img pro establishing shoty).
- `bible.factions` ani jiné klíče bible kromě `rules` se do storyboard promptu nedostanou (parita s prototypem).
- Řazení postav a lokací (sloupec `position`) nemá endpoint.
- Detekce bbox postav (ocásky bublin), komprese timeline, RAG nad epizodami, větvení kampaní (pole
  `branch_parent_episode_id` připravené).
- Moderace výstupu je jen rule check (publikum) + WD14. Samostatné moderační volání nad texty bublin chybí.
- Úklid starých obrázků po regeneraci panelu.
