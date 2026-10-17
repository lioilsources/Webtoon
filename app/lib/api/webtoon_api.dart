import 'package:flutter/widgets.dart';

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

  /// Image for a panel's `image_url`.
  ImageProvider panelImage(String imageUrl);
}

/// Czech text for an HTTP status when the body has no usable message.
String czechStatus(int code) => switch (code) {
  400 => 'Neplatný požadavek',
  401 => 'Chybí přihlášení (X-User-ID)',
  403 => 'Na tohle nemáš oprávnění',
  404 => 'Nenalezeno',
  409 => 'Konflikt — něco se právě generuje',
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
  };
  if (known.containsKey(msg)) return known[msg]!;
  if (msg.startsWith('free_text longer than')) {
    return 'Text je moc dlouhý (max. 500 znaků).';
  }
  return msg.isEmpty ? czechStatus(code) : '${czechStatus(code)}: $msg';
}
