// Episode(s) → a 9:16 mp4 for TikTok / YouTube Shorts, made on the phone: every line spoken by the system TTS
// (optional), subtitles instead of bubbles, a music track under the voices. Steps: voice the lines, plan the
// timing (export_plan.dart), mix one audio track, draw and encode the frames (toonfork_export).

import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter/services.dart' show rootBundle;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:toonfork_export/toonfork_export.dart';

import '../models/episode.dart';
import 'export_plan.dart';
import 'frame_renderer.dart';
import 'voices.dart';
import 'wav.dart';

/// Tracks bundled with the app (ACE-Step, MIT; tools: m0/music.py). A world always gets the same one.
const kExportMusic = [
  'assets/music/lofi_1.m4a',
  'assets/music/piano_2.m4a',
  'assets/music/synth_2.m4a',
  'assets/music/strings_2.m4a',
];

String musicFor(String worldId) {
  var h = 0;
  for (final c in worldId.codeUnits) {
    h = (h * 31 + c) & 0x7fffffff;
  }
  return kExportMusic[h % kExportMusic.length];
}

class ExportOptions {
  final List<Episode> episodes;
  final String? lang; // null = original
  final String ttsLang; // the language the voices speak (BCP 47)
  final bool dub;
  final String? music; // asset path, or null for none
  final Cast cast;
  final String endText;
  final FrameSpec spec;
  final String fileName;
  const ExportOptions({
    required this.episodes,
    required this.lang,
    required this.ttsLang,
    required this.dub,
    required this.music,
    required this.cast,
    required this.endText,
    required this.fileName,
    this.spec = const FrameSpec(),
  });
}

enum ExportPhase { voices, music, frames, done }

class ExportProgress {
  final ExportPhase phase;
  final double fraction; // of this phase
  const ExportProgress(this.phase, this.fraction);
}

class ExportCancelled implements Exception {}

class VideoExporter {
  bool _cancel = false;
  void cancel() => _cancel = true;

  void _check() {
    if (_cancel) throw ExportCancelled();
  }

  Future<String> run(
    ExportOptions o,
    void Function(ExportProgress) onProgress,
  ) async {
    final work = Directory(
      p.join((await getTemporaryDirectory()).path, 'toonfork_export'),
    );
    if (work.existsSync()) work.deleteSync(recursive: true);
    work.createSync(recursive: true);

    // 1. voices
    final lines = [
      for (final ep in o.episodes)
        for (final panel in ep.panels.where((x) => x.imageUrl != null))
          ...panelLines(ep.id, panel, o.lang),
    ];
    final spoken = <String, Float32List>{};
    if (o.dub) {
      for (var i = 0; i < lines.length; i++) {
        _check();
        onProgress(
          ExportProgress(ExportPhase.voices, i / math.max(1, lines.length)),
        );
        final l = lines[i];
        final v = o.cast.voiceFor(l);
        final path = p.join(work.path, 'line_$i.wav');
        try {
          await ToonforkExport.synth(
            text: _speakable(l.text),
            lang: o.ttsLang,
            voice: v.voiceId,
            rate: v.rate,
            pitch: v.pitch,
            path: path,
          );
          var x = trimSilence(await readWav(path));
          if (v.robot) x = robotize(x);
          if (x.isNotEmpty) spoken[l.key] = x;
        } catch (e) {
          // one line the TTS refuses must not stop the video: it stays a subtitle
          debugPrint('export: no voice for ${l.key}: $e');
        }
      }
    }

    debugPrint('export: ${spoken.length} of ${lines.length} lines voiced');

    // 2. timing
    final plan = buildPlan(
      episodes: o.episodes,
      lang: o.lang,
      endText: o.endText,
      roleOf: o.cast.roleOf,
      lineSeconds: o.dub
          ? (l) => spoken[l.key] == null
                ? null
                : spoken[l.key]!.length / kExportRate
          : null,
    );
    if (plan.segments.isEmpty) throw StateError('nothing to export');

    // 3. one audio track: the lines where they are spoken, the music under them
    onProgress(const ExportProgress(ExportPhase.music, 0));
    final total = plan.duration;
    final mix = Float32List((total * kExportRate).ceil());
    for (final (t, key) in plan.placedVoice) {
      final x = spoken[key]!;
      final at = (t * kExportRate).round();
      for (var i = 0; i < x.length && at + i < mix.length; i++) {
        mix[at + i] += x[i];
      }
    }
    if (o.music != null) {
      final src = p.join(work.path, 'music${p.extension(o.music!)}');
      await File(
        src,
      ).writeAsBytes((await rootBundle.load(o.music!)).buffer.asUint8List());
      final wav = await ToonforkExport.decode(
        src,
        p.join(work.path, 'music.wav'),
      );
      final m = await readWav(wav);
      if (m.isNotEmpty) {
        final gain = o.dub ? 0.35 : 0.8;
        final fadeIn = 0.5 * kExportRate, fadeOut = 2.0 * kExportRate;
        for (var i = 0; i < mix.length; i++) {
          var g = gain;
          if (i < fadeIn) g *= i / fadeIn;
          if (i > mix.length - fadeOut) g *= (mix.length - i) / fadeOut;
          mix[i] += m[i % m.length] * g;
        }
      }
    }
    final audio = p.join(work.path, 'mix.wav');
    await File(audio).writeAsBytes(encodeWav(mix));

    // 4. frames
    final out = p.join(work.path, o.fileName);
    final spec = o.spec;
    final r = FrameRenderer(spec);
    await ToonforkExport.start(
      path: out,
      width: spec.width,
      height: spec.height,
      fps: spec.fps,
      audio: audio,
    );
    try {
      final frames = (total * spec.fps).round();
      final assets = <int, SegmentAssets>{};
      Future<SegmentAssets> load(int k) async =>
          assets[k] ??= await r.load(plan.segments[k]);
      var k = 0, kStart = 0.0;
      for (var n = 0; n < frames; n++) {
        _check();
        final t = n / spec.fps;
        while (k < plan.segments.length - 1 &&
            t >= kStart + plan.segments[k].duration - ExportTiming.fade) {
          kStart += plan.segments[k].duration - ExportTiming.fade;
          assets.remove(k - 1)?.dispose();
          k++;
        }
        // t is in segment k; in its last FADE seconds the next one fades in over it
        final s = plan.segments[k];
        final local = t - kStart;
        final a = await load(k);
        final hasNext = k + 1 < plan.segments.length;
        final rgba = hasNext && local > s.duration - ExportTiming.fade
            ? await r.frame(
                s,
                a,
                local,
                next: plan.segments[k + 1],
                nextAssets: await load(k + 1),
                tNext: local - (s.duration - ExportTiming.fade),
              )
            : await r.frame(s, a, local);
        await ToonforkExport.frame(rgba);
        if (n % 15 == 0) {
          onProgress(ExportProgress(ExportPhase.frames, n / frames));
        }
      }
      for (final a in assets.values) {
        a.dispose();
      }
      final path = await ToonforkExport.finish();
      onProgress(const ExportProgress(ExportPhase.done, 1));
      return path;
    } catch (e) {
      await ToonforkExport.cancel();
      rethrow;
    }
  }
}

/// What the TTS reads: ALL-CAPS narration would be spelled out letter by letter.
String _speakable(String text) =>
    text == text.toUpperCase() && text != text.toLowerCase()
    ? text[0] + text.substring(1).toLowerCase()
    : text;
