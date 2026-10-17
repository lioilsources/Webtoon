// Author tools against a live backend (no fakes). Needs `webtoon serve` on WEBTOON_API; never
// enqueues GPU jobs (no sheet, no campaign), so it is safe outside the ComfyUI window.
//
//   flutter test integration_test/author_live_test.dart -d macos \
//     --dart-define=WEBTOON_API=http://localhost:8095 --dart-define=WEBTOON_USER=author_live
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:webtoon/api/http_webtoon_api.dart';
import 'package:webtoon/app.dart';
import 'package:webtoon/config.dart';
import 'package:webtoon/providers/providers.dart';
import 'package:webtoon/services/image_picker.dart';

import '../test/fake_api.dart' show kTinyPng;

Future<void> tapKey(WidgetTester tester, String key) async {
  await tester.ensureVisible(find.byKey(ValueKey(key)));
  await tester.tap(find.byKey(ValueKey(key)));
  await tester.pumpAndSettle(const Duration(milliseconds: 100), EnginePhase.sendSemanticsUpdate, const Duration(seconds: 20));
}

Future<void> tapText(WidgetTester tester, String text) async {
  await tester.tap(find.text(text).first);
  await tester.pumpAndSettle(const Duration(milliseconds: 100), EnginePhase.sendSemanticsUpdate, const Duration(seconds: 20));
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  final cfg = AppConfig.fromEnvironment();
  final api = HttpWebtoonApi(cfg);

  testWidgets('create and edit a world end to end', (tester) async {
    final title = 'Live test ${DateTime.now().millisecondsSinceEpoch}';
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          imagePickerProvider.overrideWithValue(
            () async => PickedImage(Uint8List.fromList(kTinyPng), 'face.png'),
          ),
        ],
        child: const WebtoonApp(),
      ),
    );
    await tester.pumpAndSettle(const Duration(milliseconds: 100), EnginePhase.sendSemanticsUpdate, const Duration(seconds: 20));

    // Tvořit → Nový svět.
    await tapText(tester, 'Tvořit');
    await tapKey(tester, 'new-world');
    await tester.enterText(
      find.byKey(const ValueKey('new-world-title')),
      title,
    );
    await tapKey(tester, 'new-world-create');
    final world = (await api.listWorlds()).singleWhere((w) => w.title == title);
    expect(world.ownerId, cfg.userId);

    // Basics + permissions.
    await tester.enterText(
      find.byKey(const ValueKey('world-synopsis')),
      'Podmořské město pod skleněnou kupolí.',
    );
    await tapText(tester, 'Pro děti');
    await tapKey(tester, 'preset-hassaku_soft');
    await tester.enterText(
      find.byKey(const ValueKey('perm-max-episodes')),
      '12',
    );
    await tapKey(tester, 'save-world');
    expect(find.text('Svět uložen.'), findsOneWidget);

    // Lore & kánon.
    await tapText(tester, 'Lore & kánon');
    await tapKey(tester, 'rule-add');
    await tester.enterText(
      find.byKey(const ValueKey('rule-0')),
      'Kupole se nesmí otevřít.',
    );
    await tapKey(tester, 'canon-add');
    await tester.enterText(
      find.byKey(const ValueKey('canon-text-0')),
      'Mira najde prasklinu v kupoli.',
    );
    await tapKey(tester, 'save-world');

    var w = await api.getWorld(world.id);
    expect(w.synopsis, 'Podmořské město pod skleněnou kupolí.');
    expect(w.audience, 'kids');
    expect(w.styleId, 'hassaku_soft');
    expect(w.rules, ['Kupole se nesmí otevřít.']);
    expect(w.canonNodes.single.text, 'Mira najde prasklinu v kupoli.');
    expect(w.canonNodes.single.id, isNotEmpty, reason: 'server assigns ids');

    // New character, manual tags, LLM tags (Czech error when the LLM is off), reference.
    await tapText(tester, 'Postavy');
    await tapKey(tester, 'new-character');
    await tester.enterText(find.byKey(const ValueKey('char-name')), 'Mira');
    await tapText(tester, 'Dívka');
    await tester.enterText(
      find.byKey(const ValueKey('char-description')),
      'Dívka s dlouhými modrými vlasy a žlutou potápěčskou kombinézou.',
    );
    await tapKey(tester, 'save-character');
    // Comma-separated input is split into chips (a second enterText into the same
    // just-cleared field is not delivered by the test text input).
    await tester.ensureVisible(find.byKey(const ValueKey('tag-add-field')));
    await tester.enterText(
      find.byKey(const ValueKey('tag-add-field')),
      'Blue_Hair, long hair',
    );
    await tapKey(tester, 'tag-add');
    expect(find.byKey(const ValueKey('tag-blue hair')), findsOneWidget);
    expect(find.byKey(const ValueKey('tag-long hair')), findsOneWidget);
    await tapKey(tester, 'save-character');
    await tapKey(tester, 'generate-tags');
    final tagsOk = find
        .textContaining('Tagy vygenerovány')
        .evaluate()
        .isNotEmpty;
    if (!tagsOk) expect(find.textContaining('LLM teď neběží'), findsOneWidget);
    debugPrint(
      'generate-tags: ${tagsOk ? 'tags returned' : 'LLM off message'}',
    );
    await tapKey(tester, 'upload-reference');

    w = await api.getWorld(world.id);
    final mira = w.characters.singleWhere((c) => c.name == 'Mira');
    expect(mira.countTag, '1girl');
    expect(mira.tagPrompt, 'blue hair, long hair');
    expect(mira.referenceImages, hasLength(1));

    // Location.
    await tester.pageBack();
    await tester.pumpAndSettle(const Duration(milliseconds: 100), EnginePhase.sendSemanticsUpdate, const Duration(seconds: 20));
    await tapText(tester, 'Lokace');
    await tapKey(tester, 'new-location');
    await tester.enterText(
      find.byKey(const ValueKey('loc-name')),
      'Korálový trh',
    );
    await tester.enterText(find.byKey(const ValueKey('loc-mood')), 'rušná');
    await tapKey(tester, 'save-location');
    await tapKey(tester, 'upload-reference');

    w = await api.getWorld(world.id);
    final trh = w.locations.singleWhere((l) => l.name == 'Korálový trh');
    expect(trh.referenceImages, hasLength(1));

    // Dashboard of a fresh world.
    await tester.pageBack();
    await tester.pumpAndSettle(const Duration(milliseconds: 100), EnginePhase.sendSemanticsUpdate, const Duration(seconds: 20));
    await tapText(tester, 'Přehled');
    expect(find.byKey(const ValueKey('dashboard')), findsOneWidget);
    debugPrint('live world: ${world.id}');
  });
}
