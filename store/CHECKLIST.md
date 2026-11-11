# Store submission checklist: Toonfork

Texts: `listing/<locale>/` (check with `python3 store/check_listing.py`). Rating: `age-rating.md`. Privacy:
`privacy-policy.md`. Products: `docs/store-products.md`, `tools/products.csv`.


## Data to republish (Direktor on M2) before the store release

- [x] Done 2026-11-07: gamebooks sara, mlceni, louka re-exported; superhero-1 v3; `starter-v2` released (15 stories,
      52 MB); new gamebooks kulovyblesk and kulovyblesktus; catalog webtoon-content v26; build `v0.6.1-alpha`.

## Before either store

- [x] Privacy policy filled in (ol1n, business@olin.now, effective 2026-11-05) and written as
      `docs/privacy.html`, with `docs/support.html` and `docs/index.html` (same layout as MirrorBooth / Kiran).
- [x] Publish them (live, HTTP 200): merge to `main`, then GitHub Pages for this repo from `main` `/docs`. URLs:
      privacy https://lioilsources.github.io/Webtoon/privacy.html · support https://lioilsources.github.io/Webtoon/support.html
      · marketing https://lioilsources.github.io/Webtoon/ (optional on the App Store)
- [ ] Decide whether to keep "Webtoon" out of the texts. It is a registered trademark (NAVER WEBTOON), so the listings
      say "vertical comics" and the keywords do not contain "webtoon" or "웹툰".
- [x] The app UI is translated into 45 languages (`app/lib/i18n/ui_strings*.dart`; 33 of them machine translations
      for native speakers to review). Stories and gamebooks stay in 12 languages, and every listing now says both.
- [ ] Locales beyond the first 12 (`listing/<locale>/`, 45 in total, Apple codes): ar-SA bn-BD ca da el es-ES fi gu-IN
      he hi hr hu id kn-IN ml-IN mr-IN ms nl-NL no or-IN pa-IN pt-PT ro sk sl-SI sv ta-IN te-IN th tr ur-PK zh-Hans
      zh-Hant. Play codes for them: ar bn-BD ca da-DK el-GR es-ES fi-FI gu hi-IN hr hu-HU id iw-IL kn-IN ml-IN mr-IN
      ms nl-NL no-NO pa pt-PT ro sk sl sv-SE ta-IN te-IN th tr-TR ur zh-CN zh-TW (Play has no Odia, `or-IN` is App
      Store only). Texts are machine translations, upload by hand; the limits are checked by `check_listing.py`.
- [x] All gamebooks are translated into 12 languages, and the listings say so. The live catalog (v26) lists all six
      (sara, mlceni, kovovenebe, louka, kulovyblesk, kulovyblesktus) with 12 languages and full titles.

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
      it is now in `tools/products.csv`), `pack_superhero_1`, `bundle_all`
      (4.99 USD; no type bundles). Each needs a review screenshot and price. Family Sharing on.
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
- [ ] In-app products: the same 5 ids as above (incl. `pack_harlequin_2`), activated, after a build with BILLING is on a
      track.
- [ ] Payments profile linked; license testers added.
- [ ] Countries; internal testing (for the products), then **production**. The Play account is a **company**
      (organization) account: no mandatory 12-tester, 14-day closed test.
