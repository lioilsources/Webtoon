// Draws one frame of an exported video (dart:ui, offscreen). Layout as m0/shorts.py: a portrait panel fills
// the 9:16 frame with a slow zoom, a landscape panel or loop sits a little low on a blurred copy of itself,
// subtitles sit just above the TikTok / Shorts caption area, cards are text on the blurred panel.

import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/painting.dart' show TextAlign;

import 'export_plan.dart';

class FrameSpec {
  final int width, height, fps;
  const FrameSpec({this.width = 720, this.height = 1280, this.fps = 30});

  double get scale => width / 1080; // shorts.yaml is in 1080×1920 pixels
  double get bottom =>
      380 * scale; // caption and buttons: no lettering in the bottom 380 px
}

const _zoomPortrait = 0.08,
    _zoomLandscape = 0.05,
    _focusY = 0.42,
    _loopFps = 16;

/// Decoded images of one segment; [dispose] when the segment has scrolled past.
class SegmentAssets {
  final ui.Image? still;
  final List<ui.Image> loop;
  final ui.Image? blurred;
  final Map<Cue, ui.Picture> subtitles;
  final ui.Picture? card;
  SegmentAssets({
    this.still,
    this.loop = const [],
    this.blurred,
    this.subtitles = const {},
    this.card,
  });

  void dispose() {
    still?.dispose();
    for (final f in loop) {
      f.dispose();
    }
    blurred?.dispose();
    for (final p in subtitles.values) {
      p.dispose();
    }
    card?.dispose();
  }
}

class FrameRenderer {
  final FrameSpec spec;
  final String? fontFamily;
  FrameRenderer(this.spec, {this.fontFamily});

  Future<ui.Image> _decode(String path) async {
    final codec = await ui.instantiateImageCodec(
      await File(path).readAsBytes(),
    );
    return (await codec.getNextFrame()).image;
  }

  Future<List<ui.Image>> _frames(String path) async {
    final codec = await ui.instantiateImageCodec(
      await File(path).readAsBytes(),
    );
    return [
      for (var i = 0; i < codec.frameCount; i++)
        (await codec.getNextFrame()).image,
    ];
  }

  Rect _coverSrc(ui.Image img, double zoom) {
    final w = spec.width.toDouble(), h = spec.height.toDouble();
    final cw = math.min(img.width.toDouble(), img.height * w / h) / zoom;
    final ch = cw * h / w;
    final x = (img.width - cw) / 2;
    final y = (img.height * _focusY - ch / 2)
        .clamp(0.0, math.max(0.0, img.height - ch))
        .toDouble();
    return Rect.fromLTWH(x, y, cw, ch);
  }

  Rect get _full =>
      Rect.fromLTWH(0, 0, spec.width.toDouble(), spec.height.toDouble());

  Future<ui.Image> _blur(ui.Image img) async {
    final r = ui.PictureRecorder();
    final c = ui.Canvas(r);
    final sigma = 40 * spec.scale;
    c.saveLayer(
      _full,
      ui.Paint()
        ..imageFilter = ui.ImageFilter.blur(
          sigmaX: sigma,
          sigmaY: sigma,
          tileMode: ui.TileMode.clamp,
        ),
    );
    c.drawImageRect(
      img,
      _coverSrc(img, 1),
      _full,
      ui.Paint()..filterQuality = ui.FilterQuality.medium,
    );
    c.restore();
    c.drawRect(
      _full,
      ui.Paint()..color = const ui.Color(0x59000000),
    ); // darkened 35 %
    final pic = r.endRecording();
    final out = await pic.toImage(spec.width, spec.height);
    pic.dispose();
    return out;
  }

  ui.Paragraph _paragraph(
    String text,
    double size,
    ui.Color color,
    double maxWidth, {
    bool stroke = false,
  }) {
    final style = ui.TextStyle(
      fontSize: size,
      fontWeight: ui.FontWeight.w800,
      fontFamily: fontFamily,
      height: 1.2,
      foreground: stroke
          ? (ui.Paint()
              ..style = ui.PaintingStyle.stroke
              ..strokeWidth = size * 0.09
              ..color = const ui.Color(0xFF000000))
          : (ui.Paint()..color = color),
    );
    final b =
        ui.ParagraphBuilder(
            ui.ParagraphStyle(
              textAlign: TextAlign.center,
              maxLines: 6,
              ellipsis: '…',
            ),
          )
          ..pushStyle(style)
          ..addText(text);
    return b.build()..layout(ui.ParagraphConstraints(width: maxWidth));
  }

  static const _roleColors = {
    LineRole.speech: ui.Color(0xFFFFFFFF),
    LineRole.narration: ui.Color(0xFFFFDE82),
    LineRole.machine: ui.Color(0xFF96E1FF),
  };

