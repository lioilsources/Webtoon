import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:webtoon/voice/voice_api.dart';
import 'package:webtoon/voice/voice_controller.dart';

class _Secrets implements VoiceSecrets {
  final m = <String, String>{};
  @override
  Future<String?> read(String key) async => m[key];
  @override
  Future<void> write(String key, String? value) async =>
      value == null ? m.remove(key) : m[key] = value;
}

/// The player API of docs/voice-backend.md, in memory.
class _Server {
  final calls = <String>[];
  String voiceStatus = 'queued';
  int jobPolls = 0;
  bool voiceGone = false;

  http.Response _j(int code, Object body) => http.Response(
    jsonEncode(body),
    code,
    headers: {'content-type': 'application/json'},
  );

  Future<http.Response> handle(http.Request r) async {
    calls.add('${r.method} ${r.url.path}');
    final authed = r.headers['Authorization'] == 'Bearer tok';
    switch ((r.method, r.url.path)) {
      case ('POST', '/v1/player/devices'):
        return _j(201, {'device_id': 'd1', 'token': 'tok'});
      case _ when !authed && r.url.path.startsWith('/v1/player/'):
        return _j(401, {'error': 'unauthorized'});
      case ('POST', '/v1/player/voices'):
        if (!r.body.contains('voice_clone-jws')) {
          return _j(402, {'error': 'receipt_invalid', 'message': 'bad'});
        }
        return _j(201, {'voice_id': 'v1', 'status': 'queued'});
      case ('GET', '/v1/player/voices/v1'):
        if (voiceGone) return _j(404, {'error': 'not_found'});
        return _j(200, {'voice_id': 'v1', 'status': voiceStatus});
      case ('POST', '/v1/player/voices/v1/lines'):
        final lines = (jsonDecode(r.body)['lines'] as List).length;
        return _j(202, {'job_id': 'j$lines', 'status': 'queued'});
      case ('GET', final p) when p.startsWith('/v1/player/jobs/'):
        jobPolls++;
        final done = jobPolls >= 2;
        return _j(200, {
          'job_id': p.split('/').last,
          'status': done ? 'done' : 'running',
          'done': done ? 1 : 0,
          'total': 2,
          'lines': [
            if (done)
              {'key': 'a', 'url': 'https://cdn.test/a.m4a', 'duration_s': 1.2},
          ],
          if (done) 'missing': ['b'],
        });
      case ('DELETE', '/v1/player/voices/v1'):
        return http.Response('', 204);
      case ('GET', '/a.m4a'):
        return http.Response('m4a-bytes', 200);
    }
    return _j(404, {'error': 'not_found'});
  }
}

void main() {
  late _Server server;
  late VoiceApi api;
  late _Secrets secrets;

  setUp(() {
    server = _Server();
    api = VoiceApi(base: 'https://api.test', client: MockClient(server.handle));
    secrets = _Secrets();
  });

  Future<void> settle() =>
      Future<void>.delayed(const Duration(milliseconds: 20));

  test(
    'upload registers the device once, sends consent and the receipt, stores the voice id',
    () async {
      final c = VoiceController(api, secrets, () => 'voice_clone-jws');
      await settle();
      final sample = File('${Directory.systemTemp.path}/voice_test.m4a')
        ..writeAsBytesSync(List.filled(64, 1));
      await c.upload(sample, 'Jsem Olin a souhlasím…');
      expect(c.state.voice?.id, 'v1');
      expect(c.state.voice?.status, VoiceStatus.queued);
      expect(secrets.m['voice_device_token'], 'tok');
      expect(secrets.m['voice_id'], 'v1');
      expect(
        server.calls.where((x) => x == 'POST /v1/player/devices'),
        hasLength(1),
      );
      c.dispose();
    },
  );

  test('a rejected purchase is a localized error, nothing is stored', () async {
    final c = VoiceController(api, secrets, () => 'something-else');
    await settle();
    final sample = File('${Directory.systemTemp.path}/voice_test2.m4a')
      ..writeAsBytesSync([1, 2, 3]);
    await c.upload(sample, 'x');
    expect(c.state.error, isA<VoiceApiError>());
    expect((c.state.error as VoiceApiError).code, 'receipt_invalid');
    expect(
      (c.state.error as VoiceApiError).localized('cs'),
      'Nákup se nepodařilo ověřit.',
    );
    expect(
      (c.state.error as VoiceApiError).localized('en'),
      isNot(contains('voice.error')),
    );
    expect(secrets.m.containsKey('voice_id'), isFalse);
    c.dispose();
  });

  test('a voice deleted on the server (404) is forgotten here', () async {
    secrets.m['voice_device_token'] = 'tok';
    secrets.m['voice_id'] = 'v1';
    server.voiceGone = true;
    final c = VoiceController(api, secrets, () => null);
    await settle();
    expect(c.state.voice, isNull);
    expect(secrets.m.containsKey('voice_id'), isFalse);
    c.dispose();
  });

  test(
    'fetchLines polls the job, downloads the made lines, leaves out the missing ones',
    () async {
      secrets.m['voice_device_token'] = 'tok';
      secrets.m['voice_id'] = 'v1';
      server.voiceStatus = 'ready';
      final c = VoiceController(api, secrets, () => null);
      await settle();
      expect(c.state.ready, isTrue);
      final dir = Directory.systemTemp.createTempSync('voice_lines');
      final progress = <int>[];
      final got = await c.fetchLines(
        'cs',
        {'a': 'Ahoj.', 'b': 'Nazdar.'},
        dir,
        onProgress: (d, _) => progress.add(d),
      );
      expect(got.keys, ['a']);
      expect(File(got['a']!).readAsStringSync(), 'm4a-bytes');
      expect(server.jobPolls, 2);
      expect(progress.last, 1);
      c.dispose();
    },
    timeout: const Timeout(Duration(seconds: 20)),
  );

  test(
    'delete removes the voice on the server, keeps the device token',
    () async {
      secrets.m['voice_device_token'] = 'tok';
      secrets.m['voice_id'] = 'v1';
      server.voiceStatus = 'ready';
      final c = VoiceController(api, secrets, () => null);
      await settle();
      await c.delete();
      expect(server.calls, contains('DELETE /v1/player/voices/v1'));
      expect(server.calls, isNot(contains('DELETE /v1/player/devices/me')));
      expect(secrets.m.keys, ['voice_device_token']);
      expect(c.state.voice, isNull);
      c.dispose();
    },
  );
}
