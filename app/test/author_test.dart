import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/api/webtoon_api.dart';
import 'package:webtoon/app.dart';
import 'package:webtoon/author/world_editor_screen.dart';
import 'package:webtoon/config.dart';
import 'package:webtoon/models/world.dart';
import 'package:webtoon/providers/providers.dart';
import 'package:webtoon/services/image_picker.dart';

import 'fake_api.dart';

World authorWorld() => World(
  id: 'w_skyisles',
  ownerId: 'author',
  title: 'Nebeské ostrovy',
  synopsis: 'Létající ostrovy.',
  styleId: 'clean_webtoon',
  visibility: 'public',
  bible: const {'lore': 'keep me'},
  rules: const ['Kurýři nikdy neotevírají cizí dopisy.'],
  factions: const ['Poštovní cech'],
  canonNodes: const [
    CanonNode(id: 'c1', text: 'Vesna najde dopis.'),
    CanonNode(id: 'c2', text: 'Bouře dorazí.'),
  ],
  constraints: const ['Nikdo neumře.'],
  characters: const [
    Character(
      id: 'c_vesna',
      ownerId: 'author',
      name: 'Vesna',
      role: 'playable',
      countTag: '1girl',
      description: 'Zrzavá kurýrka',
      tagPrompt: 'orange hair, freckles',
    ),
  ],
  locations: const [
    Location(id: 'l_post', name: 'Poštovní věž'),
    Location(id: 'l_cliff', name: 'Bouřkový útes'),
  ],
);

FakeWebtoonApi authorApi() => FakeWebtoonApi(
  userId: 'author',
  worlds: [
    authorWorld(),
    const World(id: 'w_other', ownerId: 'someone', title: 'Cizí svět'),
  ],
);

