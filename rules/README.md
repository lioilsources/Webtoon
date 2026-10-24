# rules/

Every rule the pipeline obeys, as data. The code (`m0/*.py`, `m0/local_strip.sh`, `backend/internal/pack`) is the
engine that reads these files; the reasons for each rule are the comments next to it.

```
rules/base/<file>.yaml        shared rules: storyboard, prompts, render, animate, compose, shorts, music, pipeline, pack
rules/profiles/<name>.yaml    harlequin | kids | free | superhero, deep-merged over base (or over `profile.extends`)
```

- Loader: `m0/rules.py` (`rules.load(file)` base, `rules.cfg(file, profile)` merged, `rules.profile(name)`), cached,
  required keys validated at load. `python3 m0/rules.py check` validates everything; shell scripts read one value
  with `python3 m0/rules.py get [<profile>:]<file>.<key>...`. `WEBTOON_RULES=<dir>` points at another copy.
- Go: `backend/internal/pack/rules.go` reads `base/pack.yaml` (gopkg.in/yaml.v3), found from the working directory up.
- Merge: mappings merge key by key, lists and values replace, `{extend: [...]}` appends to the inherited list,
  `{replace: ...}` replaces a mapping whole.
- Proof that moving the rules changed nothing: `python3 -m unittest discover m0/tests` (golden results of the
  code-only snapshot, `m0/tests/make_goldens.py`). Deliberate changes since then are listed in
  `m0/tests/test_golden.py` (taken out of both sides) and have their own tests: 2026-10-24 ambient-only loops
  (`test_ambient.py`).

## Profiles

Today's flags map onto profiles (`rules.profile_of`): `adapt.py` default / `--audience adult` → **harlequin**,
`--audience kids` → **kids**, `--free` → **free**. `--profile <name>` on adapt.py / render.py / animate.py and
`-P <name>` on local_strip.sh pick one directly. render/animate/prompts take the world's profile
(`rules.world_profile`: world.json `profile` key, else free / audience); a world no profile describes (audience
`teen`, `data/world_m0.json`) gets the base values.

| | harlequin | kids | free | superhero |
|---|---|---|---|---|
| what | SFW romance (the app) | adventure 6–12 | experiment outside the app | superhero action 6–12 |
| extends | – | – | – | kids |
| world.json | audience adult | audience kids | audience adult, `free: true` | audience kids, `profile: superhero` |
| style pool / adapt default / strip default | all / fashion_editorial / webtoon_romance | 6 flat kid styles / clean_webtoon_noartist ×2 | all / fashion_editorial / webtoon_romance | 6 comic styles / western_comic ×2 |
| prompt, schema, example | adapt_system.md, story.schema.json, santorini | adapt_system_kids.md, story.kids.schema.json, kids_park | adapt_system.md rewritten (`rewrite`), santorini fixed | as kids + `addendum_superhero.md` with the action vocabulary |
| `fence` (tags, outfits, photo) | banned | kids_sfw | age_banned | kids_sfw |
| `kids_fence` (+ bubbles) | never | kids_banned | never | kids_banned |
| motion fence | age_banned, banned, motion_actions | age_banned, kids_banned, kids_sfw, motion_actions | age_banned | as kids |
| allowed phrases (masked before fences) | – | – | – | action vocabulary (energy blast, punch, sword clash, explosion, motion lines, …) |
| required character keys | id name gender base outfits photo | + kind | as harlequin | as kids |
| age rules | photo_adult_age (23+) | kids_photo_age by kind (child 6–13, adult 23+) | photo_adult_age + free_base_adult | as kids |
| panel rules | same_gender, couple_not_closeup | kids_max_humans (2), kids_group_not_closeup | as harlequin + free_bubble_age | as kids |
| to_m0 tone / fonts / couple tags | romantický…, romance, couple hetero | dobrodružný…, default, – | romantický…, romance, couple hetero | akční, hrdinský, laskavý, default, – |
| prompt negative | styles adult_negative | styles kids_negative | age tags | as kids |
| WD14 limits | rating (explicit .2, questionable .3) + neckline tags | rating + sensitive .5 | age tags only | as kids |
| loop negative tail | nsfw, nude, cleavage, underwear | as harlequin | child, childlike face, aged down | as kids |
| strip prefix / out day | lx_ / local | lx_ / local | lxf_ / local_free | lx_ / local |
| pack | adult, exported | kids, exported | never exported (`forbidden_world_prefix`) | kids, exported |

## base/storyboard.yaml — adapt.py `check()` / `missing_fields()` / `to_m0()`

`checks` is a list of scopes (story, character → character_field, panel → panel_character, bubble); rules run in
file order, so the errors come out in the order the old code produced them. A rule is
`{id, profiles, if: <violation>, message: <str.format template>}`; the condition language
(`all/any/not`, `truthy/falsy`, `eq/ne/in/not_in/gt/ge`, `search/match {regex, in, mask}`, `contains`,
`intersects`, `long_items`, refs `$name.key.0`, `?` optional, `|len`) is documented in `m0/rules.py`.
`required` drives `missing_fields()` (reported first; any missing key stops the other checks).

