# Store products (App Store + Google Play)

The app is **free** (rating 16+ on the App Store, whatever IARC yields on Play, likely PEGI 12–16: decided 2026-11-05
to keep the adult drama gamebooks) with 15 bundled starter stories and free gamebooks. The stores sell only **unlocks**: every product
is a **non-consumable** in-app purchase. The content is not in the store: after a purchase the app downloads the
pack's zips from GitHub Releases (`lioilsources/webtoon-content`), listed in `catalog.json` on GitHub Pages
(PACK_FORMAT.md, catalog schema 2). Prices, names and the product scheme are declared in `rules/base/pack.yaml`
(`naming`, `price_tiers`, `types`, `bundles`); the table and `tools/products.csv` are generated from it:

```sh
python3 tools/gen_products.py                                   # pack 1 of every active type + bundles
python3 tools/gen_products.py --packs kids=2,harlequin=3,superhero=1
python3 tools/gen_products.py --catalog                         # every paid pack of the live catalog
python3 tools/gen_products.py --catalog --check                 # fail when out of date
```

## Products

| kind | product id | price | what it unlocks |
|---|---|---|---|
| pack | `pack_<type>_<n>` (`pack_kids_1`, `pack_kids_2`, …) | 0.99 USD (Tier 1) | pack `<type>-<n>`: up to 50 stories, all 12 languages |
| everything | `bundle_all` | 4.99 USD (Tier 5) | every pack of every type, current and future |
| gamebook | `gamebook_<id>` | 0.99 USD (Tier 1) | one gamebook, or one story family (Archion, Guláš a špagety: every variant shares the product) |
| gamebook + kit | `kit_<id>` | 3.99 USD (Tier 4) | the gamebook plus its editor kit (a free gamebook includes its kit) |

Tiers: Apple replaced price tiers with price points (USD base price, other storefronts derived); "Tier N" is the
old tier of the same USD price (0.99 = Tier 1, 1.99 = Tier 2, 2.99 = Tier 3, 3.99 = Tier 4, 4.99 = Tier 5). No type bundles are sold (decided 2026-11-08): only `bundle_all`.
In Play Console set the USD default price and let Play convert the other countries.

Bundles never list their packs in the store: the app resolves a bundle against the catalog at runtime
(`covers: {types: [...]}` or `all`), so a new `pack_kids_3` is already owned by `bundle_kids` buyers with no new
product, no store change and no app release. **Create a new `pack_<type>_<n>` product only when its pack is
published** (an unused product confuses review). Product ids are permanent: never reuse or rename one.

Current list (generated; names ≤ 30 and descriptions ≤ 45 characters for App Store Connect):

<!-- products:begin (tools/gen_products.py) -->
| product id | kind | type | USD | tier | name cs | name en | description cs | description en |
|---|---|---|---|---|---|---|---|---|
| `pack_harlequin_1` | pack | harlequin | 0.99 | Tier 1 | Romantika 1 | Romance 1 | Balíček komiksových příběhů, 12 jazyků | A pack of comic stories, 12 languages |
| `pack_harlequin_2` | pack | harlequin | 0.99 | Tier 1 | Romantika 2 | Romance 2 | Balíček komiksových příběhů, 12 jazyků | A pack of comic stories, 12 languages |
| `pack_kids_1` | pack | kids | 0.99 | Tier 1 | Pro děti 1 | Kids 1 | Balíček komiksových příběhů, 12 jazyků | A pack of comic stories, 12 languages |
| `pack_superhero_1` | pack | superhero | 0.99 | Tier 1 | Superhrdinové 1 | Superheroes 1 | Balíček komiksových příběhů, 12 jazyků | A pack of comic stories, 12 languages |
| `bundle_all` | bundle | all | 4.99 | Tier 5 | Úplně všechno | Everything | Všechny balíčky všech typů, i budoucí | Every pack of every type, future too |
| `gamebook_archion` | gamebook | gamebook | 0.99 | Tier 1 | Gamebook: Archion | Gamebook: Archion | Interaktivní příběh s volbami | Interactive branching story |
| `gamebook_gulasspagety` | gamebook | gamebook | 0.99 | Tier 1 | Gamebook: Guláš a špagety | Gamebook: Goulash & Spaghetti | Interaktivní příběh s volbami | Interactive branching story |
<!-- products:end -->

Paid gamebooks (none yet: every published gamebook is free and needs no product), e.g. for a gamebook `drak`:

| product id | kind | USD | tier | name cs | name en | description cs | description en |
|---|---|---|---|---|---|---|---|
| `gamebook_drak` | gamebook | 0.99 | Tier 1 | Gamebook: Drakova hora | Gamebook: Dragon Mountain | Interaktivní příběh s volbami | Interactive branching story |
| `kit_drak` | kit | 3.99 | Tier 4 | Drakova hora + editor | Dragon Mountain + editor kit | Gamebook a sada pro vlastní úpravy | The gamebook plus its editor kit |

(`python3 tools/gen_products.py --gamebook "drak:Drakova hora:Dragon Mountain"` adds them to the CSV.)

## App Store Connect

One-time:
1. **Agreements, Tax, and Banking**: the Paid Apps agreement must be active (in-app purchases need it even in a
   free app).
2. **App Information → Age Rating**: answer the questionnaire so the result is **16+** (Apple's age ratings since 2025: 4+, 9+, 13+, 16+, 18+; use Age
   Rating Override to 16+ if the answers yield 13+) (romance stories:
   "Infrequent/Mild Sexual Content or Nudity: none, Mature/Suggestive Themes"; the drama gamebooks: "Frequent/Intense
   Mature/Suggestive Themes" and "Medical/Treatment Information" — an eating disorder and thoughts of death in
   *Učit se mlčet*; no gambling, no unrestricted web). Answers in `store/age-rating.md`. Do **not** put the app in the
   Kids category: the Kids category forbids third-party content downloads and requires no external links;
   instead the app has a reader profile (Děti / Dospělí) and a **parental gate** before every purchase and before
   switching to the adult profile.
