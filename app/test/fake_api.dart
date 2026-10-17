import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:webtoon/api/webtoon_api.dart';
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
    this.worlds = const [],
    Map<String, Campaign>? campaigns,
    Map<String, List<Map<String, dynamic>>>? episodeScripts,
    this.nextEpisode,
  }) : campaigns = campaigns ?? {},
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
}

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
