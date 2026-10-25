import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/language_provider.dart';
import '../theme.dart';
import 'shop_controller.dart';

/// Top of the library when an installed pack or gamebook has a newer version in the catalog
/// (a gamebook grew new nodes, a pack got fixes): what and "Aktualizovat". The reader's
/// progress and own branches stay; the update replaces only the pack's files.
class UpdateBanner extends ConsumerWidget {
  const UpdateBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final shop = ref.watch(shopProvider);
    final ctrl = ref.read(shopProvider.notifier);
    final updates = ctrl.updates();
    if (updates.isEmpty) return const SizedBox.shrink();
    final lang = ref.watch(readerLanguageProvider);
    final busy = updates.any((p) => shop.downloads.containsKey(p.id));
    final scheme = Theme.of(context).colorScheme;
    final comic = ComicTheme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Container(
        key: const ValueKey('update-banner'),
        padding: const EdgeInsets.fromLTRB(16, 12, 12, 12),
        decoration: comic.card(
          color: ComicColors.accent.withValues(alpha: 0.10),
          radius: 16,
        ),
        child: Row(
          children: [
            const Icon(Icons.system_update_rounded),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Nová verze',
                    style: ComicFonts.ui(800).copyWith(fontSize: 15),
                  ),
                  Text(
                    updates.map((p) => p.titleIn(lang)).join(', '),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(color: scheme.onSurfaceVariant),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            busy
                ? const SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(strokeWidth: 2.5),
                  )
                : FilledButton(
                    key: const ValueKey('update-all'),
                    onPressed: () {
                      for (final p in updates) {
                        ctrl.download(p);
                      }
                    },
                    child: const Text('Aktualizovat'),
                  ),
          ],
        ),
      ),
    );
  }
}
