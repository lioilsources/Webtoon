import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n/ui_strings.dart';
import '../packs/pack_store.dart' show formatBytes;
import '../profile/parental_gate.dart';
import '../profile/reader_profile.dart';
import '../shop/catalog.dart';
import '../shop/shop_controller.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// Covers and previews from the Pages site; tests swap in a memory image.
final coverImageProvider = Provider<ImageProvider Function(String url)>(
  (ref) =>
      (url) => NetworkImage(url),
);

IconData typeIcon(String name) => switch (name) {
  'child_care' => Icons.child_care_rounded,
  'favorite' => Icons.favorite_rounded,
  'bolt' => Icons.bolt_rounded,
  'nightlight' || 'dark_mode' => Icons.nightlight_round,
  'pets' => Icons.pets_rounded,
  'search' => Icons.search_rounded,
  'rocket' || 'rocket_launch' => Icons.rocket_launch_rounded,
  'castle' || 'auto_fix_high' => Icons.auto_fix_high_rounded,
  'celebration' || 'ac_unit' => Icons.celebration_rounded,
  'flight' || 'travel_explore' => Icons.travel_explore_rounded,
  _ => Icons.auto_stories_rounded,
};

/// Which packs / types / bundles the reader profile shows (Kids: nothing adult).
class StoreView {
  final Catalog catalog;
  final ReaderProfile? profile;
  const StoreView(this.catalog, this.profile);

  bool packVisible(CatalogPack p) =>
      audienceVisible(profile, p.audience) &&
      audienceVisible(profile, catalog.audienceOfType(p.type));

  List<CatalogType> get types => [
    for (final t in catalog.types)
      if (audienceVisible(profile, t.audience) && packsOf(t.id).isNotEmpty) t,
  ];

  List<CatalogPack> packsOf(String type) => [
    for (final p in catalog.packsOfType(type))
      if (packVisible(p)) p,
  ];

  /// Drawn gamebooks (`planned` ones are not for sale yet).
  List<CatalogGamebook> get gamebooks => [
    for (final g in catalog.gamebooks)
      if (g.ready && audienceVisible(profile, g.audience)) g,
  ];

  /// A bundle is shown only when every type it covers is visible ("all" includes adult types).
  List<CatalogBundle> get bundles => [
    for (final b in catalog.bundles)
      if (catalog
          .bundleTypes(b)
          .every((t) => audienceVisible(profile, catalog.audienceOfType(t))))
        b,
  ];
}

/// "Obchod": pack types → packs (cover mosaic, size, stories, price or Zdarma), bundles.
class StoreScreen extends ConsumerWidget {
  const StoreScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(uiLanguageProvider);
    final shop = ref.watch(shopProvider);
    final profile = ref.watch(readerProfileProvider).profile;
    ref.listen<ShopNotice?>(shopProvider.select((s) => s.notice), (prev, next) {
      if (next == null || next.id == prev?.id) return;
      ScaffoldMessenger.maybeOf(
        context,
      )?.showSnackBar(SnackBar(content: Text(tr(lang, next.key, next.args))));
    });
    final catalog = shop.catalog;
    Widget body;
    if (catalog == null && shop.loading) {
      body = Center(
        key: const ValueKey('store-loading'),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CircularProgressIndicator(),
            const SizedBox(height: 12),
            Text(tr(lang, 'store.loading')),
          ],
        ),
      );
    } else if (catalog == null) {
      body = Center(
        key: const ValueKey('store-offline'),
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_rounded, size: 48),
              const SizedBox(height: 12),
              Text(tr(lang, 'store.offline'), textAlign: TextAlign.center),
              const SizedBox(height: 16),
              OutlinedButton(
                key: const ValueKey('store-retry'),
                onPressed: () => ref.read(shopProvider.notifier).refresh(),
                child: Text(tr(lang, 'store.retry')),
              ),
            ],
          ),
        ),
      );
    } else {
      final view = StoreView(catalog, profile);
      final types = view.types;
      final bundles = view.bundles;
      final gamebooks = view.gamebooks;
      body = types.isEmpty && bundles.isEmpty && gamebooks.isEmpty
          ? EmptyState(
              key: const ValueKey('store-empty'),
              icon: Icons.storefront_outlined,
              title: tr(lang, 'store.empty'),
            )
          : RefreshIndicator(
              onRefresh: () => ref.read(shopProvider.notifier).refresh(),
              child: ListView(
                key: const ValueKey('store-list'),
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
                children: [
                  for (final t in types) ...[
                    _SectionHeader(
                      key: ValueKey('store-type-${t.id}'),
                      icon: typeIcon(t.icon),
                      title: t.titleIn(lang),
                    ),
                    _PackGrid(packs: view.packsOf(t.id)),
                  ],
                  if (gamebooks.isNotEmpty) ...[
                    const _SectionHeader(
                      key: ValueKey('store-gamebooks'),
                      icon: Icons.alt_route_rounded,
                      title: 'Gamebooky',
                    ),
                    for (final g in gamebooks) GamebookStoreCard(gamebook: g),
                  ],
                  if (bundles.isNotEmpty) ...[
                    _SectionHeader(
                      key: const ValueKey('store-bundles'),
                      icon: Icons.inventory_2_rounded,
                      title: tr(lang, 'store.bundles'),
                    ),
                    for (final b in bundles) _BundleCard(bundle: b),
                  ],
                ],
              ),
            );
    }
    return Scaffold(
      appBar: AppBar(title: Text(tr(lang, 'store.title'))),
      body: body,
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final IconData icon;
  final String title;
  const _SectionHeader({super.key, required this.icon, required this.title});

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 18, 4, 10),
    child: Row(
      children: [
        Icon(icon, color: ComicColors.accent),
        const SizedBox(width: 8),
        Expanded(
          child: Text(title, style: Theme.of(context).textTheme.headlineSmall),
        ),
      ],
    ),
  );
}

