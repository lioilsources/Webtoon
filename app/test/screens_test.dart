import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/app.dart';
import 'package:webtoon/config.dart';
import 'package:webtoon/models/world.dart';
import 'package:webtoon/providers/providers.dart';

import 'fake_api.dart';

void main() {
  testWidgets('worlds → detail → Začít kampaň → pick character → reader', (
    tester,
  ) async {
    final mine = World(id: 'w_mine', ownerId: 'player', title: 'Můj svět');
    final api = FakeWebtoonApi(worlds: [testWorld(), mine]);
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          apiProvider.overrideWithValue(api),
          configProvider.overrideWithValue(
            const AppConfig(
              apiBase: 'http://t',
              userId: 'player',
              pollInterval: Duration(milliseconds: 100),
            ),
          ),
        ],
        child: const WebtoonApp(),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Moje světy'), findsOneWidget);
    expect(find.text('Veřejné světy'), findsOneWidget);
    expect(find.text('Můj'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('world-w_skyisles')));
    await tester.pumpAndSettle();
    expect(find.text('Hratelné postavy'), findsOneWidget);
    expect(find.text('Vesna'), findsOneWidget);
    expect(find.text('Kos'), findsNothing); // npc is not playable

    await tester.tap(find.byKey(const ValueKey('start-campaign')));
    await tester.pumpAndSettle();
    expect(find.text('Za koho budeš hrát?'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('confirm-start')));
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    expect(api.campaigns, hasLength(1));
    expect(api.campaigns.values.single.playerCharacterId, 'c_vesna');
    // Reader on the queued first episode.
    expect(find.text('Díl čeká ve frontě…'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('campaigns tab lists my campaigns', (tester) async {
    final api = FakeWebtoonApi(
      worlds: [testWorld()],
      campaigns: {
        'cp_1': testCampaign(['ep_1', 'ep_2']),
      },
    );
    await tester.pumpWidget(
      ProviderScope(
        overrides: [apiProvider.overrideWithValue(api)],
        child: const WebtoonApp(),
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Kampaně'));
    await tester.pumpAndSettle();
    expect(find.text('Moje dobrodružství'), findsOneWidget);
    expect(find.textContaining('2 díly'), findsOneWidget);
  });
}
