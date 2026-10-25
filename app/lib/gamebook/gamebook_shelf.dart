import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../profile/reader_profile.dart';
import '../providers/language_provider.dart';
import '../providers/providers.dart';
import '../shop/shop_controller.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'gamebook.dart';
import 'gamebook_screen.dart';

/// Installed gamebooks the reader profile may see (Kids: no adult world).
List<Gamebook> visibleGamebooks(WidgetRef ref) {
  final store = ref.watch(packStoreProvider);
  final profile = ref.watch(readerProfileProvider.select((p) => p.profile));
  return [
    for (final g in store.gamebooks)
      if (audienceVisible(
        profile,
        store
                .world(
                  store.gamebookStory(g, g.node(g.start)!.storyId)?.worldId ??
                      '',
                )
                ?.audience ??
            'kids',
      ))
        g,
  ];
}

/// The editor kit is unlocked by `kit_<id>` (or a free gamebook); offline the receipt alone decides.
bool kitUnlocked(WidgetRef ref, Gamebook g) {
  final shop = ref.watch(shopProvider);
  for (final c in shop.catalog?.gamebooks ?? const []) {
    if (c.id == g.id) return shop.entitlements.unlocksKit(c);
  }
  return shop.entitlements.ownsProduct('kit_${g.id}');
}

/// "Gamebooky" at the top of the library.
class GamebookShelf extends ConsumerWidget {
  final List<Gamebook> gamebooks;
  const GamebookShelf({super.key, required this.gamebooks});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(readerLanguageProvider);
    final store = ref.watch(packStoreProvider);
    final api = ref.watch(apiProvider);
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 8, 4, 10),
          child: Row(
            children: [
              const Icon(Icons.alt_route_rounded),
              const SizedBox(width: 8),
              Text(
                'Gamebooky',
                style: ComicFonts.title().copyWith(fontSize: 22),
              ),
            ],
          ),
        ),
        for (final g in gamebooks) ...[
          ComicCard(
            key: ValueKey('gamebook-${g.id}'),
            onTap: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => GamebookScreen(
                  gamebookId: g.id,
                  kitUnlocked: kitUnlocked(ref, g),
                ),
              ),
            ),
            child: Row(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: SizedBox(
                    width: 84,
                    height: 84,
                    child: switch (store
                        .gamebookStory(g, g.node(g.start)!.storyId)
                        ?.cover) {
                      final String c => Image(
                        image: api.panelImage(c),
                        fit: BoxFit.cover,
                      ),
                      null => ColoredBox(
                        color: scheme.surfaceContainerHighest,
                        child: const Icon(Icons.menu_book_rounded),
                      ),
                    },
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        g.titleIn(lang),
                        style: ComicFonts.title().copyWith(fontSize: 20),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Ty rozhoduješ, jak příběh dopadne · ${g.endings} konce',
                        style: TextStyle(color: scheme.onSurfaceVariant),
                      ),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right_rounded),
              ],
            ),
          ),
          const SizedBox(height: 12),
        ],
        const SizedBox(height: 8),
      ],
    );
  }
}
