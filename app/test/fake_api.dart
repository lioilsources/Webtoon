import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/widgets.dart';
import 'package:webtoon/api/webtoon_api.dart';
import 'package:webtoon/models/author.dart';
import 'package:webtoon/models/campaign.dart';
import 'package:webtoon/models/episode.dart';
import 'package:webtoon/models/world.dart';

/// 1×1 transparent PNG.
final kTinyPng = base64Decode(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
);

class ContinueCall {
  final String campaignId;
  final String? choiceId;
  final String? freeText;
  final DirectorRequest? director;
  ContinueCall(this.campaignId, this.choiceId, this.freeText, this.director);
}

/// In-memory backend. Episodes are served from scripted snapshots: each GET returns the next
/// snapshot until the last one, which then sticks (simulates the worker progressing).
class FakeWebtoonApi implements WebtoonApi {
  @override
  final String userId;

  final List<World> worlds;
  final Map<String, Campaign> campaigns;

  // --- author side ---
  List<StylePreset> presets = const [
    StylePreset(
      id: 'clean_webtoon',
      checkpoint: 'noobai-xl-eps11.safetensors',
      artistTags: ['(artist:ningen mame:0.8)'],
      aestheticTags: ['flat color', 'clean lineart'],
      sampler: 'euler_ancestral',
      steps: 28,
      cfg: 5,
    ),
    StylePreset(
      id: 'hassaku_soft',
      checkpoint: 'HassakuXL.safetensors',
      aestheticTags: ['soft shading', 'pastel colors'],
      sampler: 'euler_ancestral',
      steps: 28,
      cfg: 5.5,
    ),
  ];
  final List<(String, Map<String, dynamic>)> worldPatches = [];
  final List<(String, String, Map<String, dynamic>)> characterPatches = [];
  final List<(String, String, Map<String, dynamic>)> locationPatches = [];
  final List<(String, String, String, int)> uploads = [];
  final List<String> tagRequests = [];
  final List<String> deleted = [];
  TagSuggestion tagSuggestion = const TagSuggestion(
    tags: ['orange hair', 'short hair', 'green eyes'],
    dropped: ['copper boots'],
    notes: 'ok',
  );
  ApiException? tagError;
  Map<String, dynamic> statsJson = const {};
  final Map<String, List<Map<String, dynamic>>> sheetScripts = {};
  final Map<String, CharacterSheet> sheets = {};
  int sheetFetches = 0;
  final Map<String, List<Map<String, dynamic>>> episodeScripts;

  /// Episode JSON served for an id created by [continueCampaign].
  Map<String, dynamic> Function(String newId)? nextEpisode;

  final List<ContinueCall> continueCalls = [];
  final List<(String, int, List<Bubble>)> bubbleUpdates = [];
  final List<(String, int)> regenerations = [];
  final Map<String, int> episodeFetches = {};
  String? failNextContinue;

  FakeWebtoonApi({
    this.userId = 'player',
    List<World> worlds = const [],
    Map<String, Campaign>? campaigns,
    Map<String, List<Map<String, dynamic>>>? episodeScripts,
    this.nextEpisode,
  }) : worlds = [...worlds],
       campaigns = campaigns ?? {},
       episodeScripts = episodeScripts ?? {};

  Map<String, dynamic> _current(String id) {
    final script = episodeScripts[id];
    if (script == null || script.isEmpty) {
      throw const ApiException('Nenalezeno.', statusCode: 404);
    }
    return script.first;
  }

  @override
  Future<List<WorldSummary>> listWorlds() async => worlds;

  @override
  Future<World> getWorld(String id) async => worlds.firstWhere(
    (w) => w.id == id,
    orElse: () => throw const ApiException('Nenalezeno.', statusCode: 404),
  );

  @override
  Future<List<CampaignSummary>> listCampaigns({String? worldId}) async => [
    for (final c in campaigns.values)
      if (worldId == null || c.worldId == worldId)
        CampaignSummary(
          id: c.id,
          worldId: c.worldId,
          title: c.title,
          episodes: c.episodes.length,
          lastEpisodeStatus: c.episodes.isEmpty
              ? ''
              : c.episodes.last.status.name,
        ),
  ];

  @override
  Future<CreatedCampaign> createCampaign({
    required String worldId,
    String? playerCharacterId,
    String? title,
  }) async {
    final id = 'cp_new${campaigns.length}';
    final epId = 'ep_first_$id';
    episodeScripts[epId] = [
      episodeJson(epId, status: 'queued', panels: const []),
    ];
    final c = Campaign(
      id: id,
      worldId: worldId,
      playerId: userId,
      title: title ?? 'Nová kampaň',
      playerCharacterId: playerCharacterId,
      episodes: [EpisodeSummary(id: epId, index: 1)],
    );
    campaigns[id] = c;
    return CreatedCampaign(c, epId);
  }

