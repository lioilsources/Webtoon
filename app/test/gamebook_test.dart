// Gamebooks: gamebook.json parsing and conditions, the reader's path (flags, back, retry),
// own branches, the pack store keeping nodes out of the library, and the reader screen
// walking a fixture graph over the fixture pack's episodes.

import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:visibility_detector/visibility_detector.dart';
import 'package:webtoon/api/local_webtoon_api.dart';
import 'package:webtoon/gamebook/gamebook.dart';
import 'package:webtoon/gamebook/gamebook_screen.dart';
import 'package:webtoon/gamebook/gamebook_state.dart';
import 'package:webtoon/models/episode.dart';
import 'package:webtoon/packs/pack_bootstrap.dart';
import 'package:webtoon/packs/pack_store.dart';
import 'package:webtoon/providers/language_provider.dart';
import 'package:webtoon/providers/providers.dart';
import 'package:webtoon/shop/catalog.dart';
import 'package:webtoon/shop/entitlements.dart';
import 'package:webtoon/shop/update_banner.dart';

import 'fake_api.dart' show kTinyPng;
import 'pack_fixture.dart';
import 'shop_fakes.dart';

/// a → b (sets key) → back to a, where "open" (if key) leads to the good ending;
/// "trap" is a retry ending back to a.
Map<String, dynamic> graphJson() => {
  'schema': 1,
  'id': 'test',
  'title': 'Zkušební kniha',
  'start': 'a',
  'order': ['a', 'b', 'win', 'trap'],
  'flags': ['key'],
  'endings': 1,
  'nodes': {
    'a': {
      'story': 'cp_sova',
      'episode': 'ep_s1',
      'title': 'Rozcestí',
      'choices': [
        {'id': 'to_b', 'text': 'Do sklepa', 'to': 'b'},
        {'id': 'open', 'text': 'Odemknout dveře', 'to': 'win', 'if': 'key'},
        {'id': 'jump', 'text': 'Skočit do jámy', 'to': 'trap', 'if': 'not key'},
      ],
      'sets': [],
    },
    'b': {
      'story': 'cp_jezek',
      'episode': 'ep_j2',
      'title': 'Sklep',
      'choices': [
        {'id': 'back', 'text': 'Zpátky nahoru', 'to': 'a'},
      ],
      'sets': ['key'],
    },
    'win': {
      'story': 'cp_jezek',
      'episode': 'ep_j1',
      'title': 'Za dveřmi',
      'choices': [],
      'sets': [],
      'ending': 'good',
    },
    'trap': {
      'story': 'cp_jezek',
      'episode': 'ep_j2',
      'title': 'Jáma',
      'choices': [],
      'sets': [],
      'ending': 'retry',
      'retry_to': 'a',
    },
  },
  'lore': {
    'characters': [
      {'id': 'jezek', 'name': 'Ježek', 'description': 'a hedgehog'},
    ],
    'locations': [],
    'rules': [],
  },
};

class MemoryGamebookRepository extends GamebookRepository {
  final progress = <String, GamebookProgress>{};
  final branches = <String, GamebookBranches>{};

  @override
  Future<GamebookProgress?> loadProgress(String id) async => progress[id];

  @override
  Future<void> saveProgress(String id, GamebookProgress pr) async =>
      progress[id] = pr;

  @override
  Future<GamebookBranches> loadBranches(String id) async =>
      branches[id] ?? const GamebookBranches();

  @override
  Future<void> saveBranches(String id, GamebookBranches b) async =>
      branches[id] = b;
}

