import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:visibility_detector/visibility_detector.dart';
import 'package:webtoon/config.dart';
import 'package:webtoon/models/episode.dart';
import 'package:webtoon/providers/providers.dart';
import 'package:webtoon/reader/motion_sheet.dart';
import 'package:webtoon/reader/panel_view.dart';
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

Panel loopPanel({String videoStatus = 'ready'}) => Panel.fromJson(
  panelJson(
    0,
    animate: true,
    motion: 'her hair moves in the wind, static camera',
    videoStatus: videoStatus,
    videoUrl: videoStatus == 'ready' ? '/media/loop.webp' : null,
  ),
);

Widget panelApp(Panel p, {bool reduceMotion = false}) => MaterialApp(
  home: MediaQuery(
    data: MediaQueryData(disableAnimations: reduceMotion),
    child: Scaffold(
      body: SizedBox(
        width: 400,
        child: PanelView(
          panel: p,
          image: MemoryImage(kTinyPng),
          video: p.videoUrl == null ? null : MemoryImage(kTinyPng),
        ),
      ),
    ),
  ),
);

void main() {
  setUp(() {
    VisibilityDetectorController.instance.updateInterval = Duration.zero;
  });

  testWidgets('ready loop plays over the still; tap pauses', (tester) async {
    await tester.pumpWidget(panelApp(loopPanel()));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('panel-loop-0')), findsOneWidget);
    expect(find.byKey(const ValueKey('loop-playing')), findsOneWidget);
    // The still is still there underneath (poster + fallback).
    expect(find.byType(Image), findsNWidgets(2));
    await tester.tap(find.byKey(const ValueKey('loop-tap-0')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('loop-paused')), findsOneWidget);
    expect(find.byKey(const ValueKey('loop-playing')), findsNothing);
  });

  testWidgets('reduced motion shows the poster only', (tester) async {
    await tester.pumpWidget(panelApp(loopPanel(), reduceMotion: true));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('loop-reduced-motion')), findsOneWidget);
    expect(find.byKey(const ValueKey('loop-playing')), findsNothing);
  });

  testWidgets('pending loop shows the still and a chip', (tester) async {
    await tester.pumpWidget(panelApp(loopPanel(videoStatus: 'pending')));
    await tester.pump();
    expect(find.byKey(const ValueKey('panel-loop-pending-0')), findsOneWidget);
    expect(find.text('Rozhýbává se…'), findsOneWidget);
    expect(find.byKey(const ValueKey('panel-loop-0')), findsNothing);
  });

  test('motion edit → PATCH body and estimate', () {
    const e = MotionEdit(
      animate: true,
      motion: 'waves, static camera',
      loopSeconds: 3,
    );
    expect(e.toPatch(), {
      'animate': true,
      'motion': 'waves, static camera',
      'loop_seconds': 3,
    });
    expect(
      const MotionEdit(animate: false, motion: '', loopSeconds: 2).toPatch(),
      {'animate': false},
    );
    expect(motionEstimateSeconds(1), 100);
    expect(motionEstimateLabel(2), '≈ 2,6 min renderu');
  });

  testWidgets('editor: Rozhýbat → sheet → PATCH → chip → loop after polling', (
    tester,
  ) async {
    final api = FakeWebtoonApi(
      worlds: [testWorld()],
      campaigns: {
        'cp_1': testCampaign(['ep_m']),
      },
      episodeScripts: {
        'ep_m': [
          episodeJson('ep_m', panels: [panelJson(0), panelJson(1)]),
        ],
      },
    );
    await tester.pumpWidget(app(api, const ReaderScreen(campaignId: 'cp_1')));
    await tester.pumpAndSettle();
    final scrollable = find
        .descendant(
          of: find.byKey(const ValueKey('reader-scroll')),
          matching: find.byType(Scrollable),
        )
        .first;
    await tester.scrollUntilVisible(
      find.byKey(const ValueKey('panel-motion-0')),
      200,
      scrollable: scrollable,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('panel-motion-0')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('motion-switch')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('motion-field')),
      'her hair moves in the wind, static camera',
    );
    await tester.tap(find.text('3 s'));
    await tester.pumpAndSettle();
    expect(find.text('≈ 3,3 min renderu'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('motion-save')));
    await tester.pump();
    await tester.pump();
    expect(api.motionPatches.length, 1);
    expect(api.motionPatches.single.$3, {
      'animate': true,
      'motion': 'her hair moves in the wind, static camera',
      'loop_seconds': 3,
    });
    expect(find.byKey(const ValueKey('panel-loop-pending-0')), findsOneWidget);
    // Polling picks up the finished loop.
    await tester.pump(poll);
    await tester.pump();
    await tester.pump(poll);
    await tester.pump();
    expect(find.byKey(const ValueKey('panel-loop-0')), findsOneWidget);
    expect(find.byKey(const ValueKey('panel-loop-pending-0')), findsNothing);
    await tester.pumpWidget(const SizedBox());
  });
}
