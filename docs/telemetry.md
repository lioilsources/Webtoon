# Anonymous usage statistics

The Toonfork reader sends a small set of anonymous events through
[`ol1n_telemetry`](https://github.com/lioilsources/Ol1nTelemetry) so the
owner can see where new readers drop off, how far they read, whether gamebooks
and the branch editor are used and where purchases and downloads fail. This
file is the **event dictionary**: the constant `toonforkDictionary`
(`app/lib/telemetry/telemetry_dictionary.dart`) and this document list exactly
the same events and properties, and `app/test/telemetry_test.dart` fails when
they drift apart.

Adding an event or a property is a change to the privacy policy
(`docs/privacy.html`) and to the store privacy answers. Ask the owner first.

## Rules

The rules of `ol1n_telemetry` apply unchanged: no persistent identifier (a
random session id kept in memory only), cohorts computed on the device, only
enums, bands and numbers, no key → no network, off wipes the queue at once,
the app never waits for it and nothing in the app reads it. See the package
README. On top of them:

- **The Kids profile is never measured** (plan §4.14). Measuring is suspended
  while the profile is Kids, and also on a first launch until a profile is
  chosen (the phone may be a child's). Only switching to Adults resumes it;
  switching to Kids suspends it before anything is shown. While suspended
  nothing is recorded or sent, not even the launch. The statistics switch is
  not shown in the Kids profile.
- **Studio builds measure nothing.** `WEBTOON_STUDIO=true` builds (the private
  backend client with the author tools) never initialise the client.
- **Nothing about the stories, nothing the reader types.** No story, world,
  pack or episode id, no title, bubble, choice text, branch text or gate
  answer. An episode is only its number in its story; a product is only its
  kind (`pack`, `bundle`, `gamebook`, `kit`).
- The receiver is the developer's own server in the EU (StoreMetrics on JODA).
  It keeps the country from the connection and never stores the IP address.
  Raw events are kept 12 months.

## Configuration

| `--dart-define` | Meaning |
|---|---|
| `TELEMETRY_KEY` | The app's key at the receiver. Empty → nothing is sent. |
| `TELEMETRY_HOST` | The receiver, `https` only. Empty → nothing is sent. |
| `TELEMETRY_DEBUG` | `true` prints events to the console instead of sending them. |
| `TELEMETRY_TESTER` | `true` marks the build's events as a tester's. |

The release workflows (`release-android`, `release-ios`, `release-macos`) pass
`TELEMETRY_KEY` and `TELEMETRY_HOST` from the GitHub secrets of the same
names. An absent secret expands to an empty string and the build is silent.
The key and the receiver address never go into this public repository.

The client keeps its few values (install day, session counter, the switch,
the offline queue) under `telemetry_*` keys in SharedPreferences. An install
that already had any other saved value when measuring began counts as `pre`
(not a new install).

## Activation

The first episode read to its end: the end block of an episode came into view
in the reader (`episode_read_end` with `result: ok`), or a gamebook node was
finished.

## Features

`history` (episode list in the reader), `bubble_language` (changing the bubble
language in Settings or in the reader), `gamebook_map` ("My path"),
`gamebook_back` (one step back), `gamebook_revisit` (re-reading a visited
chapter), `gamebook_restart`, `branch_editor` (opening the editor kit),
`app_icon`, `restore_purchases`, `reinstall_starter`, `pack_delete`.

## Common properties

Sent with every event.

| Property | Type | Values |
|---|---|---|
| `app_version` | enum | the app version (`kAppVersion`, checked against `pubspec.yaml`) |
| `platform` | enum | `ios`, `android`, `macos`, `windows`, `linux`, `other` |
| `lang` | enum | the UI language (follows the bubble language; `cs` for the original): `cs`, `en`, `de`, `it`, `fr`, `pl`, `pt-BR`, `ja`, `ko`, `vi`, `ru`, `uk` |
| `session_band` | enum | session number: `1`, `2`, `3-5`, `6-10`, `11+` |
| `days_band` | enum | days since measuring began: `0`, `1`, `2-6`, `7-29`, `30+`, `pre` |
| `first_session` | bool | the very first session of a new install |
| `tester` | bool | tester build (`TELEMETRY_TESTER`, `WEBTOON_FAKE_IAP`) or tester device |
| `bubbles` | enum | the bubble language: `original`, `cs`, `en`, `de`, `it`, `fr`, `pl`, `pt-BR`, `ja`, `ko`, `vi`, `ru`, `uk` |

## Events

### `app_open`

Cold start, or a new session after more than 30 minutes in the background. In a session that began suspended (Kids, or no profile chosen yet) it comes when the reader switches to Adults.

Answers: what a new reader does after the first launch (the first-session funnel starts here); whether they come back (2nd, 3rd, 6th, 11th session; day 1, 2, 7, 30).

| Property | Type | Values |
|---|---|---|
| `start` | enum | `cold`, `resume` |
| `session_band_first` | bool | yes/no |
| `days_band_first` | bool | yes/no |
| `campaign` | campaign | optional, `^[a-z0-9-]{1,24}$` |

### `screen_view`

A screen appeared. The tabs, the start-up splash and the first-launch profile chooser are the home route; everything pushed on it has a route name (`kScreenRoutes`).

Answers: what a new reader does after the first launch; skipping back and forth (A → B → A).

| Property | Type | Values |
|---|---|---|
| `screen` | enum | `splash`, `profile_chooser`, `library`, `store`, `settings`, `reader`, `pack_detail`, `gamebook`, `gamebook_revisit`, `gamebook_preview`, `branch_editor`, `branch_node`, `other` |
| `prev` | enum | `splash`, `profile_chooser`, `library`, `store`, `settings`, `reader`, `pack_detail`, `gamebook`, `gamebook_revisit`, `gamebook_preview`, `branch_editor`, `branch_node`, `other`, `none` |

### `screen_leave`

A screen was left.

Answers: how long readers stay on which screen (median, 90th percentile, by session band); screens with a long stay and no action.

| Property | Type | Values |
|---|---|---|
| `screen` | enum | `splash`, `profile_chooser`, `library`, `store`, `settings`, `reader`, `pack_detail`, `gamebook`, `gamebook_revisit`, `gamebook_preview`, `branch_editor`, `branch_node`, `other` |
| `secs` | int | 0–86400 |
| `actions` | int | 0–100000 |

### `session_pause`

The app went to the background or is closing. Sent at once.

Answers: when and where readers leave the app (active seconds and the screen of the last pause).

| Property | Type | Values |
|---|---|---|
| `active_secs` | int | 0–86400 |
| `screen` | enum | `splash`, `profile_chooser`, `library`, `store`, `settings`, `reader`, `pack_detail`, `gamebook`, `gamebook_revisit`, `gamebook_preview`, `branch_editor`, `branch_node`, `other`, `none` |
| `screen_secs` | int | 0–86400 |

### `activation`

The first episode read to its end on this install: the end block of an episode of the reader came into view, or a gamebook node was finished (a choice or "Continue" taken, or an ending reached). Once per install.

Answers: how many new installs get to the first real reading, and how fast.

| Property | Type | Values |
|---|---|---|
| `secs` | int | 0–86400 |

### `feature_use`

The first use of a feature in a session (see Features).

Answers: which features advanced readers use.

| Property | Type | Values |
|---|---|---|
| `feature` | enum | `history`, `bubble_language`, `gamebook_map`, `gamebook_back`, `gamebook_revisit`, `gamebook_restart`, `branch_editor`, `app_icon`, `restore_purchases`, `reinstall_starter`, `pack_delete` |

### `feature_snapshot`

After `app_open` of the 3rd, 6th and 11th session: which features this install has ever used.

Answers: what advanced readers do not use.

| Property | Type | Values |
|---|---|---|
| `f_history` | bool | yes/no |
| `f_bubble_language` | bool | yes/no |
| `f_gamebook_map` | bool | yes/no |
| `f_gamebook_back` | bool | yes/no |
| `f_gamebook_revisit` | bool | yes/no |
| `f_gamebook_restart` | bool | yes/no |
| `f_branch_editor` | bool | yes/no |
| `f_app_icon` | bool | yes/no |
| `f_restore_purchases` | bool | yes/no |
| `f_reinstall_starter` | bool | yes/no |
| `f_pack_delete` | bool | yes/no |
| `features_used` | int | 0–11 |

### `error_shown`

The reader saw an error: the starter pack failed to load (`pack_load`), a story failed to open (`reader_load`), Obchod has no catalog at all (`catalog`), a download (`download`), a purchase (`purchase`) or "Restore purchases" (`restore`) failed.

Answers: where advanced readers struggle.

| Property | Type | Values |
|---|---|---|
| `kind` | enum | `pack_load`, `reader_load`, `catalog`, `download`, `purchase`, `restore` |
| `screen` | enum | `splash`, `profile_chooser`, `library`, `store`, `settings`, `reader`, `pack_detail`, `gamebook`, `gamebook_revisit`, `gamebook_preview`, `branch_editor`, `branch_node`, `other`, `none` |

### `episode_read_start`

The reader started an episode of a story: opened from the library (`library`) or from the "next story" card after the end (`next_story`), jumped to it from the episode list (`history`), or went on to it after the previous one (`continue`). `index` is the episode number in its story (1-based).

Answers: what a new reader does after the first launch; how far into a story readers get.

| Property | Type | Values |
|---|---|---|
| `index` | int | 0–1000 |
| `from` | enum | `library`, `next_story`, `history`, `continue` |

### `episode_read_end`

The episode ended: its end block came into view (`ok`; `last` = it was the story's last episode, the story is finished), the reader jumped to another episode (`skip`), left the reader (`cancel`) or the app went to the background and never came back (`background`). `secs` counts foreground time only.

Answers: where readers stop inside a story and how long an episode takes; how many stories are finished.

| Property | Type | Values |
|---|---|---|
| `result` | enum | `ok`, `cancel`, `error`, `background`, `skip` |
| `secs` | int | 0–86400 |
| `index` | int | 0–1000 |
| `last` | bool | yes/no |

### `gamebook_open`

A gamebook was opened. `resume`: it continues saved progress; `found`: good endings found so far.

Answers: whether gamebook readers come back to a book.

| Property | Type | Values |
|---|---|---|
| `resume` | bool | yes/no |
| `found` | int | 0–100 |

### `gamebook_choice`

A step in a gamebook: a choice of the book (`choice`), one of the reader's own branches (`own`) or "Continue" of a linear node (`next`). `step` is the length of the path so far. Not in an editor preview.

Answers: how deep readers get into a gamebook and whether own branches are played.

| Property | Type | Values |
|---|---|---|
| `kind` | enum | `choice`, `own`, `next` |
| `step` | int | 0–10000 |

### `gamebook_ending`

An ending card was shown: a good ending (`good`; `first` = found for the first time), a dead end with "Try again" (`retry`) or the end of an own branch (`own`). `found` / `total` are good endings found / in the book.

Answers: where readers struggle in a gamebook (dead ends) and whether they look for all endings.

| Property | Type | Values |
|---|---|---|
| `ending` | enum | `good`, `retry`, `own` |
| `first` | bool | yes/no |
| `found` | int | 0–100 |
| `total` | int | 0–100 |

### `branch_edit`

An action in the branch editor (beta, the editor kit): a new or deleted branch, an image added, removed or moved, bubbles edited, a choice added or removed, a branch played, the branches exported. Nothing of what the reader writes.

Answers: whether the editor kit is used and how far people get in it.

| Property | Type | Values |
|---|---|---|
| `action` | enum | `new_branch`, `delete_branch`, `add_image`, `remove_image`, `move_image`, `bubbles`, `add_choice`, `remove_choice`, `play`, `export` |

### `purchase_gate`

The parental gate before a purchase was closed: `passed` or not. Nothing about the question or the answers.

Answers: where purchases are lost (gate drop-off).

| Property | Type | Values |
|---|---|---|
| `passed` | bool | yes/no |

### `purchase_start`

A purchase started (after the gate). `product`: the kind of product.

Answers: which products readers try to buy.

| Property | Type | Values |
|---|---|---|
| `product` | enum | `pack`, `bundle`, `gamebook`, `kit`, `other` |

### `purchase_end`

The store answered: bought (`ok`), cancelled (`cancel`), failed (`error`), or the app went to the background and never came back (`background`).

Answers: the share of purchases that are cancelled or fail, and how long they take.

| Property | Type | Values |
|---|---|---|
| `result` | enum | `ok`, `cancel`, `error`, `background` |
| `secs` | int | 0–86400 |

### `pack_download_start`

A pack or gamebook download started. `update`: an older version is installed.

Answers: how long downloads take and whether updates are taken.

| Property | Type | Values |
|---|---|---|
| `kind` | enum | `pack`, `gamebook` |
| `update` | bool | yes/no |

### `pack_download_end`

The download ended: installed (`ok`), failed (`error`), or the store screen went away (`cancel`).

Answers: the share of downloads that fail, and how long they take.

| Property | Type | Values |
|---|---|---|
| `result` | enum | `ok`, `cancel`, `error`, `background` |
| `secs` | int | 0–86400 |

### `packs_ready`

Start-up: the installed packs are loaded, `extracted` = the bundled starter pack was (re)extracted. `ms` is the time it took.

Answers: how long the splash keeps a new reader waiting (load time).

| Property | Type | Values |
|---|---|---|
| `ms` | int | 0–600000 |
| `extracted` | bool | yes/no |
