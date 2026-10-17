import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/webtoon_api.dart';
import '../models/author.dart';
import '../providers/providers.dart';
import '../theme.dart';
import 'author_widgets.dart';

/// "Vygenerovat character sheet": POST …/sheet, then polls GET /sheets/{id} until it is
/// ready/failed. Shows progress k/n, "waiting: …" (ComfyUI off schedule) and the candidates
/// with their WD14 identity recall; the best one is highlighted (the backend adds it to the
/// character's reference images).
class SheetPanel extends ConsumerStatefulWidget {
  final String worldId;
  final String characterId;

  /// Called once a sheet finished as ready (reload the character's references).
  final VoidCallback onReady;

  const SheetPanel({
    super.key,
    required this.worldId,
    required this.characterId,
    required this.onReady,
  });

  @override
  ConsumerState<SheetPanel> createState() => _SheetPanelState();
}

class _SheetPanelState extends ConsumerState<SheetPanel> {
  CharacterSheet? _sheet;
  Timer? _timer;
  bool _starting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadLatest();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _loadLatest() async {
    try {
      final list = await ref
          .read(apiProvider)
          .listSheets(widget.worldId, widget.characterId);
      if (!mounted || list.isEmpty) return;
      setState(() => _sheet = list.first);
      if (!list.first.isFinished) _schedule();
    } on ApiException {
      // No sheets yet / older backend: just show the button.
    }
  }

  void _schedule() {
    _timer?.cancel();
    _timer = Timer(ref.read(configProvider).pollInterval, _poll);
  }

  Future<void> _poll() async {
    final id = _sheet?.id;
    if (id == null) return;
    try {
      final s = await ref.read(apiProvider).getSheet(id);
      if (!mounted) return;
      setState(() {
        _sheet = s;
        _error = null;
      });
      if (s.isFinished) {
        if (s.status == 'ready') widget.onReady();
      } else {
        _schedule();
      }
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _error = e.message);
      _schedule();
    }
  }

  Future<void> _start() async {
    setState(() {
      _starting = true;
      _error = null;
    });
    try {
      final s = await ref
          .read(apiProvider)
          .createSheet(widget.worldId, widget.characterId);
      if (!mounted) return;
      setState(() => _sheet = s);
      if (!s.isFinished) _schedule();
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _starting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final s = _sheet;
    final running = s != null && !s.isFinished;
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Hint(
          '4 varianty postavy na bílém pozadí; nejlepší podle shody tagů '
          '(WD14) se přidá mezi referenční obrázky.',
        ),
        FilledButton.icon(
          key: const ValueKey('generate-sheet'),
          onPressed: running || _starting ? null : _start,
          icon: const Icon(Icons.auto_awesome),
          label: Text(
            running
                ? 'Kreslí se…'
                : s == null
                ? 'Vygenerovat character sheet'
                : 'Vygenerovat znovu',
          ),
        ),
        if (_error != null) ...[
          const SizedBox(height: 8),
          Text(_error!, style: TextStyle(color: scheme.error)),
        ],
        if (s != null) ...[
          const SizedBox(height: 12),
          _Status(sheet: s),
          if (s.images.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                for (var i = 0; i < s.images.length; i++)
                  _Candidate(
                    key: ValueKey('sheet-image-$i'),
                    image: s.images[i],
                    best: s.best == i,
                  ),
              ],
            ),
          ],
        ],
      ],
    );
  }
}

class _Status extends StatelessWidget {
  final CharacterSheet sheet;
  const _Status({required this.sheet});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final total = sheet.seeds == 0 ? 1 : sheet.seeds;
    final String text;
    switch (sheet.status) {
      case 'ready':
        text = 'Hotovo: ${sheet.images.length} variant';
      case 'failed':
        text = 'Nepovedlo se: ${sheet.error}';
      case 'rendering':
        text = 'Kreslí se ${sheet.done}/${sheet.seeds}';
      default:
        text = 'Ve frontě (${sheet.done}/${sheet.seeds})';
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          text,
          key: const ValueKey('sheet-status'),
          style: ComicFonts.ui(
            800,
          ).copyWith(color: sheet.status == 'failed' ? scheme.error : null),
        ),
        if (!sheet.isFinished) ...[
          const SizedBox(height: 6),
          LinearProgressIndicator(value: sheet.done / total),
        ],
        if (!sheet.isFinished && sheet.isWaiting) ...[
          const SizedBox(height: 6),
          Text(
            'GPU server je mimo rozvrh, počká se: ${sheet.error}',
            key: const ValueKey('sheet-waiting'),
            style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13),
          ),
        ],
      ],
    );
  }
}

class _Candidate extends ConsumerWidget {
  final SheetImage image;
  final bool best;
  const _Candidate({super.key, required this.image, required this.best});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.watch(apiProvider);
    final comic = ComicTheme.of(context);
    final unsafe = image.status != 'ok';
    return Container(
      width: 130,
      decoration: comic
          .card(
            color: best
                ? ComicColors.accent.withValues(alpha: 0.18)
                : Theme.of(context).colorScheme.surface,
            radius: 12,
          )
          .copyWith(
            border: Border.all(
              color: best ? ComicColors.accent : comic.outline,
              width: best ? 3 : 2,
            ),
          ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          AspectRatio(
            aspectRatio: 832 / 1216,
            child: image.imageUrl == null || unsafe
                ? const Center(child: Icon(Icons.block))
                : Image(
                    image: api.panelImage(image.imageUrl!),
                    fit: BoxFit.cover,
                    errorBuilder: (_, _, _) =>
                        const Icon(Icons.broken_image_outlined),
                  ),
          ),
          Padding(
            padding: const EdgeInsets.all(6),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  unsafe
                      ? 'nevhodné'
                      : 'shoda ${(image.recall * 100).round()} %',
                  style: ComicFonts.ui(800).copyWith(fontSize: 12),
                ),
                if (best)
                  Text(
                    'nejlepší',
                    style: ComicFonts.ui(
                      800,
                    ).copyWith(fontSize: 12, color: ComicColors.accent),
                  ),
                if (image.missing.isNotEmpty)
                  Tooltip(
                    message: image.missing.join(', '),
                    child: Text(
                      'chybí: ${image.missing.take(3).join(', ')}',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
