// "Your voice" (IAP voice_clone): the player API on JODA (docs/voice-backend.md, Director's PR #23).
// The phone talks only to this API with an anonymous device token; the clone and the lines are made by a
// worker on Spark (chatterbox-cs), asynchronously: poll the voice and the jobs.

import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../i18n/ui_strings.dart' show Localizable, tr;

const kVoiceApi = String.fromEnvironment(
  'VOICE_API',
  defaultValue: 'https://webtoon-api.ol1n.com',
);

/// Behind `--dart-define=VOICE_CLONING=true` until the server is deployed.
const kVoiceCloning = bool.fromEnvironment('VOICE_CLONING');

/// The IAP product that unlocks the voice (tools/products.csv).
const kVoiceProduct = 'voice_clone';

/// An error of the API: `{"error": code, "message": text}` (codes in docs/voice-backend.md).
class VoiceApiError implements Exception, Localizable {
  final int status;
  final String code;
  final String message;
  const VoiceApiError(this.status, this.code, [this.message = '']);

  /// Worth trying again later (the store, the worker or the network).
  bool get transient =>
      status >= 500 || code == 'rate_limited' || code == 'network';

  @override
  String localized(String lang) {
    final key = 'voice.error.$code';
    final s = tr(lang, key);
    return s == key ? tr(lang, 'voice.error.other', {'code': code}) : s;
  }

  @override
  String toString() => 'VoiceApiError($status $code: $message)';
}

enum VoiceStatus { queued, ready, failed }

class VoiceInfo {
  final String id;
  final VoiceStatus status;
  final String? error;
  const VoiceInfo(this.id, this.status, [this.error]);

  static VoiceInfo fromJson(Map<String, dynamic> j) =>
      VoiceInfo('${j['voice_id']}', switch (j['status']) {
        'ready' => VoiceStatus.ready,
        'failed' => VoiceStatus.failed,
        _ => VoiceStatus.queued,
      }, j['error'] as String?);
}

class VoiceLine {
  final String key;
  final String url;
  final double seconds;
  const VoiceLine(this.key, this.url, this.seconds);
}

class VoiceJob {
  final String id;
  final String status; // queued | running | done | failed
  final int done, total;
  final List<VoiceLine> lines;
  final List<String> missing;
  const VoiceJob(
    this.id,
    this.status,
    this.done,
    this.total,
    this.lines,
    this.missing,
  );

  bool get finished => status == 'done' || status == 'failed';

  static VoiceJob fromJson(Map<String, dynamic> j) => VoiceJob(
    '${j['job_id']}',
    '${j['status']}',
    (j['done'] as num?)?.toInt() ?? 0,
    (j['total'] as num?)?.toInt() ?? 0,
    [
      for (final l in (j['lines'] as List? ?? const []))
        VoiceLine(
          '${l['key']}',
          '${l['url']}',
          (l['duration_s'] as num?)?.toDouble() ?? 0,
        ),
    ],
    [for (final k in (j['missing'] as List? ?? const [])) '$k'],
  );
}

class VoiceApi {
  final String base;
  final http.Client _http;
  VoiceApi({this.base = kVoiceApi, http.Client? client})
    : _http = client ?? http.Client();

  static const maxLines = 200, maxChars = 300;

  Uri _u(String path) => Uri.parse('$base$path');

  Map<String, String> _auth(String token) => {'Authorization': 'Bearer $token'};

  Future<Map<String, dynamic>> _json(Future<http.Response> f) async {
    http.Response r;
    try {
      r = await f;
    } on SocketException catch (e) {
      throw VoiceApiError(0, 'network', '$e');
    } on http.ClientException catch (e) {
      throw VoiceApiError(0, 'network', '$e');
    }
    if (r.statusCode == 204) return const {};
    Map<String, dynamic> body = const {};
    try {
      final d = jsonDecode(utf8.decode(r.bodyBytes));
      if (d is Map<String, dynamic>) body = d;
    } catch (_) {}
    if (r.statusCode >= 400) {
      throw VoiceApiError(
        r.statusCode,
        '${body['error'] ?? 'http_${r.statusCode}'}',
        '${body['message'] ?? ''}',
      );
    }
    return body;
  }

  /// A new anonymous device: (device id, token). Keep the token secret.
  Future<(String, String)> registerDevice(String platform) async {
    final j = await _json(
      _http.post(
        _u('/v1/player/devices'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'platform': platform}),
      ),
    );
    return ('${j['device_id']}', '${j['token']}');
  }

  /// Deletes this device and its voice on the server.
  Future<void> deleteDevice(String token) =>
      _json(_http.delete(_u('/v1/player/devices/me'), headers: _auth(token)));

  /// Uploads the recording; [receipt] is the StoreKit 2 JWS (iOS) or the Play purchase token.
  Future<VoiceInfo> createVoice({
    required String token,
    required File sample,
    required String consentText,
    required String consentVersion,
    required String receipt,
    required String platform,
  }) async {
    final req = http.MultipartRequest('POST', _u('/v1/player/voices'))
      ..headers.addAll(_auth(token))
      ..fields.addAll({
        'consent': 'true',
        'consent_text': consentText,
        'consent_version': consentVersion,
        'receipt': receipt,
        'platform': platform,
      })
      ..files.add(await http.MultipartFile.fromPath('sample', sample.path));
    final j = await _json(_http.send(req).then(http.Response.fromStream));
    return VoiceInfo.fromJson(j);
  }

  Future<VoiceInfo> getVoice(String token, String id) async =>
      VoiceInfo.fromJson(
        await _json(
          _http.get(_u('/v1/player/voices/$id'), headers: _auth(token)),
        ),
      );

  Future<void> deleteVoice(String token, String id) =>
      _json(_http.delete(_u('/v1/player/voices/$id'), headers: _auth(token)));

  /// Asks for [lines] (key → text, at most [maxLines] of [maxChars]) in the voice; returns the job id.
  Future<String> requestLines(
    String token,
    String voiceId,
    String lang,
    Map<String, String> lines,
  ) async {
    final j = await _json(
      _http.post(
        _u('/v1/player/voices/$voiceId/lines'),
        headers: {..._auth(token), 'Content-Type': 'application/json'},
        body: jsonEncode({
          'lang': lang,
          'lines': [
            for (final e in lines.entries) {'key': e.key, 'text': e.value},
          ],
        }),
      ),
    );
    return '${j['job_id']}';
  }

  Future<VoiceJob> getJob(String token, String jobId) async =>
      VoiceJob.fromJson(
        await _json(
          _http.get(_u('/v1/player/jobs/$jobId'), headers: _auth(token)),
        ),
      );

  /// Downloads a line (its URL is signed, no token) to [path].
  Future<void> download(String url, String path) async {
    final r = await _http.get(Uri.parse(url));
    if (r.statusCode != 200) {
      throw VoiceApiError(
        r.statusCode,
        r.statusCode == 403 ? 'url_expired' : 'http_${r.statusCode}',
      );
    }
    await File(path).writeAsBytes(r.bodyBytes);
  }
}
