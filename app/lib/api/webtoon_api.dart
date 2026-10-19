import 'dart:typed_data';

import 'package:flutter/widgets.dart';

import '../models/author.dart';

import '../models/campaign.dart';
import '../models/episode.dart';
import '../models/world.dart';

/// Error from the backend (`{"error": "..."}`) or the network, with a Czech message for the UI.
class ApiException implements Exception {
  final int? statusCode;
  final String message;

  const ApiException(this.message, {this.statusCode});

  @override
  String toString() => message;
}

/// Result of POST /campaigns.
class CreatedCampaign {
  final Campaign campaign;
  final String? firstEpisodeId;
  const CreatedCampaign(this.campaign, this.firstEpisodeId);
}

/// The reader's view of the Go backend (backend/README.md "API"). [HttpWebtoonApi] talks HTTP;
/// tests use a fake.
abstract class WebtoonApi {
  /// The user the requests are made as (`X-User-ID`).
  String get userId;

  /// GET /worlds — public worlds plus the caller's own.
  Future<List<WorldSummary>> listWorlds();

  /// GET /worlds/{id}
  Future<World> getWorld(String id);

  /// GET /campaigns — the caller's campaigns.
  Future<List<CampaignSummary>> listCampaigns({String? worldId});

  /// POST /campaigns {world_id, player_character_id} → first episode is enqueued.
  Future<CreatedCampaign> createCampaign({
    required String worldId,
    String? playerCharacterId,
    String? title,
  });

  /// GET /campaigns/{id}
  Future<Campaign> getCampaign(String id);

  /// POST /campaigns/{id}/episodes {choice_id | free_text, director} → new episode id.
  Future<String> continueCampaign(
    String campaignId, {
    String? choiceId,
    String? freeText,
    DirectorRequest? director,
  });

  /// GET /episodes/{id}
  Future<Episode> getEpisode(String id);

  /// PATCH /episodes/{id}/panels/{n} {"bubbles": [...]}
  Future<Panel> updateBubbles(
    String episodeId,
    int panel,
    List<Bubble> bubbles,
  );

  /// PATCH /episodes/{id}/panels/{n} {"regenerate": true}
  Future<Panel> regeneratePanel(String episodeId, int panel);

  /// PATCH /episodes/{id}/panels/{n} with any of `animate`, `motion`, `loop_seconds`,
  /// `reseed_video` — turns the panel's 1–3 s loop on/off or re-renders it.
  Future<Panel> updatePanelMotion(
    String episodeId,
    int panel,
    Map<String, dynamic> patch,
  );

  /// Image for a panel's `image_url` (also used for any `/media/...` URL).
  ImageProvider panelImage(String imageUrl);

  // --- author (M3) ---------------------------------------------------------------

  /// GET /worlds?owner=me — only the caller's own worlds.
  Future<List<WorldSummary>> listMyWorlds();

  /// GET /style_presets
  Future<List<StylePreset>> listStylePresets();

  /// POST /worlds {title, style_id, ...fields}
  Future<World> createWorld({
    required String title,
    required String styleId,
    Map<String, dynamic> fields = const {},
  });

  /// PATCH /worlds/{id} with any subset of the world fields.
  Future<World> updateWorld(String worldId, Map<String, dynamic> patch);

  /// GET /worlds/{id}/stats (owner only).
  Future<WorldStats> getWorldStats(String worldId);

  /// POST /worlds/{id}/characters
  Future<Character> createCharacter(
    String worldId,
    Map<String, dynamic> fields,
  );

  /// PATCH /worlds/{id}/characters/{cid}
  Future<Character> updateCharacter(
    String worldId,
    String characterId,
    Map<String, dynamic> patch,
  );

  /// DELETE /worlds/{id}/characters/{cid}
  Future<void> deleteCharacter(String worldId, String characterId);

  /// POST /worlds/{id}/characters/{cid}/tag_prompt — LLM suggestion, not saved.
  Future<TagSuggestion> suggestCharacterTags(
    String worldId,
    String characterId, {
    String? description,
  });

