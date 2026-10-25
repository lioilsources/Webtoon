import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/author.dart';
import '../models/world.dart';
import '../providers/providers.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'author_widgets.dart';
import 'gamebook_editor_screen.dart';
import 'world_editor_screen.dart';

/// Tab "Tvořit": the caller's own worlds (GET /worlds?owner=me) + "Nový svět".
class CreateScreen extends ConsumerWidget {
  const CreateScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final worlds = ref.watch(myWorldsProvider);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Tvořit'),
        actions: [
          IconButton(
            key: const ValueKey('open-gamebooks'),
            tooltip: 'Gamebooky',
            icon: const Icon(Icons.account_tree_rounded),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(builder: (_) => const GamebooksScreen()),
            ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        key: const ValueKey('new-world'),
        onPressed: () => createWorldFlow(context, ref),
        backgroundColor: ComicColors.accent,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.add),
        label: const Text('Nový svět'),
      ),
      body: worlds.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorRetry(
          message: '$e',
          onRetry: () => ref.invalidate(myWorldsProvider),
        ),
        data: (list) => list.isEmpty
            ? const EmptyState(
                icon: Icons.brush_outlined,
                title: 'Zatím nemáš žádný svět',
                subtitle: 'Vytvoř svět, postavy a lokace a pusť do něj hráče.',
              )
            : RefreshIndicator(
                onRefresh: () => ref.refresh(myWorldsProvider.future),
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
                  children: [
                    for (final w in list)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 14),
                        child: ComicCard(
                          key: ValueKey('my-world-${w.id}'),
                          onTap: () => openWorldEditor(context, w.id),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                w.title,
                                style: ComicFonts.title().copyWith(
                                  fontSize: 22,
                                ),
                              ),
                              if (w.synopsis.isNotEmpty)
                                Text(
                                  w.synopsis,
                                  maxLines: 2,
                                  overflow: TextOverflow.ellipsis,
                                ),
                              const SizedBox(height: 8),
                              Wrap(
                                spacing: 6,
                                runSpacing: 6,
                                children: [
                                  Tag(visibilityLabel(w.visibility)),
                                  Tag(audienceLabel(w.audience)),
                                  if (w.styleId.isNotEmpty) Tag(w.styleId),
                                ],
                              ),
                            ],
                          ),
                        ),
                      ),
                  ],
                ),
              ),
      ),
    );
  }
}

void openWorldEditor(BuildContext context, String worldId) =>
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => WorldEditorScreen(worldId: worldId),
      ),
    );

/// Dialog (title + style preset) → POST /worlds → world editor.
Future<void> createWorldFlow(BuildContext context, WidgetRef ref) async {
  final result = await showDialog<(String, String)>(
    context: context,
    builder: (_) => const _NewWorldDialog(),
  );
  if (result == null || !context.mounted) return;
  final created = await guarded(
    context,
    () =>
        ref.read(apiProvider).createWorld(title: result.$1, styleId: result.$2),
  );
  if (created == null || !context.mounted) return;
  ref.invalidate(myWorldsProvider);
  ref.invalidate(worldsProvider);
  openWorldEditor(context, created.id);
}

class _NewWorldDialog extends ConsumerStatefulWidget {
  const _NewWorldDialog();

  @override
  ConsumerState<_NewWorldDialog> createState() => _NewWorldDialogState();
}

class _NewWorldDialogState extends ConsumerState<_NewWorldDialog> {
  final _title = TextEditingController();
  String? _style;

  @override
  void dispose() {
    _title.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final presets = ref.watch(stylePresetsProvider);
    final list = presets.valueOrNull ?? const <StylePreset>[];
    _style ??= list.isEmpty ? null : list.first.id;
    return AlertDialog(
      title: const Text('Nový svět'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          TextField(
            key: const ValueKey('new-world-title'),
            controller: _title,
            autofocus: true,
            decoration: const InputDecoration(labelText: 'Název světa'),
          ),
          const SizedBox(height: 14),
          if (presets.isLoading) const LinearProgressIndicator(),
          if (presets.hasError) Text('${presets.error}'),
          if (list.isNotEmpty)
            DropdownButtonFormField<String>(
              key: const ValueKey('new-world-style'),
              initialValue: _style,
              decoration: const InputDecoration(labelText: 'Výtvarný styl'),
              items: [
                for (final p in list)
                  DropdownMenuItem(value: p.id, child: Text(p.id)),
              ],
              onChanged: (v) => setState(() => _style = v),
            ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Zrušit'),
        ),
        FilledButton(
          key: const ValueKey('new-world-create'),
          onPressed: () {
            final t = _title.text.trim();
            if (t.isEmpty || _style == null) return;
            Navigator.pop(context, (t, _style!));
          },
          child: const Text('Vytvořit'),
        ),
      ],
    );
  }
}