void main() {
  final g = Gamebook.parse(graphJson(), packId: 'gamebook-test');

  group('gamebook.json', () {
    test('parses nodes, endings and lore', () {
      expect(g.start, 'a');
      expect(g.order, ['a', 'b', 'win', 'trap']);
      expect(g.node('win')!.ending, GamebookEnding.good);
      expect(g.node('trap')!.retryTo, 'a');
      expect(g.node('a')!.choices[1].condition, 'key');
      expect(g.lore.character('jezek')!.name, 'Ježek');
    });

    test('refuses an unknown target', () {
      final j = graphJson();
      ((j['nodes'] as Map)['b'] as Map)['choices'] = [
        {'id': 'x', 'text': 'X', 'to': 'nowhere'},
      ];
      expect(
        () => Gamebook.parse(j, packId: 'p'),
        throwsA(isA<FormatException>()),
      );
    });

    test('conditions', () {
      expect(evalCondition('', {}), isTrue);
      expect(evalCondition('key', {'key'}), isTrue);
      expect(evalCondition('not key', {'key'}), isFalse);
      expect(evalCondition('a or b', {'b'}), isTrue);
      expect(evalCondition('a and b', {'b'}), isFalse);
      expect(evalCondition('a and b or c', {'c'}), isTrue);
    });
  });

  group('progress', () {
    test('flags come from the path; back and retry drop them again', () {
      var pr = GamebookProgress.start(g);
      expect(pr.flags(g), isEmpty);
      pr = pr.go('b').go('a');
      expect(pr.flags(g), {'key'});
      expect(pr.back().node, 'b');
      expect(pr.back().flags(g), isEmpty);
      // trap from the first visit of a: back at a, before b set the key
      final trapped = GamebookProgress.start(g).go('trap');
      final retried = trapped.retry('a');
      expect(retried.node, 'a');
      expect(retried.path, isEmpty);
      expect(retried.visited, containsAll(['a', 'trap']));
    });

    test('restart keeps visited nodes and found endings; json round trip', () {
      final pr = GamebookProgress.start(
        g,
      ).go('b').go('a').go('win').found('win');
      final again = pr.restart(g);
      expect(again.node, 'a');
      expect(again.path, isEmpty);
      expect(again.endingsFound, {'win'});
      final back = GamebookProgress.fromJson(
        jsonDecode(jsonEncode(pr.toJson())) as Map<String, dynamic>,
      );
      expect(back.node, 'win');
      expect(back.path, ['a', 'b', 'a']);
      expect(back.endingsFound, {'win'});
    });
  });

  test('nodes an update adds are new until visited', () {
    final v1 = GamebookProgress.start(g);
    final j = graphJson();
    (j['order'] as List).add('extra');
    (j['nodes'] as Map)['extra'] = {
      'story': 'cp_jezek',
      'episode': 'ep_j2',
      'title': 'Nová kapitola',
      'choices': [],
      'sets': [],
      'ending': 'good',
    };
    ((j['nodes'] as Map)['b'] as Map)['choices'] = [
      {'id': 'back', 'text': 'Zpátky nahoru', 'to': 'a'},
      {'id': 'more', 'text': 'Dál do tmy', 'to': 'extra'},
    ];
    final g2 = Gamebook.parse(j, packId: 'gamebook-test');
    expect(v1.newNodes(g2), ['extra']);
    expect(v1.go('b').go('extra').newNodes(g2), isEmpty);
    // progress from before known_nodes: nothing is new, then it is pinned to the book
    const legacy = GamebookProgress(node: 'a', visited: {'a'});
    expect(legacy.newNodes(g2), isEmpty);
    expect(legacy.withKnown(g).newNodes(g2), ['extra']);
  });

  group('branches', () {
    test('hooks, removal and export', () {
      var b = const GamebookBranches();
      final id = b.newNodeId();
      expect(id, 'my_1');
      b = b
          .putNode(
            BranchNode(
              id: id,
              title: 'Tajná chodba',
              panels: const [
                BranchPanel(
                  episodeId: 'ep_j1',
                  panelIndex: 1,
                  bubbles: [Bubble(speakerId: 'jezek', text: 'Psst!')],
                ),
              ],
              choices: const [GamebookChoice(id: 'c1', text: 'Ven', to: 'a')],
            ),
          )
          .addHook(
            BranchHook(
              fromNode: 'b',
              choice: GamebookChoice(id: 'c_$id', text: 'Prozkoumat', to: id),
            ),
          );
      expect(b.newNodeId(), 'my_2');
      expect(b.hooksAt('b').single.to, 'my_1');
      final round = GamebookBranches.fromJson(
        jsonDecode(jsonEncode(b.toJson())) as Map<String, dynamic>,
      );
      expect(round.node('my_1')!.panels.single.bubbles.single.text, 'Psst!');
      final export = jsonDecode(b.exportFor(g, version: 2)) as Map;
      expect(export['gamebook'], 'test');
      expect(export['gamebook_version'], 2);
      final gone = b.removeNode('my_1');
      expect(gone.nodes, isEmpty);
      expect(gone.hooks, isEmpty);
    });
  });

  group('catalog', () {
    final catalog = Catalog.parse({
      'schema': 2,
      'version': 9,
      'base_urls': {
        'pages': 'https://p.example',
        'releases': 'https://r.example',
      },
      'types': [],
      'packs': [],
      'bundles': [
        {
          'id': 'bundle_all',
          'product_id': 'bundle_all',
          'price_tier': 'bundle_all',
          'title_i18n': {},
          'covers': 'all',
        },
      ],
      'gamebooks': [
        {
          'id': 'sara',
          'product_id': 'gamebook_sara',
          'kit_product_id': 'kit_sara',
          'type': 'kids',
          'title': 'Sára a černá koruna',
          'audience': 'kids',
          'status': 'ready',
          'version': 1,
          'nodes': 10,
          'endings': 2,
          'bytes': 1000,
          'parts': [
            {
              'release': 'gamebook-sara-v1',
              'asset': 'gamebook-sara.zip',
              'bytes': 1000,
              'sha256': 'ab',
            },
          ],
        },
        {'id': 'drak', 'product_id': 'gamebook_drak', 'status': 'planned'},
      ],
      'stories': [],
    });

    test(
      'a ready gamebook is a pack for the store; bundles do not unlock it',
      () {
        final sara = catalog.gamebooks.first;
        expect(sara.ready, isTrue);
        expect(catalog.gamebooks.last.ready, isFalse);
        final pack = sara.asPack();
        expect(pack.id, 'gamebook-sara');
        expect(pack.parts.single.asset, 'gamebook-sara.zip');
        Entitlements owns(String p) =>
            Entitlements({p: Receipt(productId: p, grantedAt: DateTime(2026))});
        expect(owns('bundle_all').unlocksPack(catalog, pack), isFalse);
        expect(owns('gamebook_sara').unlocksPack(catalog, pack), isTrue);
        expect(owns('gamebook_sara').unlocksKit(sara), isFalse);
        expect(owns('kit_sara').unlocksPack(catalog, pack), isTrue);
        expect(owns('kit_sara').unlocksKit(sara), isTrue);
        expect(
          const Entitlements().packsOfProduct(catalog, 'kit_sara').single.id,
          'gamebook-sara',
        );
      },
    );
  });

  testWidgets('library banner offers an update of an older installed version', (
    tester,
  ) async {
    final installer = FakeInstaller()..outdated.add('gamebook-sara');
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          deviceLanguageProvider.overrideWithValue(null),
          ...shopOverrides(
            catalog: Catalog.parse({
              'schema': 2,
              'version': 11,
              'base_urls': {
                'pages': 'https://p.example',
                'releases': 'https://r.example',
              },
              'types': [],
              'packs': [],
              'bundles': [],
              'gamebooks': [
                {
                  'id': 'sara',
                  'title': 'Sára a černá koruna',
                  'free': true,
                  'status': 'ready',
                  'version': 2,
                  'parts': [
                    {
                      'release': 'gamebook-sara-v2',
                      'asset': 'gamebook-sara.zip',
                      'bytes': 10,
                      'sha256': 'ab',
                    },
                  ],
                },
              ],
              'stories': [],
            }),
            installer: installer,
          ),
        ],
        child: const MaterialApp(home: Scaffold(body: UpdateBanner())),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Sára a černá koruna'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('update-all')));
    await tester.pumpAndSettle();
    expect(installer.downloads, ['gamebook-sara']);
    expect(find.byKey(const ValueKey('update-banner')), findsNothing);
  });

  group('pack store', () {
    late PackStore store;
    late Directory tmp;

    setUpAll(() async {
      tmp = Directory.systemTemp.createTempSync('webtoon_gamebook_');
      store = PackStore(root: Directory('${tmp.path}/packs'));
      await store.installFromBytes(gamebookZip());
      await store.installFromFile(writeFixtureZip(tmp).path);
    });

    tearDownAll(() => tmp.deleteSync(recursive: true));

    test('nodes are not library stories; the gamebook is listed', () {
      expect(store.gamebooks.single.id, 'test');
      expect(store.gamebook('test')!.packId, 'gamebook-test');
      // the fixture pack's stories once (from the plain pack), none from the gamebook pack
      expect(store.stories.where((s) => s.packId == 'gamebook-test'), isEmpty);
      expect(store.stories.map((s) => s.packId).toSet(), {'fixture'});
      expect(
        store.gamebookStory(store.gamebooks.single, 'cp_sova')?.packId,
        'gamebook-test',
      );
    });
  });

  group('reader screen', () {
    late PackStore store;
    late Directory tmp;

    setUpAll(() async {
      tmp = Directory.systemTemp.createTempSync('webtoon_gamebook_ui_');
      store = PackStore(root: Directory('${tmp.path}/packs'));
      await store.installFromBytes(gamebookZip());
      VisibilityDetectorController.instance.updateInterval = Duration.zero;
    });

    tearDownAll(() => tmp.deleteSync(recursive: true));

    Widget app(MemoryGamebookRepository repo, Widget home) => ProviderScope(
      overrides: [
        packStoreProvider.overrideWithValue(store),
        apiProvider.overrideWithValue(LocalWebtoonApi(store)),
        packBootstrapProvider.overrideWith((ref) => PackBootstrap.ready(store)),
        deviceLanguageProvider.overrideWithValue(null),
        gamebookRepositoryProvider.overrideWithValue(repo),
        ...shopOverrides(),
      ],
      child: MaterialApp(home: home),
    );

    Future<void> show(WidgetTester tester, Finder f) async {
      await tester.scrollUntilVisible(
        f,
        300,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.ensureVisible(f);
      await tester.pumpAndSettle();
    }

    Future<void> tapChoice(WidgetTester tester, String id) async {
      final f = find.byKey(ValueKey('gamebook-choice-$id'));
      await show(tester, f);
      await tester.tap(f);
      await tester.pumpAndSettle();
    }

    testWidgets('choices follow the flags; the good ending counts', (
      tester,
    ) async {
      final repo = MemoryGamebookRepository();
      await tester.pumpWidget(
        app(repo, const GamebookScreen(gamebookId: 'test')),
      );
      await tester.pumpAndSettle();
      await show(tester, find.byKey(const ValueKey('gamebook-choice-to_b')));
      expect(find.byKey(const ValueKey('gamebook-choice-open')), findsNothing);
      expect(
        find.byKey(const ValueKey('gamebook-choice-jump')),
        findsOneWidget,
      );
      await tapChoice(tester, 'to_b');
      expect(repo.progress['test']!.node, 'b');
      await tapChoice(tester, 'back');
      expect(find.byKey(const ValueKey('gamebook-choice-jump')), findsNothing);
      await tapChoice(tester, 'open');
      await show(tester, find.byKey(const ValueKey('gamebook-endings')));
      await tester.pumpAndSettle();
      expect(find.text('Nalezené konce: 1 z 1'), findsOneWidget);
      expect(repo.progress['test']!.endingsFound, {'win'});
    });

    testWidgets('a retry ending goes back; an own branch hooks into a node', (
      tester,
    ) async {
      final repo = MemoryGamebookRepository()
        ..branches['test'] = GamebookBranches(
          nodes: const [BranchNode(id: 'my_1', title: 'Moje chodba')],
          hooks: const [
            BranchHook(
              fromNode: 'a',
              choice: GamebookChoice(
                id: 'mine',
                text: 'Tajná chodba',
                to: 'my_1',
              ),
            ),
          ],
        );
      await tester.pumpWidget(
        app(repo, const GamebookScreen(gamebookId: 'test')),
      );
      await tester.pumpAndSettle();
      await tapChoice(tester, 'jump');
      await show(tester, find.byKey(const ValueKey('gamebook-retry')));
      await tester.tap(find.byKey(const ValueKey('gamebook-retry')));
      await tester.pumpAndSettle();
      expect(repo.progress['test']!.node, 'a');
      await tapChoice(tester, 'mine');
      expect(find.text('Moje chodba'), findsOneWidget);
      expect(find.text('Konec tvé větve'), findsOneWidget);
    });
  });
}

/// The fixture pack re-id'd as a gamebook pack, with gamebook.json next to pack.json.
Uint8List gamebookZip() {
  final manifest = fixtureManifest(id: 'gamebook-test');
  final a = Archive();
  a.addFile(ArchiveFile.string('pack.json', jsonEncode(manifest)));
  a.addFile(ArchiveFile.string('gamebook.json', jsonEncode(graphJson())));
  for (final path in mediaPaths(manifest)) {
    a.addFile(ArchiveFile.bytes(path, kTinyPng));
  }
  return ZipEncoder().encodeBytes(a);
}
