# Balíček obsahu (pack) — formát v1 (pack.json), katalog v2

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

## catalog.json (kořen repa webtoon-content) — schema 2

Obchod: aplikace je zdarma s přibaleným starterem; placené jsou jen **odemčení** (non-consumable IAP),
obsah sám leží mimo obchod. `catalog.json`, obálky a náhledy jsou na **GitHub Pages** (`base_urls.pages`),
zipy balíčků na **GitHub Releases** (`base_urls.releases`), adresu zipu skládá appka. Přesun na R2 =
změna `base_urls` v katalogu, ne nová verze appky.

```jsonc
{
  "schema": 2,
  "version": 7,                               // roste při každé změně; appka bere jen vyšší než má v cache
  "generated_at": "2026-10-24T08:00:00Z",
  "base_urls": {
    "pages":    "https://lioilsources.github.io/webtoon-content/",            // catalog.json, covers/, previews/
    "releases": "https://github.com/lioilsources/webtoon-content/releases/download/",
    "r2": null                                // "https://cdn…/" → zipy se berou odtud místo z releases
  },
  "types": [                                  // typy balíčků (rules/base/pack.yaml types, jen aktivní)
    { "id": "kids", "title_i18n": {"cs": "Pro děti", "en": "Kids", …}, "audience": "kids", "icon": "child_care" },
    { "id": "harlequin", "title_i18n": {…}, "audience": "adult", "icon": "favorite" },
    { "id": "superhero", "title_i18n": {…}, "audience": "kids", "icon": "bolt" }
  ],
  "packs": [
    { "id": "kids-1", "type": "kids", "n": 1, "title": "Pro děti 1", "title_i18n": {…},
      "product_id": "pack_kids_1",            // placený: product_id; zdarma: "free": true a product_id chybí
      "free": false,
      "version": 1, "stories": 50, "bytes": 123456789,      // bytes = součet částí
      "audience": "kids", "languages": ["cs", "en", …],
      "cover": "covers/cp_….webp",            // obálka balíčku (1. příběh), relativně k base_urls.pages
      "previews": ["covers/cp_….webp", …],    // ≤ 6 obálek příběhů pro mřížku v obchodě
      "parts": [
        { "part": "a", "release": "pack-kids-1-v1", "asset": "kids-1-a.zip",
          "bytes": 61234567, "sha256": "…", "stories": 25 },
        { "part": "b", "release": "pack-kids-1-v1", "asset": "kids-1-b.zip", "bytes": …, "sha256": "…", "stories": 25 }
      ] }
  ],
  "bundles": [                                // rules/base/pack.yaml bundles
    { "id": "bundle_kids", "product_id": "bundle_kids", "price_tier": "bundle_type",
      "title_i18n": {…}, "covers": {"types": ["kids"]} },     // všechny současné I BUDOUCÍ balíčky typu
    { "id": "bundle_all", "product_id": "bundle_all", "price_tier": "bundle_all",
      "title_i18n": {…}, "covers": "all" }
  ],
  "gamebooks": [                              // docs/gamebook.md; export-pack -gamebook graph.yaml
    { "id": "sara", "product_id": "gamebook_sara", "kit_product_id": "kit_sara", "type": "kids",
      "title": "…", "title_i18n": {…}, "audience": "kids", "languages": ["cs"], "cover": "covers/cp_….webp",
      "free": false, "status": "ready", "version": 1, "nodes": 10, "endings": 2, "bytes": …,
      "graph": "gamebook.json", "lore": "gamebook.json",
      "parts": [ { "release": "gamebook-sara-v1", "asset": "gamebook-sara.zip", "bytes": …, "sha256": "…",
                   "stories": 10 } ] },
    { "id": "drak", "product_id": "gamebook_drak", "status": "planned", … }   // ohlášený, bez zipu
  ],
  "stories": [                                // knihovna a obchod bez stažení balíčku
    { "id": "cp_…", "pack_id": "kids-1", "type": "kids", "world_id": "w_…", "title": "…",
      "title_i18n": {…}, "cover": "covers/cp_….webp", "episodes": 1, "audience": "kids" }
  ]
}
```

Pravidla:
- **id a pojmenování** (rules/base/pack.yaml `naming`): balíček `<type>-<n>`, produkt `pack_<type>_<n>`,
  release tag `pack-<type>-<n>-v<version>`, asset `<type>-<n>-<part>.zip` (část a, b, … i když je jen jedna).
  Placený balíček má `pack_size` (50) příběhů, zip `part_size` (25) příběhů.