class _PackGrid extends StatelessWidget {
  final List<CatalogPack> packs;
  const _PackGrid({required this.packs});

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, c) {
      final columns = (c.maxWidth / 180).floor().clamp(1, 4);
      return GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: columns,
          mainAxisSpacing: 14,
          crossAxisSpacing: 14,
          mainAxisExtent: 340,
        ),
        itemCount: packs.length,
        itemBuilder: (_, i) => PackCard(pack: packs[i]),
      );
    },
  );
}

/// 2×2 mosaic of story covers (or the pack cover alone).
class CoverMosaic extends ConsumerWidget {
  final Catalog catalog;
  final List<String> covers;
  const CoverMosaic({super.key, required this.catalog, required this.covers});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scheme = Theme.of(context).colorScheme;
    final image = ref.watch(coverImageProvider);
    Widget tile(String path) => Image(
      image: image(catalog.baseUrls.page(path)),
      fit: BoxFit.cover,
      errorBuilder: (_, _, _) =>
          ColoredBox(color: scheme.surfaceContainerHighest),
    );
    final shown = covers.take(4).toList();
    if (shown.isEmpty) {
      return ColoredBox(
        color: scheme.surfaceContainerHighest,
        child: Center(
          child: Icon(
            Icons.auto_stories_outlined,
            color: scheme.onSurfaceVariant,
          ),
        ),
      );
    }
    if (shown.length < 4) return SizedBox.expand(child: tile(shown.first));
    return Column(
      children: [
        for (final row in [shown.sublist(0, 2), shown.sublist(2, 4)])
          Expanded(
            child: Row(
              children: [
                for (final c in row)
                  Expanded(child: SizedBox.expand(child: tile(c))),
              ],
            ),
          ),
      ],
    );
  }
}

List<String> _packCovers(Catalog c, CatalogPack p) {
  if (p.previews.isNotEmpty) return p.previews;
  final fromStories = [
    for (final s in c.storiesOf(p.id))
      if (s.cover != null) s.cover!,
  ];
  if (fromStories.isNotEmpty) return fromStories;
  return [?p.cover];
}

class PackCard extends ConsumerWidget {
  final CatalogPack pack;
  const PackCard({super.key, required this.pack});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(uiLanguageProvider);
    final catalog = ref.watch(shopProvider.select((s) => s.catalog))!;
    final comic = ComicTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        key: ValueKey('store-pack-${pack.id}'),
        borderRadius: BorderRadius.circular(14),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => PackDetailScreen(packId: pack.id),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Ink(
                decoration: comic.card(
                  color: scheme.surfaceContainerHighest,
                  radius: 14,
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: CoverMosaic(
                    catalog: catalog,
                    covers: _packCovers(catalog, pack),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              pack.titleIn(lang),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: ComicFonts.title().copyWith(fontSize: 16),
            ),
            Text(
              _meta(lang, pack),
              style: ComicFonts.ui(
                700,
              ).copyWith(fontSize: 12, color: scheme.onSurfaceVariant),
            ),
            const SizedBox(height: 6),
            PackAction(pack: pack),
          ],
        ),
      ),
    );
  }
}

