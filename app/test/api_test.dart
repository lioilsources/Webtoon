import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:webtoon/api/http_webtoon_api.dart';
import 'package:webtoon/api/webtoon_api.dart';
import 'package:webtoon/config.dart';
import 'package:webtoon/models/campaign.dart';
import 'package:webtoon/models/episode.dart';

void main() {
  const cfg = AppConfig(apiBase: 'http://api.test:8095', userId: 'player');

  test('default config points at the backend default port 8095', () {
    final c = AppConfig.fromEnvironment();
    expect(c.apiBase, 'http://localhost:8095');
    expect(c.userId, 'player');
    expect(c.resolveMedia('/media/a.png'), 'http://localhost:8095/media/a.png');
    expect(c.resolveMedia('https://cdn/x.png'), 'https://cdn/x.png');
  });

  test('requests carry X-User-ID and the documented bodies', () async {
    final seen = <http.Request>[];
    final api = HttpWebtoonApi(
      cfg,
      client: MockClient((req) async {
        seen.add(req);
        final p = req.url.path;
        if (req.method == 'POST' && p == '/campaigns/cp_1/episodes') {
          return http.Response(
            '{"episode_id":"ep_2","index":2,"status":"queued"}',
            202,
          );
        }
        if (req.method == 'PATCH') {
          return http.Response.bytes(
            utf8.encode(
              jsonEncode({
                'index': 1,
                'status': 'ready',
                'image_url': '/media/x.png',
                'bubbles': jsonDecode(req.body)['bubbles'] ?? [],
              }),
            ),
            200,
          );
        }
        if (req.method == 'POST' && p == '/campaigns') {
          return http.Response(
            '{"campaign":{"id":"cp_9","world_id":"w"},"first_episode_id":"ep_9"}',
            201,
          );
        }
        return http.Response('{}', 404);
      }),
    );

    final id = await api.continueCampaign(
      'cp_1',
      choiceId: 'c2',
      director: const DirectorRequest(locationId: 'l_cliff'),
    );
    expect(id, 'ep_2');
    expect(seen.last.headers['X-User-ID'], 'player');
    expect(jsonDecode(seen.last.body), {
      'choice_id': 'c2',
      'director': {'location_id': 'l_cliff'},
    });

    await api.continueCampaign('cp_1', freeText: 'Skočím.');
    expect(jsonDecode(seen.last.body), {'free_text': 'Skočím.'});

    final p = await api.updateBubbles('ep_1', 1, const [
      Bubble(speakerId: 'c_vesna', text: 'Ahoj', kind: BubbleKind.shout),
      Bubble(text: 'Ráno.', kind: BubbleKind.narration),
    ]);
    expect(seen.last.method, 'PATCH');
    expect(
      seen.last.url.toString(),
      'http://api.test:8095/episodes/ep_1/panels/1',
    );
    expect(jsonDecode(seen.last.body), {
      'bubbles': [
        {'speaker_id': 'c_vesna', 'text': 'Ahoj', 'kind': 'shout'},
        {'speaker_id': null, 'text': 'Ráno.', 'kind': 'narration'},
      ],
    });
    expect(p.bubbles.first.kind, BubbleKind.shout);

    await api.regeneratePanel('ep_1', 3);
    expect(jsonDecode(seen.last.body), {'regenerate': true});

    final created = await api.createCampaign(
      worldId: 'w',
      playerCharacterId: 'c_vesna',
    );
    expect(jsonDecode(seen.last.body), {
      'world_id': 'w',
      'player_character_id': 'c_vesna',
    });
    expect(created.firstEpisodeId, 'ep_9');
  });

  test('backend errors become Czech ApiExceptions', () async {
    final api = HttpWebtoonApi(
      cfg,
      client: MockClient(
        (_) async => http.Response(
          '{"error":"an episode is still being generated"}',
          409,
        ),
      ),
    );
    expect(
      () => api.continueCampaign('cp_1', choiceId: 'c1'),
      throwsA(
        isA<ApiException>()
            .having((e) => e.statusCode, 'status', 409)
            .having((e) => e.message, 'message', 'Díl se ještě generuje.'),
      ),
    );
    final down = HttpWebtoonApi(
      cfg,
      client: MockClient((_) async => throw http.ClientException('refused')),
    );
    expect(
      () => down.listWorlds(),
      throwsA(
        isA<ApiException>().having(
          (e) => e.message,
          'm',
          contains('Nelze se připojit'),
        ),
      ),
    );
  });

  test('parses the GET /episodes/{id} shape from the backend', () {
    // Copied from a live response (backend import-demo of out/dev/storyboard_ep1.json).
    final ep = Episode.fromJson(
      jsonDecode('''
{"id":"ep_839c3b89062a","campaign_id":"cp_2076b107bdbd","index":1,"title":"Dopis bez adresy",
 "status":"ready","panels_ready":6,"panels_total":6,"credits_cost":6,
 "panels":[{"index":1,"status":"ready","image_url":"/media/episodes/ep_839c3b89062a/p01_1100.png",
   "width":832,"height":1216,"shot":"medium","location_id":"l_post","gap_after":"small",
   "bubbles":[{"kind":"speech","text":"Opět jen účty za uhlí...","speaker_id":"c_vesna"}],
   "sfx":[{"text":"škrt","style":"soft"}],
   "characters":[{"id":"c_vesna","action":"sorting letters, sighing","emotion":["bored","tired"]}],
   "seed":1100}],
 "choices":[{"id":"c1","kind":"closed","text":"Otevřít dopis."},{"id":"free","kind":"free","text":"Nebo napiš, co uděláš…"}],
 "chosen":null,"warnings":[],"error":""}''')
          as Map<String, dynamic>,
    );
    expect(ep.status, EpisodeStatus.ready);
    expect(ep.needsPolling, isFalse);
    expect(ep.creditsCost, 6);
    final p = ep.panels.single;
    expect(p.gapAfter, GapSize.small);
    expect(p.aspect, closeTo(832 / 1216, 1e-9));
    expect(p.sfx.single.style, 'soft');
    expect(p.characters.single.emotion, 'bored, tired');
    expect(p.characters.single.bbox, isNull);
    expect(ep.closedChoices.single.id, 'c1');
    expect(ep.freeChoice!.text, 'Nebo napiš, co uděláš…');
    expect(ep.chosen, isNull);
  });

  test(
    'pending panels get the shot-based aspect and keep the episode polling',
    () {
      final ep = Episode.fromJson({
        'id': 'e',
        'status': 'ready',
        'panels': [
          {'index': 0, 'status': 'pending', 'shot': 'establishing'},
          {
            'index': 1,
            'status': 'ready',
            'shot': 'close-up',
            'image_url': '/m',
          },
        ],
      });
      expect(ep.panels[0].aspect, closeTo(1216 / 832, 1e-9));
      expect(ep.panels[1].aspect, closeTo(832 / 1216, 1e-9));
      expect(ep.needsPolling, isTrue);
    },
  );

  group('author (M3) endpoints', () {
    late List<http.Request> seen;
    late HttpWebtoonApi api;
    const character = {
      'id': 'c_vesna',
      'name': 'Vesna',
      'role': 'playable',
      'tag_prompt': 'orange hair, short hair',
      'reference_images': ['characters/w/c_vesna/ref_1.png'],
      'reference_urls': ['/media/characters/w/c_vesna/ref_1.png'],
      'identity_level': 'ip_adapter',
      'ip_adapter': {
        'preset': 'PLUS FACE (portraits)',
        'weight': 0.35,
        'end_at': 0.7,
      },
    };
    const sheet = {
      'id': 'sh_1',
      'world_id': 'w',
      'character_id': 'c_vesna',
      'status': 'rendering',
      'error': '',
      'seeds': 4,
      'done': 1,
      'images': [
        {
          'seed': 11,
          'image_url': '/media/x.png',
          'recall': 0.82,
          'missing': ['freckles'],
          'status': 'ok',
        },
      ],
      'best': null,
      'best_image_url': null,
    };

    setUp(() {
      seen = [];
      api = HttpWebtoonApi(
        cfg,
        client: MockClient((req) async {
          seen.add(req);
          final p = req.url.path;
          Map<String, dynamic>? body;
          if (p == '/style_presets') {
            body = {
              'presets': [
                {
                  'id': 'clean_webtoon',
                  'artist_tags': ['(artist:ningen mame:0.8)'],
                  'aesthetic_tags': ['flat color'],
                  'steps': 28,
                  'cfg': 5,
                  'preview_url': null,
                },
              ],
            };
          } else if (p == '/worlds' && req.method == 'GET') {
            body = {
              'worlds': [
                {'id': 'w', 'owner_id': 'player', 'title': 'Můj'},
              ],
            };
          } else if (p.startsWith('/worlds') && p.endsWith('/stats')) {
            body = {
              'campaigns': 2,
              'stopped_at': [
                {'episode': 2, 'campaigns': 1},
                {'episode': 0, 'campaigns': 1},
              ],
              'choices_by_episode': [
                {
                  'episode': 1,
                  'total': 1,
                  'choices': {'c2': 1},
                },
              ],
              'choices': {
                'by_kind': {'closed': 1},
                'by_choice': {'c2': 1},
              },
              'player_created': [
                {'id': 'c_p', 'name': 'Bára', 'owner_id': 'p'},
              ],
            };
          } else if (p.endsWith('/tag_prompt')) {
            body = {
              'tags': ['orange hair'],
              'tag_prompt': 'orange hair',
              'dropped': ['copper boots'],
              'notes': 'n',
            };
          } else if (p.endsWith('/sheet') || p.startsWith('/sheets/')) {
            body = sheet;
          } else if (p.endsWith('/sheets')) {
            body = {
              'sheets': [sheet],
            };
          } else if (req.method == 'DELETE') {
            return http.Response('', 204);
          } else if (p.contains('/locations')) {
            body = {
              'id': 'l_post',
              'name': 'Věž',
              'tag_prompt': 'indoors',
              'reference_urls': [],
            };
          } else if (p.contains('/characters')) {
            body = character;
          } else if (p.startsWith('/worlds')) {
            body = {
              'id': 'w',
              'owner_id': 'player',
              'title': 'Svět',
              'style_id': 'clean_webtoon',
              'bible': {
                'rules': ['r'],
                'factions': [
                  'Cech',
                  {'name': 'Strážci', 'description': 'hlídají'},
                ],
                'lore': 'x',
              },
              'canon': {
                'nodes': [
                  {'id': 'c1', 'text': 'A'},
                ],
                'constraints': ['nic'],
              },
              'characters': [character],
            };
          }
          if (body == null) return http.Response('{"error":"not found"}', 404);
          return http.Response.bytes(
            utf8.encode(jsonEncode(body)),
            req.method == 'POST' ? 201 : 200,
          );
        }),
      );
    });

    test('world endpoints', () async {
      final mine = await api.listMyWorlds();
      expect(seen.last.url.toString(), 'http://api.test:8095/worlds?owner=me');
      expect(mine.single.title, 'Můj');

      final presets = await api.listStylePresets();
      expect(presets.single.summary, 'ningen mame · flat color');

      final w = await api.createWorld(title: 'Svět', styleId: 'clean_webtoon');
      expect(seen.last.method, 'POST');
      expect(jsonDecode(seen.last.body), {
        'title': 'Svět',
        'style_id': 'clean_webtoon',
      });
      expect(w.factions, ['Cech', 'Strážci — hlídají']);
      expect(w.bible['lore'], 'x');
      expect(w.canonNodes.single.id, 'c1');
      expect(w.constraints, ['nic']);
      final c = w.characters.single;
      expect(c.ipAdapter!.weight, 0.35);
      expect(c.referenceUrls.single, '/media/characters/w/c_vesna/ref_1.png');
      expect(c.tags, ['orange hair', 'short hair']);

      await api.updateWorld('w', {'tone': 'temný'});
      expect(seen.last.method, 'PATCH');
      expect(seen.last.url.path, '/worlds/w');
      expect(jsonDecode(seen.last.body), {'tone': 'temný'});

      final st = await api.getWorldStats('w');
      expect(st.campaigns, 2);
      expect(st.stoppedAt.map((b) => b.key), [0, 2]);
      expect(st.choicesByEpisode.single.choices, {'c2': 1});
      expect(st.playerCreated.single.name, 'Bára');
    });

    test('character endpoints incl. multipart upload', () async {
      await api.createCharacter('w', {'name': 'Otto'});
      expect(seen.last.url.path, '/worlds/w/characters');
      await api.updateCharacter('w', 'c_vesna', {'tag_prompt': 'a, b'});
      expect(seen.last.method, 'PATCH');
      expect(seen.last.url.path, '/worlds/w/characters/c_vesna');
      expect(jsonDecode(seen.last.body), {'tag_prompt': 'a, b'});

      final t = await api.suggestCharacterTags(
        'w',
        'c_vesna',
        description: 'zrzka',
      );
      expect(seen.last.url.path, '/worlds/w/characters/c_vesna/tag_prompt');
      expect(jsonDecode(seen.last.body), {'description': 'zrzka'});
      expect(t.dropped, ['copper boots']);
      await api.suggestCharacterTags('w', 'c_vesna');
      expect(jsonDecode(seen.last.body), <String, dynamic>{});

      final s = await api.createSheet('w', 'c_vesna');
      expect(seen.last.url.path, '/worlds/w/characters/c_vesna/sheet');
      expect(jsonDecode(seen.last.body), {'seeds': 4});
      expect(s.done, 1);
      expect(s.images.single.recall, 0.82);
      expect(s.isFinished, isFalse);
      await api.getSheet('sh_1');
      expect(seen.last.url.path, '/sheets/sh_1');
      final list = await api.listSheets('w', 'c_vesna');
      expect(seen.last.url.path, '/worlds/w/characters/c_vesna/sheets');
      expect(list, hasLength(1));

      await api.uploadCharacterReference(
        'w',
        'c_vesna',
        Uint8List.fromList([1, 2, 3]),
        'face.png',
      );
      final up = seen.last;
      expect(up.method, 'POST');
      expect(up.url.path, '/worlds/w/characters/c_vesna/references');
      expect(up.headers['X-User-ID'], 'player');
      expect(
        up.headers['content-type'],
        startsWith('multipart/form-data; boundary='),
      );
      final raw = latin1.decode(up.bodyBytes);
      expect(raw, contains('name="file"; filename="face.png"'));
      expect(raw, contains('content-type: image/png'));

      await api.deleteCharacter('w', 'c_vesna');
      expect(seen.last.method, 'DELETE');
      expect(seen.last.url.path, '/worlds/w/characters/c_vesna');
    });

    test('location endpoints', () async {
      final l = await api.updateLocation('w', 'l_post', {'mood': 'klid'});
      expect(seen.last.url.path, '/worlds/w/locations/l_post');
      expect(l.tags, ['indoors']);
      await api.suggestLocationTags('w', 'l_post');
      expect(seen.last.url.path, '/worlds/w/locations/l_post/tag_prompt');
      await api.uploadLocationReference(
        'w',
        'l_post',
        Uint8List(4),
        'tower.JPG',
      );
      expect(seen.last.url.path, '/worlds/w/locations/l_post/references');
      expect(
        latin1.decode(seen.last.bodyBytes),
        contains('content-type: image/jpeg'),
      );
      await api.deleteLocation('w', 'l_post');
      expect(seen.last.method, 'DELETE');
    });

    test('author errors in Czech; 503 = LLM off schedule', () {
      expect(
        czechError('character is the player character of a campaign', 409),
        contains('hraje za ni hráč'),
      );
      expect(czechError('file too large (max 8 MiB)', 413), contains('8 MiB'));
      expect(
        czechError('llm unavailable: dial tcp', 503),
        contains('LLM teď neběží'),
      );
    });
  });
}