  /// A subtitle block on a translucent box, bottom-aligned just above the caption area.
  ui.Picture _subtitle(Cue cue) {
    final size = 44 * spec.scale * 1.5, margin = 40 * spec.scale;
    final maxW = spec.width - 4 * margin;
    final fill = _paragraph(cue.line.text, size, _roleColors[cue.role]!, maxW);
    final edge = _paragraph(
      cue.line.text,
      size,
      _roleColors[cue.role]!,
      maxW,
      stroke: true,
    );
    var widest = 0.0;
    for (final l in fill.computeLineMetrics()) {
      widest = math.max(widest, l.width);
    }
    final bottom = spec.height - spec.bottom - 10 * spec.scale;
    final top = bottom - fill.height - margin;
    final r = ui.PictureRecorder();
    final c = ui.Canvas(r);
    c.drawRRect(
      ui.RRect.fromLTRBR(
        (spec.width - widest) / 2 - margin * 0.75,
        top,
        (spec.width + widest) / 2 + margin * 0.75,
        bottom,
        ui.Radius.circular(24 * spec.scale),
      ),
      ui.Paint()..color = const ui.Color(0x96000000),
    );
    final at = ui.Offset((spec.width - maxW) / 2, top + margin / 2);
    c.drawParagraph(edge, at);
    c.drawParagraph(fill, at);
    return r.endRecording();
  }

  ui.Picture _cardText(String text, bool big) {
    final size = (big ? 120 : 96) * spec.scale;
    final maxW = spec.width - 160 * spec.scale;
    final fill = _paragraph(text, size, const ui.Color(0xFFFFFFFF), maxW);
    final edge = _paragraph(
      text,
      size,
      const ui.Color(0xFFFFFFFF),
      maxW,
      stroke: true,
    );
    final r = ui.PictureRecorder();
    final c = ui.Canvas(r);
    final at = ui.Offset(
      (spec.width - maxW) / 2,
      (spec.height - fill.height) / 2,
    );
    c.drawParagraph(edge, at);
    c.drawParagraph(fill, at);
    return r.endRecording();
  }

  Future<SegmentAssets> load(Segment s) async {
    switch (s) {
      case CardSegment c:
        final under = c.underImage == null
            ? null
            : await _decode(c.underImage!);
        final blurred = under == null ? null : await _blur(under);
        under?.dispose();
        return SegmentAssets(blurred: blurred, card: _cardText(c.text, c.big));
      case PanelSegment p:
        final still = await _decode(p.panel.imageUrl!);
        var loop = <ui.Image>[];
        final v = p.panel.videoUrl;
        if (v != null &&
            p.panel.videoStatus != 'failed' &&
            File(v).existsSync()) {
          try {
            loop = await _frames(v);
          } catch (_) {
            loop = []; // a loop the decoder cannot read: the still does
          }
        }
        final landscape = still.width > still.height;
        return SegmentAssets(
          still: still,
          loop: loop,
          blurred: landscape ? await _blur(still) : null,
          subtitles: {for (final cue in p.cues) cue: _subtitle(cue)},
        );
    }
  }

  void _drawPanel(ui.Canvas c, PanelSegment p, SegmentAssets a, double t) {
    final paint = ui.Paint()..filterQuality = ui.FilterQuality.medium;
    final img = a.loop.isNotEmpty
        ? a.loop[(t * _loopFps).floor() % a.loop.length]
        : a.still!;
    final landscape = a.still!.width > a.still!.height;
    if (landscape) {
      c.drawImage(a.blurred!, ui.Offset.zero, ui.Paint());
      final z = a.loop.isEmpty ? 1 + _zoomLandscape * t / p.duration : 1.0;
      final fw = spec.width.toDouble(), fh = img.height * fw / img.width;
      final src = Rect.fromCenter(
        center: ui.Offset(img.width / 2, img.height / 2),
        width: img.width / z,
        height: img.height / z,
      );
      final top =
          (spec.height - fh) / 2 +
          120 * spec.scale; // a little low, the subtitles sit on the blur
      c.drawImageRect(img, src, Rect.fromLTWH(0, top, fw, fh), paint);
    } else {
      final z = a.loop.isEmpty
          ? 1 + _zoomPortrait * t / p.duration
          : 1 + _zoomPortrait / 2;
      c.drawImageRect(img, _coverSrc(img, z), _full, paint);
    }
    final cue = cueAt(p.cues, t);
    if (cue != null) c.drawPicture(a.subtitles[cue]!);
  }

  void _draw(ui.Canvas c, Segment s, SegmentAssets a, double t) {
    switch (s) {
      case CardSegment _:
        if (a.blurred != null) {
          c.drawImage(a.blurred!, ui.Offset.zero, ui.Paint());
        } else {
          c.drawRect(_full, ui.Paint()..color = const ui.Color(0xFF111111));
        }
        c.drawPicture(a.card!);
      case PanelSegment p:
        _drawPanel(c, p, a, t);
    }
  }

  /// RGBA bytes of segment [s] at its time [t], crossfaded into [next] at [tNext] when given.
  Future<Uint8List> frame(
    Segment s,
    SegmentAssets a,
    double t, {
    Segment? next,
    SegmentAssets? nextAssets,
    double? tNext,
  }) async {
    final r = ui.PictureRecorder();
    final c = ui.Canvas(r, _full);
    _draw(c, s, a, t);
    if (next != null && nextAssets != null && tNext != null) {
      final alpha = (tNext / ExportTiming.fade).clamp(0.0, 1.0);
      c.saveLayer(_full, ui.Paint()..color = ui.Color.fromRGBO(0, 0, 0, alpha));
      _draw(c, next, nextAssets, tNext);
      c.restore();
    }
    final pic = r.endRecording();
    final img = pic.toImageSync(spec.width, spec.height);
    pic.dispose();
    final bytes = await img.toByteData(format: ui.ImageByteFormat.rawRgba);
    img.dispose();
    return bytes!.buffer.asUint8List();
  }
}

typedef Rect = ui.Rect;
