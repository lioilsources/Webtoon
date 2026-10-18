# Paměťová matice — modely a styly pro dětské webtoony

Generováno `kids/tools/matrix.py` z `kids/runs/jobs.jsonl` (čísla) a `kids/runs/matrix_notes.json` (poznatky).
Verdikt: **A** výchozí volba · **B** dobré se známými opravami · **C** jen na některé záběry · **D** nepoužívat.

Výhrady k číslům: příběhy 01–15 jsou v registru zpětně (`reconstructed`) a jejich zamítnuté varianty se nezachovaly, takže „přegenerování na panel“ je u nich podhodnocené (Juggernaut i Pony měly ve skutečnosti best-of-3 na ~40 % panelů). Sekundy jsou čas od odeslání po stažení, včetně čekání ve sdílené frontě ComfyUI — srovnávat jen v rámci jednoho běhu.

## Obecná poučení

- Multi-character scenes (2–4 characters + animals) are where models differ most; single portraits are easy for all.
- FLUX draws speech bubbles with gibberish when scene_en contains a verb of speaking (whispers, says, asks) — describe what is seen, not what is said; schnell does it far more often than dev.
- SDXL (CLIP, ~77 tokens): character descriptions after the scene get merged into whoever the scene names first; put who first (who_first).
- Booru anime checkpoints leak animal features onto humans (rabbit/fox/cat ears and tails) when an animal is in the same panel; negate 'animal ears, kemonomimi, fox tail' per panel.
- Pony family draws animals as anthro characters unless tagged 'feral, quadruped' with 'anthro, humanoid, standing on two legs' negated.
- Establishing/wide shots with SDXL drop the characters or the giant; a medium shot with the creature tags weighted brings them back.
- A style word that is also an object gets drawn literally: Animagine 'storybook' put books in hands.
- Realistic checkpoints (RealVis, CyberRealistic, Juggernaut Lightning) ignore drawn styles; claymation only took with weights (1.3–1.4) and a 'miniature diorama' framing.
- FLUX-dev takes some media from the prompt alone (paper cut-out collage, chalk pastel, ink graphic novel, toy diorama with LoRA) but not others (pixel art, stained glass, two-tone risograph).

## Presety

