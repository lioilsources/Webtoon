// Author (DM) side of the API: style presets, tag suggestions, character sheets, world stats
// (backend/README.md "API").

import 'json.dart';

class StylePreset {
  final String id;
  final String checkpoint;
  final String prediction;
  final List<String> artistTags;
  final List<String> aestheticTags;
  final String sampler;
  final int steps;
  final double cfg;
  final String? previewUrl;

  const StylePreset({
    required this.id,
    this.checkpoint = '',
    this.prediction = '',
    this.artistTags = const [],
    this.aestheticTags = const [],
    this.sampler = '',
    this.steps = 0,
    this.cfg = 0,
    this.previewUrl,
  });

  factory StylePreset.fromJson(Map<String, dynamic> j) => StylePreset(
    id: str(j['id']),
    checkpoint: str(j['checkpoint']),
    prediction: str(j['prediction']),
    artistTags: strList(j['artist_tags']),
    aestheticTags: strList(j['aesthetic_tags']),
    sampler: str(j['sampler']),
    steps: integer(j['steps']),
    cfg: dbl(j['cfg']) ?? 0,
    previewUrl: strOrNull(j['preview_url']),
  );

  /// "ningen mame, ciloranko · flat color, clean lineart"
  String get summary {
    final artists = artistTags
        .map((t) => t.replaceAll(RegExp(r'^\(|\)$|:[\d.]+\)?$'), ''))
        .map((t) => t.replaceFirst('artist:', ''))
        .join(', ');
    final aes = aestheticTags.join(', ');
    return [artists, aes].where((s) => s.isNotEmpty).join(' · ');
  }
}

/// POST …/tag_prompt: the LLM's tags (kept = in the WD14 vocabulary) and the dropped ones.
class TagSuggestion {
  final List<String> tags;
  final List<String> dropped;
  final String notes;

  const TagSuggestion({
    this.tags = const [],
    this.dropped = const [],
    this.notes = '',
  });

  factory TagSuggestion.fromJson(Map<String, dynamic> j) => TagSuggestion(
    tags: strList(j['tags']).isNotEmpty
        ? strList(j['tags'])
        : str(
            j['tag_prompt'],
          ).split(',').map((t) => t.trim()).where((t) => t.isNotEmpty).toList(),
    dropped: strList(j['dropped']),
    notes: str(j['notes']),
  );
}

class SheetImage {
  final int seed;
  final String? imageUrl;
  final double recall;
  final List<String> missing;
  final String status; // ok | unsafe

  /// Ratings over the audience's threshold, e.g. {"sensitive": 0.87} in a kids world.
  final Map<String, double> unsafe;

  const SheetImage({
    this.seed = 0,
    this.imageUrl,
    this.recall = 0,
    this.missing = const [],
    this.status = 'ok',
    this.unsafe = const {},
  });

  /// Rejected only as "sensitive" (tight or revealing clothes), i.e. only for kids.
  bool get onlySensitive =>
      unsafe.keys.every((k) => k == 'sensitive') && unsafe.isNotEmpty;

  factory SheetImage.fromJson(Map<String, dynamic> j) => SheetImage(
    seed: integer(j['seed']),
    imageUrl: strOrNull(j['image_url']),
    recall: dbl(j['recall']) ?? 0,
    missing: strList(j['missing']),
    status: str(j['status'], 'ok'),
    unsafe: {
      for (final e in ((j['unsafe'] as Map?) ?? const {}).entries)
        '${e.key}': dbl(e.value) ?? 0,
    },
  );
}

/// A character reference sheet job (POST …/sheet, GET /sheets/{id}).
class CharacterSheet {
  final String id;
  final String worldId;
  final String characterId;
  final String status; // queued | rendering | ready | failed
  final String error;
  final int seeds;
  final int done;
  final List<SheetImage> images;
  final int? best;
  final String? bestImageUrl;

  const CharacterSheet({
    required this.id,
    this.worldId = '',
    this.characterId = '',
    this.status = 'queued',
    this.error = '',
    this.seeds = 4,
    this.done = 0,
    this.images = const [],
    this.best,
    this.bestImageUrl,
  });

