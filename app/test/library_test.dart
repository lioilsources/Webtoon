// Reader mode (offline packs): Knihovna, Nastavení, and the reader's end-of-episode blocks
// over a fixture pack installed into a temp dir.

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:visibility_detector/visibility_detector.dart';
import 'package:webtoon/api/local_webtoon_api.dart';
import 'package:webtoon/app.dart';
import 'package:webtoon/packs/pack_bootstrap.dart';
import 'package:webtoon/packs/pack_store.dart';
import 'package:webtoon/providers/language_provider.dart';
import 'package:webtoon/providers/providers.dart';
import 'package:webtoon/screens/reader_screen.dart';

import 'pack_fixture.dart';

void main() {
  late PackStore store;
  late Directory tmp;

  // Real file I/O does not complete inside testWidgets' fake async; install once outside.
  setUpAll(() async {
    (store, tmp) = await installedFixtureStore();
    // ep_j1 has a loop; the loop's VisibilityDetector would otherwise leave a timer pending.
    VisibilityDetectorController.instance.updateInterval = Duration.zero;
  });

  tearDownAll(() => tmp.deleteSync(recursive: true));

  Widget app({Widget? home}) => ProviderScope(
    overrides: [
      packStoreProvider.overrideWithValue(store),
      apiProvider.overrideWithValue(LocalWebtoonApi(store)),
      packBootstrapProvider.overrideWith((ref) => PackBootstrap.ready(store)),
      // The host locale is English and the fixture is translated into it; start on the
      // originals so the Czech texts are what the tests see.
      deviceLanguageProvider.overrideWithValue(null),
    ],
    child: home == null ? const WebtoonApp() : MaterialApp(home: home),
  );

  Finder readerScrollable() => find
      .descendant(
        of: find.byKey(const ValueKey('reader-scroll')),
        matching: find.byType(Scrollable),
      )
      .first;

  Future<void> scrollTo(WidgetTester tester, Finder f) async {
    await tester.scrollUntilVisible(f, 300, scrollable: readerScrollable());
    await tester.pumpAndSettle();
  }

  testWidgets('Knihovna: stories grouped by world, audience badge, no author tabs', (
    tester,
  ) async {
    await tester.pumpWidget(app());
    await tester.pumpAndSettle();

    expect(find.text('Knihovna'), findsWidgets); // app bar + tab
    expect(find.text('Nastavení'), findsOneWidget);
    expect(find.text('Tvořit'), findsNothing);
    expect(find.text('Světy'), findsNothing);
    expect(find.text('Kampaně'), findsNothing);
    expect(find.byKey(const ValueKey('pack-splash')), findsNothing);

    expect(find.byKey(const ValueKey('library-world-w_les')), findsOneWidget);
    expect(find.text('Les za humny'), findsOneWidget);
    expect(find.byKey(const ValueKey('audience-w_les')), findsOneWidget);
    expect(find.text('Pro děti'), findsOneWidget);
    expect(find.byKey(const ValueKey('story-cp_jezek')), findsOneWidget);
    expect(find.byKey(const ValueKey('story-cp_sova')), findsOneWidget);
    expect(find.text('Ježek a lucerna'), findsOneWidget);
    expect(find.text('2 díly'), findsOneWidget);
    expect(find.text('1 díl'), findsOneWidget);

    // Tap → reader on episode 1 (not the latest).
    await tester.tap(find.byKey(const ValueKey('story-cp_jezek')));
    await tester.pumpAndSettle();
    expect(find.text('DÍL 1'), findsOneWidget);
    expect(find.text('Ztracené světlo'), findsOneWidget);
    expect(tester.getRect(find.text('Ztracené světlo')).top, lessThan(200));
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('splash while the starter is extracting; retry on error', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          packStoreProvider.overrideWithValue(store),
          apiProvider.overrideWithValue(LocalWebtoonApi(store)),
          packBootstrapProvider.overrideWith(
            (ref) => PackBootstrap(
              store,
              initial: const PackBootstrapState(
                phase: PackPhase.extracting,
                done: 3,
                total: 12,
              ),
            ),
          ),
        ],
        child: const WebtoonApp(),
      ),
    );
    await tester.pump();
    expect(find.byKey(const ValueKey('pack-splash')), findsOneWidget);
    expect(find.text('Připravuji příběhy… 3/12'), findsOneWidget);
    expect(find.byKey(const ValueKey('library-list')), findsNothing);
    final bar = tester.widget<LinearProgressIndicator>(
      find.byType(LinearProgressIndicator),
    );
    expect(bar.value, closeTo(0.25, 1e-9));
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets(
    'end of episode offline: recorded choice marked, others muted, Další díl; last → Konec + next story',
    (tester) async {
      await tester.pumpWidget(
        app(home: const ReaderScreen(campaignId: 'cp_jezek', startAtFirst: true)),
      );
      await tester.pumpAndSettle();
      expect(find.text('DÍL 1'), findsOneWidget);
      expect(find.text('Kde je moje lucerna?'), findsOneWidget);

      // No generation UI, no motion / regenerate controls.
      await scrollTo(tester, find.byKey(const ValueKey('local-episode-end')));
      expect(find.byKey(const ValueKey('episode-end-block')), findsNothing);
      expect(find.byKey(const ValueKey('free-text')), findsNothing);
      expect(find.byKey(const ValueKey('credits-cost')), findsNothing);
      expect(find.byKey(const ValueKey('panel-motion-0')), findsNothing);
      expect(find.textContaining('kredit'), findsNothing);

      // Choices of episode 1 with episode 2's `chosen` (c2) as the one taken.
      expect(find.byKey(const ValueKey('choice-c1')), findsOneWidget);
      expect(find.byKey(const ValueKey('choice-c2')), findsOneWidget);
      expect(find.text('Jít hledat k potoku.'), findsOneWidget);
      expect(find.text('Zeptat se sovy.'), findsOneWidget);
      expect(find.text('Nebo napiš, co uděláš…'), findsNothing);
      final taken = find.descendant(
        of: find.byKey(const ValueKey('choice-c2')),
        matching: find.byIcon(Icons.check_circle_rounded),
      );
      expect(taken, findsOneWidget);
      expect(
        find.descendant(
          of: find.byKey(const ValueKey('choice-c1')),
          matching: find.byIcon(Icons.check_circle_rounded),
        ),
        findsNothing,
      );
      // Not tappable: tapping a choice opens no dialog.
      await tester.tap(find.byKey(const ValueKey('choice-c1')));
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsNothing);
      expect(find.byKey(const ValueKey('confirm-generate')), findsNothing);

      // "Další díl" focuses episode 2 (it is at the top now).
      await tester.tap(find.byKey(const ValueKey('next-episode')));
      await tester.pumpAndSettle();
      final ep2 = find.byKey(const ValueKey('episode-title-ep_j2'));
      expect(ep2, findsOneWidget);
      expect(tester.getRect(ep2).top, lessThan(200));

      // Last episode: "Konec" + the other story of the same world.
      await scrollTo(tester, find.byKey(const ValueKey('story-end')));
      expect(find.text('Konec'), findsOneWidget);
      expect(find.text('Další příběh'), findsOneWidget);
      expect(find.byKey(const ValueKey('next-story')), findsOneWidget);
      expect(find.text('Sova, která nespala'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('next-story')));
      await tester.pumpAndSettle();
      expect(find.text('Dlouhá noc'), findsOneWidget);
      expect(find.text('DÍL 1'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets('story with a single episode: Konec right away; no bubble editing', (
    tester,
  ) async {
    await tester.pumpWidget(
      app(home: const ReaderScreen(campaignId: 'cp_sova', startAtFirst: true)),
    );
    await tester.pumpAndSettle();
    expect(find.text('Zase nespím.'), findsOneWidget);
    await tester.longPress(find.text('Zase nespím.'));
    await tester.pumpAndSettle();
    expect(find.text('Upravit bublinu'), findsNothing);

    expect(find.byKey(const ValueKey('local-episode-end')), findsNothing);
    await scrollTo(tester, find.byKey(const ValueKey('story-end')));
    expect(find.text('Konec'), findsOneWidget);
    expect(find.text('Ježek a lucerna'), findsOneWidget); // suggestion
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('Nastavení: language, storage, Obnovit starter', (tester) async {
    await tester.pumpWidget(app());
    await tester.pumpAndSettle();
    await tester.tap(find.text('Nastavení'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('settings-language')), findsOneWidget);
    expect(find.text('Jazyk bublin'), findsOneWidget);
    expect(find.byKey(const ValueKey('storage-used')), findsOneWidget);
    expect(find.text('Fixture'), findsOneWidget);
    expect(find.text('v1 · 2 příběhy'), findsOneWidget);
    expect(find.byKey(const ValueKey('reinstall-starter')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('reinstall-starter')));
    await tester.pumpAndSettle();
    expect(find.text('Obnovit starter?'), findsOneWidget);
    await tester.tap(find.text('Zrušit'));
    await tester.pumpAndSettle();
    expect(find.text('Obnovit starter?'), findsNothing);

    // Language change goes through readerLanguageProvider (Czech story has an English title).
    await tester.tap(find.byKey(const ValueKey('settings-language')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('🇬🇧  English').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Knihovna').last);
    await tester.pumpAndSettle();
    expect(find.text('The Hedgehog and the Lantern'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });
}
