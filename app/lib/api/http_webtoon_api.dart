import 'dart:async';
import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/campaign.dart';
import '../models/episode.dart';
import '../models/json.dart';
import '../models/world.dart';
import 'webtoon_api.dart';

class HttpWebtoonApi implements WebtoonApi {
  final AppConfig config;
  final http.Client _client;
  final Duration timeout;

  HttpWebtoonApi(
    this.config, {
    http.Client? client,
    this.timeout = const Duration(seconds: 20),
  }) : _client = client ?? http.Client();

  @override
  String get userId => config.userId;

  Map<String, String> get _headers => {
    'X-User-ID': config.userId,
    'Accept': 'application/json',
  };

  Uri _uri(String path, [Map<String, String>? query]) => Uri.parse(
    '${config.apiBase}$path',
  ).replace(queryParameters: query == null || query.isEmpty ? null : query);

  Future<Map<String, dynamic>> _send(
    String method,
    String path, {
    Object? body,
    Map<String, String>? query,
  }) async {
    final req = http.Request(method, _uri(path, query))
      ..headers.addAll(_headers);
    if (body != null) {
      req.headers['Content-Type'] = 'application/json';
      req.body = jsonEncode(body);
    }
    final http.Response resp;
    try {
      resp = await http.Response.fromStream(
        await _client.send(req).timeout(timeout),
      );
    } on TimeoutException {
      throw const ApiException('Server neodpovídá (timeout).');
    } catch (e) {
      throw ApiException('Nelze se připojit k serveru ${config.apiBase}.');
    }
    final text = utf8.decode(resp.bodyBytes);
    Object? decoded;
    try {
      decoded = text.isEmpty ? null : jsonDecode(text);
    } on FormatException {
      decoded = null;
    }
    if (resp.statusCode >= 400) {
      final msg = decoded is Map ? str(decoded['error']) : '';
      throw ApiException(
        czechError(msg, resp.statusCode),
        statusCode: resp.statusCode,
      );
    }
    if (decoded is! Map) {
      throw ApiException(
        'Neočekávaná odpověď serveru (${resp.statusCode}).',
        statusCode: resp.statusCode,
      );
    }
    return obj(decoded);
  }

  @override
  Future<List<WorldSummary>> listWorlds() async {
    final j = await _send('GET', '/worlds');
    return objList(j['worlds']).map(WorldSummary.fromJson).toList();
  }

  @override
  Future<World> getWorld(String id) async =>
      World.fromJson(await _send('GET', '/worlds/${Uri.encodeComponent(id)}'));

  @override
  Future<List<CampaignSummary>> listCampaigns({String? worldId}) async {
    final j = await _send(
      'GET',
      '/campaigns',
      query: worldId == null ? null : {'world_id': worldId},
    );
    return objList(j['campaigns']).map(CampaignSummary.fromJson).toList();
  }

  @override
  Future<CreatedCampaign> createCampaign({
    required String worldId,
    String? playerCharacterId,
    String? title,
  }) async {
    final j = await _send(
      'POST',
      '/campaigns',
      body: {
        'world_id': worldId,
        'player_character_id': ?playerCharacterId,
        'title': ?title,
      },
    );
    return CreatedCampaign(
      Campaign.fromJson(obj(j['campaign'])),
      strOrNull(j['first_episode_id']),
    );
  }

  @override
  Future<Campaign> getCampaign(String id) async => Campaign.fromJson(
    await _send('GET', '/campaigns/${Uri.encodeComponent(id)}'),
  );

  @override
  Future<String> continueCampaign(
    String campaignId, {
    String? choiceId,
    String? freeText,
    DirectorRequest? director,
  }) async {
    final j = await _send(
      'POST',
      '/campaigns/${Uri.encodeComponent(campaignId)}/episodes',
      body: {
        'choice_id': ?choiceId,
        'free_text': ?freeText,
        if (director != null && !director.isEmpty)
          'director': director.toJson(),
      },
    );
    return str(j['episode_id']);
  }

  @override
  Future<Episode> getEpisode(String id) async => Episode.fromJson(
    await _send('GET', '/episodes/${Uri.encodeComponent(id)}'),
  );

  @override
  Future<Panel> updateBubbles(
    String episodeId,
    int panel,
    List<Bubble> bubbles,
  ) async => Panel.fromJson(
    await _send(
      'PATCH',
      '/episodes/${Uri.encodeComponent(episodeId)}/panels/$panel',
      body: {'bubbles': bubbles.map((b) => b.toJson()).toList()},
    ),
  );

  @override
  Future<Panel> regeneratePanel(String episodeId, int panel) async =>
      Panel.fromJson(
        await _send(
          'PATCH',
          '/episodes/${Uri.encodeComponent(episodeId)}/panels/$panel',
          body: {'regenerate': true},
        ),
      );

  @override
  ImageProvider panelImage(String imageUrl) =>
      NetworkImage(config.resolveMedia(imageUrl));
}
