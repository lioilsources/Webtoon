import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../models/episode.dart';
import '../theme.dart';
import 'bubble_layout.dart';
import 'bubble_painter.dart';

/// One webtoon panel: the image with bubbles + SFX laid over it (Stack overlay, §5.5).
/// Pending panels show a placeholder with progress; failed ones offer "regenerate".
class PanelView extends StatelessWidget {
  final Panel panel;
  final ImageProvider? image;
  final int panelsTotal;
  final bool busy;

  /// Long-press on a bubble (index into panel.bubbles). Null = not editable.
  final void Function(int bubbleIndex)? onEditBubble;
  final VoidCallback? onRegenerate;

  const PanelView({
    super.key,
    required this.panel,
    this.image,
    this.panelsTotal = 0,
    this.busy = false,
    this.onEditBubble,
    this.onRegenerate,
  });

  @override
  Widget build(BuildContext context) {
    return AspectRatio(
      aspectRatio: panel.aspect,
      child: LayoutBuilder(
        builder: (context, c) {
          final size = Size(c.maxWidth, c.maxHeight);
          if (panel.isFailed) return _failed(context, size);
          if (!panel.isReady || image == null) return _pending(context, size);
          return _ready(context, size);
        },
      ),
    );
  }

  Widget _ready(BuildContext context, Size size) {
    final scaler = MediaQuery.textScalerOf(context).clamp(maxScaleFactor: 1.4);
    final placed = layoutBubbles(
      size,
      panel.bubbles,
      characters: panel.characters,
      textScaler: scaler,
    );
    return Stack(
      fit: StackFit.expand,
      children: [
        Image(
          image: image!,
          fit: BoxFit.cover,
          gaplessPlayback: true,
          frameBuilder: (context, child, frame, sync) => AnimatedOpacity(
            opacity: frame == null && !sync ? 0 : 1,
            duration: const Duration(milliseconds: 250),
            child: child,
          ),
          errorBuilder: (context, error, stack) => _imageError(context),
        ),
        for (var i = 0; i < panel.sfx.length; i++)
          SfxText(sfx: panel.sfx[i], index: i, panelSize: size),
        IgnorePointer(
          child: CustomPaint(painter: BubblesPainter(placed), size: size),
        ),
        for (final b in placed)
          Positioned.fromRect(
            rect: b.rect,
            child: GestureDetector(
              key: ValueKey('bubble-${panel.index}-${b.index}'),
              behavior: HitTestBehavior.opaque,
              onLongPress: onEditBubble == null
                  ? null
                  : () => onEditBubble!(b.index),
              child: Padding(
                padding: b.padding,
                child: Center(
                  child: Text(
                    b.bubble.text,
                    style: b.style,
                    textAlign: TextAlign.center,
                    textScaler: scaler,
                    softWrap: true,
                  ),
                ),
              ),
            ),
          ),
        if (busy)
          const Positioned(
            right: 10,
            top: 10,
            child: SizedBox.square(
              dimension: 18,
              child: CircularProgressIndicator(strokeWidth: 2.5),
            ),
          ),
      ],
    );
  }

  Widget _imageError(BuildContext context) => ColoredBox(
    color: Theme.of(context).colorScheme.surfaceContainerHighest,
    child: const Center(child: Icon(Icons.broken_image_outlined, size: 40)),
  );

