import 'dart:math' as math;

import 'package:flutter/painting.dart';

import '../models/episode.dart';
import '../theme.dart';

/// All m0/compose.py measures are for a strip 800 px wide; everything here is scaled by
/// `panelWidth / 800`.
const double kReferenceWidth = 800;

/// A bubble with its computed box and tail, in panel coordinates (logical px).
class PlacedBubble {
  /// Index into `panel.bubbles` (edits are addressed by it).
  final int index;
  final Bubble bubble;
  final Rect rect;

  /// Where the tail leaves the bubble (bottom or top edge) and where it points.
  /// Null for narration.
  final Offset? tailBase;
  final Offset? tailTip;

  final TextStyle style;

  /// Inner text box (rect minus padding).
  final EdgeInsets padding;

  /// Scale factor (panel width / 800) — line widths etc. derive from it.
  final double scale;

  const PlacedBubble({
    required this.index,
    required this.bubble,
    required this.rect,
    required this.style,
    required this.padding,
    required this.scale,
    this.tailBase,
    this.tailTip,
  });

  BubbleKind get kind => bubble.kind;
  Rect get textRect => padding.deflateRect(rect);
}

/// Font for a bubble kind at a given scale (compose.py: 26 px, shout 30 px at width 800).
TextStyle bubbleTextStyle(BubbleKind kind, double scale) {
  final base = switch (kind) {
    BubbleKind.speech => ComicFonts.speech(),
    BubbleKind.thought => ComicFonts.thought(),
    BubbleKind.shout => ComicFonts.shout(),
    BubbleKind.narration => ComicFonts.narration(),
  };
  final size = (kind == BubbleKind.shout ? 30.0 : 26.0) * scale;
  // Every metric is explicit: the Text widget would otherwise inherit e.g. Material's
  // letterSpacing from DefaultTextStyle and wrap differently from the measurement here.
  return base.copyWith(
    fontSize: size,
    height: 1.25,
    color: ComicColors.ink,
    letterSpacing: 0,
    wordSpacing: 0,
    decoration: TextDecoration.none,
    fontFeatures: const [],
    shadows: const [],
    leadingDistribution: TextLeadingDistribution.even,
  );
}

typedef BubbleStyleFor = TextStyle Function(BubbleKind kind, double scale);