  @override
  Future<Campaign> getCampaign(String id) async {
    final c = campaigns[id];
    if (c == null) throw const ApiException('Nenalezeno.', statusCode: 404);
    // Summaries follow the episodes' current scripted status.
    return Campaign(
      id: c.id,
      worldId: c.worldId,
      playerId: c.playerId,
      title: c.title,
      playerCharacterId: c.playerCharacterId,
      state: c.state,
      episodes: [
        for (final e in c.episodes)
          episodeScripts.containsKey(e.id)
              ? EpisodeSummary.fromJson(_current(e.id))
              : e,
      ],
    );
  }

  @override
  Future<String> continueCampaign(
    String campaignId, {
    String? choiceId,
    String? freeText,
    DirectorRequest? director,
  }) async {
    continueCalls.add(ContinueCall(campaignId, choiceId, freeText, director));
    if (failNextContinue != null) {
      final m = failNextContinue!;
      failNextContinue = null;
      throw ApiException(m, statusCode: 409);
    }
    final c = campaigns[campaignId]!;
    final id = 'ep_next${continueCalls.length}';
    final idx = c.episodes.isEmpty ? 1 : c.episodes.last.index + 1;
    episodeScripts[id] = [
      nextEpisode?.call(id) ??
          episodeJson(id, index: idx, status: 'queued', panels: const []),
    ];
    final chosen = Chosen(
      choiceId: choiceId ?? 'free',
      kind: freeText != null ? 'free' : 'closed',
      text: freeText ?? choiceId ?? '',
    );
    campaigns[campaignId] = Campaign(
      id: c.id,
      worldId: c.worldId,
      playerId: c.playerId,
      title: c.title,
      state: c.state,
      episodes: [
        ...c.episodes,
        EpisodeSummary(id: id, index: idx, chosen: chosen),
      ],
    );
    return id;
  }

  @override
  Future<Episode> getEpisode(String id) async {
    episodeFetches[id] = (episodeFetches[id] ?? 0) + 1;
    final script = episodeScripts[id];
    if (script == null) {
      throw const ApiException('Nenalezeno.', statusCode: 404);
    }
    final j = script.first;
    if (script.length > 1) script.removeAt(0);
    return Episode.fromJson(j);
  }

  @override
  Future<Panel> updateBubbles(
    String episodeId,
    int panel,
    List<Bubble> bubbles,
  ) async {
    bubbleUpdates.add((episodeId, panel, bubbles));
    final j = _current(episodeId);
    final p = (j['panels'] as List).cast<Map<String, dynamic>>()[panel];
    p['bubbles'] = [for (final b in bubbles) b.toJson()];
    return Panel.fromJson(p);
  }

  @override
  Future<Panel> regeneratePanel(String episodeId, int panel) async {
    regenerations.add((episodeId, panel));
    final j = _current(episodeId);
    final p = (j['panels'] as List).cast<Map<String, dynamic>>()[panel];
    p['status'] = 'pending';
    p.remove('image_url');
    // Next fetch: rendered.
    final done = jsonDecode(jsonEncode(j)) as Map<String, dynamic>;
    final dp = (done['panels'] as List).cast<Map<String, dynamic>>()[panel];
    dp['status'] = 'ready';
    dp['image_url'] = '/media/regen.png';
    episodeScripts[episodeId] = [j, done];
    return Panel.fromJson(p);
  }

  @override
  ImageProvider panelImage(String imageUrl) => MemoryImage(kTinyPng);

  // --- author (M3) ---------------------------------------------------------------

  int _seq = 0;

  int _worldIndex(String id) {
    final i = worlds.indexWhere((w) => w.id == id);
    if (i < 0) throw const ApiException('Nenalezeno.', statusCode: 404);
    return i;
  }

  Map<String, dynamic> _wj(String id) => worldToJson(worlds[_worldIndex(id)]);

  void _put(Map<String, dynamic> j) =>
      worlds[_worldIndex(str(j['id']))] = World.fromJson(j);

  static String str(Object? v) => v == null ? '' : '$v';

  @override
  Future<List<WorldSummary>> listMyWorlds() async =>
      worlds.where((w) => w.ownerId == userId).toList();

  @override
  Future<List<StylePreset>> listStylePresets() async => presets;