  factory CharacterSheet.fromJson(Map<String, dynamic> j) => CharacterSheet(
    id: str(j['id']),
    worldId: str(j['world_id']),
    characterId: str(j['character_id']),
    status: str(j['status'], 'queued'),
    error: str(j['error']),
    seeds: integer(j['seeds'], 4),
    done: integer(j['done']),
    images: objList(j['images']).map(SheetImage.fromJson).toList(),
    best: j['best'] == null ? null : integer(j['best']),
    bestImageUrl: strOrNull(j['best_image_url']),
  );

  bool get isFinished => status == 'ready' || status == 'failed';
  bool get isWaiting => error.startsWith('waiting');
}

class CountBucket {
  final int key;
  final int count;
  const CountBucket(this.key, this.count);
}

class EpisodeChoices {
  final int episode;
  final int total;
  final Map<String, int> choices;
  const EpisodeChoices(this.episode, this.total, this.choices);
}

class PlayerCreatedCharacter {
  final String id;
  final String name;
  final String ownerId;
  final String description;
  const PlayerCreatedCharacter({
    required this.id,
    required this.name,
    this.ownerId = '',
    this.description = '',
  });
}

/// GET /worlds/{id}/stats — the author dashboard.
class WorldStats {
  final int campaigns;
  final int players;
  final int episodes;
  final int episodesReady;
  final int episodesFailed;
  final int panelsReady;
  final int playerCreatedCount;
  final Map<String, int> byKind;
  final Map<String, int> byChoice;
  final List<CountBucket> stoppedAt;
  final List<EpisodeChoices> choicesByEpisode;
  final Map<String, int> canonReached;
  final List<PlayerCreatedCharacter> playerCreated;

  const WorldStats({
    this.campaigns = 0,
    this.players = 0,
    this.episodes = 0,
    this.episodesReady = 0,
    this.episodesFailed = 0,
    this.panelsReady = 0,
    this.playerCreatedCount = 0,
    this.byKind = const {},
    this.byChoice = const {},
    this.stoppedAt = const [],
    this.choicesByEpisode = const [],
    this.canonReached = const {},
    this.playerCreated = const [],
  });

  static Map<String, int> _counts(Object? v) =>
      obj(v).map((k, val) => MapEntry(k, integer(val)));

  factory WorldStats.fromJson(Map<String, dynamic> j) {
    final choices = obj(j['choices']);
    // Older backends only send campaign_depth.
    final stopped = objList(j['stopped_at']).isNotEmpty
        ? objList(j['stopped_at'])
              .map(
                (b) =>
                    CountBucket(integer(b['episode']), integer(b['campaigns'])),
              )
              .toList()
        : objList(j['campaign_depth'])
              .map(
                (b) => CountBucket(
                  integer(b['episodes']),
                  integer(b['campaigns']),
                ),
              )
              .toList();
    return WorldStats(
      campaigns: integer(j['campaigns']),
      players: integer(j['players']),
      episodes: integer(j['episodes']),
      episodesReady: integer(j['episodes_ready']),
      episodesFailed: integer(j['episodes_failed']),
      panelsReady: integer(j['panels_ready']),
      playerCreatedCount: integer(j['player_created_characters']),
      byKind: _counts(choices['by_kind']),
      byChoice: _counts(choices['by_choice']),
      stoppedAt: stopped..sort((a, b) => a.key.compareTo(b.key)),
      choicesByEpisode:
          objList(j['choices_by_episode'])
              .map(
                (e) => EpisodeChoices(
                  integer(e['episode']),
                  integer(e['total']),
                  _counts(e['choices']),
                ),
              )
              .toList()
            ..sort((a, b) => a.episode.compareTo(b.episode)),
      canonReached: _counts(j['canon_reached']),
      playerCreated: objList(j['player_created'])
          .map(
            (c) => PlayerCreatedCharacter(
              id: str(c['id']),
              name: str(c['name']),
              ownerId: str(c['owner_id']),
              description: str(c['description']),
            ),
          )
          .toList(),
    );
  }
}
