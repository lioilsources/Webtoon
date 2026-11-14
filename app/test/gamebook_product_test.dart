// Gamebooks sharing one store product (gamebook_archion unlocks every Archion book): one card,
// one price, one purchase unlocks and downloads them all; and grandfathering — a gamebook
// installed while the catalog had it free stays unlocked once a newer catalog makes it paid.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/profile/reader_profile.dart';
import 'package:webtoon/providers/language_provider.dart';
import 'package:webtoon/screens/store_screen.dart';
import 'package:webtoon/shop/catalog.dart';
import 'package:webtoon/shop/entitlements.dart';
import 'package:webtoon/shop/shop_controller.dart';
import 'package:webtoon/shop/store_gateway.dart';

import 'shop_fakes.dart';

Map<String, dynamic> gamebook(
  String id,
  String productId, {
  bool free = false,
  String? kit,
}) => {
  'id': id,
  'product_id': productId,
  'kit_product_id': kit ?? '',
  'type': 'kids',
  'title': 'Book $id',
  'audience': 'kids',
  'cover': 'covers/gb_$id.webp',
  'free': free,
  'status': 'ready',
  'version': 1,
  'nodes': 10,
  'endings': 2,
  'bytes': 1000,
  'parts': [
    {
      'release': 'gamebook-$id-v1',
      'asset': 'gamebook-$id.zip',
      'bytes': 1000,
      'sha256': 'ab',
    },
  ],
};

const archion = ['archion_oil', 'archion_semireal', 'archion_claude'];
const gulas = ['uknedliku', 'poslednislovo', 'gulasspagety'];

/// [gulasFree]: the live catalog (the Guláš books free); false: the next one (paid).
Catalog shopCatalog({int version = 1, bool gulasFree = false}) =>
    Catalog.parse({
      'schema': 2,
      'version': version,
      'base_urls': {
        'pages': 'https://p.example/',
        'releases': 'https://r.example/',
      },
      'types': [],
      'packs': [],
      'bundles': [
        {'id': 'bundle_all', 'product_id': 'bundle_all', 'covers': 'all'},
      ],
      'gamebooks': [
        for (final id in archion) gamebook(id, 'gamebook_archion'),
        for (final id in gulas)
          gamebook(id, 'gamebook_gulasspagety', free: gulasFree),
        gamebook('sara', 'gamebook_sara', kit: 'kit_sara'),
      ],
      'stories': [],
    });

Receipt r(String id) => Receipt(productId: id, grantedAt: DateTime(2026));

