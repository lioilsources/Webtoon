import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/api/webtoon_api.dart';
import 'package:webtoon/config.dart';
import 'package:webtoon/models/world.dart';
import 'package:webtoon/providers/providers.dart';
import 'package:webtoon/screens/reader_screen.dart';

import 'fake_api.dart';

const poll = Duration(milliseconds: 100);

Widget app(FakeWebtoonApi api, Widget home) => ProviderScope(
  overrides: [
    apiProvider.overrideWithValue(api),
    configProvider.overrideWithValue(
      const AppConfig(
        apiBase: 'http://test',
        userId: 'player',
        pollInterval: poll,
      ),
    ),
  ],
  child: MaterialApp(home: home),
);

Finder get readerScrollable => find
    .descendant(
      of: find.byKey(const ValueKey('reader-scroll')),
      matching: find.byType(Scrollable),
    )
    .first;

Future<void> scrollTo(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(f, 300, scrollable: readerScrollable);
  await tester.pumpAndSettle();
}

/// pumpAndSettle never settles while a queued episode shows an indeterminate progress bar
/// (and is being polled), so pump a fixed time instead.
Future<void> settleBusy(WidgetTester tester) async {
  for (var i = 0; i < 10; i++) {
    await tester.pump(const Duration(milliseconds: 50));
  }
}

