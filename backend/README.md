# Webtoon backend (M1)

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

Příkazy binárky: `serve` (výchozí), `migrate`, `seed [-world f.json] [-styles f.json] [-owner id] [-visibility public]`.
Migrace (embedded, golang-migrate) běží při každém startu `serve` i `seed`.

### Konfigurace (env)

| proměnná | výchozí | |
|---|---|---|
| `WEBTOON_LLM` | `http://192.168.88.66:8080/v1` | OpenAI-kompatibilní endpoint (LiteLLM/vLLM) |
| `WEBTOON_LLM_MODEL` | `openclaw-default` | |
| `WEBTOON_COMFY` | `http://192.168.88.66:8188` | ComfyUI. Služba ho **nikdy nespouští**, jen se ptá `/system_stats` |
| `WEBTOON_WD14` | `http://192.168.88.66:8097` | WD14 tagger (`POST /tag`) |
| `DATABASE_URL` | `postgres://webtoon:webtoon@localhost:5434/webtoon?sslmode=disable` | |
| `MEDIA_DIR` | `./media` | sem se ukládají PNG panelů, servíruje `GET /media/...` |
| `MEDIA_BASE_URL` | `/media` | prefix `image_url` v odpovědích (např. `https://webtoon.ol1n.com/media`) |
| `WORKERS` | `2` | počet worker goroutin (0 = bez workeru) |
| `MODE` | `all` | `all` / `api` / `worker` (víc procesů nad stejnou DB je OK, SKIP LOCKED) |
| `LISTEN_ADDR` | `:8095` | |
| `WEBTOON_BACKOFF` | `5m` | odklad jobu, když LLM / ComfyUI / WD14 neodpovídá |
| `WEBTOON_MAX_ATTEMPTS` | `3` | pokusy při běžné chybě (exponenciální backoff od 30 s) |
| `WEBTOON_SEED`, `WEBTOON_SEED_OWNER` | `false`, `seed` | seed při startu |

## Pipeline (worker)

1. **episode job**: free text projde nejdřív moderací (LLM, JSON verdikt; `kids` = přísnější instrukce, fail-closed).
   Pak storyboard (LLM) → validátor (schéma, id postav/lokací, 6–8 panelů, 2–3 closed + 1 free volba) →
   tagy filtrované proti `data/wd14_tags.json` + EXTRA_TAGS → neznámé fráze jedním LLM voláním přeložené na tagy
   (kandidáti ze slovníku) → rule check (počítá se jen `certain: true`). Po 3 pokusech se přijme schema-valid
   storyboard s `warnings`. Pak se uloží panely a pro každý se zařadí panel job (+ id voleb `c1..c3`, `free`).
2. **panel job**: prompt (pořadí quality → count → character tag_prompt → artist/style → shot → scene → location → SFW,
   odstranění negativů, které koliduje s pozitivem) → ComfyUI (eps/v-pred, IP-Adapter, pokud má postava
   `identity_level=ip_adapter` a referenci v `MEDIA_DIR`) → WD14 safety (`explicit>0.2`, `questionable>0.3`,
   max 2 reseedy, pak panel `failed`, obrázek se neuloží) → PNG do `MEDIA_DIR/episodes/<ep>/pNN_<seed>.png` →
   `panels_ready++`, identity recall per postava.
3. Když jsou všechny panely hotové, `state_diff` se aplikuje na kampaň (+ `canon_progress`), uloží se snapshot
   stavu u epizody a epizoda je `ready`. Pokud selžou všechny panely, epizoda je `failed`.

Výpadek LLM (běží 13–07) nebo ComfyUI/WD14 (07–13): job dostane `run_after = now + 5 min`, attempt se nepočítá,
epizoda zůstává `queued`/`generating` a v `error` je "waiting: …". Epizoda kvůli rozvrhu nikdy neselže.

## API

Auth je zatím stub: hlavička `X-User-ID` (placeholder pro Ol1nLLM účty). Bez ní mutace vrací 401.

```
POST   /worlds                          {title, style_id, synopsis, tone, audience, language, visibility, bible, canon, permissions, characters[], locations[]}
GET    /worlds?visibility=public        veřejné + vlastní
GET    /worlds/{id}                     vč. characters, locations
PATCH  /worlds/{id}                     jen owner
POST   /worlds/{id}/characters          owner; ostatní jen když permissions.can_create_character (role player_created)
POST   /worlds/{id}/locations           jen owner
GET    /worlds/{id}/stats               jen owner: počty, rozložení voleb (by_kind, by_choice), hloubka kampaní, canon
POST   /campaigns                       {world_id, player_character_id?, title?, start?=true} → 201 + first_episode_id
GET    /campaigns/{id}                  hráč nebo owner světa; state, canon_progress, seznam epizod
POST   /campaigns/{id}/episodes         jen hráč; {choice_id} | {free_text} → 202 {episode_id}
GET    /episodes/{id}                   status, panels_ready/total, panels[] (image_url, bubbles, sfx, gap_after…), choices
PATCH  /episodes/{id}/panels/{n}        jen hráč; {"bubbles": [...]} (bez regenerace) | {"regenerate": true} → 202
GET    /media/{path}                    soubory z MEDIA_DIR
GET    /health
```

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
(čisté funkce z `m0/*.py`); při změně promptů
v prototypu je potřeba ho vygenerovat znovu.

## Struktura

```
cmd/webtoon/            main: serve | migrate | seed
data/                   kopie ../data (world_m0, styles, wd14_tags), embedded
internal/api/           HTTP handlery, auth stub, /media
internal/comfy/         ComfyUI klient + workflow (port m0/comfy.py)
internal/config/        env
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
- Generování `tag_prompt` postavy LLM (`m0/gen_character.py`), upload referenčních obrázků, character sheet.
  `reference_images` jsou cesty relativní k `MEDIA_DIR`.
- Detekce bbox postav (ocásky bublin), komprese timeline, RAG nad epizodami, větvení kampaní (pole
  `branch_parent_episode_id` připravené).
- Moderace výstupu je jen rule check (publikum) + WD14. Samostatné moderační volání nad texty bublin chybí.
- Úklid starých obrázků po regeneraci panelu.
