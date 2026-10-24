// Obchod, reader profile and parental gate over FakeStoreGateway + FakeInstaller (no network,
// no store): first-launch chooser, prices / Zdarma, buy → gate → purchase → download, bundles,
// Kids filtering of Obchod and Knihovna, delete, restore, offline catalog.

import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/api/local_webtoon_api.dart';
import 'package:webtoon/app.dart';
import 'package:webtoon/packs/pack_bootstrap.dart';
import 'package:webtoon/packs/pack_store.dart';
import 'package:webtoon/profile/reader_profile.dart';
import 'package:webtoon/providers/language_provider.dart';
import 'package:webtoon/providers/providers.dart';
import 'package:webtoon/shop/entitlements.dart';
import 'package:webtoon/shop/store_gateway.dart';

import 'pack_fixture.dart';
import 'shop_fakes.dart';

/// The fixture pack as an adult pack: world w_romance (audience adult), stories r_*.
Map<String, dynamic> adultManifest() {
  final m = fixtureManifest(id: 'romance');
  final w = (m['worlds'] as List).first as Map<String, dynamic>;
  w['id'] = 'w_romance';
  w['title'] = 'Noci na Santorini';
  w['audience'] = 'adult';
  for (final s in (m['stories'] as List).cast<Map<String, dynamic>>()) {
    s['id'] = 'r_${s['id']}';
    s['world_id'] = 'w_romance';
    s['title'] = 'Romance: ${s['title']}';
    s['title_i18n'] = {};
    s['type'] = 'harlequin';
  }
  return m;
}

