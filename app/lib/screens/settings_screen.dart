import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n/languages.dart';
import '../packs/pack_store.dart';
import '../providers/language_provider.dart';
import '../providers/providers.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// Reader mode: bubble language, storage used by packs, "Obnovit starter".
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    final lang = ref.watch(readerLanguageProvider);
    final store = ref.watch(packStoreProvider);
    final boot = ref.watch(packBootstrapProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Nastavení')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          Text('Jazyk bublin', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 4),
          Text(
            'Díl se ukáže v tomhle jazyce, když je do něj přeložený; jinak v originále.',
            style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13),
          ),
          const SizedBox(height: 10),
          DropdownButtonFormField<String>(
            key: const ValueKey('settings-language'),
            initialValue: lang ?? '',
            items: [
              const DropdownMenuItem(value: '', child: Text('Originál')),
              for (final l in kReaderLanguages)
                DropdownMenuItem(
                  value: l,
                  child: Text('${langFlag(l)}  ${langDisplayName(l)}'),
                ),
            ],
            onChanged: (v) => ref
                .read(readerLanguageProvider.notifier)
                .select(v == null || v.isEmpty ? null : v),
          ),
          const SizedBox(height: 28),
          Text('Úložiště', style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          ComicCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                FutureBuilder<int>(
                  // Re-measured after every (re)install.
                  key: ValueKey('storage-${boot.phase}-${store.packs.length}'),
                  future: store.storageBytes(),
                  builder: (_, snap) => Row(
                    children: [
                      const Icon(Icons.sd_storage_outlined),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'Balíčky zabírají '
                          '${snap.hasData ? formatBytes(snap.data!) : '…'}',
                          key: const ValueKey('storage-used'),
                          style: ComicFonts.ui(700),
                        ),
                      ),
                    ],
                  ),
                ),
                if (store.packs.isNotEmpty) ...[
                  const Divider(height: 24),
                  for (final pk in store.packs)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 6),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              pk.manifest.part == null
                                  ? pk.manifest.title
                                  : '${pk.manifest.title} (${pk.manifest.part})',
                              style: ComicFonts.ui(700),
                            ),
                          ),
                          Text(
                            'v${pk.manifest.version} · '
                            '${_stories(pk.manifest.stories.length)}',
                            style: TextStyle(
                              color: scheme.onSurfaceVariant,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ),
                ] else ...[
                  const SizedBox(height: 8),
                  Text(
                    'Žádný balíček není nainstalovaný.',
                    style: TextStyle(color: scheme.onSurfaceVariant),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 16),
          OutlinedButton.icon(
            key: const ValueKey('reinstall-starter'),
            onPressed: boot.isReady ? () => _reinstall(context, ref) : null,
            icon: const Icon(Icons.restore_rounded),
            label: const Text('Obnovit starter'),
          ),
          const SizedBox(height: 6),
          Text(
            'Znovu rozbalí příběhy přibalené v aplikaci. Stažené balíčky zůstanou.',
            style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13),
          ),
        ],
      ),
    );
  }

  Future<void> _reinstall(BuildContext context, WidgetRef ref) async {
    // Read before awaiting: while the starter extracts, the home screen shows the splash and
    // this screen is unmounted (its ref must not be used after that). The library reads the
    // store directly and the reader's providers are autoDispose, so nothing else needs an
    // explicit refresh.
    final boot = ref.read(packBootstrapProvider.notifier);
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Obnovit starter?'),
        content: const Text(
          'Přibalené příběhy se znovu rozbalí z aplikace. Chvíli to potrvá.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Zrušit'),
          ),
          FilledButton(
            key: const ValueKey('reinstall-confirm'),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Obnovit'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    await boot.reinstallStarter();
  }

  static String _stories(int n) => switch (n) {
    1 => '1 příběh',
    2 || 3 || 4 => '$n příběhy',
    _ => '$n příběhů',
  };
}
