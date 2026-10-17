import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/webtoon_api.dart';
import '../providers/providers.dart';
import '../services/image_picker.dart';
import '../theme.dart';

/// Section heading inside the editors.
class SectionTitle extends StatelessWidget {
  final String text;
  final Widget? trailing;
  const SectionTitle(this.text, {super.key, this.trailing});

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(2, 22, 2, 10),
    child: Row(
      children: [
        Expanded(
          child: Text(text, style: Theme.of(context).textTheme.titleLarge),
        ),
        ?trailing,
      ],
    ),
  );
}

/// Muted helper text under a section title.
class Hint extends StatelessWidget {
  final String text;
  const Hint(this.text, {super.key});

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: Text(
      text,
      style: TextStyle(
        color: Theme.of(context).colorScheme.onSurfaceVariant,
        fontSize: 13,
        height: 1.35,
      ),
    ),
  );
}

void showSnack(BuildContext context, String text) =>
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

/// Runs [fn], shows the Czech error message of an [ApiException] as a snack bar.
Future<T?> guarded<T>(BuildContext context, Future<T> Function() fn) async {
  final messenger = ScaffoldMessenger.of(context);
  try {
    return await fn();
  } on ApiException catch (e) {
    messenger.showSnackBar(SnackBar(content: Text(e.message)));
    return null;
  }
}

Future<bool> confirmDialog(
  BuildContext context, {
  required String title,
  required String body,
  String confirm = 'Smazat',
}) async =>
    await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Zrušit'),
          ),
          FilledButton(
            key: const ValueKey('confirm-dialog'),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(confirm),
          ),
        ],
      ),
    ) ??
    false;

/// Booru tags as editable chips: delete a chip, add a tag, dropped tags (not in the WD14
/// vocabulary) greyed out — tapping one adds it anyway.
class TagChipsEditor extends StatefulWidget {
  final List<String> tags;
  final List<String> dropped;
  final ValueChanged<List<String>> onChanged;

  const TagChipsEditor({
    super.key,
    required this.tags,
    this.dropped = const [],
    required this.onChanged,
  });

  @override
  State<TagChipsEditor> createState() => _TagChipsEditorState();
}

class _TagChipsEditorState extends State<TagChipsEditor> {
  final _add = TextEditingController();

  @override
  void dispose() {
    _add.dispose();
    super.dispose();
  }

  void _addTags(String raw) {
    final next = [...widget.tags];
    for (final t in raw.split(',')) {
      final tag = t.trim().toLowerCase().replaceAll('_', ' ');
      if (tag.isNotEmpty && !next.contains(tag)) next.add(tag);
    }
    _add.clear();
    widget.onChanged(next);
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final dropped = widget.dropped
        .where((t) => !widget.tags.contains(t))
        .toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.tags.isEmpty)
          const Hint('Zatím žádné tagy.')
        else
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final t in widget.tags)
                InputChip(
                  key: ValueKey('tag-$t'),
                  label: Text(t),
                  deleteIcon: Icon(
                    Icons.close,
                    size: 16,
                    key: ValueKey('tag-delete-$t'),
                  ),
                  deleteButtonTooltipMessage: 'Odebrat',
                  onDeleted: () => widget.onChanged(
                    widget.tags.where((x) => x != t).toList(),
                  ),
                ),
            ],
          ),
        if (dropped.isNotEmpty) ...[
          const SizedBox(height: 10),
          const Hint(
            'Vyřazené (nejsou ve slovníku WD14, model je nejspíš nezná) — '
            'klepnutím je přesto přidáš:',
          ),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final t in dropped)
                ActionChip(
                  key: ValueKey('dropped-$t'),
                  label: Text(
                    t,
                    style: TextStyle(
                      color: scheme.onSurface.withValues(alpha: 0.45),
                      decoration: TextDecoration.lineThrough,
                    ),
                  ),
                  backgroundColor: scheme.surfaceContainerHighest.withValues(
                    alpha: 0.5,
                  ),
                  onPressed: () => widget.onChanged([...widget.tags, t]),
                ),
            ],
          ),
        ],
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: TextField(
                key: const ValueKey('tag-add-field'),
                controller: _add,
                decoration: const InputDecoration(
                  hintText: 'Přidat tag (např. green eyes)',
                  isDense: true,
                ),
                onSubmitted: _addTags,
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filledTonal(
              key: const ValueKey('tag-add'),
              tooltip: 'Přidat tag',
              onPressed: () => _addTags(_add.text),
              icon: const Icon(Icons.add),
            ),
          ],
        ),
      ],
    );
  }
}

/// Reference image thumbnails (first = used by IP-Adapter) with "move first", remove and
/// upload. [onReorder] gets the new list of paths (PATCH reference_images).
class ReferenceImagesEditor extends ConsumerWidget {
  final List<String> paths;
  final List<String> urls;
  final Future<void> Function(List<String> paths) onChanged;
  final Future<void> Function(PickedImage image) onUpload;