| verdikt | preset | model | LoRA | styl | příběhy | rendery strip / varianty / test | přegenerování na panel | medián s/panel |
|---|---|---|---|---|---|---|---|---|
| A | `flux_chalk` | flux1-dev | — | chalk pastel (FLUX dev) | — | 0 / 0 / 2 | — | 43 |
| A | `flux_dev_ink` | flux1-dev | — | graphic novel ink (FLUX dev) | 30 | 13 / 0 / 1 | 0.00 | 32 |
| A | `flux_kawaii` | flux1-dev | Cute-3d-Kawaii 0.8 | kawaii 3D (FLUX dev + Cute-3d-Kawaii) | 28 | 10 / 0 / 0 | 0.00 | 31 |
| A | `flux_manga` | flux1-dev | — | manga webtoon (FLUX dev, no LoRA) | 14, 22 | 21 / 0 / 0 | 0.00 | 93 |
| A | `flux_papercut` | flux1-dev | — | paper cut-out collage (FLUX dev) | — | 0 / 0 / 1 | — | 244 |
| A | `flux_pixar` | flux1-dev | Canopus-Pixar-3D-FluxDev-LoRA 0.8 | 3D animated film (FLUX dev + Canopus Pixar) | 12, 21 | 21 / 0 / 0 | 0.00 | 77 |
| A | `flux_toybox` | flux1-dev | Toy_Box_Flux_v2_renderartist 0.9 | toy diorama (FLUX dev + Toy Box) | 17, 29 | 24 / 0 / 1 | 0.00 | 67 |
| B | `animagine_storybook` | animagine-xl-40-opt | — | painterly cinematic light (Animagine XL 4) | 07, 09, 10, 23 | 78 / 6 / 0 | 0.08 | 45 |
| B | `atomix_space` | atomixPonyAnimeXL_v30 | Starship_Hulls_-_Pony_r1 0.6 | anime sci-fi (Atomix Pony + Starship Hulls) | 13 | 8 / 0 / 0 | 0.00 | — |
| B | `clean_webtoon` | noobai-xl-eps11 | — | flat clean webtoon (NoobAI + ningen mame/ciloranko) | 01, 02, 03, 04, 05, 27 | 50 / 3 / 0 | 0.06 | 18 |
| B | `cyberreal_clay` | CyberRealisticXL_v10 | — | claymation diorama (CyberRealisticXL) | 20 | 12 / 6 / 6 | 0.50 | 46 |
| B | `flux_riso` | flux1-dev | — | risograph (FLUX dev) | — | 0 / 0 / 1 | — | 29 |
| B | `flux_schnell_ink` | flux1-schnell | — | graphic novel ink (FLUX schnell, 4 steps) | 18, 25 | 26 / 15 / 1 | 0.58 | 43 |
| B | `illustrious_storybook` | Illustrious-XL-v2.0 | — | watercolour picture book (Illustrious XL 2.0) | 06, 08, 24 | 54 / 9 / 0 | 0.17 | 43 |
| B | `noobai_flat` | noobai-xl-eps11 | MeMaXL_Flat_Anime_Style_-_NoobIllustriousPonyXL 0.8 | flat ligne claire (NoobAI + MeMaXL Flat) | 16, 26 | 26 / 6 / 1 | 0.23 | 34 |
| C | `flux_dev_pixel` | flux1-dev | — | 'pixel art' prompt (FLUX dev) | — | 0 / 0 / 1 | — | 47 |
| C | `flux_stainedglass` | flux1-dev | — | 'stained glass' prompt (FLUX dev) | — | 0 / 0 / 1 | — | 49 |
| C | `juggernaut_book` | Juggernaut-XL_v9_RunDiffusionPhoto_v2 | — | gouache book (Juggernaut) | — | 0 / 0 / 0 | — | — |
| C | `juggernaut_clay` | Juggernaut-XL_v9_RunDiffusionPhoto_v2 | — | claymation (Juggernaut) | — | 0 / 0 / 2 | — | 20 |
| C | `juggernaut_pixar` | Juggernaut-XL_v9_RunDiffusionPhoto_v2 | PixarXL 0.8 | 3D Pixar (Juggernaut XL + PixarXL) | 11 | 7 / 0 / 0 | 0.00 | — |
| C | `pony_pixar` | ponyDiffusionV6XL_v6StartWithThisOne | Pixar_Pony 0.8 | 3D (Pony V6 + Pixar Pony) | 15 | 8 / 0 / 0 | 0.00 | — |
| C | `realvis_matte` | RealVisXL_V5.0 | — | photoreal family film (RealVisXL V5) | 19 | 13 / 3 / 1 | 0.23 | 47 |
| D | `animagine_nouveau` | animagine-xl-40-opt | — | Art Nouveau (Animagine) | — | 0 / 0 / 1 | — | 22 |
| D | `autismmix_anime` | AutismMix_pony | — | anime (AutismMix Pony) | — | 0 / 0 / 0 | — | — |
| D | `cyberreal_matte` | CyberRealisticXL_v10 | — | matte painting (CyberRealistic) | — | 0 / 0 / 1 | — | 20 |
| D | `flux_schnell_pixel` | flux1-schnell | — | pixel art (FLUX schnell) | — | 0 / 0 / 1 | — | 60 |
| D | `hassaku_pixar` | HassakuXL_Illustrious_v3.4 | Pixar_Illustrious 0.8 | 3D cartoon (Hassaku + Pixar Illustrious) | — | 0 / 0 / 1 | — | 22 |
| D | `hassaku_storybook` | HassakuXL_Illustrious_v3.4 | — | watercolour (Hassaku XL) | — | 0 / 0 / 0 | — | — |
| D | `illustrious_pixar` | Illustrious-XL-v2.0 | Pixar_Illustrious 0.8 | 3D cartoon (Illustrious + Pixar Illustrious) | — | 0 / 0 / 2 | — | 20 |
| D | `juggernaut_lightning_comic` | Juggernaut-XL-Lightning_4Steps | — | retro comic (Juggernaut Lightning) | — | 0 / 0 / 1 | — | 13 |
| D | `realvis_clay` | RealVisXL_V5.0 | — | claymation (RealVis) | — | 0 / 0 / 3 | — | 20 |
| - | `clean_webtoon_noartist` | noobai-xl-eps11 | — | unused | — | 0 / 0 / 0 | — | — |
| - | `hassaku_soft` | HassakuXL_Illustrious_v3.4 | — | unused | — | 0 / 0 / 0 | — | — |

