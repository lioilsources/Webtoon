# Vlastní hlas hráče: serverová část

Serverová strana funkce „Tvůj hlas“ (IAP `voice_clone`) pro export videa s dabingem. Plán appky
a kontrakt jsou v `docs/VOICE_EXPORT_PLAN.md` (PR #22). Kód: `backend/internal/voice` (API na JODĚ),
`backend/internal/voice/receipt` (ověření nákupu), `backend/internal/voiceworker` (worker na SPARKu).

## Jak to funguje

```
telefon ──HTTPS──▶ webtoon-api.ol1n.com (JODA: API + fronta voice_tasks + šifrovaná data)
                         ▲   │
             worker token│   │ GET pending / claim / PUT line
                         │   ▼
                    voice-worker (SPARK, Docker) ──lease tts──▶ spark-broker :8100
                         │
                         └──▶ AiStack audio :8093 (chatterbox-cs: /v1/audio/voices, /v1/audio/tts)
```

- Telefon mluví jen s API na JODĚ (anonymní token zařízení), nikdy se SPARKem.
- API nikdy nečeká na GPU. Úloha čeká ve frontě a app vidí `queued`.
- Worker na SPARKu se každých 30 s zeptá API, jestli je práce. Teprve když je, zažádá brokera
  o lease služby `tts` (projekt `webtoon`, priorita 20). Pak bere úlohy po jedné a po 2 min prázdné
  fronty lease vrátí (`done` s metrikami `lines`/`voices`). Když broker chce GPU zpátky (`draining`,
  zamítnuté prodloužení), worker dokončí rozdělanou úlohu a lease vrátí. Když lease zmizí, úloha
  se vrátí do fronty.
- Vzor je převzatý z Hajánka (`forge worker`): klient AiStack audio, kontrola záběrů (useknutý,
  přetažený, tichý záběr se opakuje s jiným seedem), dělení na věty, `retry` při 503/5xx/síti.
  Navíc je tu lease brokeru, Hajánkův worker ho nedrží.
- Klon: `POST /v1/audio/voices` s `voice_id=toonfork-<uuid>`, `rights=own`, `source=toonfork-app`,
  `language=cs`. Řádky: `POST /v1/audio/tts` s `engine=chatterbox`, `language=cs`,
  `commercial_only=false`, wav. Worker věty spojí (mezera 0,3 s), ořízne ticho na začátku a konci,
  provede dvouprůchodový `loudnorm` na −16 LUFS (TP −1,5) a uloží AAC 96 kb/s mono 48 kHz `.m4a`.

## API (`https://webtoon-api.ol1n.com`)

Auth hráče: `Authorization: Bearer <token>` z `POST /v1/player/devices`. Server drží jen sha256
tokenu. Cizí nebo smazaný hlas či job vrací `404`.

| Metoda | Cesta | Popis |
|---|---|---|
| POST | `/v1/player/devices` | `{platform?: ios\|android}` → `201 {device_id, token}`; limit 10/h na IP |
| DELETE | `/v1/player/devices/me` | smaže zařízení i jeho hlas → `204` |
| POST | `/v1/player/voices` | multipart: `sample` (m4a/wav, 5–30 s, ≤ 5 MB), `consent=true`, `consent_text`, `receipt`, volitelně `consent_version`, `platform` → `201 {voice_id, status: "queued", created_at}` |
| GET | `/v1/player/voices/{id}` | `{voice_id, status: queued\|ready\|failed, error?, created_at}` |
| DELETE | `/v1/player/voices/{id}` | hned smaže vzorek i řádky, zařadí smazání hlasu v AiStacku → `204` |
| POST | `/v1/player/voices/{id}/lines` | `{lang: "cs", lines: [{key, text}]}`, nejvýš 200 řádků po 300 znacích → `202 {job_id, status}` |
| GET | `/v1/player/jobs/{job_id}` | `{job_id, status: queued\|running\|done\|failed, lang, done, total, lines: [{key, url, duration_s}], missing?, error?}` |
| GET | `/v1/player/lines/{voice_id}/{hash}.m4a?exp=&sig=` | podepsaná URL řádku (bez tokenu), platí 1–1¼ h |

- `receipt`: na iOS **StoreKit 2 signed transaction (JWS)**, na Androidu purchase token z Play.
  Bez `platform` server pozná JWS sám, jinak bere Play.
- Řádky jsou idempotentní. Klíč cache je `sha256(voice_id 0x1f lang 0x1f text)`, text po NFC
  a sloučení mezer. Stejný text má stejný soubor a v rámci 15min okna i stejnou URL. Stejný
  požadavek, který ještě čeká, vrátí týž `job_id`. Když jsou všechny řádky v cache, job je hned `done`.
- `lines` v jobu obsahuje hotové řádky i během `running`. Po `done`/`failed` jsou v `missing` klíče,
  které se nepovedly. Ty app přečte systémovým hlasem.
- Denní kvóta počítá jen nově generované řádky (výchozí 300 na zařízení a den UTC). Řádky z cache
  ani opakovaný požadavek se nepočítají. Při chybě se kvóta nevrací.

Chybové kódy (`{"error": kód, "message": text}`):

| HTTP | `error` | kdy |
|---|---|---|
| 400 | `invalid_request` | chybí/špatné pole, duplicitní `key`, prázdný text |
| 400 | `consent_required` | `consent` není `true` |
| 400 | `sample_invalid` | nečitelné audio, délka mimo 5–30 s |
| 400 | `too_many_lines`, `line_too_long`, `unsupported_lang` | limity řádků, jazyk mimo `VOICE_LANGS` (výchozí `cs`) |
| 401 | `unauthorized` | chybí nebo neznámý token |
| 402 | `receipt_invalid` | nákup ověřen a odmítnut (jiný bundle/produkt, refund, cizí podpis) |
| 403 | `receipt_in_use` | týž nákup už má hlas na 3 zařízeních (`VOICE_RECEIPT_MAX_DEVICES`) |
| 403 | `url_expired` | podepsaná URL řádku je neplatná nebo prošlá; stačí znovu `GET /jobs/{id}` |
| 404 | `not_found` | |
| 409 | `voice_exists` | zařízení už hlas má (1 hlas na zařízení) |
| 409 | `voice_not_ready`, `voice_failed` | řádky pro hlas, který se ještě připravuje nebo selhal |
| 413 | `sample_too_large` | |
| 415 | `sample_format` | vzorek není m4a ani wav |
| 429 | `quota_exceeded` | denní kvóta; navíc `limit`, `used`, `requested`, `resets_at` |
| 429 | `rate_limited` | registrace zařízení |
| 503 | `receipt_verification_unavailable` | server nemůže nákup ověřit (chybí údaje, obchod nedostupný, test režim na produkci) |
| 503 | `voice_unavailable` | na serveru chybí `VOICE_DATA_KEY` |

Workerové API (`/v1/worker/*`, `Authorization: Bearer $VOICE_WORKER_TOKEN`): `GET voice-tasks/pending`,
`POST voice-tasks/claim {worker}` (`204` = nic), `POST voice-tasks/{id}/heartbeat`,
`POST voice-tasks/{id}/complete {worker, ok, error, retry}`, `GET voices/{id}/sample`,
`PUT voices/{id}/lines/{hash}` (m4a, `X-Duration-S`, `X-Lang`). `409 lease_lost` znamená, že úloha
byla zrušena (hlas se maže) nebo převzata. `retry` vrátí úlohu do fronty s odkladem 30 s až 10 min.
Po 20 pokusech úloha selže.

## Ověření nákupu

- **App Store**: offline. Server kontroluje podpis JWS (ES256), řetězec `x5c` až po připnutý
  Apple Root CA - G3 (otisk SHA-256 `63:34:3A:…:91:79`, hlídá test), značky Apple v listovém
  a mezilehlém certifikátu, `bundleId`, `productId = voice_clone`, `revocationDate` (refund)
  a prostředí (`Production` a `Sandbox`, protože App Review i TestFlight nakupují v sandboxu).
- **Google Play**: `purchases.products.get` přes Play Developer API se servisním účtem (JWT bearer,
  bez SDK). `purchaseState` musí být 0. Bez souboru se servisním účtem Play nákupy selžou.
- **Fail closed**: chybějící údaje nebo nedostupný obchod vrací `receipt_verification_unavailable`.
  Žádný obchvat neexistuje.
- **Testy**: `VOICE_RECEIPT_MODE=test` přijme `receipt=test:<id>`. Na produkčním hostu
  (`webtoon-api.ol1n.com`, `VOICE_PRODUCTION_HOSTS`) se ten režim nikdy nezapne. Platí to pro hlavičku
  `Host` i pro `VOICE_PUBLIC_URL`. Server zaloguje varování a všechny nákupy odmítne.

## Jaká data se ukládají a jak dlouho

| Data | Kde | Jak dlouho |
|---|---|---|
| Vzorek hlasu (biometrie) | JODA, `~/deploy/Webtoon/voice-data/voices/<id>/sample.*.enc`. AES-256-GCM, klíč z `VOICE_DATA_KEY`, cesta jako AAD, soubory 0600 | do smazání hlasu; automaticky po 180 dnech bez použití (`VOICE_RETENTION_DAYS`) |
| Hlas v AiStacku (referenční wav) | SPARK, úložiště audio služby, `toonfork-<id>` | smaže ho worker hned po smazání hlasu |
| Vygenerované řádky | JODA, `voice-data/voices/<id>/lines/*.m4a.enc`, šifrované | se hlasem |
| Záznam souhlasu: `consent_text`, sha256, verze, čas | Postgres `player_voice_consents` | 365 dní po smazání hlasu jako doklad souhlasu (`VOICE_CONSENT_RETENTION_DAYS`); bez biometrie |
| Zařízení (id, sha256 tokenu, platforma) | Postgres `player_devices` | do smazání; bez hlasu se maže po 180 dnech nečinnosti |
| Nákup (platforma, transaction id) | u hlasu | se hlasem |
| Kvóta, fronta úloh | Postgres | kvóta 2 dny, hotové úlohy 7 dní |

- Vzorek neleží nikde v otevřené podobě: API ho čte do paměti, délku zjistí z kontejneru (mvhd,
  RIFF) a zapíše ho rovnou zašifrovaný. Worker ho drží jen v paměti a záběry v tmpfs.
- Nic z toho se neloguje. Logují se jen id, velikost a délka. Text souhlasu ani receipt se neloguje.
- Smazání (`DELETE`, smazání zařízení nebo nečinnost) nejdřív v DB zablokuje přístup workeru,
  pak smaže soubory a zruší rozdělané úlohy. Smazání hlasu v AiStacku je úloha s nejvyšší prioritou.
  Úklid každou hodinu smaže i soubory, které po chybě zůstaly bez hlasu.
- Ztráta `VOICE_DATA_KEY` znamená, že uložené vzorky nejde přečíst. Hráči je nahrají znovu.

## Co musí Olin dodat

1. **Apple**: bundle id appky. Výchozí je `com.ol1n.webtoon` (z `app/ios`). Jiný se nastaví jako
   `VOICE_APPLE_BUNDLE_ID` v `deploy/.env`. Žádný klíč není potřeba, ověření je offline.
   V App Store Connect produkt `voice_clone` (non-consumable).
2. **Google Play**: servisní účet s přístupem k appce v Play Console (Users and permissions,
   oprávnění číst objednávky). JSON klíč patří na JODU do `~/deploy/Webtoon/secrets/play-service-account.json`
   (0600, mimo repo). Package je výchozí `com.ol1n.webtoon`. Bez klíče selžou Play nákupy se
   `receipt_verification_unavailable`.
3. **Appka (Webtoon session)** musí na iOS posílat StoreKit 2 JWS (`signedTransaction`, např.
   `in_app_purchase` se StoreKit 2), ne starý app receipt.

## Nasazení (zatím neproběhlo)

1. JODA: `deploy/deploy.sh` vytvoří `voice-data/` a `secrets/` (0700). Do `.env` doplní
   `VOICE_DATA_KEY` a `VOICE_WORKER_TOKEN` a nikdy je nevypíše. Kvůli novému Caddyfile pak
   `docker compose restart caddy`. Migrace 000007 proběhne při startu API.
2. SPARK: zkopírovat `backend/` a `deploy/voice-worker/` (např. rsync do `~/deploy/Webtoon/`).
   Vytvořit `worker.env` z `worker.env.example`. Token přenést bez vypsání:
   `ssh joda 'grep ^VOICE_WORKER_TOKEN= ~/deploy/Webtoon/deploy/.env' | ssh spark 'cat >> ~/deploy/Webtoon/deploy/voice-worker/worker.env'`
   (a smazat placeholder řádek). Pak `docker compose up -d --build` v `deploy/voice-worker/`.
   Kontejner sám GPU nedrží. Lease si bere přes broker jen při práci.

## Ověření naživo

1. Na JODĚ s `VOICE_RECEIPT_MODE=test` jen na **ne-produkčním** hostu (např. lokálně
   `MODE=api go run ./cmd/webtoon serve` s `VOICE_DATA_KEY`, `VOICE_WORKER_TOKEN`), nebo rovnou
   s pravým sandbox nákupem z TestFlightu na produkci.
2. `curl -X POST …/v1/player/devices` → token. Pak `POST /v1/player/voices` s 10s nahrávkou m4a.
3. Na SPARKu `VOICE_API_URL=… SPARK_BROKER=http://localhost:8100 webtoon voice-worker -once`.
   V `sparkctl ls webtoon` je vidět lease `tts` a po doběhnutí se vrátí.
4. `GET /v1/player/voices/{id}` → `ready`. Pak `POST …/lines` se 2–3 větami, `-once` znovu,
   `GET /v1/player/jobs/{id}` → URL. Stáhnout, poslechnout a `ffmpeg -i x.m4a -af ebur128 -f null -`
   má ukázat zhruba −16 LUFS.
5. `DELETE /v1/player/voices/{id}`, `-once`. `GET {AUDIO_URL}/v1/audio/voices/toonfork-<id>` → 404
   a `voice-data/voices/<id>` neexistuje.

## Otevřené body

- Licence chatterbox-cs je neověřená (`commercial_only=false`). Rozhodl o tom Olin, riziko nese firma.
- Ověření, že nahrávka obsahuje souhlasnou větu (ASR), chybí stejně jako v Hajánku.
- App Store Server Notifications (refund po nákupu) se nezpracovávají. Refund se projeví až při
  dalším nahrání hlasu. Hlas, který už existuje, zůstane.
- Rotace `VOICE_DATA_KEY` není. Nový klíč znamená nové nahrávky.
- Worker běží v kontejneru `unless-stopped` jako Hajánkův. Pokud ho zabije OOM guard, sám se nevrátí.
