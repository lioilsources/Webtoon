# Store submission checklist: Toonfork

Texts: `listing/<locale>/` (check with `python3 store/check_listing.py`). Rating: `age-rating.md`. Privacy:
`privacy-policy.md`. Products: `docs/store-products.md`, `tools/products.csv`.


## Data to republish (Direktor on M2) before the store release

Changed in the repo on 2026-11-05, not in the live catalog yet:
- Gamebooks **sara** (translations into 11 languages; node `n2` trimmed from 12 to 5 panels: panels 5–11 repeated
  panel 4) and **mlceni** (translations into 11 languages), **louka** (`title_i18n` was cut at commas by YAML).
  Re-import their storyboards and export new versions (node ids unchanged, so the update check passes).
- Pack **superhero-1**: stories `lx_k4_09_leo_zapisnik_osudu` (12 → 7 panels) and `lx_k4_10_max_octo_boy` (12 → 5)
  ended with the same panel 6–7× in a row (paid content). Re-import and export superhero-1 v3.
  (`lx_k4_05_amaya_strazkyne_dzungle` had the same defect, 8 → 7; it is in no published pack.)
- Starter pack (bundled, `starter-v1`): worlds have no `title_i18n` / `synopsis_i18n`, and 4 stories have no
  `title_i18n` (Zahrada světlušek, Nebeské ostrovy, Záhada v lese (volba 2/3)). The app now borrows a story title
  for the world heading and hides an untranslated synopsis, but these titles stay Czech for every reader until a
  starter-v2 with the translations (needs an app build, the starter is bundled).

## Before either store

- [x] Privacy policy filled in (ol1n, oldrich.vorechovsky.jr@gmail.com, effective 2026-11-05) and written as
      `docs/privacy.html`, with `docs/support.html` and `docs/index.html` (same layout as MirrorBooth / Kiran).
- [ ] Publish them: merge to `main`, then GitHub Pages for this repo from `main` `/docs`. URLs:
      privacy https://lioilsources.github.io/Webtoon/privacy.html · support https://lioilsources.github.io/Webtoon/support.html
      · marketing https://lioilsources.github.io/Webtoon/ (optional on the App Store)
- [ ] Decide whether to keep "Webtoon" out of the texts. It is a registered trademark (NAVER WEBTOON), so the listings
      say "vertical comics" and the keywords do not contain "webtoon" or "웹툰".
- [ ] The app UI is only partly translated. The store, profile and gate texts are in 12 languages; the rest is in Czech
      (`app/README.md`), and the UI translation is still in progress. The listings promise only that the **stories and
      gamebooks** are in 12 languages; they do not claim a translated interface. Add that line once the UI ships.
- [ ] All four gamebooks are translated into 12 languages, and the listings say so. Run the **catalog export** before
      release so that the live `catalog.json` carries the new languages of Sára and Učit se mlčet and Louka's fixed
      `title_i18n`. Today the live catalog still lists them as Czech only, with truncated de/pl/ru/uk titles of Louka.

## App Store Connect

- [ ] App Information: name, subtitle, privacy policy URL per locale (12 locales: cs, en-US, de-DE, it, fr-FR, pl,
      pt-BR, ja, ko, vi, ru, uk). Primary language: decide between cs and en-US.
- [ ] Category: Books (primary) and Entertainment (secondary). **Not** Kids.
- [ ] Age Rating questionnaire per `age-rating.md` → 16+ (override if needed). Made for Kids: No.
- [ ] App Privacy: "Data Not Collected".
- [ ] Version page per locale: description, keywords, promotional text, release notes ("What's New" is hidden on the
      first version; keep the text for 1.0.1), support URL.
- [ ] Screenshots: **iPhone 6.9"** (1320×2868 or 1290×2796 portrait), 3–10 per locale (the localized UI matters most
      for cs/en). **iPad 13"** (2064×2752 or 2048×2732) if the app runs on iPad. Optional app preview video
      (the TikTok trailers from `webtoon trailer` can be cut to 15–30 s).
- [ ] In-app purchases (non-consumable; name ≤ 30, description ≤ 45; cs + en at least, ideally all 12 from the
      catalog `title_i18n`): `pack_kids_1`, `pack_harlequin_1`, **`pack_harlequin_2`** (the catalog already sells it;
      it is now in `tools/products.csv`), `pack_superhero_1`, `bundle_kids`,
      `bundle_harlequin`, `bundle_superhero`, `bundle_all`. Each needs a review screenshot and price. Family Sharing on.
      Submit them **with** version 1.0.
- [ ] Paid Apps agreement, tax and banking active.
- [ ] Review notes from `docs/store-products.md` (add the four free gamebooks and the 16+ content of the dramas); a
      sandbox tester or promo code for the reviewer.

## Google Play Console

- [ ] Store listing per locale (Play codes: cs-CZ, en-US, de-DE, it-IT, fr-FR, pl-PL, pt-BR, ja-JP, ko-KR, vi, ru-RU,
      uk): app name (Play allows 30; reuse `name.txt`), short description, full description.
- [ ] Graphics: app icon 512×512; **feature graphic 1024×500** (required); **phone** screenshots (2–8, 16:9 or 9:16,
      at least 1080 px on the short side recommended); **7" tablet** and **10" tablet** screenshots (needed for the
      tablet listing).
- [ ] Category: Comics. Tags: comics, books, interactive stories.
- [ ] App content: privacy policy URL; **Data safety**: "No data collected", "No data shared". Data is not encrypted in
      transit to us because nothing is sent to us, and there is no account to delete. **Ads**: No. **App access**: all
      functionality available without special access (put the review notes there). **Content rating** (IARC) per
      `age-rating.md`. **Target audience**: 16+ (or 13+), no children's groups. **News app**: No. **Government app**:
      No. **Financial features**: none. **Health**: No **[?]** (the drama mentions health but the app has no health
      features).
- [ ] In-app products: the same 8 ids as above (incl. `pack_harlequin_2`), activated, after a build with BILLING is on a
      track.
- [ ] Payments profile linked; license testers added.
- [ ] Countries; release on internal → closed testing. New personal developer accounts need a 12-tester, 14-day closed
      test before production **[?]: check whether this applies to the account**.