## Poznámky k presetům

### `flux_chalk` — A
- **funguje:** soft texture, ghost + cat right on first try
- **chyby:** -
- **opravy:** -

### `flux_dev_ink` — A
- **funguje:** no bubbles, no fixes
- **chyby:** -
- **opravy:** -

### `flux_kawaii` — A
- **funguje:** consistent, cute, no fixes
- **chyby:** -
- **opravy:** -

### `flux_manga` — A
- **funguje:** zero fixes in two stories; ghost, owl, clock, shark, mermaid all right
- **chyby:** slow
- **opravy:** -

### `flux_papercut` — A
- **funguje:** style clearly taken from the prompt alone
- **chyby:** -
- **opravy:** -

### `flux_pixar` — A
- **funguje:** holds 3–4 characters incl. animals; no fixes needed
- **chyby:** slow (40–70 s)
- **opravy:** -

### `flux_toybox` — A
- **funguje:** the most consistent characters of all; tilt-shift toy look
- **chyby:** slowest (~65 s)
- **opravy:** -

### `animagine_storybook` — B
- **funguje:** best night, lanterns and moonlight among SDXL
- **chyby:** 'storybook' → books in hands (fixed); swaps hair colours between two kids; lost the chihuahua and the acrobat once
- **opravy:** aesthetic 'illustration, painterly' and negate books; medium shots for small animals

### `atomix_space` — B
- **funguje:** excellent humans (Viktorie, captain); LoRA shows in backgrounds
- **chyby:** cat → cat-girl/anthro, blue-skinned spacewalk
- **opravy:** feral, quadruped; negate anthro, humanoid, cat ears

### `clean_webtoon` — B
- **funguje:** consistent cute characters, pastel, fast (~14 s)
- **chyby:** close-ups of animals turn abstract; duplicates a second character; fox kit's ears leak to the girl
- **opravy:** negative_extra for duplicates and animal ears; medium shot instead of close-up for animals

### `cyberreal_clay` — B
- **funguje:** plasticine figures with fingerprints once weighted
- **chyby:** drifts back to photo (a real-looking girl), a herd instead of one goat
- **opravy:** (claymation:1.4), (miniature diorama set:1.3); scene_en 'one small goat'

### `flux_riso` — B
- **funguje:** grain and good scene
- **chyby:** two-tone ink not taken
- **opravy:** -

### `flux_schnell_ink` — B
- **funguje:** ~2× faster than dev, style as good
- **chyby:** draws speech bubbles / watermarks (4 of 26 panels)
- **opravy:** scene_en without speech verbs; extra_en 'Absolutely no speech bubbles, no lettering'

### `illustrious_storybook` — B
- **funguje:** the most 'book-like' look, soft and consistent
- **chyby:** duplicate rabbits; gardener drawn as a child; ice giant missing in wide shots; black-ear weight leaked onto a hat
- **opravy:** weight the creature in a medium shot; '(old man:1.3)'; avoid strong attribute weights

### `noobai_flat` — B
- **funguje:** strong, clean graphic look; overgrown ruins look great
- **chyby:** rabbit ears on the girl, extra rabbits
- **opravy:** negate animal ears / multiple rabbits per panel

### `flux_dev_pixel` — C
- **funguje:** great scene
- **chyby:** pixel art not taken — plain cartoon
- **opravy:** a pixel-art LoRA would be needed

### `flux_stainedglass` — C
- **funguje:** good storytelling (girl + fox kit + notebook)
- **chyby:** no stained glass look; fox tail behind the girl
- **opravy:** -

### `juggernaut_book` — C
- **funguje:** two subjects slightly better than with LoRA
- **chyby:** still bleeds clothes onto the dog
- **opravy:** who_first

### `juggernaut_clay` — C
- **funguje:** close-up OK
- **chyby:** wide shots photoreal
- **opravy:** -

