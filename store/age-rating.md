# Age rating: Toonfork

The owner decided: **keep the adult dramas in the app**, so the app is rated for older teens and adults and is **not**
in the Kids category (App Store) and **not** in Designed for Families (Play). This matches `docs/store-products.md`: **16+ on the App Store**, and on Play **whatever the IARC questionnaire yields**
(likely PEGI 12, possibly 16).

Marks: **[?]** = I am not sure; check this in the console before you submit.

## What is in the app (the facts the answers come from)

| content | where | what it means for the rating |
|---|---|---|
| Romance (Romantika 1, 2) | paid packs, `audience: adult` | SFW couples (pipeline rule "finished SFW romance strips"): flirting, dates, embraces, maybe a kiss **[?]: spot-check a few strips**. No nudity, no sex scenes |
| Učit se mlčet | free drama, adult | a therapy session with a 25-year-old woman with **anorexia**. The text names it and asks about **wanting to die** ("Vy jste někdy chtěl umřít?"). It shows that medical care matters. A content warning opens the story; the endings carry a helpline (new text, approved by the author on 2026-11-05) |
| Kovové nebe nad námi | free drama, adult | a father who emotionally dominates his son over 42 years; a polluted megacity ("benzene over the limit", shelters). No physical violence **[?]** |
| Rozkvetlá louka, která zšedla | free drama, adult | a marriage breaking down over 20 years, a father who has to leave for two years, quarrels ("vypadni"). No violence |
| Superhrdinové 1 | paid pack, kids | cartoon or fantasy action (fights, powers), no blood **[?]: spot-check** |
| Pro děti 1, Sára a černá koruna | kids | fairy-tale adventure, mild peril |
| Profanity | all | none found in the drama scripts; the romance and superhero packs were not checked **[?]** |
| Alcohol, tobacco, drugs | all | none in the drama scripts; romance strips may show wine at dinner **[?]** |
| Gambling | none | the story "Noc v kasinu v Las Vegas" is set in a casino: it is a setting, not gambling the player does. Answer "None" for simulated gambling **[?]: check the story for on-screen betting** |
| Web access | none | the app downloads catalog and packs from fixed GitHub URLs; there is no browser and no free links |
| User-generated content | none shared | the gamebook editor kit (beta) makes branches **only on the device**; export goes only through the system share sheet to the author. Nothing is shown to other users |
| Purchases | yes | non-consumable in-app purchases behind a parental gate |
| Ads, accounts, chat, location | none | |

## Apple (App Store Connect → App Information → Age Rating)

Apple replaced 4+/9+/12+/17+ with **4+, 9+, 13+, 16+, 18+** in 2025, and since 31 January 2026 every app must answer the
new questionnaire, so **"17+" no longer exists**. The target is **16+**.

| section | question | answer |
|---|---|---|
| In-app controls | Parental Controls | **Yes** (Kids/Adults profile; parental gate before purchases and before switching to Adults) |
| | Age Assurance | No |
| Capabilities | Unrestricted Web Access | No |
| | User-Generated Content | No (nothing is shared between users) **[?]: Yes only if you count the editor kit; it is local only** |
| | Messaging and Chat | No |
| | Advertising | No |
| Mature themes | Profanity or Crude Humor | None **[?]** (Infrequent/Mild if a strip has a mild swear word) |
| | Horror/Fear Themes | Infrequent/Mild (dystopian city, a dark family drama) |
| | Alcohol, Tobacco, or Drug Use or References | None **[?]** (Infrequent/Mild if a romance strip shows drinking) |
| Medical or wellness | Medical or Treatment Information | **Infrequent/Mild** (eating disorder, therapy, "get medical care") |
| | Health or Wellness Topics | **Yes** |
| Sexuality or nudity | Mature or Suggestive Themes | **Frequent/Intense**. The romance packs are a whole category, and the dramas deal with eating disorders and thoughts of death. "Infrequent/Mild" would be the more literal answer for the romance alone **[?]** |
| | Sexual Content or Nudity | None |
| | Graphic Sexual Content and Nudity | None |
| Violence | Cartoon or Fantasy Violence | Infrequent/Mild (superheroes) |
| | Realistic Violence | None |
| | Prolonged Graphic or Sadistic Realistic Violence | None |
| | Guns or Other Weapons | None **[?]** (Infrequent/Mild if a superhero strip shows weapons) |
| Chance-based activities | Simulated Gambling | None |
| | Contests | None |
| | Gambling | No |
| | Loot Boxes | No |