void main() {
  late PackStore store;
  late Directory tmp;

  setUpAll(() async {
    (store, tmp) = await installedFixtureStore();
    final f = File('${tmp.path}/romance.zip')
      ..writeAsBytesSync(fixtureZip(adultManifest()));
    await store.installFromFile(f.path);
  });
  tearDownAll(() => tmp.deleteSync(recursive: true));

  Widget app({
    ReaderProfile? profile = ReaderProfile.adults,
    MemoryProfileStore? profileStore,
    FakeStoreGateway? gateway,
    FakeInstaller? installer,
    MemoryEntitlementStore? entitlements,
    bool offline = false,
  }) => ProviderScope(
    overrides: [
      packStoreProvider.overrideWithValue(store),
      packBootstrapProvider.overrideWith((ref) => PackBootstrap.ready(store)),
      deviceLanguageProvider.overrideWithValue(null),
      ...shopOverrides(
        profile: profile,
        profileStore: profileStore,
        gateway: gateway,
        installer: installer,
        entitlements: entitlements,
        offline: offline,
      ),
    ],
    child: const WebtoonApp(),
  );

  Future<void> bigScreen(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1200, 2600);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
  }

  Future<void> openStore(WidgetTester tester) async {
    await tester.tap(find.byKey(const ValueKey('tab-store')));
    await tester.pumpAndSettle();
  }

  Future<void> answerGate(WidgetTester tester, String answer) async {
    expect(find.byKey(const ValueKey('parental-gate')), findsOneWidget);
    expect(find.text('Kolik je 6 × 7?'), findsOneWidget);
    await tester.enterText(find.byKey(const ValueKey('gate-answer')), answer);
    await tester.tap(find.byKey(const ValueKey('gate-submit')));
    await tester.pumpAndSettle();
  }

  group('reader profile', () {
    testWidgets('first launch: chooser; Děti needs no gate and is saved', (
      tester,
    ) async {
      final ps = MemoryProfileStore();
      await tester.pumpWidget(app(profileStore: ps));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('profile-chooser')), findsOneWidget);
      expect(find.text('Kdo bude číst?'), findsOneWidget);
      expect(find.text('Knihovna'), findsNothing);
      await tester.tap(find.byKey(const ValueKey('profile-kids')));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('parental-gate')), findsNothing);
      expect(ps.saved, ReaderProfile.kids);
      expect(find.text('Knihovna'), findsWidgets);
      expect(find.text('Obchod'), findsOneWidget);
    });

    testWidgets(
      'first launch: Dospělí is behind the gate; wrong answer, cancel, right answer',
      (tester) async {
        final ps = MemoryProfileStore();
        await tester.pumpWidget(app(profileStore: ps));
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const ValueKey('profile-adults')));
        await tester.pumpAndSettle();
        await answerGate(tester, '41');
        expect(find.text('To není správně, zkus to znovu.'), findsOneWidget);
        expect(ps.saved, isNull);
        await tester.tap(find.byKey(const ValueKey('gate-cancel')));
        await tester.pumpAndSettle();
        expect(find.byKey(const ValueKey('profile-chooser')), findsOneWidget);
        expect(ps.saved, isNull);

        await tester.tap(find.byKey(const ValueKey('profile-adults')));
        await tester.pumpAndSettle();
        await answerGate(tester, '42');
        expect(ps.saved, ReaderProfile.adults);
        expect(find.byKey(const ValueKey('profile-chooser')), findsNothing);
      },
    );

    testWidgets('Knihovna: Kids hides the adult world, Adults shows it', (
      tester,
    ) async {
      await bigScreen(tester);
      await tester.pumpWidget(app(profile: ReaderProfile.kids));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('library-world-w_les')), findsOneWidget);
      expect(
        find.byKey(const ValueKey('library-world-w_romance')),
        findsNothing,
      );
      expect(find.byKey(const ValueKey('story-r_cp_jezek')), findsNothing);

      await tester.pumpWidget(const SizedBox());
      await tester.pumpWidget(app(profile: ReaderProfile.adults));
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('library-world-w_romance')),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey('story-r_cp_jezek')), findsOneWidget);
    });

    test(
      'LocalWebtoonApi with the Kids filter lists no adult world or story',
      () async {
        final api = LocalWebtoonApi(
          store,
          storyFilter: (s) => storyVisibleIn(store, ReaderProfile.kids, s),
        );
        expect((await api.listWorlds()).map((w) => w.id), ['w_les']);
        expect(
          (await api.listCampaigns()).map((c) => c.id),
          isNot(contains('r_cp_jezek')),
        );
        expect(
          storyVisible(
            ReaderProfile.kids,
            worldAudience: 'kids',
            type: 'harlequin',
          ),
          isFalse,
        );
        expect(
          storyVisible(
            ReaderProfile.adults,
            worldAudience: 'adult',
            type: 'harlequin',
          ),
          isTrue,
        );
        expect(storyVisible(null, worldAudience: 'adult'), isTrue);
      },
    );

    testWidgets(
      'Nastavení: switch to Kids freely, back to Adults only past the gate',
      (tester) async {
        await bigScreen(tester);
        final ps = MemoryProfileStore(ReaderProfile.adults);
        await tester.pumpWidget(app(profileStore: ps));
        await tester.pumpAndSettle();
        await tester.tap(find.text('Nastavení'));
        await tester.pumpAndSettle();
        expect(find.text('Profil čtenáře'), findsOneWidget);
        expect(find.text('Dospělí'), findsOneWidget);
        await tester.tap(find.byKey(const ValueKey('settings-switch-profile')));
        await tester.pumpAndSettle();
        expect(find.byKey(const ValueKey('parental-gate')), findsNothing);
        expect(ps.saved, ReaderProfile.kids);
        expect(find.text('Přepnout na Dospělí'), findsOneWidget);

        await tester.tap(find.byKey(const ValueKey('settings-switch-profile')));
        await tester.pumpAndSettle();
        await answerGate(tester, '42');
        expect(ps.saved, ReaderProfile.adults);
      },
    );
  });

  group('Obchod', () {
    testWidgets('types, packs with store prices or Zdarma, bundles', (
      tester,
    ) async {
      await bigScreen(tester);
      await tester.pumpWidget(app());
      await tester.pumpAndSettle();
      await openStore(tester);
      expect(find.byKey(const ValueKey('store-type-kids')), findsOneWidget);
      expect(
        find.byKey(const ValueKey('store-type-superhero')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('store-type-harlequin')),
        findsOneWidget,
      );
      expect(find.text('Pro děti'), findsOneWidget);
      expect(find.text('Děti I'), findsOneWidget);
      expect(find.text(r'$0.99'), findsNWidgets(2)); // kids-1, harlequin-1
      expect(find.text('Zdarma · Stáhnout'), findsOneWidget); // superhero-1
      expect(find.text('50 příběhů · 2 kB'), findsNWidgets(3));
      expect(find.byKey(const ValueKey('store-bundles')), findsOneWidget);
      expect(find.text(r'$2.99'), findsNWidgets(2));
      expect(find.text(r'$6.99'), findsOneWidget);
      expect(
        find.text('Všechny současné i budoucí balíčky: Pro děti'),
        findsOneWidget,
      );
      expect(
        find.text('Všechny současné i budoucí balíčky všech typů'),
        findsOneWidget,
      );
    });

    testWidgets(
      'buy: parental gate → purchase → receipt saved → download → Staženo',
      (tester) async {
        await bigScreen(tester);
        final gateway = FakeStoreGateway();
        final installer = FakeInstaller();
        final ents = MemoryEntitlementStore();
        await tester.pumpWidget(
          app(gateway: gateway, installer: installer, entitlements: ents),
        );
        await tester.pumpAndSettle();
        await openStore(tester);

        // Cancelled gate: no purchase.
        await tester.tap(find.byKey(const ValueKey('pack-buy-kids-1')));
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const ValueKey('gate-cancel')));
        await tester.pumpAndSettle();
        expect(gateway.bought, isEmpty);

        await tester.tap(find.byKey(const ValueKey('pack-buy-kids-1')));
        await tester.pumpAndSettle();
        await answerGate(tester, '42');
        expect(gateway.bought, ['pack_kids_1']);
        expect(gateway.finished, ['pack_kids_1']);
        expect(ents.saved.map((r) => r.productId), ['pack_kids_1']);
        expect(ents.saved.single.receipt, 'fake-receipt-pack_kids_1');
        expect(installer.downloads, ['kids-1']);
        expect(
          find.byKey(const ValueKey('pack-installed-kids-1')),
          findsOneWidget,
        );
        expect(find.text('Staženo'), findsOneWidget);
        expect(find.byKey(const ValueKey('pack-buy-kids-1')), findsNothing);
      },
    );

    testWidgets('download progress is shown while the pack downloads', (
      tester,
    ) async {
      await bigScreen(tester);
      final installer = FakeInstaller()..gate = Completer();
      await tester.pumpWidget(app(installer: installer));
      await tester.pumpAndSettle();
      await openStore(tester);
      await tester.tap(find.byKey(const ValueKey('pack-download-superhero-1')));
      await tester.pump();
      await tester.pump();
      expect(
        find.byKey(const ValueKey('pack-progress-superhero-1')),
        findsOneWidget,
      );
      expect(find.text('Stahuji… 25 %'), findsOneWidget);
      installer.gate!.complete();
      await tester.pumpAndSettle();
      expect(
        find.byKey(const ValueKey('pack-installed-superhero-1')),
        findsOneWidget,
      );
    });

    testWidgets('free pack downloads without the store or the gate', (
      tester,
    ) async {
      await bigScreen(tester);
      final gateway = FakeStoreGateway();
      final installer = FakeInstaller();
      await tester.pumpWidget(app(gateway: gateway, installer: installer));
      await tester.pumpAndSettle();
      await openStore(tester);
      await tester.tap(find.byKey(const ValueKey('pack-download-superhero-1')));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('parental-gate')), findsNothing);
      expect(gateway.bought, isEmpty);
      expect(installer.downloads, ['superhero-1']);
      expect(
        find.byKey(const ValueKey('pack-installed-superhero-1')),
        findsOneWidget,
      );
    });

    testWidgets('failed and cancelled purchases: snackbar, nothing granted', (
      tester,
    ) async {
      await bigScreen(tester);
      final gateway = FakeStoreGateway()..nextResult = PurchaseState.failed;
      final ents = MemoryEntitlementStore();
      await tester.pumpWidget(app(gateway: gateway, entitlements: ents));
      await tester.pumpAndSettle();
      await openStore(tester);
      await tester.tap(find.byKey(const ValueKey('pack-buy-kids-1')));
      await tester.pumpAndSettle();
      await answerGate(tester, '42');
      expect(find.text('Nákup se nepodařil: fake failure'), findsOneWidget);
      expect(ents.saved, isEmpty);
      expect(find.byKey(const ValueKey('pack-buy-kids-1')), findsOneWidget);

      gateway.nextResult = PurchaseState.cancelled;
      await tester.tap(find.byKey(const ValueKey('pack-buy-kids-1')));
      await tester.pumpAndSettle();
      await answerGate(tester, '42');
      await tester.pump(const Duration(seconds: 5));
      await tester.pumpAndSettle();
      expect(find.text('Nákup byl zrušen.'), findsOneWidget);
      expect(ents.saved, isEmpty);
    });

    testWidgets(
      'owned bundle: packs of its type download without buying; bundle shows Zakoupeno',
      (tester) async {
        await bigScreen(tester);
        final ents = MemoryEntitlementStore([
          Receipt(productId: 'bundle_kids', grantedAt: DateTime.utc(2026)),
        ]);
        await tester.pumpWidget(app(entitlements: ents));
        await tester.pumpAndSettle();
        await openStore(tester);
        expect(
          find.byKey(const ValueKey('pack-download-kids-1')),
          findsOneWidget,
        );
        expect(find.byKey(const ValueKey('pack-buy-kids-1')), findsNothing);
        expect(
          find.byKey(const ValueKey('pack-buy-harlequin-1')),
          findsOneWidget,
        );
        expect(
          find.byKey(const ValueKey('bundle-owned-bundle_kids')),
          findsOneWidget,
        );
        expect(find.text('Zakoupeno'), findsOneWidget);
      },
    );

    testWidgets('buying a bundle does not download everything at once', (
      tester,
    ) async {
      await bigScreen(tester);
      final gateway = FakeStoreGateway();
      final installer = FakeInstaller();
      await tester.pumpWidget(app(gateway: gateway, installer: installer));
      await tester.pumpAndSettle();
      await openStore(tester);
      await tester.tap(
        find.descendant(
          of: find.byKey(const ValueKey('bundle-buy-bundle_all')),
          matching: find.byType(FilledButton),
        ),
      );
      await tester.pumpAndSettle();
      await answerGate(tester, '42');
      expect(gateway.bought, ['bundle_all']);
      expect(installer.downloads, isEmpty);
      expect(
        find.byKey(const ValueKey('pack-download-kids-1')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('pack-download-harlequin-1')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('bundle-owned-bundle_all')),
        findsOneWidget,
      );
    });

    testWidgets('Kids profile: no romance type, pack or adult bundle', (
      tester,
    ) async {
      await bigScreen(tester);
      await tester.pumpWidget(app(profile: ReaderProfile.kids));
      await tester.pumpAndSettle();
      await openStore(tester);
      expect(find.byKey(const ValueKey('store-type-kids')), findsOneWidget);
      expect(
        find.byKey(const ValueKey('store-type-superhero')),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey('store-type-harlequin')), findsNothing);
      expect(
        find.byKey(const ValueKey('store-pack-harlequin-1')),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('store-bundle-bundle_kids')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('store-bundle-bundle_harlequin')),
        findsNothing,
      );
      expect(
        find.byKey(const ValueKey('store-bundle-bundle_all')),
        findsNothing,
      );
    });

    testWidgets('installed pack: Smazat after confirmation', (tester) async {
      await bigScreen(tester);
      final installer = FakeInstaller({'superhero-1'});
      await tester.pumpWidget(app(installer: installer));
      await tester.pumpAndSettle();
      await openStore(tester);
      expect(
        find.byKey(const ValueKey('pack-installed-superhero-1')),
        findsOneWidget,
      );
      await tester.tap(find.byKey(const ValueKey('pack-delete-superhero-1')));
      await tester.pumpAndSettle();
      expect(find.text('Smazat balíček?'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('pack-delete-confirm')));
      await tester.pumpAndSettle();
      expect(installer.installed, isEmpty);
      expect(
        find.byKey(const ValueKey('pack-download-superhero-1')),
        findsOneWidget,
      );
    });

    testWidgets('pack detail: story previews and the same action', (
      tester,
    ) async {
      await bigScreen(tester);
      await tester.pumpWidget(app());
      await tester.pumpAndSettle();
      await openStore(tester);
      await tester.tap(find.byKey(const ValueKey('store-pack-kids-1')));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('pack-detail-kids-1')), findsOneWidget);
      expect(find.text('Ukázka příběhů'), findsOneWidget);
      expect(find.text('Drak a lucerna'), findsOneWidget);
      expect(find.text('Jazyky: 2'), findsOneWidget);
      expect(find.byKey(const ValueKey('pack-buy-kids-1')), findsOneWidget);
    });

    testWidgets('offline without a cached catalog: message and retry', (
      tester,
    ) async {
      await tester.pumpWidget(app(offline: true));
      await tester.pumpAndSettle();
      await openStore(tester);
      expect(find.byKey(const ValueKey('store-offline')), findsOneWidget);
      expect(find.byKey(const ValueKey('store-retry')), findsOneWidget);
    });

    testWidgets(
      'Nastavení: Obnovit nákupy re-grants what the store account owns',
      (tester) async {
        await bigScreen(tester);
        final gateway = FakeStoreGateway(owned: {'pack_harlequin_1'});
        final ents = MemoryEntitlementStore();
        await tester.pumpWidget(app(gateway: gateway, entitlements: ents));
        await tester.pumpAndSettle();
        await tester.tap(find.text('Nastavení'));
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const ValueKey('restore-purchases')));
        await tester.pumpAndSettle();
        expect(gateway.restoreCalls, 1);
        expect(find.text('Nákupy obnoveny.'), findsOneWidget);
        expect(ents.saved.map((r) => r.productId), ['pack_harlequin_1']);
        await openStore(tester);
        expect(
          find.byKey(const ValueKey('pack-download-harlequin-1')),
          findsOneWidget,
        );
      },
    );

    testWidgets('UI follows the reader language (English)', (tester) async {
      await bigScreen(tester);
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            packStoreProvider.overrideWithValue(store),
            packBootstrapProvider.overrideWith(
              (ref) => PackBootstrap.ready(store),
            ),
            deviceLanguageProvider.overrideWithValue('en'),
            ...shopOverrides(),
          ],
          child: const WebtoonApp(),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Store'), findsOneWidget);
      await openStore(tester);
      expect(find.text('Kids'), findsOneWidget);
      expect(find.text('50 stories · 2 kB'), findsNWidgets(3));
      expect(find.text('Free · Download'), findsOneWidget);
      expect(find.text('Bundles'), findsOneWidget);
    });
  });
}
