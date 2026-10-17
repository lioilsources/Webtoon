import 'dart:convert';

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
}
