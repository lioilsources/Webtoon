# Gamebook a editor kit (beta)

Stav: beta. První gamebook je `data/gamebooks/sara/graph.yaml` (osnova schválena 2026-10-25).
Výroba: `m0/gamebook.py` (scénáře uzlů, adapt, unify) → `m0/local_strip.sh -I -a kids <ids>` (render, smyčky,
import) → `webtoon export-pack -gamebook data/gamebooks/sara/graph.yaml -out <webtoon-content>`.
Appka: `app/lib/gamebook/` (čtečka `gamebook_screen.dart`, editor `branch_editor_screen.dart`).

## Formát

Zip jako balíček (PACK_FORMAT.md) s `gamebook.json` navíc:

- `nodes{id: {episode_id, title, next?, choices[{id, text, i18n, to, if?}], sets[], ending?, retry_to?}}`
  — epizody a panely jsou v `pack.json` jako u balíčků, čtečka je kreslí stejně.
- `start`, `flags[]`, `lore` = postavy, lokace a pravidla světa (z world.json) pro editor.
- Podmínky `if` jsou jen `flag`, `a or b`, `a and b`, `not a` — žádný skriptovací jazyk.

Vzniká ze `graph.yaml`: osnova → storyboard každého uzlu (adapt s `beats`, postavy a lokace ze světa) →
render a smyčky (sparkctl lease) → obličeje → `export-pack -gamebook data/gamebooks/<id>/graph.yaml`.

## Čtečka (offline)

- Prochází graf: na konci uzlu stávající blok s volbami (`EpisodeEndBlock`, jen pevné volby, bez
  volného textu), `next` pokračuje sám, konec ukáže „Konec“ / „Zkus to znovu“ (`retry_to`).
- Stav na zařízení: aktuální uzel, příznaky, navštívené uzly a nalezené konce; začít znovu, krok zpět.
- Mapa cesty: navštívené uzly a nalezené konce (x/3), neodkrývá nenavštívené.

## Editor kit — beta (offline remix)

Nová větev potřebuje nakreslit (LLM + ComfyUI na Sparku), což appka u testera nemá: TestFlight build míří
na backend v tailnetu. Beta editor proto běží offline nad tím, co je v zipu:

1. **Graf**: seznam/strom uzlů gamebooku; tester přidá vlastní uzel za libovolnou volbu, nebo novou volbu
   k existujícímu uzlu (cíl = existující nebo vlastní uzel).
2. **Vlastní uzel = remix**: vybírá panely z knihovny obrázků gamebooku (všech ~70) a ke každému píše
   bubliny (mluvčí z `lore`, druh řeč/výkřik/vyprávění); rozmístění bublin se stávající logikou mimo obličeje.
3. **Hraní**: vlastní větve se hrají ve čtečce hned (štítek „Moje větev“), jen na zařízení testera.
4. **Odeslat autorovi**: export větve jako JSON přes systémové sdílení (žádný server). Autor ji může nechat
   nakreslit pipeline (beats → storyboard) a vydat v další verzi gamebooku.

Mimo betu: kreslení nových panelů z editoru (fronta na backendu), sdílení větví mezi čtenáři (moderace).
Odemyká `kit_<id>`; v TestFlightu jsou nákupy sandbox (zdarma).