/// Placement heuristic from m0/compose.py:
///  * narration: boxes stacked at the top-left, up to 80 % of the width;
///  * talk bubbles (speech/thought/shout): up to 62 % wide, alternating top corners
///    (left, right, left, …; the first one goes right when there is narration), the right
///    column 40 px lower so the bubbles zig-zag; tails point toward the panel centre.
///
/// Improvements over the script: columns are stacked with cursors and a bubble that would
/// collide with an earlier one moves below it (as long as the panel is tall enough),
/// everything is clamped inside the panel, and when the speaker has a `bbox`
/// (characters[].bbox, §5.4 postprocess) the bubble takes the corner that covers the fewest
/// character boxes and its tail aims at the speaker's head. An explicit `anchor` on the
/// bubble wins over both.
List<PlacedBubble> layoutBubbles(
  Size size,
  List<Bubble> bubbles, {
  List<PanelCharacter> characters = const [],
  TextScaler textScaler = TextScaler.noScaling,
  BubbleStyleFor styleFor = bubbleTextStyle,
}) {
  if (size.isEmpty || bubbles.isEmpty) return const [];
  final w = size.width, h = size.height;
  final s = w / kReferenceWidth;
  final margin = 22 * s;
  final padding = EdgeInsets.symmetric(horizontal: 22 * s, vertical: 15 * s);
  final boxes = <String, Rect>{
    for (final c in characters)
      if (c.bbox != null)
        c.id: Rect.fromLTRB(
          c.bbox!.left * w,
          c.bbox!.top * h,
          c.bbox!.right * w,
          c.bbox!.bottom * h,
        ),
  };

  Size measure(Bubble b, TextStyle style) {
    final maxW = w * (b.isNarration ? 0.8 : 0.62);
    final tp = TextPainter(
      text: TextSpan(text: b.text.isEmpty ? ' ' : b.text, style: style),
      textAlign: TextAlign.center,
      textDirection: TextDirection.ltr,
      textScaler: textScaler,
    )..layout(maxWidth: math.max(1, maxW - padding.horizontal));
    final size = Size(
      math.min(tp.width + padding.horizontal + 1, w - 2 * margin),
      tp.height + padding.vertical,
    );
    tp.dispose();
    return size;
  }

  Rect clampRect(Rect r) {
    final dx = r.left < margin
        ? margin - r.left
        : (r.right > w - margin ? (w - margin) - r.right : 0.0);
    final maxTop = math.max(margin, h - margin - r.height);
    final top = r.top.clamp(margin, maxTop);
    return Rect.fromLTWH(r.left + dx, top, r.width, r.height);
  }

  final out = <PlacedBubble>[];

  // --- narration: top-left stack -----------------------------------------------------
  var y = margin;
  for (var i = 0; i < bubbles.length; i++) {
    final b = bubbles[i];
    if (!b.isNarration) continue;
    final style = styleFor(b.kind, s);
    final sz = measure(b, style);
    final rect = clampRect(Rect.fromLTWH(margin, y, sz.width, sz.height));
    out.add(
      PlacedBubble(
        index: i,
        bubble: b,
        rect: rect,
        style: style,
        padding: padding,
        scale: s,
      ),
    );
    y = rect.bottom + 12 * s;
  }

  // --- talk bubbles: alternate top corners -----------------------------------------
  final hasNarration = out.isNotEmpty;
  final top = hasNarration ? y : margin;
  var leftY = top;
  var rightY = top + 40 * s;
  var k = 0;
  for (var i = 0; i < bubbles.length; i++) {
    final b = bubbles[i];
    if (b.isNarration) continue;
    final slot = k + (hasNarration ? 1 : 0);
    k++;
    final style = styleFor(b.kind, s);
    final sz = measure(b, style);
    Rect at(bool right) {
      var r = Rect.fromLTWH(
        right ? w - margin - sz.width : margin,
        right ? rightY : leftY,
        sz.width,
        sz.height,
      );
      // Two wide bubbles (62 % each) can collide across the columns: move below the other.
      for (var moved = true; moved;) {
        moved = false;
        for (final o in out) {
          final x = r.intersect(o.rect.inflate(6 * s));
          if (x.width > 0 && x.height > 0) {
            r = r.translate(0, o.rect.bottom + 12 * s - r.top);
            moved = true;
          }
        }
      }
      return clampRect(r);
    }

    var right = slot.isOdd;
    final speakerBox = boxes[b.speakerId];
    if (boxes.isNotEmpty) {
      // Corner covering the least of the characters; ties keep the alternation.
      double cover(Rect r) => boxes.values.fold(0.0, (a, bb) {
        final x = r.intersect(bb);
        return a + (x.width > 0 && x.height > 0 ? x.width * x.height : 0);
      });
      final l = cover(at(false)), r = cover(at(true));
      if ((l - r).abs() > 1) right = r < l;
    }
    final rect = at(right);
    if (right) {
      rightY = rect.bottom + 30 * s;
    } else {
      leftY = rect.bottom + 30 * s;
    }

    Offset? target;
    if (b.anchor != null) {
      target = Offset(b.anchor!.dx * w, b.anchor!.dy * h);
    } else if (speakerBox != null) {
      // Aim at the head: upper part of the speaker's box, horizontally under the bubble if possible.
      target = Offset(
        rect.center.dx.clamp(
          speakerBox.left + speakerBox.width * 0.25,
          speakerBox.right - speakerBox.width * 0.25,
        ),
        speakerBox.top + speakerBox.height * 0.15,
      );
    }
    final (base, tip) = _tail(rect, target, size, s);
    out.add(
      PlacedBubble(
        index: i,
        bubble: b,
        rect: rect,
        style: style,
        padding: padding,
        scale: s,
        tailBase: base,
        tailTip: tip,
      ),
    );
  }
  return out;
}

/// Tail geometry. Without a target: compose.py — from the bottom centre, 48 px down and 40 px
/// toward the panel centre. With a target: from the edge facing it, pointing at it but not
/// longer than 120 px (×scale) and stopping a bit short so it doesn't cover the face.
(Offset, Offset) _tail(Rect rect, Offset? target, Size size, double s) {
  final cx = rect.center.dx;
  if (target == null) {
    final base = Offset(cx, rect.bottom);
    final tip = Offset(
      cx + (cx < size.width / 2 ? 40 : -40) * s,
      math.min(size.height - 20 * s, rect.bottom + 48 * s),
    );
    return (base, tip);
  }
  final below = target.dy >= rect.center.dy;
  final inset = math.min(rect.width / 2, 30 * s);
  final base = Offset(
    target.dx.clamp(rect.left + inset, rect.right - inset),
    below ? rect.bottom : rect.top,
  );
  var d = target - base;
  final len = d.distance;
  if (len < 1) return (base, base + Offset(0, (below ? 1 : -1) * 24 * s));
  final maxLen = 120 * s;
  final useLen = math.min(len * 0.85, maxLen);
  d = d / len * math.max(useLen, 24 * s);
  var tip = base + d;
  tip = Offset(
    tip.dx.clamp(2.0, size.width - 2),
    tip.dy.clamp(2.0, size.height - 2),
  );
  return (base, tip);
}
