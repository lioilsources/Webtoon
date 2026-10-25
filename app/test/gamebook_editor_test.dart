// Studio's gamebook graph editor over the fake API: edit a node, add one, keep drawn nodes.

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/author/gamebook_editor_screen.dart';
import 'package:webtoon/models/gamebook_graph.dart';

import 'author_test.dart' show pumpApp;
import 'fake_api.dart';

FakeWebtoonApi graphApi() {
  final api = FakeWebtoonApi(userId: 'author');
  api.gamebooks['sara'] = GamebookDoc(
    id: 'sara',
    graph: {
      'schema': 1,
      'id': 'sara',
      'title': 'Sára a černá koruna',
      'start': 'a',
      'nodes': {
        'a': {
          'title': 'Koruna',
          'location': 'l_bedroom',
          'beats': ['Noc v pokoji.'],
          'choices': [
            {'id': 'go', 'text': 'Do města', 'to': 'b'},
          ],
        },
        'b': {
          'title': 'Město',
          'location': 'l_city',
          'beats': ['Lucerny zhasínají.'],
          'ending': 'good',
        },
      },
    },
    drawn: const {'a': true, 'b': false},
    characters: const [NamedId('sara', 'Sára')],
    locations: const [
      NamedId('l_bedroom', 'Ložnice'),
      NamedId('l_city', 'Město duchů'),
    ],
    drawCommand: 'python3 m0/gamebook.py write …',
  );
  return api;
}

void main() {
  testWidgets('edit a node and save the graph', (tester) async {
    final api = graphApi();
    await pumpApp(tester, api, home: const GamebooksScreen());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('gamebook-graph-sara')));
    await tester.pumpAndSettle();
    expect(find.text('nakresleno'), findsOneWidget);
    expect(find.text('ke kreslení'), findsOneWidget);
    expect(find.byKey(const ValueKey('graph-draw')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('graph-node-b')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('node-title')),
      'Zhasínající město',
    );
    await tester.tap(find.byKey(const ValueKey('node-add-beat')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('node-beat-1')),
      'Sára: Kde jsou všichni?',
    );
    await tester.tap(find.byKey(const ValueKey('node-done')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('graph-save')));
    await tester.pumpAndSettle();

    final b = (api.savedGraphs.single['nodes'] as Map)['b'] as Map;
    expect(b['title'], 'Zhasínající město');
    expect(b['beats'], ['Lucerny zhasínají.', 'Sára: Kde jsou všichni?']);
    expect(b['ending'], 'good');
  });

  testWidgets(
    'a new node keeps the book order; a drawn node cannot be deleted',
    (tester) async {
      final api = graphApi();
      await pumpApp(
        tester,
        api,
        home: const GraphEditorScreen(gamebookId: 'sara'),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('graph-new-node')));
      await tester.pumpAndSettle();
      await tester.enterText(find.byKey(const ValueKey('graph-node-id')), 'c');
      await tester.tap(find.byKey(const ValueKey('graph-node-create')));
      await tester.pumpAndSettle();
      // the node editor opened on c: a new node may go
      expect(find.byKey(const ValueKey('node-delete')), findsOneWidget);
      await tester.tap(find.byKey(const ValueKey('node-done')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('graph-node-a')));
      await tester.pumpAndSettle();
      expect(find.byKey(const ValueKey('node-delete')), findsNothing);
      await tester.tap(find.byKey(const ValueKey('node-done')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('graph-save')));
      await tester.pumpAndSettle();
      expect((api.savedGraphs.single['nodes'] as Map).keys, ['a', 'b', 'c']);
    },
  );
}