  /// POST /worlds/{id}/characters/{cid}/sheet → 202 sheet job.
  Future<CharacterSheet> createSheet(
    String worldId,
    String characterId, {
    int seeds = 4,
  });

  /// GET /worlds/{id}/characters/{cid}/sheets (newest first).
  Future<List<CharacterSheet>> listSheets(String worldId, String characterId);

  /// GET /sheets/{id}
  Future<CharacterSheet> getSheet(String sheetId);

  /// POST /worlds/{id}/characters/{cid}/references (multipart "file").
  Future<Character> uploadCharacterReference(
    String worldId,
    String characterId,
    Uint8List bytes,
    String filename,
  );

  /// POST /worlds/{id}/locations
  Future<Location> createLocation(String worldId, Map<String, dynamic> fields);

  /// PATCH /worlds/{id}/locations/{lid}
  Future<Location> updateLocation(
    String worldId,
    String locationId,
    Map<String, dynamic> patch,
  );

  /// DELETE /worlds/{id}/locations/{lid}
  Future<void> deleteLocation(String worldId, String locationId);

  /// POST /worlds/{id}/locations/{lid}/tag_prompt
  Future<TagSuggestion> suggestLocationTags(
    String worldId,
    String locationId, {
    String? description,
  });

  /// POST /worlds/{id}/locations/{lid}/references (multipart "file").
  Future<Location> uploadLocationReference(
    String worldId,
    String locationId,
    Uint8List bytes,
    String filename,
  );
}

/// Czech text for an HTTP status when the body has no usable message.
String czechStatus(int code) => switch (code) {
  400 => 'Neplatný požadavek',
  401 => 'Chybí přihlášení (X-User-ID)',
  403 => 'Na tohle nemáš oprávnění',
  404 => 'Nenalezeno',
  409 => 'Konflikt — něco se právě generuje',
  413 => 'Soubor je moc velký',
  503 => 'LLM teď neběží (GPU server mimo rozvrh), zkus to později',
  >= 500 => 'Chyba serveru',
  _ => 'HTTP $code',
};

/// Backend messages are English; translate the ones a reader can hit.
String czechError(String msg, int code) {
  const known = {
    'an episode is still being generated': 'Díl se ještě generuje.',
    'campaign reached max_episodes of this world':
        'Kampaň dosáhla maximálního počtu dílů tohoto světa.',
    'panel is already being rendered': 'Panel se už kreslí.',
    'only the campaign\'s player can continue it':
        'Pokračovat může jen hráč této kampaně.',
    'only the campaign\'s player can edit panels':
        'Upravovat panely může jen hráč této kampaně.',
    'that character is not playable for you': 'Za tuhle postavu hrát nemůžeš.',
    'the previous episode does not offer a free choice':
        'Předchozí díl nenabízí volnou odpověď.',
    'missing X-User-ID': 'Chybí přihlášení (X-User-ID).',
    'not found': 'Nenalezeno.',
    'only the world owner can edit it': 'Svět může upravovat jen jeho autor.',
    'only the world owner can add locations':
        'Lokace může přidávat jen autor světa.',
    'only the world owner can see stats': 'Statistiky vidí jen autor světa.',
    'character is the player character of a campaign':
        'Postavu nejde smazat, hraje za ni hráč v některé kampani.',
    'file must be a PNG or JPEG image':
        'Soubor musí být obrázek PNG nebo JPEG.',
    'file too large (max 8 MiB)': 'Soubor je moc velký (max. 8 MiB).',
    'unknown style_id': 'Neznámý výtvarný styl.',
    'title and style_id are required': 'Vyplň název a vyber styl.',
  };
  if (code == 503) {
    return 'LLM teď neběží (GPU server mimo rozvrh), zkus to později.';
  }
  if (known.containsKey(msg)) return known[msg]!;
  if (msg.startsWith('free_text longer than')) {
    return 'Text je moc dlouhý (max. 500 znaků).';
  }
  return msg.isEmpty ? czechStatus(code) : '${czechStatus(code)}: $msg';
}