### `juggernaut_pixar` — C
- **funguje:** the most polished single characters
- **chyby:** merges two characters (pug wears the girl's dress); third character never appears
- **opravy:** who_first; best of 3; keep to one subject per panel

### `pony_pixar` — C
- **funguje:** girl in costume looks good
- **chyby:** never drew the pumpkin king next to the girl; kitten turned into a masked girl/raccoon
- **opravy:** feral/quadruped + anti-anthro; creature only in solo shots

### `realvis_matte` — C
- **funguje:** beautiful snow and light
- **chyby:** ignores painted styles; wrong dog breed once
- **opravy:** describe the breed in scene_en, negate wrong breeds

### `animagine_nouveau` — D
- **funguje:** pretty ornament
- **chyby:** test panel lost the fox and the action (cotton candy instead of notebook)
- **opravy:** -

### `autismmix_anime` — D
- **funguje:** -
- **chyby:** cat-girl even with anti-anthro tags
- **opravy:** -

### `cyberreal_matte` — D
- **funguje:** -
- **chyby:** photoreal, style ignored
- **opravy:** -

### `flux_schnell_pixel` — D
- **funguje:** -
- **chyby:** no pixel art; watermark text
- **opravy:** -

### `hassaku_pixar` — D
- **funguje:** -
- **chyby:** turned the rabbit anthro
- **opravy:** -

### `hassaku_storybook` — D
- **funguje:** -
- **chyby:** put bunny ears on the girl in the first test
- **opravy:** -

### `illustrious_pixar` — D
- **funguje:** -
- **chyby:** chaotic tiny characters underwater, empty classroom instead of ghost + cat
- **opravy:** -

### `juggernaut_lightning_comic` — D
- **funguje:** fast (13 s)
- **chyby:** ignores the style, photoreal child
- **opravy:** -

### `realvis_clay` — D
- **funguje:** -
- **chyby:** photoreal even with weights
- **opravy:** -

## Příběhy

| příběh | preset | remake of |
|---|---|---|
| 01_park | `clean_webtoon` |  |
| 02_more | `clean_webtoon` |  |
| 03_les | `clean_webtoon` |  |
| 04_kuchyne | `clean_webtoon` |  |
| 05_halloween | `clean_webtoon` |  |
| 06_ema | `illustrious_storybook` |  |
| 07_majak | `animagine_storybook` |  |
| 08_tereza | `illustrious_storybook` |  |
| 09_klarka | `animagine_storybook` |  |
| 10_anicka_les | `animagine_storybook` |  |
| 11_kolac | `juggernaut_pixar` |  |
| 12_more | `flux_pixar` |  |
| 13_orbita | `atomix_space` |  |
| 14_hrad | `flux_manga` |  |
| 15_dynovy_kral | `pony_pixar` |  |
| 16_mrkvicka | `noobai_flat` |  |
| 17_zako | `flux_toybox` |  |
| 18_luna | `flux_schnell_ink` |  |
| 19_bublina | `realvis_matte` |  |
| 20_mina | `cyberreal_clay` |  |
| 21_kolacova_loupez | `flux_pixar` |  |
| 22_ponorne_mesto | `flux_manga` |  |
| 23_cirkus | `animagine_storybook` |  |
| 24_ledova_zahradka | `illustrious_storybook` |  |
| 25_cokoladovy_zamek | `flux_schnell_ink` |  |
| 26_slunecni_destnik | `noobai_flat` |  |
| 27_zmrzly_kolotoc | `clean_webtoon` |  |
| 28_modra_zprava | `flux_kawaii` |  |
| 29_cukrova_vata | `flux_toybox` |  |
| 30_duch_a_kocky | `flux_dev_ink` |  |
| 31_slunecni_destnik_b | `flux_papercut` | 26_slunecni_destnik |
| 32_zmrzly_kolotoc_b | `flux_stainedglass` | 27_zmrzly_kolotoc |
| 33_modra_zprava_b | `flux_riso` | 28_modra_zprava |
| 34_cukrova_vata_b | `flux_dev_pixel` | 29_cukrova_vata |
| 35_duch_a_kocky_b | `flux_chalk` | 30_duch_a_kocky |
