# Balíček obsahu (pack) — formát v1

Reader čte příběhy offline z balíčků. Balíček vyrábí `webtoon export-pack` z backendu, appka ho
rozbalí do svého úložiště (starter z `assets/packs/starter.zip` při prvním startu, ostatní po stažení
z `webtoon-content`). Jeden loader pro oba případy.

## Zip

```
<pack>.zip
  pack.json
  media/<episode_id>/pNN.webp          panel (PNG z backendu → WebP q85, stejné rozměry)
  media/<episode_id>/pNN_loop.webp     smyčka, animovaný WebP beze změny
  covers/<story_id>.webp               náhled příběhu (p00 prvního dílu, 416×608)
```

Cesty v `pack.json` jsou relativní ke kořeni zipu. Soubory balíčku se nikdy nepřepisují: nová verze
= nový název (`romance-1-v2.zip`).

## pack.json

```jsonc
{
  "schema": 1,
  "id": "starter",                 // id balíčku, [a-z0-9-]
  "title": "Starter",
  "version": 1,
  "generated_at": "2026-10-23T08:00:00Z",
  "worlds": [                      // jen světy, které mají v balíčku příběh
    { "id": "w_les", "title": "…", "synopsis": "…", "tone": "…", "audience": "kids|teen|adult",
      "language": "cs", "style_id": "…" }
  ],
  "stories": [                     // příběh = kampaň; pořadí v poli = pořadí v knihovně
    { "id": "cp_…", "world_id": "w_les", "title": "…", "title_i18n": {"en": "…"},
      "episodes": ["ep_…", "ep_…"],   // jen hotové díly, v pořadí idx; končí u prvního nehotového
      "cover": "covers/cp_….webp", "languages": ["cs","en",…] }   // průnik languages dílů
  ],
  "episodes": [                    // přesně tvar GET /episodes/{id} (backend episodes.go), až na:
    { "id": "ep_…", "campaign_id": "cp_…", "index": 1, "title": "…", "status": "ready",
      "title_i18n": {}, "source_language": "cs", "languages": [],
      "panels_ready": 9, "panels_total": 9, "credits_cost": 0,
      "panels": [ { "index": 0, "status": "ready",
                    "image_url": "media/ep_…/p00.webp",        // relativní, ne /media/…
                    "video_url": "media/ep_…/p00_loop.webp",   // jen když smyčka existuje
                    "video_status": "ready", "animate": true, "loop_seconds": 2,
                    "width": 832, "height": 1216, "shot": "…", "location_id": "…", "gap_after": "…",
                    "bubbles": [...], "sfx": [...], "characters": [...] } ],
      "choices": [...], "chosen": {...}, "warnings": [] }
  ]
}
```

Vynechaná pole oproti API: `seed`, `identity_score`, `error`, `video_error`, `estimate_seconds`,
`created_at`, `updated_at`. Modely v appce (`lib/models/episode.dart`) tolerují chybějící pole.

Pravidla exportu:
- svět s `id` začínajícím `w_lxf_` export odmítne (free stripy se nikdy nepublikují);
- díl bez `image_url` u některého panelu (status ≠ ready) se nebere, příběh končí před ním;
- příběh bez jediného hotového dílu se vynechá;
- texty nesou všechny jazyky z `i18n`, nic se nepřekládá při exportu;
- volná volba hráče je `chosen: {choice_id: "free", kind: "free", text: …}` a v `choices` nemá protějšek; appka ji ukáže jako vlastní řádek;
- `stories[].languages` = jazyk světa + průnik `languages` dílů; `title_i18n` příběhu se bere z prvního dílu, když má kampaň stejný název.

## catalog.json (kořen repa webtoon-content)

```jsonc
{
  "schema": 1,
  "version": 3,                               // roste při každé změně; appka stahuje jen když je vyšší
  "generated_at": "…",
  "base_url": "https://lioilsources.github.io/webtoon-content/",
  "packs": [
    { "id": "romance-1", "title": "Romance I", "stories": 100,
      "parts": [ { "path": "packs/romance-1-v1-a.zip", "bytes": 61234567, "sha256": "…" }, … ],
      "free": false, "product_id": "pack_romance_1",   // free:true = bez obchodu, product_id pak chybí
      "languages": ["cs","en",…], "audience": "adult", "version": 1 }
  ],
  "stories": [                                // pro knihovnu a hledání bez stažení balíčku
    { "id": "cp_…", "pack_id": "romance-1", "world_id": "w_rb_01_ny", "title": "…",
      "title_i18n": {…}, "cover": "covers/cp_….webp", "episodes": 1, "audience": "adult" }
  ]
}
```

Balíček nad ~25 příběhů se dělí na části (`parts`) po 25 příbězích; každá část je samostatný zip ve
stejném formátu (vlastní `pack.json` s podmnožinou příběhů, stejné `id` balíčku, `part: "a"`).
Appka považuje balíček za nainstalovaný, až když má všechny části.

## Starter

`webtoon export-pack -starter …` zapíše jeden zip `app/assets/packs/starter.zip` (bez dělení) a
nic do katalogu. Appka ho při prvním startu rozbalí do `getApplicationSupportDirectory()/packs/starter/`.