  @override
  Future<World> createWorld({
    required String title,
    required String styleId,
    Map<String, dynamic> fields = const {},
  }) async {
    final w = World(
      id: 'w_new${++_seq}',
      ownerId: userId,
      title: title,
      styleId: styleId,
    );
    worlds.add(w);
    return w;
  }

  @override
  Future<World> updateWorld(String worldId, Map<String, dynamic> patch) async {
    worldPatches.add((worldId, patch));
    final j = _wj(worldId)..addAll(jsonDecode(jsonEncode(patch)));
    final canon = (j['canon'] as Map?) ?? {};
    var n = 0;
    for (final node in (canon['nodes'] as List? ?? const [])) {
      if ((node as Map)['id'] == null) node['id'] = 'n${++n}';
    }
    _put(j);
    return worlds[_worldIndex(worldId)];
  }

  @override
  Future<WorldStats> getWorldStats(String worldId) async =>
      WorldStats.fromJson(statsJson);

  Map<String, dynamic> _char(String worldId, String cid) {
    final j = _wj(worldId);
    return (j['characters'] as List).cast<Map<String, dynamic>>().firstWhere(
      (c) => c['id'] == cid,
      orElse: () => throw const ApiException('Nenalezeno.', statusCode: 404),
    );
  }

  Character _updateChar(
    String worldId,
    String cid,
    void Function(Map<String, dynamic> c) fn,
  ) {
    final j = _wj(worldId);
    final c = (j['characters'] as List).cast<Map<String, dynamic>>().firstWhere(
      (c) => c['id'] == cid,
      orElse: () => throw const ApiException('Nenalezeno.', statusCode: 404),
    );
    fn(c);
    _put(j);
    return Character.fromJson(c);
  }

  @override
  Future<Character> createCharacter(
    String worldId,
    Map<String, dynamic> fields,
  ) async {
    final j = _wj(worldId);
    final c = {
      ...fields,
      'id': fields['id'] ?? 'c_new${++_seq}',
      'owner_id': userId,
      'reference_images': <String>[],
      'reference_urls': <String>[],
    };
    (j['characters'] as List).add(c);
    _put(j);
    return Character.fromJson(c);
  }

  @override
  Future<Character> updateCharacter(
    String worldId,
    String characterId,
    Map<String, dynamic> patch,
  ) async {
    characterPatches.add((worldId, characterId, patch));
    return _updateChar(worldId, characterId, (c) {
      c.addAll(jsonDecode(jsonEncode(patch)));
      if (patch.containsKey('reference_images')) {
        c['reference_urls'] = [
          for (final p in patch['reference_images'] as List) '/media/$p',
        ];
      }
    });
  }

  @override
  Future<void> deleteCharacter(String worldId, String characterId) async {
    _char(worldId, characterId);
    deleted.add(characterId);
    final j = _wj(worldId);
    (j['characters'] as List).removeWhere((c) => c['id'] == characterId);
    _put(j);
  }

  @override
  Future<TagSuggestion> suggestCharacterTags(
    String worldId,
    String characterId, {
    String? description,
  }) async {
    tagRequests.add(characterId);
    if (tagError != null) throw tagError!;
    return tagSuggestion;
  }

  /// Sheet progress: each GET /sheets/{id} serves the next snapshot (the last one sticks).
  /// When the "ready" snapshot is served the best image becomes a reference image.
  @override
  Future<CharacterSheet> createSheet(
    String worldId,
    String characterId, {
    int seeds = 4,
  }) async {
    final id = 'sh_${++_seq}';
    Map<String, dynamic> img(int k) => {
      'seed': 1000 + k,
      'image_url': '/media/characters/$worldId/$characterId/sheet_${id}_$k.png',
      'recall': [0.5, 0.75, 0.9, 0.6][k % 4],
      'missing': k == 2 ? <String>[] : ['freckles'],
      'status': 'ok',
    };
    Map<String, dynamic> snap(String status, int done, {String error = ''}) => {
      'id': id,
      'world_id': worldId,
      'character_id': characterId,
      'status': status,
      'error': error,
      'seeds': seeds,
      'done': done,
      'images': [for (var k = 0; k < done; k++) img(k)],
      'best': status == 'ready' ? 2 : null,
      'best_image_url': status == 'ready' ? img(2)['image_url'] : null,
    };
    sheetScripts[id] = [
      snap('queued', 0, error: 'waiting: comfyui unavailable (next try 12:00)'),
      snap('rendering', 2),
      snap('ready', seeds),
    ];
    final s = CharacterSheet.fromJson(
      snap('queued', 0, error: 'waiting: comfyui unavailable (next try 12:00)'),
    );
    sheets[id] = s;
    return s;
  }