| id | scope | profiles | what | why |
|---|---|---|---|---|
| char_banned_term | character_field | all | no `fence` / `kids_fence` term in base, photo, any outfit | code-side SFW fence, whatever the model says |
| free_base_adult | character | free | base has `adult` and `mature female`/`mature male` | the age anchor once the SFW fence is gone |
| kids_child_base | character | kids | a child's base starts `female child, ` / `male child, ` | the count/age anchor leads the prompt |
| kids_adult_base | character | kids | an adult's base starts `adult, mature (fe)male, ` | same |
| kids_nonhuman_words | character | kids | creature/robot/spirit: no human words in base + photo | a human word turns the dog into a dog-eared kid |
| kids_human_gender | character | kids | child/adult gender is f or m | the count tag 1girl/1boy comes from it |
| photo_no_clothing | character | all | photo sentence names no clothes | photo is identity; clothes are outfits (change per panel) |
| photo_adult_age | character | harlequin, free | photo says `aged N`, N ≥ 23 | adults only |
| kids_photo_age | character | kids | `aged N` by kind (child 6–13, adult ≥ 23) | ages the drawing; creatures state none |
| first_panel_establishing | story | all | panel 0 is an establishing shot without characters | the strip opens on the place |
| last_panel_gap | story | all | last gap_after is large | the end beat before "Konec" |
| max_animated | story | all | ≤ limits.max_animated (2) animated panels | one Wan loop ≈ 11 stills |
| motion_required | panel | all | animate needs a motion prompt | – |
| motion_banned | panel | all | no term of the profile's motion fence in motion | Wan cannot keep two bodies apart; no undressing |
| motion_two_people_ambient | panel | all | 2+ characters: motion starts "ambient only, characters still" (since 2026-10-24; before, any ambient / only / static passed) | Wan merges two moving bodies |
| character_motion_verbs | panel | all | 2+ characters: no word that moves a character (dancing, running, jumps, turns, waving, rises, walks, …) | the loop moves the surroundings only |
| known_location | panel | all | location_id exists | – |
| known_character | panel_character | all | character id exists | – |
| known_outfit | panel_character | all | a named outfit exists | – |
| kids_max_humans | panel | kids | ≤ 2 humans per panel | NoobAI draws at most two humans; the rest are companions |
| kids_group_not_closeup | panel | kids | 2+ characters never a close-up | collage risk |
| same_gender | panel | harlequin, free | two characters are not the same gender | SDXL swaps/merges same-gender designs; hetero romance app |
| couple_not_closeup | panel | harlequin, free | a couple is never a close-up | collage risk |
| establishing_empty | panel | all | establishing shots have no characters | – |
| banned_tag | panel | all | no fence term in visual_tags | – |
| free_bubble_age | panel | free | no age term in bubbles | free lifts the SFW fence on text, never the age one |
| kids_bubble | panel | kids | no kids_banned term in bubbles | no blood, death or kissing in reader text |
| narration_no_speaker | bubble | all | narration has empty speaker_id | – |
| speaker_in_panel | bubble | all | a speaker is in the panel | – |
| tags_not_sentences | panel | all | with a vocabulary: no unknown tag over 6 words | real booru tags run to ~6 words |

Also here: the regex library (`banned`, `age_banned`, `kids_sfw` = banned − child, `kids_banned`, …, as word
lists), `limits`, `age_by_kind`, `human_kinds`, the shared `to_m0` mapping (count tag by kind + gender, roles,
sfx style), `adapt` attempts / temperatures / language, and `pick_motion` (≤ 2 loops picked for a rendered story).

## base/prompts.yaml — prompts.py

| rule | what | why |
|---|---|---|
| regex.design | scene tags naming hair/eyes/clothes are dropped | the character's tag_prompt owns the design |
| regex.expression | … unless they describe a moment (closed eyes, wet hair, looking …) | expression, not design |
| regex.lower / feet | close-up drops lower-body tags, medium/over-shoulder drop feet | out of frame tags pull the camera back |
| regex.color + color_weight | hair/eye colours weighted 1.2 | colour tells two people apart; style tags wash it out |
| age_anchor | shared prompt of a regional two-shot keeps adult / mature female / mature male | it still says who is adult |
| count_tags | the storyboard's own count tags are dropped | count_tags() derives them from the characters |
| negative | audience negative (per profile) | kids/adult lists of styles.json; free: age tags |
| close_up_location_tags | close-up keeps 3 location tags | a full scene description pulls the camera back |
| default_size | 832×1216 for a shot missing in styles.json | – |
| natural.* | photoreal presets: couple / one / group leads, `, wearing …` | photoreal models drop the second person unless the pair leads |

## base/render.yaml — render.py (and animate.py's safety check)