**Expected result:** the answers alone probably give **13+**. With "Frequent/Intense" mature themes they may give
**16+** **[?]: Apple does not publish the exact mapping**. Then use **Age Rating Override → 16+** (Apple only lets you
raise the rating, never lower it). Also:
- **Made for Kids: No.** Do not choose the Kids category.
- Age Suitability URL: optional. You could point it at the content-note section of the support page.
- Content warning: the description already names the eating disorder and thoughts of death (all 12 locales).

## Google Play (Policy → App content → Content rating, IARC)

Play has no override: the rating is what the questionnaire gives. Answer the questions truthfully and do not aim for a
rating (as `docs/store-products.md` says: whatever IARC yields). IARC raises PEGI to 16 mainly for sexual activity,
realistic violence or drugs, and the app has none of these. The most likely result is **PEGI 12 / ESRB Teen /
USK 12**. **[?]**

- **Category:** "Entertainment" (a reader for comics and stories). **[?]** Some reviewers treat gamebooks as
  "Game". If Play asks, take the questionnaire for the category that describes most of the app: the reader.
- Email for the IARC certificate: `<CONTACT EMAIL>`.

| topic | question (paraphrased) | answer |
|---|---|---|
| Violence | violence of any kind? | **Yes**: cartoon or fantasy only, no blood, not realistic, not against humans in a realistic way **[?]** |
| Fear | content that may scare young children? | **Yes**: mild (dystopian city, family conflict) **[?]** |
| Sexuality | sexual content or nudity? | **Yes, mild**: romantic or suggestive themes (flirting, embraces, a kiss), **no nudity, no sexual activity** |
| Language | profanity or crude humour? | No **[?]** |
| Controlled substances | drugs, alcohol, tobacco? | No **[?]** (references only, if a romance strip shows wine) |
| Crude humour | | No |
| Gambling | real or simulated gambling? | No |
| Sensitive topics | references to suicide, self-harm, eating disorders? (the newer IARC form asks this) | **Yes**: discussed in a serious, non-graphic way in one drama, with a warning and a helpline **[?]: the exact wording varies** |
| Miscellaneous | users interact or exchange content? | No |
| | shares the user's location? | No |
| | digital purchases? | **Yes** |
| | unrestricted internet access? | No |
| | the app is a web browser or search engine? | No |

**Expected result:** **PEGI 12** (sexual innuendo, mild violence), **ESRB Teen**, **USK 12**, **IARC 12+**. The answer on
sensitive topics may raise this to **PEGI 16 / ESRB Mature 17+** **[?]**. Whatever comes out, keep it.

**Target audience and content** (a separate form): age groups **16–17 and 18+** (or 13–15 too, if the rating stays
PEGI 12 and the owner prefers that). Do **not** tick any group under 13. Then the app is not in Designed for Families and
needs no Families policy review. Appeal to children: **No** (the store listing describes a Kids profile, so add a note
that the kids' content sits behind a profile in an app for older readers).

## Consistency notes

- The listing (all 12 locales) says: the romance is for adults and nothing in it is explicit; the dramas deal with an
  eating disorder, thoughts of death and difficult family relationships; the Kids profile hides romance and the dramas;
  there is a parental gate. Keep the rating answers in line with these sentences.
- All four gamebooks, including Učit se mlčet (eating disorder, thoughts of death), are now in 12 languages. The content
  note in every locale applies to all buyers, not only to Czech readers.
- The listings name no rating; the consoles show it. If the final Play rating differs from PEGI 16, nothing in the texts
  needs to change.