  Widget _pending(BuildContext context, Size size) {
    final scheme = Theme.of(context).colorScheme;
    final label = panel.status == 'rendering'
        ? 'Kreslím panel ${panel.index + 1}${panelsTotal > 0 ? '/$panelsTotal' : ''}…'
        : 'Panel ${panel.index + 1} čeká na kreslení';
    return _Placeholder(
      key: ValueKey('panel-pending-${panel.index}'),
      color: scheme.surfaceContainerHighest,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const SizedBox.square(
            dimension: 34,
            child: CircularProgressIndicator(strokeWidth: 3.5),
          ),
          const SizedBox(height: 14),
          Text(label, style: ComicFonts.ui(700).copyWith(fontSize: 15)),
        ],
      ),
    );
  }

  Widget _failed(BuildContext context, Size size) {
    final scheme = Theme.of(context).colorScheme;
    return _Placeholder(
      key: ValueKey('panel-failed-${panel.index}'),
      color: scheme.errorContainer,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.brush_outlined,
              size: 40,
              color: scheme.onErrorContainer,
            ),
            const SizedBox(height: 10),
            Text(
              'Panel ${panel.index + 1} se nepodařilo nakreslit',
              textAlign: TextAlign.center,
              style: ComicFonts.title().copyWith(
                fontSize: 19,
                color: scheme.onErrorContainer,
              ),
            ),
            const SizedBox(height: 14),
            if (onRegenerate != null)
              FilledButton.icon(
                onPressed: busy ? null : onRegenerate,
                icon: busy
                    ? const SizedBox.square(
                        dimension: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.refresh),
                label: const Text('Vygenerovat znovu'),
              ),
          ],
        ),
      ),
    );
  }
}

class _Placeholder extends StatelessWidget {
  final Color color;
  final Widget child;
  const _Placeholder({super.key, required this.color, required this.child});

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(color: color),
    child: CustomPaint(
      painter: _HalftonePainter(Theme.of(context).colorScheme.onSurface),
      child: Center(child: child),
    ),
  );
}

/// Faint screentone dots behind placeholders.
class _HalftonePainter extends CustomPainter {
  final Color color;
  const _HalftonePainter(this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final p = Paint()..color = color.withValues(alpha: 0.07);
    const step = 14.0;
    for (var y = 0.0; y < size.height; y += step) {
      final odd = (y / step).round().isOdd;
      for (var x = odd ? step / 2 : 0.0; x < size.width; x += step) {
        canvas.drawCircle(Offset(x, y), 2.2, p);
      }
    }
  }

  @override
  bool shouldRepaint(_HalftonePainter old) => old.color != color;
}

/// Sound effect lettering: DynaPuff, yellow with a thick ink stroke (compose.py draw_sfx:
/// 64 px at width 800, at 55 % / 10 % of the width alternately, 68 % of the height).
class SfxText extends StatelessWidget {
  final Sfx sfx;
  final int index;
  final Size panelSize;

  const SfxText({
    super.key,
    required this.sfx,
    required this.index,
    required this.panelSize,
  });

  @override
  Widget build(BuildContext context) {
    final s = panelSize.width / kReferenceWidth;
    final (scale, fill, angle) = switch (sfx.style) {
      'bold' => (1.15, const Color(0xFFFF8A3C), -0.08),
      'soft' => (0.8, const Color(0xFFFFF1C2), 0.06),
      'shaky' => (1.0, ComicColors.sfxYellow, -0.16),
      _ => (1.0, ComicColors.sfxYellow, -0.05),
    };
    final size = 64 * s * scale;
    final pos = sfx.position ?? Offset(index.isEven ? 0.55 : 0.1, 0.68);
    final base = ComicFonts.shout().copyWith(fontSize: size, height: 1);
    final strokeW = math.max(2.0, 6 * s * (sfx.style == 'soft' ? 0.7 : 1));
    return Positioned(
      left: pos.dx * panelSize.width,
      top: pos.dy * panelSize.height,
      child: IgnorePointer(
        child: Transform.rotate(
          angle: angle,
          alignment: Alignment.centerLeft,
          child: Stack(
            children: [
              Text(
                sfx.text,
                textScaler: TextScaler.noScaling,
                style: base.copyWith(
                  foreground: Paint()
                    ..style = PaintingStyle.stroke
                    ..strokeWidth = strokeW * 2
                    ..strokeJoin = StrokeJoin.round
                    ..color = ComicColors.ink,
                ),
              ),
              Text(
                sfx.text,
                textScaler: TextScaler.noScaling,
                style: base.copyWith(color: fill),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
