# Webtoon

<!-- Max 80 řádků. Co se nevejde, jde do docs/ a sem jeden odkaz. Veřejné repo: žádné LAN IP, domovské cesty, ID. -->

## Účel
Interaktivní webtoon: autor definuje svět, čtenář volí pokračování, nový díl generuje LLM storyboard + SDXL panely na SPARKu. Flutter čtečka, Go backend, Python prototyp M0.

## Build a test
```
# backend/ (gate z .github/workflows/backend.yml)
test -z "$(gofmt -l .)" && go vet ./... && go test ./...
# app/ (gate z .github/workflows/ci.yml)
flutter analyze --no-fatal-infos && flutter test
```
Integrační testy s DB: `WEBTOON_TEST_DATABASE_URL` (viz `backend/README.md`, Testy).

## Mapa
- `app/` Flutter klient (čtečka, IAP)
- `backend/` Go API + worker pool nad Postgres frontou (`SKIP LOCKED`)
- `m0/` Python prototyp pipeline (zdroj golden testů backendu)
- `data/`, `rules/` světy, příběhy, gamebooky, styly, pravidla tagů
- `deploy/` docker compose pro JODU (DB, API, Caddy, cloudflared), `deploy/voice-worker/` pro SPARK
- `tools/` skripty pro App Store / Play (produkty, IAP, ikony, shorts)
- `skills/`, `store/`, `docs/` skill storyboardu, podklady obchodů, GitHub Pages a dokumentace

## Invarianty
- Jediná databáze je Postgres na JODĚ; Mac se připojuje přes `backend/.env` (vzor `backend/.env.example`). Na Macu žádný Docker ani Postgres.
- Testy nikdy nevolají reálné ComfyUI/WD14, jen `backend/internal/fakes`.
- `backend/data/styles.json` musí být shodný s `data/styles.json`.

## Kam dál
`README.md`, `backend/README.md`, `PACK_FORMAT.md`, `docs/voice-backend.md`, `docs/gamebook.md`, `Prompts/00-WEBTOON_PLAN.md`