String _meta(String lang, CatalogPack p) {
  final size = p.totalBytes > 0 ? ' · ${formatBytes(p.totalBytes)}' : '';
  return '${storiesCount(lang, p.stories)}$size';
}

/// Buy (price) / Stáhnout / progress / Staženo + Smazat, by entitlement and install state.
class PackAction extends ConsumerWidget {
  final CatalogPack pack;
  const PackAction({super.key, required this.pack});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(uiLanguageProvider);
    final shop = ref.watch(shopProvider);
    final ctrl = ref.read(shopProvider.notifier);
    final progress = shop.downloads[pack.id];
    if (pack.bundled) {
      return Tag(
        tr(lang, 'store.inApp'),
        key: ValueKey('pack-inapp-${pack.id}'),
      );
    }
    if (progress != null) {
      final f = progress.fraction;
      return Column(
        key: ValueKey('pack-progress-${pack.id}'),
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          LinearProgressIndicator(value: f),
          const SizedBox(height: 4),
          Text(
            tr(lang, 'store.downloading', {'pct': ((f ?? 0) * 100).round()}),
            style: const TextStyle(fontSize: 12),
          ),
        ],
      );
    }
    if (shop.unlocked(pack)) {
      if (ctrl.isInstalled(pack)) {
        return Row(
          children: [
            Expanded(
              child: Row(
                key: ValueKey('pack-installed-${pack.id}'),
                children: [
                  const Icon(
                    Icons.check_circle_rounded,
                    size: 18,
                    color: Color(0xFF2E9E5B),
                  ),
                  const SizedBox(width: 4),
                  Flexible(
                    child: Text(
                      tr(lang, 'store.downloaded'),
                      overflow: TextOverflow.ellipsis,
                      style: ComicFonts.ui(800).copyWith(fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
            TextButton(
              key: ValueKey('pack-delete-${pack.id}'),
              onPressed: () => _confirmDelete(context, ref, lang),
              child: Text(tr(lang, 'store.delete')),
            ),
          ],
        );
      }
      return SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          key: ValueKey('pack-download-${pack.id}'),
          onPressed: () => ctrl.download(pack),
          icon: const Icon(Icons.download_rounded, size: 18),
          label: Text(
            pack.free
                ? '${tr(lang, 'store.free')} · ${tr(lang, 'store.download')}'
                : tr(lang, 'store.download'),
          ),
        ),
      );
    }
    return BuyButton(
      key: ValueKey('pack-buy-${pack.id}'),
      productId: pack.productId,
    );
  }

  Future<void> _confirmDelete(
    BuildContext context,
    WidgetRef ref,
    String lang,
  ) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(tr(lang, 'store.deleteTitle')),
        content: Text(tr(lang, 'store.deleteBody')),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(tr(lang, 'store.cancel')),
          ),
          FilledButton(
            key: const ValueKey('pack-delete-confirm'),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(tr(lang, 'store.delete')),
          ),
        ],
      ),
    );
    if (ok == true) await ref.read(shopProvider.notifier).remove(pack);
  }
}

/// Price from the store; tap → parental gate → purchase.
class BuyButton extends ConsumerWidget {
  final String? productId;
  const BuyButton({super.key, required this.productId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(uiLanguageProvider);
    final shop = ref.watch(shopProvider);
    final product = productId == null ? null : shop.products[productId];
    final busy = productId != null && shop.buying.contains(productId);
    return SizedBox(
      width: double.infinity,
      child: FilledButton(
        onPressed: product == null || busy
            ? null
            : () async {
                final ctrl = ref.read(shopProvider.notifier);
                if (!await showParentalGate(context, ref)) return;
                await ctrl.buy(product.id);
              },
        child: busy
            ? const SizedBox(
                width: 18,
                height: 18,
                child: CircularProgressIndicator(strokeWidth: 2),
              )
            : Text(product?.price ?? tr(lang, 'store.noPrice')),
      ),
    );
  }
}

class _BundleCard extends ConsumerWidget {
  final CatalogBundle bundle;
  const _BundleCard({required this.bundle});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(uiLanguageProvider);
    final shop = ref.watch(shopProvider);
    final catalog = shop.catalog!;
    final owned = shop.entitlements.ownsBundle(bundle);
    final desc = bundle.covers.all
        ? tr(lang, 'store.bundleAll')
        : tr(lang, 'store.bundleTypes', {
            'types': [
              for (final t in bundle.covers.types)
                catalog.type(t)?.titleIn(lang) ?? t,
            ].join(', '),
          });
    return Padding(
      key: ValueKey('store-bundle-${bundle.id}'),
      padding: const EdgeInsets.only(bottom: 12),
      child: ComicCard(
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    bundle.titleIn(lang),
                    style: ComicFonts.title().copyWith(fontSize: 18),
                  ),
                  const SizedBox(height: 2),
                  Text(desc, style: const TextStyle(fontSize: 13)),
                ],
              ),
            ),
            const SizedBox(width: 12),
            SizedBox(
              width: 110,
              child: owned
                  ? Tag(
                      tr(lang, 'store.owned'),
                      key: ValueKey('bundle-owned-${bundle.id}'),
                    )
                  : BuyButton(
                      key: ValueKey('bundle-buy-${bundle.id}'),
                      productId: bundle.productId,
                    ),
            ),
          ],
        ),
      ),
    );
  }
}