  const ReferenceImagesEditor({
    super.key,
    required this.paths,
    required this.urls,
    required this.onChanged,
    required this.onUpload,
  });

  Future<void> _upload(BuildContext context, WidgetRef ref) async {
    final picked = await ref.read(imagePickerProvider)();
    if (picked == null || !context.mounted) return;
    if (picked.bytes.length > maxReferenceBytes) {
      showSnack(context, 'Soubor je moc velký (max. 8 MiB).');
      return;
    }
    await onUpload(picked);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.watch(apiProvider);
    final comic = ComicTheme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (paths.isEmpty)
          const Hint('Zatím žádné reference.')
        else
          SizedBox(
            height: 150,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: paths.length,
              separatorBuilder: (_, _) => const SizedBox(width: 10),
              itemBuilder: (context, i) {
                final url = i < urls.length ? urls[i] : null;
                return Container(
                  key: ValueKey('ref-$i'),
                  width: 110,
                  decoration: comic.card(
                    color: Theme.of(context).colorScheme.surface,
                    radius: 12,
                  ),
                  clipBehavior: Clip.antiAlias,
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      if (url != null)
                        Image(
                          image: api.panelImage(url),
                          fit: BoxFit.cover,
                          errorBuilder: (_, _, _) =>
                              const Icon(Icons.broken_image_outlined),
                        ),
                      if (i == 0)
                        const Positioned(
                          left: 4,
                          top: 4,
                          child: _Badge('Hlavní'),
                        ),
                      Positioned(
                        right: 0,
                        bottom: 0,
                        child: Row(
                          children: [
                            if (i > 0)
                              _ThumbButton(
                                key: ValueKey('ref-first-$i'),
                                icon: Icons.star_outline,
                                tooltip: 'Použít jako hlavní',
                                onTap: () => onChanged([
                                  paths[i],
                                  for (var k = 0; k < paths.length; k++)
                                    if (k != i) paths[k],
                                ]),
                              ),
                            _ThumbButton(
                              key: ValueKey('ref-remove-$i'),
                              icon: Icons.close,
                              tooltip: 'Odebrat',
                              onTap: () => onChanged([
                                for (var k = 0; k < paths.length; k++)
                                  if (k != i) paths[k],
                              ]),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        const SizedBox(height: 10),
        OutlinedButton.icon(
          key: const ValueKey('upload-reference'),
          onPressed: () => _upload(context, ref),
          icon: const Icon(Icons.upload_file),
          label: const Text('Nahrát obrázek (PNG/JPEG)'),
        ),
      ],
    );
  }
}

class _Badge extends StatelessWidget {
  final String text;
  const _Badge(this.text);

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
    decoration: BoxDecoration(
      color: ComicColors.accent,
      borderRadius: BorderRadius.circular(8),
    ),
    child: Text(
      text,
      style: ComicFonts.ui(800).copyWith(fontSize: 11, color: Colors.white),
    ),
  );
}

class _ThumbButton extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;
  const _ThumbButton({
    super.key,
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) => Tooltip(
    message: tooltip,
    child: InkWell(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.all(3),
        padding: const EdgeInsets.all(4),
        decoration: const BoxDecoration(
          color: Colors.black54,
          shape: BoxShape.circle,
        ),
        child: Icon(icon, size: 16, color: Colors.white),
      ),
    ),
  );
}

/// A growable list of single-line/multi-line text items (rules, constraints).
class StringListEditor extends StatelessWidget {
  final String keyPrefix;
  final List<TextEditingController> controllers;
  final String hint;
  final String addLabel;
  final VoidCallback onAdd;
  final ValueChanged<int> onRemove;

  const StringListEditor({
    super.key,
    required this.keyPrefix,
    required this.controllers,
    required this.hint,
    required this.addLabel,
    required this.onAdd,
    required this.onRemove,
  });

  @override
  Widget build(BuildContext context) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      for (var i = 0; i < controllers.length; i++)
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  key: ValueKey('$keyPrefix-$i'),
                  controller: controllers[i],
                  minLines: 1,
                  maxLines: 3,
                  decoration: InputDecoration(hintText: hint, isDense: true),
                ),
              ),
              IconButton(
                key: ValueKey('$keyPrefix-remove-$i'),
                tooltip: 'Odebrat',
                onPressed: () => onRemove(i),
                icon: const Icon(Icons.delete_outline),
              ),
            ],
          ),
        ),
      TextButton.icon(
        key: ValueKey('$keyPrefix-add'),
        onPressed: onAdd,
        icon: const Icon(Icons.add),
        label: Text(addLabel),
      ),
    ],
  );
}