3. **App Privacy**: no data collected (purchases are handled by Apple; the app stores entitlements on device).

Per product (Features → **In-App Purchases** → **+**):
1. Type **Non-Consumable**; Reference Name = the product id (e.g. `pack_kids_1`); Product ID = the product id.
2. **Availability**: all countries the app is in.
3. **Price Schedule**: base country United States, price 0.99 / 3.99 / 4.99 USD (table above);
   accept the generated prices of the other storefronts.
4. **App Store Localization**: add **Czech** and **English (U.S.)** (more later) with the display name and
   description from the table / `tools/products.csv`.
5. **Review Information**: screenshot of the Obchod tab showing the product (one screenshot per product is
   required; the same store screen works for every pack), review notes (below).
6. Family Sharing: on (non-consumables can be shared; the app restores them with "Obnovit nákupy").
7. The first in-app purchases must be submitted **together with an app version** (App Store → the version →
   "In-App Purchases and Subscriptions" → select them). Later ones can be submitted alone.

Bulk: App Store Connect has no CSV import in the web UI. With many packs, create them through the App Store
Connect API (`POST /v1/inAppPurchases` + `inAppPurchaseLocalizations` + `inAppPurchasePriceSchedules`) driven by
`tools/products.csv` (a script for that is not part of this repo yet; never run it without the owner's go).

Testing: **Users and Access → Sandbox Testers** → add a tester; on the device sign in under Settings → App Store →
Sandbox Account. A StoreKit configuration file is not needed (`--dart-define=WEBTOON_FAKE_IAP=true` gives the app
a fake store for UI work). **Promo codes** for in-app purchases: App Store Connect → the app → Promo Codes /
Offer Codes (up to 100 per product per quarter) — give one to the reviewer if they ask.

## Google Play Console

One-time:
1. **Setup → Payments profile** linked (merchant account), otherwise products cannot be priced.
2. Upload a build with the `com.android.vending.BILLING` permission (the `in_app_purchase` plugin adds it) to
   any track (internal testing is enough) — Play lets you create products only after that.
3. **Policy → App content**: content rating questionnaire (IARC) → IARC decides (no override on Play; likely PEGI 12 or 16)
   (answers in `store/age-rating.md`); **Target audience and content**: 16+ and older (not "children"), so the app is **not** in the Designed for Families program; the
   in-app parental gate still protects purchases and the adult profile. Data safety: no data collected.

Per product (**Monetize → Products → In-app products → Create product**):
1. Product ID = the product id (lower case, digits, `_` and `.` only: `pack_kids_1` is valid). Permanent.
2. Name and description: English (default) and Czech from the table (Play allows 55 / 200 characters).
3. Default price 0.99 / 3.99 / 4.99 USD → **Update exchange rates** fills the other countries.
4. **Activate**. (Play has no consumable flag; the app never consumes these purchases, which makes them
   non-consumable.)

Bulk: **In-app products → Import** accepts a CSV in Play's own format (`Product ID,Published State,Purchase
Type,Auto Translate,Locale; Title; Description,Auto Fill Prices,Price,Pricing Template ID`). Convert
`tools/products.csv`: `pack_kids_1,published,managed_by_android,false,en_US; Kids 1; A pack of comic stories, 12
languages; cs_CZ; Pro děti 1; Balíček komiksových příběhů, 12 jazyků,true,990000,` (price in micros of the default
currency). Or use the Play Developer API (`inappproducts.insert` / `monetization.onetimeproducts`).

Testing: **Setup → License testing** → add tester Gmail accounts (test purchases are free and auto-refunded);
install from the internal testing track. Promo codes: **Monetize → Promo codes** (one-time codes per product).

## Review notes (paste into App Store "Notes" and Play "App access")

```
Toonfork is a free offline webtoon reader. 15 stories are bundled in the app and are free (no account,
no purchase). Additional story packs are optional non-consumable in-app purchases (Obchod tab):
pack_<type>_<n> unlocks one pack of up to 50 stories; bundle_all unlocks every current and future pack.

After a purchase the app downloads the pack (zip files, ~50–150 MB) from GitHub Releases
(github.com/lioilsources/webtoon-content), verifies its SHA-256 checksum and installs it; the stories then
appear in Knihovna (Library). The list of packs (catalog.json) and covers come from GitHub Pages. No
content is executable; packs contain images and JSON text only.

Reader profile: on first launch the app asks for Děti (Kids) or Dospělí (Adults). The Kids profile hides
romance stories, packs and the adult drama gamebooks. Every purchase and switching to Adults is behind a parental gate: a simple
arithmetic question (e.g. "Kolik je 7 × 8?" / "What is 7 × 8?") the parent must answer.

Restore Purchases: Nastavení (Settings) tab → "Obnovit nákupy".

To test a purchase: use a sandbox tester account (any pack, e.g. pack_kids_1), or the promo code we
provide on request. The app works fully offline after the download.

Gamebooks (Knihovna → Gamebooky) are free branching comics: the reader picks a choice at the end of a chapter.
The adult dramas deal with mature themes (one with an eating disorder and thoughts of death, with a content
note at the start and a crisis line at every ending); they are hidden in the Kids profile.
```

## Server receipt validation (later)

Today the app trusts the store's purchase result and keeps the owned product ids + receipts on the device. Phase
2: a small Go service (`store.ol1n.com`) verifies receipts (App Store Server API / Play Developer API) and hands
out signed download URLs (R2) — the catalog's `base_urls.r2` is already there for it.