/// One pack: all its story covers and titles, and the same action as the card.
class PackDetailScreen extends ConsumerWidget {
  final String packId;
  const PackDetailScreen({super.key, required this.packId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(uiLanguageProvider);
    final catalog = ref.watch(shopProvider.select((s) => s.catalog));
    final pack = catalog?.pack(packId);
    if (catalog == null || pack == null) {
      return Scaffold(appBar: AppBar());
    }
    final image = ref.watch(coverImageProvider);
    final scheme = Theme.of(context).colorScheme;
    final stories = catalog.storiesOf(pack.id);
    return Scaffold(
      appBar: AppBar(title: Text(pack.titleIn(lang))),
      body: ListView(
        key: ValueKey('pack-detail-${pack.id}'),
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
        children: [
          Text(_meta(lang, pack), style: ComicFonts.ui(800)),
          if (pack.languages.isNotEmpty)
            Text(
              tr(lang, 'store.languages', {'n': pack.languages.length}),
              style: TextStyle(color: scheme.onSurfaceVariant),
            ),
          const SizedBox(height: 12),
          PackAction(pack: pack),
          const SizedBox(height: 20),
          if (stories.isNotEmpty) ...[
            Text(
              tr(lang, 'store.preview'),
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 10),
            GridView.count(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisCount: 3,
              mainAxisSpacing: 10,
              crossAxisSpacing: 10,
              childAspectRatio: 416 / (608 + 120),
              children: [
                for (final s in stories)
                  Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(10),
                          child: SizedBox.expand(
                            child: s.cover == null
                                ? ColoredBox(
                                    color: scheme.surfaceContainerHighest,
                                  )
                                : Image(
                                    image: image(
                                      catalog.baseUrls.page(s.cover!),
                                    ),
                                    fit: BoxFit.cover,
                                    errorBuilder: (_, _, _) => ColoredBox(
                                      color: scheme.surfaceContainerHighest,
                                    ),
                                  ),
                          ),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        s.titleIn(lang),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

/// A gamebook in Obchod: the book (buy / download like a pack) and its editor kit.
class GamebookStoreCard extends ConsumerWidget {
  final CatalogGamebook gamebook;
  const GamebookStoreCard({super.key, required this.gamebook});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(uiLanguageProvider);
    final shop = ref.watch(shopProvider);
    final catalog = shop.catalog!;
    final comic = ComicTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    final g = gamebook;
    final size = g.bytes > 0 ? ' · ${formatBytes(g.bytes)}' : '';
    return Padding(
      key: ValueKey('store-gamebook-${g.id}'),
      padding: const EdgeInsets.only(bottom: 14),
      child: Ink(
        padding: const EdgeInsets.all(12),
        decoration: comic.card(color: scheme.surface, radius: 16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                ClipRRect(
                  borderRadius: BorderRadius.circular(10),
                  child: SizedBox(
                    width: 96,
                    height: 96,
                    child: CoverMosaic(catalog: catalog, covers: [?g.cover]),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        g.titleIn(lang),
                        style: ComicFonts.title().copyWith(fontSize: 18),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Gamebook · ${g.nodes} částí · ${g.endings} konce$size',
                        style: ComicFonts.ui(700).copyWith(
                          fontSize: 12,
                          color: scheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            PackAction(pack: g.asPack()),
            if (g.kitProductId != null && !shop.entitlements.unlocksKit(g)) ...[
              const SizedBox(height: 10),
              Text(
                'S editorem větví: piš vlastní odbočky z obrázků knihy.',
                style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13),
              ),
              const SizedBox(height: 6),
              BuyButton(
                key: ValueKey('gamebook-kit-buy-${g.id}'),
                productId: g.kitProductId,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