  @override
  Future<List<CharacterSheet>> listSheets(
    String worldId,
    String characterId,
  ) async => sheets.values
      .where((s) => s.characterId == characterId)
      .toList()
      .reversed
      .toList();

  @override
  Future<CharacterSheet> getSheet(String sheetId) async {
    sheetFetches++;
    final script = sheetScripts[sheetId]!;
    final j = script.first;
    if (script.length > 1) script.removeAt(0);
    final s = CharacterSheet.fromJson(j);
    if (s.status == 'ready' && sheets[sheetId]?.status != 'ready') {
      _updateChar(s.worldId, s.characterId, (c) {
        final path = s.bestImageUrl!.replaceFirst('/media/', '');
        c['reference_images'] = [...(c['reference_images'] as List), path];
        c['reference_urls'] = [
          ...(c['reference_urls'] as List),
          s.bestImageUrl,
        ];
      });
    }
    sheets[sheetId] = s;
    return s;
  }

  @override
  Future<Character> uploadCharacterReference(
    String worldId,
    String characterId,
    Uint8List bytes,
    String filename,
  ) async {
    uploads.add((worldId, characterId, filename, bytes.length));
    final path = 'characters/$worldId/$characterId/ref_${++_seq}.png';
    return _updateChar(worldId, characterId, (c) {
      c['reference_images'] = [...(c['reference_images'] as List), path];
      c['reference_urls'] = [...(c['reference_urls'] as List), '/media/$path'];
    });
  }

  Location _updateLoc(
    String worldId,
    String lid,
    void Function(Map<String, dynamic> l) fn,
  ) {
    final j = _wj(worldId);
    final l = (j['locations'] as List).cast<Map<String, dynamic>>().firstWhere(
      (l) => l['id'] == lid,
      orElse: () => throw const ApiException('Nenalezeno.', statusCode: 404),
    );
    fn(l);
    _put(j);
    return Location.fromJson(l);
  }

  @override
  Future<Location> createLocation(
    String worldId,
    Map<String, dynamic> fields,
  ) async {
    final j = _wj(worldId);
    final l = {
      ...fields,
      'id': fields['id'] ?? 'l_new${++_seq}',
      'reference_images': <String>[],
      'reference_urls': <String>[],
    };
    (j['locations'] as List).add(l);
    _put(j);
    return Location.fromJson(l);
  }

  @override
  Future<Location> updateLocation(
    String worldId,
    String locationId,
    Map<String, dynamic> patch,
  ) async {
    locationPatches.add((worldId, locationId, patch));
    return _updateLoc(worldId, locationId, (l) {
      l.addAll(jsonDecode(jsonEncode(patch)));
      if (patch.containsKey('reference_images')) {
        l['reference_urls'] = [
          for (final p in patch['reference_images'] as List) '/media/$p',
        ];
      }
    });
  }

  @override
  Future<void> deleteLocation(String worldId, String locationId) async {
    deleted.add(locationId);
    final j = _wj(worldId);
    (j['locations'] as List).removeWhere((l) => l['id'] == locationId);
    _put(j);
  }

  @override
  Future<TagSuggestion> suggestLocationTags(
    String worldId,
    String locationId, {
    String? description,
  }) async {
    tagRequests.add(locationId);
    if (tagError != null) throw tagError!;
    return const TagSuggestion(
      tags: ['indoors', 'wooden floor', 'window'],
      dropped: ['letter shelves'],
    );
  }

  @override
  Future<Location> uploadLocationReference(
    String worldId,
    String locationId,
    Uint8List bytes,
    String filename,
  ) async {
    uploads.add((worldId, locationId, filename, bytes.length));
    final path = 'locations/$worldId/$locationId/ref_${++_seq}.png';
    return _updateLoc(worldId, locationId, (l) {
      l['reference_images'] = [...(l['reference_images'] as List), path];
      l['reference_urls'] = [...(l['reference_urls'] as List), '/media/$path'];
    });
  }
}

