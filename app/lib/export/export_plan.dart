// Timing of an exported video: the same rules as m0/shorts.py (rules/base/shorts.yaml), so a video made in the
// app looks like the TikToks made in the studio. Pure Dart: what is on screen when, and where each line is
// spoken; frame_renderer.dart draws it and video_exporter.dart encodes it.

import 'dart:math' as math;

import '../models/episode.dart';

class ExportTiming {
  static const fade = 0.35; // crossfade between segments
  static const titleCard = 1.8;
  static const endCard = 2.0;
  // a silent panel stays up as long as its text takes to read
  static const readBase = 1.8, readPerChar = 0.07, readMin = 2.5, readMax = 6.0;
  static const loopMin = 4.0; // at least two passes of a 2 s motion loop
  // a voiced panel stays up while its lines are spoken
  static const lead = 0.25, gap = 0.3, tail = 0.5;
}

/// How a line is shown and voiced.
enum LineRole { speech, narration, machine }

class ExportLine {
  /// Unique within the export: `<episode id>/<panel index>/<bubble index>`.
  final String key;
  final String text;
  final String speakerId;
  final BubbleKind kind;
  const ExportLine({
    required this.key,
    required this.text,
    required this.speakerId,
    required this.kind,
  });
}

class Cue {
  final double start;
  final ExportLine line;
  final LineRole role;
  const Cue(this.start, this.line, this.role);
}

sealed class Segment {
  double get duration;
}

class CardSegment extends Segment {
  final String text;
  final bool big; // the end card
  /// The panel image under the card (blurred).
  final String? underImage;
  @override
  final double duration;
  CardSegment(this.text, this.underImage, this.duration, {this.big = false});
}

class PanelSegment extends Segment {
  final Panel panel;
  final List<Cue> cues;

  /// Lines with a voice: (start in the segment, line key).
  final List<(double, String)> voice;
  @override
  final double duration;
  PanelSegment(this.panel, this.cues, this.voice, this.duration);
}

class ExportPlan {
  final List<Segment> segments;
  const ExportPlan(this.segments);

  /// Segments overlap by [ExportTiming.fade].
  double get duration =>
      segments.fold<double>(0, (s, g) => s + g.duration) -
      ExportTiming.fade * math.max(0, segments.length - 1);

  double startOf(int i) {
    var t = 0.0;
    for (var k = 0; k < i; k++) {
      t += segments[k].duration - ExportTiming.fade;
    }
    return t;
  }

  /// Every voiced line at its time in the video.
  List<(double, String)> get placedVoice => [
    for (var i = 0; i < segments.length; i++)
      if (segments[i] case PanelSegment p)
        for (final (t, key) in p.voice) (startOf(i) + t, key),
  ];
}

/// The panel's lines in reading order: narration first (as the bubbles stack), then the rest.
List<ExportLine> panelLines(String episodeId, Panel p, String? lang) {
  final order = [
    for (var i = 0; i < p.bubbles.length; i++)
      if (p.bubbles[i].isNarration) i,
    for (var i = 0; i < p.bubbles.length; i++)
      if (!p.bubbles[i].isNarration) i,
  ];
  return [
    for (final i in order)
      if (p.bubbles[i].textIn(lang).trim().isNotEmpty)
        ExportLine(
          key: '$episodeId/${p.index}/$i',
          text: p.bubbles[i].textIn(lang).trim(),
          speakerId: p.bubbles[i].speakerId ?? '',
          kind: p.bubbles[i].kind,
        ),
  ];
}

/// [episodes] in order (one chapter, or a whole story); [lineSeconds] is the spoken length of a line, or null
/// when it has no voice (then the panel times like a silent one); [roleOf] colours the subtitles.
ExportPlan buildPlan({
  required List<Episode> episodes,
  required String? lang,
  required String endText,
  required LineRole Function(ExportLine) roleOf,
  double? Function(ExportLine)? lineSeconds,
}) {
  final segs = <Segment>[];
  for (final ep in episodes) {
    final panels = ep.panels.where((p) => p.imageUrl != null).toList();
    if (panels.isEmpty) continue;
    segs.add(
      CardSegment(
        ep.titleIn(lang),
        panels.first.imageUrl,
        ExportTiming.titleCard,
      ),
    );
    for (final p in panels) {
      segs.add(_panel(ep.id, p, lang, roleOf, lineSeconds));
    }
  }
  if (segs.isNotEmpty) {
    final last = episodes.last.panels.lastWhere(
      (p) => p.imageUrl != null,
      orElse: () => episodes.last.panels.first,
    );
    segs.add(
      CardSegment(endText, last.imageUrl, ExportTiming.endCard, big: true),
    );
  }
  return ExportPlan(segs);
}

PanelSegment _panel(
  String episodeId,
  Panel p,
  String? lang,
  LineRole Function(ExportLine) roleOf,
  double? Function(ExportLine)? lineSeconds,
) {
  final lines = panelLines(episodeId, p, lang);
  final cues = <Cue>[];
  final voice = <(double, String)>[];
  final chars = lines.fold<int>(0, (n, l) => n + l.text.length);
  final reading = (ExportTiming.readBase + ExportTiming.readPerChar * chars)
      .clamp(ExportTiming.readMin, ExportTiming.readMax);
  final voiced =
      lineSeconds != null && lines.any((l) => lineSeconds(l) != null);
  double dur;
  if (voiced) {
    var t = ExportTiming.lead;
    for (final l in lines) {
      final s = lineSeconds(l);
      cues.add(Cue(t, l, roleOf(l)));
      if (s != null) voice.add((t, l.key));
      t += (s ?? ExportTiming.readBase) + ExportTiming.gap;
    }
    dur = math.max(
      ExportTiming.readMin,
      t - ExportTiming.gap + ExportTiming.tail,
    );
  } else {
    var t = 0.0;
    for (final l in lines) {
      cues.add(Cue(t, l, roleOf(l)));
      t += reading * l.text.length / math.max(chars, 1);
    }
    dur = reading;
  }
  if (p.videoUrl != null && p.videoStatus != 'failed') {
    dur = math.max(dur, ExportTiming.loopMin);
  }
  return PanelSegment(p, cues, voice, dur);
}

/// The cue on screen at [t] in a panel: the latest one started, or the first before it starts.
Cue? cueAt(List<Cue> cues, double t) {
  if (cues.isEmpty) return null;
  Cue c = cues.first;
  for (final x in cues) {
    if (x.start <= t) c = x;
  }
  return c;
}
