import 'dart:math' as math;

import 'package:flutter/rendering.dart';

import '../models/episode.dart';
import '../theme.dart';
import 'bubble_layout.dart';

/// Paints bubble bodies and tails (the text is laid out by widgets on top, so it stays
/// selectable/accessible and editable). Bubbles are always white with ink outlines, in both
/// themes, as in print comics.
class BubblesPainter extends CustomPainter {
  final List<PlacedBubble> bubbles;
  final int? highlighted;

  const BubblesPainter(this.bubbles, {this.highlighted});

  @override
  void paint(Canvas canvas, Size size) {
    for (final b in bubbles) {
      paintBubble(canvas, b, highlighted: b.index == highlighted);
    }
  }

  @override
  bool shouldRepaint(BubblesPainter old) =>
      old.bubbles != bubbles || old.highlighted != highlighted;
}

/// Outline path of one bubble including its tail (thought trails are separate circles).
Path bubblePath(PlacedBubble b) {
  final s = b.scale;
  final r = b.rect;
  switch (b.kind) {
    case BubbleKind.narration:
      return Path()..addRect(r);
    case BubbleKind.speech:
      final body = Path()
        ..addRRect(
          RRect.fromRectAndRadius(
            r,
            Radius.circular(math.min(r.height / 2, 40 * s)),
          ),
        );
      return _withTail(body, b, 16 * s);
    case BubbleKind.thought:
      return _cloud(r, s);
    case BubbleKind.shout:
      return _withTail(_burst(r, s), b, 18 * s);
  }
}

void paintBubble(Canvas canvas, PlacedBubble b, {bool highlighted = false}) {
  final s = b.scale;
  final stroke = Paint()
    ..style = PaintingStyle.stroke
    ..color = ComicColors.ink
    ..strokeJoin = StrokeJoin.round
    ..strokeWidth = math.max(1.5, (b.kind == BubbleKind.shout ? 4 : 3) * s);
  final fill = Paint()
    ..color = b.kind == BubbleKind.narration
        ? ComicColors.narrationBox
        : ComicColors.bubble;
  final path = bubblePath(b);

  if (b.kind == BubbleKind.narration) {
    // Hard drop shadow, like a caption box glued on the panel.
    canvas.drawPath(
      path.shift(Offset(4 * s, 4 * s)),
      Paint()..color = ComicColors.ink.withValues(alpha: 0.85),
    );
  }
  if (b.kind == BubbleKind.thought && b.tailBase != null && b.tailTip != null) {
    final base = b.tailBase!, tip = b.tailTip!;
    for (final (rad, f) in [(10.0, 0.35), (7.0, 0.65), (5.0, 0.9)]) {
      final c = Offset.lerp(base, tip, f)!;
      canvas.drawCircle(c, rad * s, fill);
      canvas.drawCircle(c, rad * s, stroke..strokeWidth = math.max(1.2, 2 * s));
    }
    stroke.strokeWidth = math.max(1.5, 3 * s);
  }
  canvas.drawPath(path, fill);
  canvas.drawPath(path, stroke);
  if (highlighted) {
    canvas.drawPath(
      path,
      Paint()
        ..style = PaintingStyle.stroke
        ..color = ComicColors.accent
        ..strokeWidth = math.max(2, 5 * s),
    );
  }
}

/// Union of the body and a triangular tail from tailBase to tailTip.
Path _withTail(Path body, PlacedBubble b, double halfWidth) {
  final base = b.tailBase, tip = b.tailTip;
  if (base == null || tip == null) return body;
  final dir = tip - base;
  if (dir.distance < 1) return body;
  // Base points along the bubble edge (horizontal), pushed slightly inside the body so the
  // union has no seam.
  final inward = base.dy >= b.rect.center.dy ? -6.0 * b.scale : 6.0 * b.scale;
  final skew = dir.dx.sign * halfWidth * 0.35;
  final tail = Path()
    ..moveTo(base.dx - halfWidth + skew, base.dy + inward)
    ..lineTo(base.dx + halfWidth * 0.6 + skew, base.dy + inward)
    ..lineTo(tip.dx, tip.dy)
    ..close();
  return Path.combine(PathOperation.union, body, tail);
}

/// Thought cloud: a rounded body with scalloped bumps along its border.
Path _cloud(Rect r, double s) {
  var p = Path()
    ..addRRect(RRect.fromRectAndRadius(r, Radius.circular(r.shortestSide / 2)));
  final bump = math.max(8 * s, math.min(r.height * 0.28, 22 * s));
  final inner = r.deflate(bump * 0.35);
  final per = 2 * (inner.width + inner.height);
  final n = math.max(8, (per / (bump * 1.5)).round());
  for (var i = 0; i < n; i++) {
    final c = _onRectPerimeter(inner, i / n);
    p = Path.combine(
      PathOperation.union,
      p,
      Path()..addOval(Rect.fromCircle(center: c, radius: bump * 0.62)),
    );
  }
  return p;
}

Offset _onRectPerimeter(Rect r, double t) {
  final per = 2 * (r.width + r.height);
  var d = (t % 1) * per;
  if (d < r.width) return Offset(r.left + d, r.top);
  d -= r.width;
  if (d < r.height) return Offset(r.right, r.top + d);
  d -= r.height;
  if (d < r.width) return Offset(r.right - d, r.bottom);
  d -= r.width;
  return Offset(r.left, r.bottom - d);
}

/// Shout: spiky burst around the text box.
Path _burst(Rect r, double s) {
  final c = r.center;
  final spikes = math.max(14, (2 * (r.width + r.height) / (34 * s)).round());
  final out = 14 * s, inn = 2 * s;
  final p = Path();
  for (var i = 0; i < spikes * 2; i++) {
    final a = -math.pi / 2 + i * math.pi / spikes;
    final dir = Offset(math.cos(a), math.sin(a));
    // Ray from the centre to the box edge.
    final tx = dir.dx.abs() < 1e-6
        ? double.infinity
        : (r.width / 2) / dir.dx.abs();
    final ty = dir.dy.abs() < 1e-6
        ? double.infinity
        : (r.height / 2) / dir.dy.abs();
    final edge = c + dir * math.min(tx, ty);
    final pt = edge + dir * (i.isEven ? out : -inn);
    if (i == 0) {
      p.moveTo(pt.dx, pt.dy);
    } else {
      p.lineTo(pt.dx, pt.dy);
    }
  }
  return p..close();
}
