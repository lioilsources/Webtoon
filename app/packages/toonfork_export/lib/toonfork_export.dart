/// Native side of Toonfork's video export (iOS / macOS: AVFoundation, Android: MediaCodec + TTS).
///
/// - [voices] / [synth]: the system text-to-speech, one line to a wav file;
/// - [decode]: any audio file (mp3, m4a) to a wav;
/// - [start] / [frame] / [finish]: an H.264 + AAC mp4 from RGBA frames and one prepared wav track.
library;

import 'package:flutter/services.dart';

const _ch = MethodChannel('toonfork/export');

class SystemVoice {
  final String id;
  final String name;
  final String lang;

  /// 'm', 'f' or '' (Android voices rarely say).
  final String gender;

  /// 0 default, 1 enhanced, 2 premium.
  final int quality;

  const SystemVoice({
    required this.id,
    required this.name,
    required this.lang,
    this.gender = '',
    this.quality = 0,
  });
}

class ToonforkExport {
  static Future<List<SystemVoice>> voices(String lang) async {
    final list =
        await _ch.invokeListMethod<Map<Object?, Object?>>('voices', {
          'lang': lang,
        }) ??
        const [];
    return [
      for (final v in list)
        SystemVoice(
          id: '${v['id']}',
          name: '${v['name']}',
          lang: '${v['lang']}',
          gender: '${v['gender'] ?? ''}',
          quality: (v['quality'] as int?) ?? 0,
        ),
    ];
  }

  /// [rate] and [pitch]: 1.0 is the voice's normal.
  static Future<String> synth({
    required String text,
    required String lang,
    String? voice,
    double rate = 1,
    double pitch = 1,
    required String path,
  }) async => (await _ch.invokeMethod<String>('synth', {
    'text': text,
    'lang': lang,
    'voice': voice,
    'rate': rate,
    'pitch': pitch,
    'path': path,
  }))!;

  static Future<String> decode(String src, String dst) async =>
      (await _ch.invokeMethod<String>('decode', {'src': src, 'dst': dst}))!;

  /// [audio]: a 16-bit mono wav as long as the video (or null for none).
  static Future<void> start({
    required String path,
    required int width,
    required int height,
    required int fps,
    String? audio,
  }) => _ch.invokeMethod('start', {
    'path': path,
    'width': width,
    'height': height,
    'fps': fps,
    'audio': audio,
  });

  /// One frame, width × height × 4 bytes of RGBA.
  static Future<void> frame(Uint8List rgba) =>
      _ch.invokeMethod('frame', {'rgba': rgba});

  static Future<String> finish() async =>
      (await _ch.invokeMethod<String>('finish'))!;

  static Future<void> cancel() => _ch.invokeMethod('cancel');
}