- **URL zipu**: `part.url`, když je; jinak `(base_urls.r2 ?? base_urls.releases) + release + "/" + asset`;
  u části bez `release` (schema 1) `base_urls.pages + path`. Obálky a náhledy: `base_urls.pages + cover`.
  Releases přesměrovávají na `objects.githubusercontent.com` — klient sleduje redirect; stahuje s
  `Range` (pokračování), ověří sha256 celé části a teprve pak ji rozbalí.
- **Nárok** se počítá v appce z katalogu: balíček je odemčený, když je `free`, když vlastní jeho
  `product_id`, nebo bundle, jehož `covers.types` obsahuje `type` balíčku (`"all"` = všechny typy).
  Bundle tedy pokryje i balíčky, které v katalogu přibudou později. `gamebook_<id>` odemyká gamebook,
  `kit_<id>` gamebook + editor kit; bundly gamebooky neodemykají.
- **Gamebook** je jeden zip (bez částí) s pack.json (příběh = uzel, jedna epizoda) a `gamebook.json`
  (graf, příznaky, konce, lore). Jeho příběhy nejsou v `stories[]` katalogu ani v knihovně appky.
- **Publikum**: profil čtenáře Děti skryje typy, balíčky, bundly a příběhy s `audience: "adult"`
  (bundle podle publika svých typů; `all` obsahuje dospělé typy). Zdarma obsah nikdy nejde přes obchod.
- Zipy se do gitu repa nikdy necommitují (`releases/` je v .gitignore webtoon-content): `export-pack`
  je zapíše do `<out>/releases/<tag>/<asset>` a vypíše příkaz `gh release create …`, který je nahraje.
- Soubory se nepřepisují: nová verze balíčku = nový release tag (`-v2`), katalog se přepne až po nahrání.
- `price_tier` je jen nápověda pro docs/store-products.md (cenu ukazuje appka z obchodu):
  `pack` 0.99 USD, `bundle_type` 2.99, `bundle_all` 6.99, `gamebook` 1.99, `kit` 3.99.

### Schema 1 (čte se dál)

```jsonc
{ "schema": 1, "version": 3, "generated_at": "…",
  "base_url": "https://lioilsources.github.io/webtoon-content/",
  "packs": [ { "id": "romance-1", "title": "Romance I", "stories": 100,
               "parts": [ { "path": "packs/romance-1-v1-a.zip", "bytes": 61234567, "sha256": "…" } ],
               "free": false, "product_id": "pack_romance_1",
               "languages": ["cs","en"], "audience": "adult", "version": 1 } ],
  "stories": [ { "id": "cp_…", "pack_id": "romance-1", "world_id": "…", "title": "…", "title_i18n": {},
                 "cover": "covers/cp_….webp", "episodes": 1, "audience": "adult" } ] }
```

Appka i backend čtou schema 1 i 2: `base_url` = `base_urls.pages`, části mají `path` relativně k němu,
`type` chybí (appka ho odvodí z `audience`: adult → harlequin, jinak kids), `types`/`bundles`/`gamebooks`
jsou prázdné. Backend při dalším exportu katalog přepíše na schema 2 (staré `path` části nechá).

Balíček nad `part_size` příběhů se dělí na části; každá část je samostatný zip ve stejném formátu
(vlastní `pack.json` s podmnožinou příběhů, stejné `id` balíčku, `part: "a"`). Appka považuje balíček
za nainstalovaný, až když má všechny části ve verzi z katalogu.

`pack.json` zůstává **schema 1**; navíc (volitelně) `type` u `stories[]` a `worlds[]` — starší appky ho
ignorují.

## Starter

15 příběhů zdarma přibalených v appce: 5 kids + 5 harlequin + 5 superhero, každý v jiném stylu (výkladní
skříň stylů). Výběr je v `data/starter_showcase.yaml` (id světů; export si ke světu najde jeho kampaň).
`webtoon export-pack -starter app/assets/packs/starter.zip -starter-pick data/starter_showcase.yaml`
zapíše jeden zip (bez dělení) a nic do katalogu. Appka ho při prvním startu rozbalí do `getApplicationSupportDirectory()/packs/starter/`.