/// World → the JSON shape of GET /worlds/{id} (so the fake can patch and re-parse it).
Map<String, dynamic> worldToJson(World w) => <String, dynamic>{
  'id': w.id,
  'owner_id': w.ownerId,
  'title': w.title,
  'synopsis': w.synopsis,
  'tone': w.tone,
  'audience': w.audience,
  'language': w.language,
  'style_id': w.styleId,
  'visibility': w.visibility,
  'bible': {...w.bible, 'rules': w.rules, 'factions': w.factions},
  'canon': {
    'nodes': [
      for (final n in w.canonNodes) {'id': n.id, 'text': n.text},
    ],
    'constraints': w.constraints,
  },
  'permissions': w.permissions.toJson(),
  'characters': [
    for (final c in w.characters)
      <String, dynamic>{
        'id': c.id,
        'owner_id': c.ownerId,
        'name': c.name,
        'role': c.role,
        'count_tag': c.countTag,
        'description': c.description,
        'personality': c.personality,
        'speech_style': c.speechStyle,
        'tag_prompt': c.tagPrompt,
        'reference_images': c.referenceImages,
        'reference_urls': c.referenceUrls,
        'identity_level': c.identityLevel,
        'ip_adapter': c.ipAdapter?.toJson(),
      },
  ],
  'locations': [
    for (final l in w.locations)
      <String, dynamic>{
        'id': l.id,
        'name': l.name,
        'description': l.description,
        'mood': l.mood,
        'tag_prompt': l.tagPrompt,
        'reference_images': l.referenceImages,
        'reference_urls': l.referenceUrls,
      },
  ],
};

// --- fixtures ------------------------------------------------------------------------

Map<String, dynamic> panelJson(
  int i, {
  String status = 'ready',
  List<Map<String, dynamic>>? bubbles,
  List<Map<String, dynamic>> sfx = const [],
  String gap = 'medium',
  List<Map<String, dynamic>> characters = const [],
}) => {
  'index': i,
  'status': status,
  if (status == 'ready') 'image_url': '/media/episodes/ep/p0${i}_1.png',
  if (status == 'ready') 'width': 1216,
  if (status == 'ready') 'height': 832,
  'shot': 'wide',
  'location_id': 'l_post',
  'gap_after': gap,
  'bubbles':
      bubbles ??
      [
        {'speaker_id': 'c_vesna', 'text': 'Bublina $i', 'kind': 'speech'},
      ],
  'sfx': sfx,
  'characters': characters,
  if (status == 'failed') 'error': 'unsafe output',
};

Map<String, dynamic> episodeJson(
  String id, {
  int index = 1,
  String title = 'Dopis bez adresy',
  String status = 'ready',
  List<Map<String, dynamic>>? panels,
  int? panelsReady,
  List<Map<String, dynamic>>? choices,
  String error = '',
}) {
  final ps = panels ?? [panelJson(0), panelJson(1), panelJson(2)];
  return {
    'id': id,
    'campaign_id': 'cp_1',
    'index': index,
    'title': status == 'queued' ? '' : title,
    'status': status,
    'panels_ready':
        panelsReady ?? ps.where((p) => p['status'] == 'ready').length,
    'panels_total': ps.length,
    'credits_cost': ps.length,
    'panels': ps,
    'choices':
        choices ??
        [
          {'id': 'c1', 'kind': 'closed', 'text': 'Otevřít dopis a přečíst ho.'},
          {'id': 'c2', 'kind': 'closed', 'text': 'Utéct zpět.'},
          {'id': 'free', 'kind': 'free', 'text': 'Nebo napiš, co uděláš…'},
        ],
    'chosen': null,
    'warnings': [],
    'error': error,
  };
}

World testWorld({Permissions permissions = const Permissions()}) => World(
  id: 'w_skyisles',
  ownerId: 'author',
  title: 'Nebeské ostrovy',
  synopsis: 'Létající ostrovy spojené lanovými mosty.',
  tone: 'dobrodružný',
  characters: const [
    Character(
      id: 'c_vesna',
      name: 'Vesna',
      role: 'playable',
      personality: 'zvědavá',
    ),
    Character(id: 'c_kos', name: 'Kos', role: 'npc'),
  ],
  locations: const [
    Location(id: 'l_post', name: 'Poštovní věž'),
    Location(id: 'l_cliff', name: 'Bouřkový útes'),
  ],
  permissions: permissions,
);

Campaign testCampaign(List<String> episodeIds, {String playerId = 'player'}) =>
    Campaign(
      id: 'cp_1',
      worldId: 'w_skyisles',
      playerId: playerId,
      title: 'Moje dobrodružství',
      state: const {
        'current_location': 'l_post',
        'characters': {
          'c_vesna': {'alive': true},
        },
      },
      episodes: [
        for (var i = 0; i < episodeIds.length; i++)
          EpisodeSummary(id: episodeIds[i], index: i + 1),
      ],
    );