Future<void> pumpApp(
  WidgetTester tester,
  FakeWebtoonApi api, {
  Widget? home,
  ImagePickerFn? picker,
}) async {
  tester.view.physicalSize = const Size(1200, 3200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        apiProvider.overrideWithValue(api),
        configProvider.overrideWithValue(
          const AppConfig(
            apiBase: 'http://t',
            userId: 'author',
            pollInterval: Duration(milliseconds: 100),
          ),
        ),
        if (picker != null) imagePickerProvider.overrideWithValue(picker),
      ],
      child: home == null ? const WebtoonApp() : MaterialApp(home: home),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> openEditor(
  WidgetTester tester,
  FakeWebtoonApi api, {
  ImagePickerFn? picker,
}) => pumpApp(
  tester,
  api,
  picker: picker,
  home: const WorldEditorScreen(worldId: 'w_skyisles'),
);

Future<void> openCharacter(
  WidgetTester tester,
  FakeWebtoonApi api, {
  ImagePickerFn? picker,
}) async {
  await openEditor(tester, api, picker: picker);
  await tester.tap(find.text('Postavy'));
  await tester.pumpAndSettle();
  await tester.tap(find.byKey(const ValueKey('edit-character-c_vesna')));
  await tester.pumpAndSettle();
}

Future<void> save(WidgetTester tester, String key) async {
  await tester.tap(find.byKey(ValueKey(key)));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets(
    'Tvořit lists my worlds; Nový svět creates one and opens the editor',
    (tester) async {
      final api = authorApi();
      await pumpApp(tester, api);
      await tester.tap(find.text('Tvořit'));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('my-world-w_skyisles')), findsOneWidget);
      expect(find.text('Cizí svět'), findsNothing);

      await tester.tap(find.byKey(const ValueKey('new-world')));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const ValueKey('new-world-title')),
        'Podmořské město',
      );
      await tester.tap(find.byKey(const ValueKey('new-world-create')));
      await tester.pumpAndSettle();
      expect(api.worlds.last.title, 'Podmořské město');
      expect(api.worlds.last.styleId, 'clean_webtoon');
      expect(api.worlds.last.ownerId, 'author');
      // Editor of the new world.
      expect(find.text('Lore & kánon'), findsOneWidget);
      expect(find.byKey(const ValueKey('world-title')), findsOneWidget);
    },
  );

  testWidgets('world editor saves basics, style and permissions', (
    tester,
  ) async {
    final api = authorApi();
    await openEditor(tester, api);
    await tester.enterText(
      find.byKey(const ValueKey('world-synopsis')),
      'Nová synopse',
    );
    await tester.tap(find.text('Pro děti'));
    await tester.tap(find.text('Soukromý'));
    await tester.tap(find.byKey(const ValueKey('preset-hassaku_soft')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('perm-create')));
    await tester.tap(find.byKey(const ValueKey('allowed-l_cliff')));
    await tester.enterText(
      find.byKey(const ValueKey('perm-max-episodes')),
      '12',
    );
    await save(tester, 'save-world');

    final (id, p) = api.worldPatches.single;
    expect(id, 'w_skyisles');
    expect(p['synopsis'], 'Nová synopse');
    expect(p['audience'], 'kids');
    expect(p['visibility'], 'private');
    expect(p['style_id'], 'hassaku_soft');
    expect(p['permissions'], {
      'can_add_characters': false,
      'can_create_character': true,
      'can_change_location': false,
      'allowed_locations': ['l_cliff'],
      'max_episodes': 12,
    });
    // bible keys the editor does not know are preserved.
    expect((p['bible'] as Map)['lore'], 'keep me');
    expect(find.text('Svět uložen.'), findsOneWidget);
  });

  testWidgets('lore & canon: rules, factions, reorder nodes, constraints', (
    tester,
  ) async {
    final api = authorApi();
    await openEditor(tester, api);
    await tester.tap(find.text('Lore & kánon'));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('rule-add')));
    await tester.pump();
    await tester.enterText(
      find.byKey(const ValueKey('rule-1')),
      'Krystaly drží ostrovy.',
    );
    await tester.tap(find.byKey(const ValueKey('faction-add')));
    await tester.pump();
    await tester.enterText(
      find.byKey(const ValueKey('faction-1')),
      'Strážci krystalů',
    );
    // Move "Vesna najde dopis." below "Bouře dorazí.", then add a new node.
    await tester.tap(find.byKey(const ValueKey('canon-down-0')));
    await tester.pump();
    expect(
      tester
          .widget<TextField>(find.byKey(const ValueKey('canon-text-0')))
          .controller!
          .text,
      'Bouře dorazí.',
    );
    await tester.tap(find.byKey(const ValueKey('canon-add')));
    await tester.pump();
    await tester.enterText(
      find.byKey(const ValueKey('canon-text-2')),
      'Finále na útesu.',
    );
    await tester.tap(find.byKey(const ValueKey('constraint-remove-0')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('constraint-add')));
    await tester.pump();
    await tester.enterText(
      find.byKey(const ValueKey('constraint-0')),
      'Žádné násilí.',
    );
    await save(tester, 'save-world');

    final p = api.worldPatches.single.$2;
    expect((p['bible'] as Map)['rules'], [
      'Kurýři nikdy neotevírají cizí dopisy.',
      'Krystaly drží ostrovy.',
    ]);
    expect((p['bible'] as Map)['factions'], [
      'Poštovní cech',
      'Strážci krystalů',
    ]);
    expect(p['canon'], {
      'nodes': [
        {'id': 'c2', 'text': 'Bouře dorazí.'},
        {'id': 'c1', 'text': 'Vesna najde dopis.'},
        {'text': 'Finále na útesu.'},
      ],
      'constraints': ['Žádné násilí.'],
    });
    // The fake assigned an id to the new node; the editor shows the saved order.
    expect(api.worlds.first.canonNodes.map((n) => n.id), ['c2', 'c1', 'n1']);
  });

  testWidgets('character: generate tags, edit chips, save tag_prompt', (
    tester,
  ) async {
    final api = authorApi();
    await openCharacter(tester, api);
    expect(find.byKey(const ValueKey('tag-orange hair')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('generate-tags')));
    await tester.pumpAndSettle();
    expect(api.tagRequests, ['c_vesna']);
    expect(find.byKey(const ValueKey('tag-green eyes')), findsOneWidget);
    expect(find.byKey(const ValueKey('dropped-copper boots')), findsOneWidget);

    // Remove a chip, re-add a dropped one, add a new one.
    await tester.tap(find.byKey(const ValueKey('tag-delete-short hair')));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('dropped-copper boots')));
    await tester.pump();
    await tester.enterText(
      find.byKey(const ValueKey('tag-add-field')),
      'Goggles_On_Head',
    );
    await tester.tap(find.byKey(const ValueKey('tag-add')));
    await tester.pump();
    await save(tester, 'save-character');

    final (_, cid, patch) = api.characterPatches.single;
    expect(cid, 'c_vesna');
    expect(
      patch['tag_prompt'],
      'orange hair, green eyes, copper boots, goggles on head',
    );
    expect(patch['identity_level'], 'prompt');
    expect(patch['ip_adapter'], isNull);
    expect(
      api.worlds.first.character('c_vesna')!.tagPrompt,
      'orange hair, green eyes, copper boots, goggles on head',
    );
  });

  testWidgets('LLM off schedule shows the Czech message', (tester) async {
    final api = authorApi()
      ..tagError = ApiException(
        czechError('llm unavailable', 503),
        statusCode: 503,
      );
    await openCharacter(tester, api);
    await tester.tap(find.byKey(const ValueKey('generate-tags')));
    await tester.pumpAndSettle();
    expect(find.textContaining('LLM teď neběží'), findsOneWidget);
  });

  testWidgets('character sheet: progress, waiting, results, best → reference', (
    tester,
  ) async {
    final api = authorApi();
    await openCharacter(tester, api);
    await tester.tap(find.byKey(const ValueKey('generate-sheet')));
    await tester.pump();
    await tester.pump();
    expect(find.text('Ve frontě (0/4)'), findsOneWidget);
    expect(find.byKey(const ValueKey('sheet-waiting')), findsOneWidget);

    await tester.pump(
      const Duration(milliseconds: 120),
    ); // poll 1: still queued
    await tester.pump(const Duration(milliseconds: 120)); // poll 2: rendering
    expect(find.text('Kreslí se 2/4'), findsOneWidget);
    expect(find.byKey(const ValueKey('sheet-image-1')), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 120)); // poll 3: ready
    await tester.pumpAndSettle();
    expect(find.text('Hotovo: 4 variant'), findsOneWidget);
    expect(find.text('nejlepší'), findsOneWidget);
    expect(find.text('shoda 90 %'), findsOneWidget);
    // Best image became the character's reference.
    expect(api.worlds.first.character('c_vesna')!.referenceImages, [
      'characters/w_skyisles/c_vesna/sheet_sh_1_2.png',
    ]);
    expect(find.byKey(const ValueKey('ref-0')), findsOneWidget);
    final fetches = api.sheetFetches;
    await tester.pump(const Duration(milliseconds: 500));
    expect(api.sheetFetches, fetches, reason: 'polling stops when ready');
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('reference upload, make main, remove', (tester) async {
    final api = authorApi();
    var n = 0;
    await openCharacter(
      tester,
      api,
      picker: () async =>
          PickedImage(Uint8List.fromList(kTinyPng), 'face${n++}.png'),
    );
    await tester.tap(find.byKey(const ValueKey('upload-reference')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('upload-reference')));
    await tester.pumpAndSettle();
    expect(api.uploads.map((u) => u.$3), ['face0.png', 'face1.png']);
    expect(find.byKey(const ValueKey('ref-1')), findsOneWidget);
    final refs = api.worlds.first.character('c_vesna')!.referenceImages;

    await tester.tap(find.byKey(const ValueKey('ref-first-1')));
    await tester.pumpAndSettle();
    expect(api.characterPatches.last.$3['reference_images'], [
      refs[1],
      refs[0],
    ]);
    await tester.tap(find.byKey(const ValueKey('ref-remove-0')));
    await tester.pumpAndSettle();
    expect(api.characterPatches.last.$3['reference_images'], [refs[0]]);
    expect(find.byKey(const ValueKey('ref-1')), findsNothing);
  });

  testWidgets('too large reference is rejected client-side', (tester) async {
    final api = authorApi();
    await openCharacter(
      tester,
      api,
      picker: () async =>
          PickedImage(Uint8List(maxReferenceBytes + 1), 'big.png'),
    );
    await tester.tap(find.byKey(const ValueKey('upload-reference')));
    await tester.pumpAndSettle();
    expect(api.uploads, isEmpty);
    expect(find.text('Soubor je moc velký (max. 8 MiB).'), findsOneWidget);
  });

  testWidgets('identity level ip_adapter sends IP-Adapter settings', (
    tester,
  ) async {
    final api = authorApi();
    await openCharacter(tester, api);
    expect(find.byKey(const ValueKey('ip-preset')), findsNothing);
    await tester.tap(find.text('IP-Adapter'));
    await tester.pump();
    await tester.tap(find.byKey(const ValueKey('ip-preset')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('PLUS FACE (portraits)').last);
    await tester.pumpAndSettle();
    await save(tester, 'save-character');
    final patch = api.characterPatches.single.$3;
    expect(patch['identity_level'], 'ip_adapter');
    expect(patch['ip_adapter'], {
      'preset': 'PLUS FACE (portraits)',
      'weight': 0.6,
      'end_at': 0.8,
    });
  });

  testWidgets('new character and delete', (tester) async {
    final api = authorApi();
    await openEditor(tester, api);
    await tester.tap(find.text('Postavy'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('new-character')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('generate-tags')), findsNothing);
    await tester.enterText(find.byKey(const ValueKey('char-name')), 'Otto');
    await tester.tap(find.text('Chlapec'));
    await tester.enterText(
      find.byKey(const ValueKey('char-description')),
      'Starý strážce majáku',
    );
    await save(tester, 'save-character');
    final otto = api.worlds.first.characters.last;
    expect(otto.name, 'Otto');
    expect(otto.countTag, '1boy');
    expect(otto.role, 'npc');
    // Now saved: generation and references are available.
    expect(find.byKey(const ValueKey('generate-tags')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('delete-character')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('confirm-dialog')));
    await tester.pumpAndSettle();
    expect(api.deleted, [otto.id]);
    expect(find.byKey(ValueKey('edit-character-${otto.id}')), findsNothing);
  });

  testWidgets('location: edit, generate tags, upload reference', (
    tester,
  ) async {
    final api = authorApi();
    await openEditor(
      tester,
      api,
      picker: () async =>
          PickedImage(Uint8List.fromList(kTinyPng), 'tower.jpg'),
    );
    await tester.tap(find.text('Lokace'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('edit-location-l_post')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const ValueKey('loc-mood')), 'útulná');
    await tester.tap(find.byKey(const ValueKey('generate-loc-tags')));
    await tester.pumpAndSettle();
    expect(
      find.byKey(const ValueKey('dropped-letter shelves')),
      findsOneWidget,
    );
    await save(tester, 'save-location');
    final (_, lid, patch) = api.locationPatches.single;
    expect(lid, 'l_post');
    expect(patch['mood'], 'útulná');
    expect(patch['tag_prompt'], 'indoors, wooden floor, window');

    await tester.tap(find.byKey(const ValueKey('upload-reference')));
    await tester.pumpAndSettle();
    expect(api.uploads.single.$2, 'l_post');
    expect(api.worlds.first.location('l_post')!.referenceImages, hasLength(1));
  });

  testWidgets('dashboard renders stats', (tester) async {
    final api = authorApi()
      ..statsJson = {
        'campaigns': 3,
        'players': 2,
        'episodes': 7,
        'episodes_ready': 6,
        'episodes_failed': 1,
        'panels_ready': 40,
        'player_created_characters': 1,
        'choices': {
          'by_kind': {'closed': 3, 'free': 1},
          'by_choice': {'c1': 2, 'c2': 1, 'free': 1},
        },
        'stopped_at': [
          {'episode': 1, 'campaigns': 1},
          {'episode': 3, 'campaigns': 2},
        ],
        'choices_by_episode': [
          {
            'episode': 1,
            'total': 2,
            'choices': {'c1': 1, 'free': 1},
          },
          {
            'episode': 2,
            'total': 2,
            'choices': {'c1': 1, 'c2': 1},
          },
        ],
        'canon_reached': {'c1': 2},
        'player_created': [
          {
            'id': 'c_p',
            'name': 'Bára',
            'owner_id': 'p1',
            'description': 'pilotka',
          },
        ],
      };
    await openEditor(tester, api);
    await tester.tap(find.text('Přehled'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('dashboard')), findsOneWidget);
    expect(find.text('Kampaně'), findsOneWidget);
    expect(find.text('40'), findsOneWidget);
    expect(find.text('3. díl'), findsOneWidget);
    expect(find.text('Po 1. dílu (2×)'), findsOneWidget);
    expect(find.text('volný text'), findsOneWidget);
    expect(find.text('Vesna najde dopis.'), findsOneWidget);
    expect(find.text('Bára'), findsOneWidget);
    expect(find.textContaining('uzavřené volby 3×'), findsOneWidget);
  });

  testWidgets('Zahraj si vlastní svět starts a normal campaign', (
    tester,
  ) async {
    final api = authorApi();
    await openEditor(tester, api);
    await tester.tap(find.byKey(const ValueKey('play-own')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('confirm-start')));
    for (var i = 0; i < 10; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    expect(api.campaigns.values.single.worldId, 'w_skyisles');
    expect(api.campaigns.values.single.playerId, 'author');
    expect(find.text('Díl čeká ve frontě…'), findsOneWidget);
    await tester.pumpWidget(const SizedBox());
  });

  testWidgets('world detail shows "Upravit" only to the owner', (tester) async {
    final api = authorApi();
    await pumpApp(tester, api);
    await tester.tap(find.byKey(const ValueKey('world-w_skyisles')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('edit-world')), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('edit-world')));
    await tester.pumpAndSettle();
    expect(find.text('Lore & kánon'), findsOneWidget);
  });
}