| rule | what | why |
|---|---|---|
| rating_limits | WD14 rating thresholds (explicit .2, questionable .3; profiles extend/replace) | audience-safe panels |
| tag_limits | general-tag limits (profiles: harlequin neckline, free age) | fashion yes, neckline-dominated no; free stays adult |
| max_reseed | 2 redraws of an unsafe panel | then status failed: never imported |
| design_threshold | 0.35 confidence for identity recall | – |
| ip_adapter | weights 0.6 (--ref) / 0.5 (--char-refs), preset, end 0.8 | a sheet at full strength drags pose and backdrop in; burns NoobAI colours |
| sheet_tags | pose/backdrop of a character sheet | – |
| wd14_tags | general tags ≥ 0.35, top 40, stored per panel in meta.json | animate.py builds the ambient loop from them |

## base/animate.yaml — animate.py

| rule | what | why |
|---|---|---|
| fps | 16, length 4n+1 | Wan native rate; VAE compresses time 4:1 |
| size | 480×704 / 704×480 | ~0.34 Mpx, upscaled in the strip; HD costs 5× |
| negative.common + tail | Wan artefacts + SFW tail (free: age tail) | free lifts SFW, never adults-only |
| style_tail_tags | 4 aesthetic tags of the preset appended | the loop keeps the look |
| default_motion | for --panels without a motion prompt | – |
| webp_quality | 80 | – |
| ambient.template / template_empty / template_single | 2+ characters: "ambient only, characters still, {ambient}, static camera"; establishing: "ambient only, {ambient}, static camera"; one character: storyboard motion + ambient | Wan swaps or merges two moving bodies |
| ambient.from_tags / max_phrases / default | WD14 tag → phrase (rain → rain falling, night/starry sky → stars twinkling, fire/torch → flames flickering, water/ocean/river → water rippling, cloud/sky → clouds drifting slowly, tree/leaf/forest → leaves swaying, smoke → smoke swirling, glowing/aura/magic → soft glow pulsing, bubble → bubbles rising, …), ≤ 3, else "dust motes floating, light shifting" | the still's own features move; a run without meta.json wd14_tags keeps the storyboard motion |

The per-story loop limit is `storyboard.limits.max_animated`.

## base/compose.yaml — compose.py

| rule | what | why |
|---|---|---|
| width | 800 px strip | – |
| gaps / default_gap | small 40, medium 140, large 320 | reading rhythm |
| fonts.default / fonts.romance | children's bundled fonts / macOS system fonts per bubble kind | grown-up lettering for romance; Avenir Next covers Czech (Gill Sans does not) |
| bubble.* | font sizes 26/30, width 0.62/0.8, inset, line height, pad, margin, narration fill | no bboxes in M0: corners alternate |
| sfx, title, texts | sfx 64 px yellow, title 54/66, "Konec", "Co udělá dál?" | – |

## base/shorts.yaml — shorts.py

| rule | what | why |
|---|---|---|
| frame | 1080×1920 at 30 fps | 9:16 |
| top / bottom | no lettering above 200 px / in the bottom 380 px | TikTok/Shorts top bar, caption and buttons |
| fade | 0.35 s crossfade | – |
| font_scale | 2.2 × compose.py letters | an 800 px strip's letters are small on a phone |
| panel_duration | clamp(1.8 + 0.07 × characters, 2.5, 6.0) s | as long as the text takes to read |
| loop | ≥ 4.0 s with a loop, frames at 16 fps | two passes of a 2 s loop |
| zoom | 8 % portrait, 5 % landscape over the panel | slow movement |
| cards | title 1.8 s / 96 px, end 2.0 s / 120 px | – |
| end | end card text by language, default "The End" | – |

Free worlds are refused by `base/pack.yaml forbidden_world_prefix` (shared with the Go pack).

## base/music.yaml — music.py

| rule | what | why |
|---|---|---|
| length | 80 s requested | ACE-Step returns 9–19 % short; longest short ~65 s; shorts loop anyway |
| window | 07:05–12:45 | audio is down while the big LLMs run (Director's rule) |
| model | acestep-v15-turbo must be available | never start audio-music yourself; ask Director |
| prompt_suffix, seed_base | ", instrumental, no vocals", seed 4200 + k | instrumental only; stable reruns |
| moods | 15 mood prompts | shorts.py picks one per world (a series keeps its sound) |

## base/pipeline.yaml — local_strip.sh

| rule | what | why |
|---|---|---|
| strip.prefix / day | lx_ / local (free: lxf_ / local_free) | own reader category; free never published |
| strip.wait_seconds | 300 s poll | waiting for the LLM / ComfyUI window |
| strip.deadline | 13:00 in the morning window, else now + 60 min, never past 23:59 | ComfyUI window; HH:MM compared as strings |

Default styles: the profile's `styles.strip_default`.

## base/pack.yaml — backend export-pack

| rule | what | why |
|---|---|---|
| part_size | 25 stories per zip | store download sizes |
| webp_quality | cwebp -q 85 | – |
| cover | 416×608 centre crop | story cover aspect |
| forbidden_world_prefix | w_lxf_ never exported (shorts.py too) | free strips are never published |
| dropped_episode_fields | error, created_at, updated_at | server state the offline reader does not need |