void main() {
  testWidgets(
    'ready episode: panels with bubbles, gaps, end block with cost; choice → follows new episode',
    (tester) async {
      final api = FakeWebtoonApi(
        worlds: [testWorld()],
        campaigns: {
          'cp_1': testCampaign(['ep_1']),
        },
        episodeScripts: {
          'ep_1': [
            episodeJson(
              'ep_1',
              panels: [
                panelJson(0, gap: 'large'),
                panelJson(1),
                panelJson(2),
              ],
            ),
          ],
        },
      );
      await tester.pumpWidget(app(api, const ReaderScreen(campaignId: 'cp_1')));
      await tester.pumpAndSettle();

      expect(find.text('Moje dobrodružství'), findsOneWidget); // app bar
      expect(find.text('Dopis bez adresy'), findsOneWidget);
      expect(find.text('DÍL 1'), findsOneWidget);
      expect(find.text('Bublina 0'), findsOneWidget);

      // gap_after large = 320 at width 800 → the gap below panel 0 is 320 px (window is 800 wide).
      final p0 = tester.getRect(find.byKey(const ValueKey('panel-ep_1-0')));
      final p1 = tester.getRect(find.byKey(const ValueKey('panel-ep_1-1')));
      expect(p0.width, 800);
      expect(p1.top - p0.bottom, closeTo(320, 0.5));

      await scrollTo(tester, find.byKey(const ValueKey('choice-c1')));
      expect(find.text('Co udělá dál?'), findsOneWidget);
      expect(find.text('Další díl: ≈ 3 kredity'), findsOneWidget);
      expect(find.byKey(const ValueKey('free-text')), findsOneWidget);
      // No director permissions → no director section.
      expect(find.byKey(const ValueKey('director-section')), findsNothing);

      await tester.tap(find.byKey(const ValueKey('choice-c1')));
      await tester.pumpAndSettle();
      expect(find.text('Cena: ≈ 3 kredity'), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('confirm-generate')));
      await settleBusy(tester);

      expect(api.continueCalls, hasLength(1));
      expect(api.continueCalls.single.choiceId, 'c1');
      expect(api.continueCalls.single.director, isNull);
      // Reader follows the new (queued) episode: its header + progress are at the top.
      expect(find.text('DÍL 2'), findsOneWidget);
      expect(find.text('Díl čeká ve frontě…'), findsOneWidget);
      expect(find.byKey(const ValueKey('episode-end-block')), findsNothing);

      // Earlier episode is still there above (scroll back) with what was chosen.
      await tester.scrollUntilVisible(
        find.text('Dopis bez adresy'),
        -300,
        scrollable: readerScrollable,
        duration: const Duration(milliseconds: 20),
      );
      expect(find.text('Dopis bez adresy'), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets(
    'generating: polls, shows progress and panels as they arrive, then choices',
    (tester) async {
      final api = FakeWebtoonApi(
        worlds: [testWorld()],
        campaigns: {
          'cp_1': testCampaign(['ep_g']),
        },
        episodeScripts: {
          'ep_g': [
            episodeJson('ep_g', status: 'queued', panels: const []),
            episodeJson(
              'ep_g',
              status: 'generating',
              panels: [
                panelJson(0, status: 'pending'),
                panelJson(1, status: 'pending'),
                panelJson(2, status: 'pending'),
              ],
            ),
            episodeJson(
              'ep_g',
              status: 'generating',
              panels: [
                panelJson(0),
                panelJson(1, status: 'rendering'),
                panelJson(2, status: 'pending'),
              ],
            ),
            episodeJson(
              'ep_g',
              panels: [panelJson(0), panelJson(1), panelJson(2)],
            ),
          ],
        },
      );
      await tester.pumpWidget(app(api, const ReaderScreen(campaignId: 'cp_1')));
      await tester.pump();
      await tester.pump();
      expect(find.text('Díl čeká ve frontě…'), findsOneWidget);

      await tester.pump(poll);
      await tester.pump();
      expect(find.text('Kreslím panely 0/3'), findsOneWidget);
      expect(find.byKey(const ValueKey('panel-pending-0')), findsOneWidget);

      await tester.pump(poll);
      await tester.pump();
      expect(find.text('Kreslím panely 1/3'), findsOneWidget);
      expect(find.text('Bublina 0'), findsOneWidget); // first panel is in
      expect(find.text('Kreslím panel 2/3…'), findsOneWidget);
      final bar = tester.widget<LinearProgressIndicator>(
        find.descendant(
          of: find.byKey(const ValueKey('generating-banner')),
          matching: find.byType(LinearProgressIndicator),
        ),
      );
      expect(bar.value, closeTo(1 / 3, 1e-9));

      await tester.pump(poll);
      await tester.pump();
      expect(find.byKey(const ValueKey('generating-banner')), findsNothing);
      final fetches = api.episodeFetches['ep_g']!;
      await tester.pump(poll * 5);
      expect(
        api.episodeFetches['ep_g'],
        fetches,
        reason: 'polling stops once ready',
      );

      await tester.pumpAndSettle();
      await scrollTo(tester, find.byKey(const ValueKey('choice-c2')));
      expect(find.byKey(const ValueKey('episode-end-block')), findsOneWidget);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets('failed panel → regenerate → re-polls until it is drawn', (
    tester,
  ) async {
    final api = FakeWebtoonApi(
      worlds: [testWorld()],
      campaigns: {
        'cp_1': testCampaign(['ep_f']),
      },
      episodeScripts: {
        'ep_f': [
          episodeJson(
            'ep_f',
            panels: [
              panelJson(0, status: 'failed'),
              panelJson(1),
            ],
          ),
        ],
      },
    );
    await tester.pumpWidget(app(api, const ReaderScreen(campaignId: 'cp_1')));
    await tester.pumpAndSettle();
    expect(find.text('Panel 1 se nepodařilo nakreslit'), findsOneWidget);
    await tester.tap(find.text('Vygenerovat znovu'));
    await tester.pump();
    await tester.pump();
    expect(api.regenerations, [('ep_f', 0)]);
    expect(find.byKey(const ValueKey('panel-pending-0')), findsOneWidget);
    await tester.pump(poll);
    await tester.pump();
    await tester.pump(poll);
    await tester.pump();
    expect(find.text('Panel 1 se nepodařilo nakreslit'), findsNothing);
    expect(find.text('Bublina 0'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('long-press a bubble → edit → PATCH with the new text', (
    tester,
  ) async {
    final api = FakeWebtoonApi(
      worlds: [testWorld()],
      campaigns: {
        'cp_1': testCampaign(['ep_1']),
      },
      episodeScripts: {
        'ep_1': [
          episodeJson(
            'ep_1',
            panels: [
              panelJson(
                0,
                bubbles: [
                  {
                    'speaker_id': null,
                    'text': 'Poštovní věž.',
                    'kind': 'narration',
                  },
                  {
                    'speaker_id': 'c_vesna',
                    'text': 'Kdo sem píše?',
                    'kind': 'speech',
                  },
                ],
              ),
            ],
          ),
        ],
      },
    );
    await tester.pumpWidget(app(api, const ReaderScreen(campaignId: 'cp_1')));
    await tester.pumpAndSettle();
    await tester.longPress(find.text('Kdo sem píše?'));
    await tester.pumpAndSettle();
    expect(find.text('Upravit bublinu'), findsOneWidget);
    expect(find.text('Řeč · Vesna'), findsOneWidget);
    await tester.enterText(
      find.byKey(const ValueKey('bubble-edit-field')),
      'Kdo mi to píše?',
    );
    await tester.tap(find.byKey(const ValueKey('bubble-edit-save')));
    await tester.pumpAndSettle();

    expect(api.bubbleUpdates, hasLength(1));
    final (ep, panel, bubbles) = api.bubbleUpdates.single;
    expect(ep, 'ep_1');
    expect(panel, 0);
    expect(bubbles.map((b) => b.text), ['Poštovní věž.', 'Kdo mi to píše?']);
    expect(bubbles[1].speakerId, 'c_vesna');
    expect(find.text('Kdo mi to píše?'), findsOneWidget);
    expect(find.text('Kdo sem píše?'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('not the player: read-only, no end block', (tester) async {
    final api = FakeWebtoonApi(
      worlds: [testWorld()],
      campaigns: {
        'cp_1': testCampaign(['ep_1'], playerId: 'someone'),
      },
      episodeScripts: {
        'ep_1': [
          episodeJson('ep_1', panels: [panelJson(0)]),
        ],
      },
    );
    await tester.pumpWidget(app(api, const ReaderScreen(campaignId: 'cp_1')));
    await tester.pumpAndSettle();
    await tester.longPress(find.text('Bublina 0'));
    await tester.pumpAndSettle();
    expect(find.text('Upravit bublinu'), findsNothing);
    expect(find.byKey(const ValueKey('episode-end-block')), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('free text + director (when permitted) are sent', (tester) async {
    final api = FakeWebtoonApi(
      worlds: [
        testWorld(
          permissions: const Permissions(
            canChangeLocation: true,
            canAddCharacters: true,
            allowedLocations: ['l_post', 'l_cliff'],
          ),
        ),
      ],
      campaigns: {
        'cp_1': testCampaign(['ep_1']),
      },
      episodeScripts: {
        'ep_1': [
          episodeJson('ep_1', panels: [panelJson(0)]),
        ],
      },
    );
    await tester.pumpWidget(app(api, const ReaderScreen(campaignId: 'cp_1')));
    await tester.pumpAndSettle();
    await scrollTo(tester, find.byKey(const ValueKey('director-section')));
    await tester.tap(find.text('Režie'));
    await tester.pumpAndSettle();
    await scrollTo(tester, find.byKey(const ValueKey('location-l_cliff')));
    await tester.tap(find.byKey(const ValueKey('location-l_cliff')));
    await tester.tap(find.text('Přidat Kos'));
    await tester.pumpAndSettle();

    await scrollTo(tester, find.byKey(const ValueKey('free-text')));
    await tester.enterText(
      find.byKey(const ValueKey('free-text')),
      'Schovám dopis do brašny.',
    );
    await tester.tap(find.byKey(const ValueKey('free-send')));
    await tester.pumpAndSettle();
    expect(find.text('„Schovám dopis do brašny.“'), findsOneWidget);
    expect(find.textContaining('Lokace: Bouřkový útes'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('confirm-generate')));
    await settleBusy(tester);

    final call = api.continueCalls.single;
    expect(call.freeText, 'Schovám dopis do brašny.');
    expect(call.choiceId, isNull);
    expect(call.director!.toJson(), {
      'add_characters': ['c_kos'],
      'location_id': 'l_cliff',
    });
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('backend refusal is shown and nothing is followed', (
    tester,
  ) async {
    final api =
        FakeWebtoonApi(
            worlds: [testWorld()],
            campaigns: {
              'cp_1': testCampaign(['ep_1']),
            },
            episodeScripts: {
              'ep_1': [
                episodeJson('ep_1', panels: [panelJson(0)]),
              ],
            },
          )
          ..failNextContinue = czechError(
            'an episode is still being generated',
            409,
          );
    await tester.pumpWidget(app(api, const ReaderScreen(campaignId: 'cp_1')));
    await tester.pumpAndSettle();
    await scrollTo(tester, find.byKey(const ValueKey('choice-c2')));
    await tester.tap(find.byKey(const ValueKey('choice-c2')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('confirm-generate')));
    await settleBusy(tester);
    expect(find.text('Díl se ještě generuje.'), findsOneWidget);
    expect(find.text('DÍL 2'), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('history sheet lists episodes and focuses an earlier one', (
    tester,
  ) async {
    final api = FakeWebtoonApi(
      worlds: [testWorld()],
      campaigns: {
        'cp_1': testCampaign(['ep_1', 'ep_2']),
      },
      episodeScripts: {
        'ep_1': [
          episodeJson('ep_1', title: 'První', panels: [panelJson(0)]),
        ],
        'ep_2': [
          episodeJson('ep_2', index: 2, title: 'Druhý', panels: [panelJson(0)]),
        ],
      },
    );
    await tester.pumpWidget(app(api, const ReaderScreen(campaignId: 'cp_1')));
    await tester.pumpAndSettle();
    // Opens on the latest episode.
    expect(find.text('Druhý'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('history-button')));
    await tester.pumpAndSettle();
    expect(find.text('Historie dílů'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('history-ep_1')));
    await tester.pumpAndSettle();
    final title = find.byKey(const ValueKey('episode-title-ep_1'));
    expect(title, findsOneWidget);
    expect(tester.getRect(title).top, lessThan(200));
    await tester.pumpWidget(const SizedBox());
  });
}
