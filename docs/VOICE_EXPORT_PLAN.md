# Voice cloning (IAP) and TikTok/YT export

Olin's decisions, 2026-11-11:
- the video is rendered **on the phone** from the installed pack: panels and loops, subtitles instead of bubbles,
  a music track, and a dub;
- the dub uses the **system TTS** voices by default (iOS AVSpeechSynthesizer, Android TextToSpeech, which have
  Czech and most of the app's languages);
- "Your voice" is an **in-app purchase**. The player records 5–30 s, as in Hajánek, and the lines of the player's
  character are then spoken in that voice;
- the clone engine is **chatterbox-cs**, at the company's risk. Its licence is unverified; XTTS is
  non-commercial and is not used for the IAP;
- **Director builds the server side** (public player API, voice upload, Spark worker). This repo's app side
  follows the contract below.

## Phase 1: export, on the phone, no server

| Piece | Where | Notes |
|---|---|---|
| Lines and timing | `app/lib/export/dub_plan.dart` | Same rules as m0/shorts.py `--dub`: narration first, lead 0.25 s, gap 0.3 s, tail 0.5 s. A panel stays up while its lines are spoken; with no voice, its duration comes from the reading-time rule. |
| Voices | `app/lib/export/voices.dart` | Each speaker gets a system voice: the player's character, partner, and machines/narration. Pitch and rate give the robot. A purchased clone replaces the player's character's voice. |
| TTS to file | `flutter_tts` `synthesizeToFile` | The wav's duration times the panel. |
| Frames | `dart:ui` | Each panel (cover crop, slow zoom; landscape on a blurred copy; loops frame by frame) plus a subtitle layer. 720×1280, 30 fps, crossfade 0.35 s. |
| Encoder | platform channel `toonfork/video` | iOS: AVAssetWriter, H.264 + AAC. Android: MediaCodec + MediaMuxer. Takes RGBA frames and one mixed PCM track. No ffmpeg: LGPL/GPL, size, and App Store issues. |
| Audio mix | Dart | Voice lines placed at their times plus music under them, ducked to 0.35. |
| Music | `app/assets/music/` | A few tracks bundled with the app (about 2 MB each); later per pack. |
| UI | episode end block / reader menu | Export button → sheet: language, voice on/off, subtitles on/off, music. Shows progress, then the system share sheet (TikTok, YouTube, Photos, Files). |
| Branding | last card | "Toonfork" end card with the store link text, plus voice attributions (Kasandra CC BY) when used. |

Free episodes and every bought pack can be exported. Free strips (`lxf_`) never can, the same as shorts.py.

## Phase 2: Your voice (IAP)

- Product `voice_clone` (non-consumable, Tier 1 / 0.99 USD like a pack), added to tools/products.csv, App Store Connect and
  Play.
- Recording screen, ported from Hajánek (`features/voice/record_voice_screen.dart`, package `record`):
  - consent checkbox, with the consent sentence read first on the teleprompter;
  - 5–30 s of a Czech script;
  - AAC m4a.
- Upload and synthesis go only through the public API below; the app never talks to Spark.
- In the export sheet, "Your voice" applies to the player's character (`olin_*` in the guláš books, generally the
  episode's `player_character_id`). The phone fetches every line of that speaker for the episode as audio
  from the server, then renders the video as in phase 1.
- Settings: "Delete my voice" (DELETE on the server, then the local state).
- Behind a feature flag `--dart-define=VOICE_CLONING=true` until the server is live.
- Store work:
  - privacy labels / data safety: audio recording, linked to a device ID, deletable;
  - privacy policy text;
  - App Review notes.

## Server contract (for Director)

Public API (`https://webtoon-api.ol1n.com/v1/player/...`, or a separate host):
- Auth is an anonymous device token, the same as Hajánek: `Authorization: Bearer <token>`, from
  `POST /v1/player/devices`.
- `POST /v1/player/voices` (multipart):
  - fields: `sample` (m4a, 5–30 s), `consent=true`, `consent_text`, and `receipt` (App Store / Play receipt of
    `voice_clone`, verified server-side);
  - returns `{voice_id, status}`.
- `GET /v1/player/voices/{id}` → `{status: queued|ready|failed, error}`.
- `DELETE /v1/player/voices/{id}` deletes the sample and the AiStack voice.
- `POST /v1/player/voices/{id}/lines` with `{lang:"cs", lines:[{key, text}]}` (at most 200 lines, 300 chars each)
  returns `{job_id}`.
- `GET /v1/player/jobs/{job_id}` → `{status, lines:[{key, url, duration_s}]}`; each url is a short-lived wav or m4a.
- Worker on Spark (sparkctl lease `tts`):
  - create: AiStack `POST /v1/audio/voices`, with `rights=own` and `source=toonfork-app`;
  - lines: `POST /v1/audio/tts` with `engine=chatterbox`, `language=cs`, `commercial_only=false`;
  - it trims, then loudnorms to -16 LUFS.
- Limits: one voice per device and a daily line quota.

## Order of work

1. Phase 1 in the app (this repo), as a TestFlight / internal-track build behind `EXPORT_VIDEO=true`.
2. Director: the server contract above.
3. Phase 2 in the app, with the IAP product.
4. Store submission of the next version (1.1), after 1.0 is approved.
