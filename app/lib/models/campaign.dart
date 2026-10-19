// Campaign as returned by GET /campaigns and GET /campaigns/{id} (backend/internal/api/campaigns.go).

import 'episode.dart';
import 'json.dart';

class CampaignSummary {
  final String id;
  final String worldId;
  final String worldTitle;
  final String title;
  final String status;
  final String? playerCharacterId;
  final int episodes;
  final String lastEpisodeStatus;
  final DateTime? lastActivity;

  const CampaignSummary({
    required this.id,
    required this.worldId,
    this.worldTitle = '',
    this.title = '',
    this.status = 'active',
    this.playerCharacterId,
    this.episodes = 0,
    this.lastEpisodeStatus = '',
    this.lastActivity,
  });

  factory CampaignSummary.fromJson(Map<String, dynamic> j) => CampaignSummary(
    id: str(j['id']),
    worldId: str(j['world_id']),
    worldTitle: str(j['world_title']),
    title: str(j['title']),
    status: str(j['status'], 'active'),
    playerCharacterId: strOrNull(j['player_character_id']),
    episodes: integer(j['episodes']),
    lastEpisodeStatus: str(j['last_episode_status']),
    lastActivity: date(j['last_activity']),
  );
}

class EpisodeSummary {
  final String id;
  final int index;
  final String title;
  final EpisodeStatus status;
  final int panelsReady;
  final int panelsTotal;
  final Chosen? chosen;

  /// Translated titles by language (complete or not: the history list just shows what exists).
  final Map<String, String> titleI18n;

  const EpisodeSummary({
    required this.id,
    required this.index,
    this.title = '',
    this.status = EpisodeStatus.queued,
    this.panelsReady = 0,
    this.panelsTotal = 0,
    this.chosen,
    this.titleI18n = const {},
  });

  factory EpisodeSummary.fromJson(Map<String, dynamic> j) => EpisodeSummary(
    id: str(j['id']),
    index: integer(j['index'], 1),
    title: str(j['title']),
    status: EpisodeStatus.parse(str(j['status'], 'queued')),
    panelsReady: integer(j['panels_ready']),
    panelsTotal: integer(j['panels_total']),
    chosen: Chosen.fromJson(j['chosen']),
    titleI18n: strMap(j['title_i18n']),
  );

  String titleIn(String? lang) =>
      lang == null ? title : (titleI18n[lang] ?? title);
}

class Campaign {
  final String id;
  final String worldId;
  final String playerId;
  final String title;
  final String status;
  final String? playerCharacterId;
  final List<EpisodeSummary> episodes;
  final Map<String, dynamic> state;

  const Campaign({
    required this.id,
    required this.worldId,
    this.playerId = '',
    this.title = '',
    this.status = 'active',
    this.playerCharacterId,
    this.episodes = const [],
    this.state = const {},
  });

  factory Campaign.fromJson(Map<String, dynamic> j) => Campaign(
    id: str(j['id']),
    worldId: str(j['world_id']),
    playerId: str(j['player_id']),
    title: str(j['title']),
    status: str(j['status'], 'active'),
    playerCharacterId: strOrNull(j['player_character_id']),
    episodes: objList(j['episodes']).map(EpisodeSummary.fromJson).toList()
      ..sort((a, b) => a.index.compareTo(b.index)),
    state: obj(j['state']),
  );

  String? get currentLocation => strOrNull(state['current_location']);

  /// Characters currently in the story state (alive), for the director's "remove" chips.
  List<String> get stateCharacterIds {
    final chars = obj(state['characters']);
    return [
      for (final e in chars.entries)
        if (obj(e.value)['alive'] != false) e.key,
    ];
  }
}

/// Director overrides sent with POST /campaigns/{id}/episodes (§6). The backend ignores
/// `director` for now; the client already sends it.
class DirectorRequest {
  final List<String> addCharacters;
  final List<String> removeCharacters;
  final String? locationId;

  const DirectorRequest({
    this.addCharacters = const [],
    this.removeCharacters = const [],
    this.locationId,
  });

  bool get isEmpty =>
      addCharacters.isEmpty && removeCharacters.isEmpty && locationId == null;

  Map<String, dynamic> toJson() => {
    if (addCharacters.isNotEmpty) 'add_characters': addCharacters,
    if (removeCharacters.isNotEmpty) 'remove_characters': removeCharacters,
    if (locationId != null) 'location_id': locationId,
  };
}
