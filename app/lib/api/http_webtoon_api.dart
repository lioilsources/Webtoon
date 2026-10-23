import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/widgets.dart';
import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/author.dart';
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

  @override
  bool get canEdit => true;

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
    bool allowEmpty = false,
  }) async {
    final req = http.Request(method, _uri(path, query))
      ..headers.addAll(_headers);
    if (body != null) {
      req.headers['Content-Type'] = 'application/json';
      req.body = jsonEncode(body);
    }
    return _exec(req, allowEmpty: allowEmpty);
  }

  Future<Map<String, dynamic>> _exec(
    http.BaseRequest req, {
    bool allowEmpty = false,
  }) async {
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
      if (allowEmpty) return const {};
      throw ApiException(
        'Neočekávaná odpověď serveru (${resp.statusCode}).',
        statusCode: resp.statusCode,
      );
    }
    return obj(decoded);
  }

  Future<Map<String, dynamic>> _upload(
    String path,
    Uint8List bytes,
    String filename,
  ) {
    final lower = filename.toLowerCase();
    final type = lower.endsWith('.png')
        ? http.MediaType('image', 'png')
        : http.MediaType('image', 'jpeg');
    final req = http.MultipartRequest('POST', _uri(path))
      ..headers.addAll(_headers)
      ..files.add(
        http.MultipartFile.fromBytes(
          'file',
          bytes,
          filename: filename,
          contentType: type,
        ),
      );
    return _exec(req);
  }

  static String _e(String s) => Uri.encodeComponent(s);

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
  Future<Panel> updatePanelMotion(
    String episodeId,
    int panel,
    Map<String, dynamic> patch,
  ) async => Panel.fromJson(
    await _send(
      'PATCH',
      '/episodes/${Uri.encodeComponent(episodeId)}/panels/$panel',
      body: patch,
    ),
  );

  @override
  ImageProvider panelImage(String imageUrl) =>
      NetworkImage(config.resolveMedia(imageUrl));

  // --- author (M3) ---------------------------------------------------------------

  @override
  Future<List<WorldSummary>> listMyWorlds() async {
    final j = await _send('GET', '/worlds', query: {'owner': 'me'});
    return objList(j['worlds']).map(WorldSummary.fromJson).toList();
  }

  @override
  Future<List<StylePreset>> listStylePresets() async {
    final j = await _send('GET', '/style_presets');
    return objList(j['presets']).map(StylePreset.fromJson).toList();
  }

  @override
  Future<World> createWorld({
    required String title,
    required String styleId,
    Map<String, dynamic> fields = const {},
  }) async => World.fromJson(
    await _send(
      'POST',
      '/worlds',
      body: {...fields, 'title': title, 'style_id': styleId},
    ),
  );

  @override
  Future<World> updateWorld(String worldId, Map<String, dynamic> patch) async =>
      World.fromJson(
        await _send('PATCH', '/worlds/${_e(worldId)}', body: patch),
      );

  @override
  Future<WorldStats> getWorldStats(String worldId) async =>
      WorldStats.fromJson(await _send('GET', '/worlds/${_e(worldId)}/stats'));

  @override
  Future<Character> createCharacter(
    String worldId,
    Map<String, dynamic> fields,
  ) async => Character.fromJson(
    await _send('POST', '/worlds/${_e(worldId)}/characters', body: fields),
  );

  @override
  Future<Character> updateCharacter(
    String worldId,
    String characterId,
    Map<String, dynamic> patch,
  ) async => Character.fromJson(
    await _send(
      'PATCH',
      '/worlds/${_e(worldId)}/characters/${_e(characterId)}',
      body: patch,
    ),
  );

  @override
  Future<void> deleteCharacter(String worldId, String characterId) => _send(
    'DELETE',
    '/worlds/${_e(worldId)}/characters/${_e(characterId)}',
    allowEmpty: true,
  );

  @override
  Future<TagSuggestion> suggestCharacterTags(
    String worldId,
    String characterId, {
    String? description,
  }) async => TagSuggestion.fromJson(
    await _send(
      'POST',
      '/worlds/${_e(worldId)}/characters/${_e(characterId)}/tag_prompt',
      body: {'description': ?description},
    ),
  );

  @override
  Future<CharacterSheet> createSheet(
    String worldId,
    String characterId, {
    int seeds = 4,
  }) async => CharacterSheet.fromJson(
    await _send(
      'POST',
      '/worlds/${_e(worldId)}/characters/${_e(characterId)}/sheet',
      body: {'seeds': seeds},
    ),
  );

  @override
  Future<List<CharacterSheet>> listSheets(
    String worldId,
    String characterId,
  ) async {
    final j = await _send(
      'GET',
      '/worlds/${_e(worldId)}/characters/${_e(characterId)}/sheets',
    );
    return objList(j['sheets']).map(CharacterSheet.fromJson).toList();
  }

  @override
  Future<CharacterSheet> getSheet(String sheetId) async =>
      CharacterSheet.fromJson(await _send('GET', '/sheets/${_e(sheetId)}'));

  @override
  Future<Character> uploadCharacterReference(
    String worldId,
    String characterId,
    Uint8List bytes,
    String filename,
  ) async => Character.fromJson(
    await _upload(
      '/worlds/${_e(worldId)}/characters/${_e(characterId)}/references',
      bytes,
      filename,
    ),
  );

  @override
  Future<Location> createLocation(
    String worldId,
    Map<String, dynamic> fields,
  ) async => Location.fromJson(
    await _send('POST', '/worlds/${_e(worldId)}/locations', body: fields),
  );

  @override
  Future<Location> updateLocation(
    String worldId,
    String locationId,
    Map<String, dynamic> patch,
  ) async => Location.fromJson(
    await _send(
      'PATCH',
      '/worlds/${_e(worldId)}/locations/${_e(locationId)}',
      body: patch,
    ),
  );

  @override
  Future<void> deleteLocation(String worldId, String locationId) => _send(
    'DELETE',
    '/worlds/${_e(worldId)}/locations/${_e(locationId)}',
    allowEmpty: true,
  );

  @override
  Future<TagSuggestion> suggestLocationTags(
    String worldId,
    String locationId, {
    String? description,
  }) async => TagSuggestion.fromJson(
    await _send(
      'POST',
      '/worlds/${_e(worldId)}/locations/${_e(locationId)}/tag_prompt',
      body: {'description': ?description},
    ),
  );

  @override
  Future<Location> uploadLocationReference(
    String worldId,
    String locationId,
    Uint8List bytes,
    String filename,
  ) async => Location.fromJson(
    await _upload(
      '/worlds/${_e(worldId)}/locations/${_e(locationId)}/references',
      bytes,
      filename,
    ),
  );
}