void main() {
  group('shared gamebook product', () {
    final catalog = shopCatalog();

    test('an empty kit_product_id means no kit', () {
      final g = catalog.gamebooks.first;
      expect(g.kitProductId, isNull);
      expect(g.asPack().kitProductId, isNull);
      expect(catalog.productIds, {
        'bundle_all',
        'gamebook_archion',
        'gamebook_gulasspagety',
        'gamebook_sara',
        'kit_sara',
      });
    });

    test('one purchase unlocks every gamebook of the product', () {
      final ents = const Entitlements().grant(r('gamebook_archion'));
      for (final g in catalog.gamebooks) {
        final unlocked = archion.contains(g.id);
        expect(ents.unlocksGamebook(g), unlocked, reason: g.id);
        expect(ents.unlocksPack(catalog, g.asPack()), unlocked, reason: g.id);
        expect(ents.unlocksKit(g), isFalse, reason: g.id);
      }
      expect(
        ents.packsOfProduct(catalog, 'gamebook_archion').map((p) => p.id),
        [for (final id in archion) 'gamebook-$id'],
      );
    });

    test('the store groups gamebooks by product id, in catalog order', () {
      final groups = StoreView(catalog, ReaderProfile.adults).gamebookGroups;
      expect(
        [
          for (final g in groups) [for (final b in g) b.id],
        ],
        [
          archion,
          gulas,
          ['sara'],
        ],
      );
    });
  });

  group('grandfathering', () {
    test('a grandfathered gamebook stays unlocked (book and kit)', () {
      final paid = shopCatalog();
      final g = paid.gamebooks.firstWhere((g) => g.id == 'uknedliku');
      final other = paid.gamebooks.firstWhere((g) => g.id == 'poslednislovo');
      final ents = const Entitlements().withGrandfathered(['uknedliku']);
      expect(ents.unlocksGamebook(g), isTrue);
      expect(ents.unlocksKit(g), isTrue);
      expect(ents.unlocksPack(paid, g.asPack()), isTrue);
      expect(ents.unlocksGamebook(other), isFalse);
      expect(ents.unlocksPack(paid, other.asPack()), isFalse);
      // A purchase keeps the grandfathered set.
      expect(ents.grant(r('pack_x')).grandfathered, {'uknedliku'});
    });

    test('the repository persists the grandfathered set', () async {
      final store = MemoryEntitlementStore();
      final repo = EntitlementRepository(store);
      await repo.load();
      await repo.grandfather(['uknedliku']);
      await repo.grant(r('gamebook_archion'));
      await repo.grandfather(['uknedliku', 'gulasspagety']);
      expect(store.grandfathered, {'uknedliku', 'gulasspagety'});
      final again = await EntitlementRepository(store).load();
      expect(again.grandfathered, {'uknedliku', 'gulasspagety'});
      expect(again.productIds, {'gamebook_archion'});
    });

    Future<ShopController> startShop({
      required Catalog fresh,
      Catalog? cached,
      required FakeInstaller installer,
      required MemoryEntitlementStore store,
    }) async {
      final c = ShopController(
        gateway: FakeStoreGateway(),
        catalogs: FakeCatalogRepository(fresh, cachedCatalog: cached),
        entitlementRepo: EntitlementRepository(store),
        installer: installer,
        onPacksChanged: () {},
      );
      addTearDown(c.dispose);
      await c.start();
      return c;
    }

    test(
      'first start of the new version: installs under the old free cache stay unlocked',
      () async {
        final store = MemoryEntitlementStore();
        // The old app installed two free books; its catalog is still the cached copy.
        final installer = FakeInstaller({
          'gamebook-uknedliku',
          'gamebook-gulasspagety',
        });
        final c = await startShop(
          cached: shopCatalog(version: 1, gulasFree: true),
          fresh: shopCatalog(version: 2),
          installer: installer,
          store: store,
        );
        final paid = c.state.catalog!;
        expect(paid.version, 2);
        bool unlocked(String id) => c.state.unlocked(
          paid.gamebooks.firstWhere((g) => g.id == id).asPack(),
        );
        expect(unlocked('uknedliku'), isTrue);
        expect(unlocked('gulasspagety'), isTrue);
        expect(unlocked('poslednislovo'), isFalse);
        expect(store.grandfathered, {'uknedliku', 'gulasspagety'});

        // Deleted and downloaded again later: still unlocked (the fact is persisted).
        installer.installed.clear();
        final later = await startShop(
          fresh: shopCatalog(version: 3),
          installer: installer,
          store: store,
        );
        final g = later.state.catalog!.gamebooks.firstWhere(
          (g) => g.id == 'uknedliku',
        );
        await later.download(g.asPack());
        expect(installer.installed, {'gamebook-uknedliku'});
      },
    );

    test('a free gamebook downloaded now is remembered at once', () async {
      final store = MemoryEntitlementStore();
      final c = await startShop(
        fresh: shopCatalog(gulasFree: true),
        installer: FakeInstaller(),
        store: store,
      );
      expect(store.grandfathered, isEmpty);
      final g = c.state.catalog!.gamebooks.firstWhere(
        (g) => g.id == 'poslednislovo',
      );
      await c.download(g.asPack());
      expect(store.grandfathered, {'poslednislovo'});
    });

    test('paid or not installed gamebooks are never grandfathered', () async {
      final store = MemoryEntitlementStore();
      await startShop(
        cached: shopCatalog(gulasFree: true),
        fresh: shopCatalog(version: 2),
        // archion_oil is installed but was never free.
        installer: FakeInstaller({'gamebook-archion_oil'}),
        store: store,
      );
      expect(store.grandfathered, isEmpty);
    });
  });

  group('store card', () {
    Widget app({
      required FakeStoreGateway gateway,
      required FakeInstaller installer,
      MemoryEntitlementStore? entitlements,
    }) => ProviderScope(
      overrides: [
        deviceLanguageProvider.overrideWithValue(null),
        ...shopOverrides(
          catalog: shopCatalog(),
          gateway: gateway,
          installer: installer,
          entitlements: entitlements,
        ),
      ],
      child: const MaterialApp(home: StoreScreen()),
    );

    Future<void> bigScreen(WidgetTester tester) async {
      tester.view.physicalSize = const Size(1200, 4000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
    }

    testWidgets('one card, one price; buying unlocks and downloads every book', (
      tester,
    ) async {
      await bigScreen(tester);
      final gateway = FakeStoreGateway();
      final installer = FakeInstaller();
      await tester.pumpWidget(app(gateway: gateway, installer: installer));
      await tester.pumpAndSettle();

      final card = find.byKey(
        const ValueKey('store-gamebook-product-gamebook_archion'),
      );
      expect(card, findsOneWidget);
      for (final id in archion) {
        expect(
          find.descendant(of: card, matching: find.text('Book $id')),
          findsOneWidget,
        );
        expect(find.byKey(ValueKey('pack-buy-gamebook-$id')), findsNothing);
      }
      final buy = find.byKey(
        const ValueKey('gamebook-product-buy-gamebook_archion'),
      );
      expect(buy, findsOneWidget);
      expect(
        find.descendant(of: buy, matching: find.text(r'$0.99')),
        findsOneWidget,
      );
      // No kit offer without a kit product; the lone gamebook keeps its own card and kit.
      for (final id in [...archion, ...gulas]) {
        expect(find.byKey(ValueKey('gamebook-kit-buy-$id')), findsNothing);
      }
      expect(find.byKey(const ValueKey('store-gamebook-sara')), findsOneWidget);
      expect(
        find.byKey(const ValueKey('gamebook-kit-buy-sara')),
        findsOneWidget,
      );

      await tester.tap(buy);
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const ValueKey('gate-answer')), '42');
      await tester.tap(find.byKey(const ValueKey('gate-submit')));
      await tester.pumpAndSettle();

      expect(gateway.bought, ['gamebook_archion']);
      expect(installer.downloads, [for (final id in archion) 'gamebook-$id']);
      expect(buy, findsNothing);
      for (final id in archion) {
        expect(
          find.byKey(ValueKey('pack-installed-gamebook-$id')),
          findsOneWidget,
        );
      }
      // The other shared product is still for sale.
      expect(
        find.byKey(
          const ValueKey('gamebook-product-buy-gamebook_gulasspagety'),
        ),
        findsOneWidget,
      );
    });

    testWidgets(
      'a grandfathered book downloads; the card still sells the rest',
      (tester) async {
        await bigScreen(tester);
        await tester.pumpWidget(
          app(
            gateway: FakeStoreGateway(),
            installer: FakeInstaller(),
            entitlements: MemoryEntitlementStore(null, {'uknedliku'}),
          ),
        );
        await tester.pumpAndSettle();
        expect(
          find.byKey(const ValueKey('pack-download-gamebook-uknedliku')),
          findsOneWidget,
        );
        expect(
          find.byKey(const ValueKey('pack-download-gamebook-poslednislovo')),
          findsNothing,
        );
        expect(
          find.byKey(
            const ValueKey('gamebook-product-buy-gamebook_gulasspagety'),
          ),
          findsOneWidget,
        );
      },
    );
  });
}
