import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/models/episode.dart';
import 'package:webtoon/reader/bubble_layout.dart';
import 'package:webtoon/reader/bubble_painter.dart';
import 'package:webtoon/reader/panel_view.dart';

const narr = Bubble(text: 'Poštovní věž. Ticho.', kind: BubbleKind.narration);
Bubble talk(
  String t, {
  BubbleKind kind = BubbleKind.speech,
  String who = 'c_vesna',
  Offset? anchor,
}) => Bubble(speakerId: who, text: t, kind: kind, anchor: anchor);

bool overlaps(Rect a, Rect b) {
  final x = a.intersect(b);
  return x.width > 0.5 && x.height > 0.5;
}

void main() {
  const portrait = Size(800, 1169); // 832×1216 at width 800
  const s = 1.0;

  group('compose.py heuristic', () {
    test('narration is a box at the top-left, up to 80 % wide', () {
      final out = layoutBubbles(portrait, [narr]);
      expect(out, hasLength(1));
      final r = out.single.rect;
      expect(r.left, closeTo(22 * s, 0.01));
      expect(r.top, closeTo(22 * s, 0.01));
      expect(r.width, lessThanOrEqualTo(800 * 0.8 + 1));
      expect(out.single.tailTip, isNull);
    });

    test(
      'talk bubbles alternate top corners starting left; right column is 40 px lower',
      () {
        final out = layoutBubbles(portrait, [
          talk('Ahoj'),
          talk('Nazdar'),
          talk('Co je?'),
        ]);
        expect(out, hasLength(3));
        final a = out[0].rect, b = out[1].rect, c = out[2].rect;
        expect(a.left, closeTo(22, 0.01)); // left
        expect(b.right, closeTo(800 - 22, 0.01)); // right
        expect(c.left, closeTo(22, 0.01)); // left again, below the first
        expect(b.top - a.top, closeTo(40, 0.01));
        expect(c.top, greaterThan(a.bottom));
      },
    );

    test(
      'with narration the first talk bubble goes right, below the narration',
      () {
        final out = layoutBubbles(portrait, [
          narr,
          talk('Opět jen účty za uhlí...'),
        ]);
        final n = out.firstWhere((p) => p.kind == BubbleKind.narration).rect;
        final t = out.firstWhere((p) => p.kind == BubbleKind.speech).rect;
        expect(t.right, closeTo(800 - 22, 0.01));
        expect(t.top, greaterThanOrEqualTo(n.bottom));
      },
    );

    test('talk bubbles wrap at 62 % of the width', () {
      final long = talk(
        'Tohle je hodně dlouhá věta, která se určitě musí zalomit do několika řádků.',
      );
      final out = layoutBubbles(portrait, [long]);
      expect(out.single.rect.width, lessThanOrEqualTo(800 * 0.62 + 1));
      expect(out.single.rect.height, greaterThan(26 * 1.25 * 2)); // > 2 lines
    });

    test('indices point back into panel.bubbles regardless of kind order', () {
      final out = layoutBubbles(portrait, [talk('a'), narr, talk('b')]);
      expect(out.map((p) => p.index).toSet(), {0, 1, 2});
      expect(out.firstWhere((p) => p.index == 1).kind, BubbleKind.narration);
    });

    test('nothing overlaps and everything stays inside the panel', () {
      const landscape = Size(800, 547);
      final bubbles = [
        narr,
        talk('První věta.'),
        talk('Druhá, trochu delší věta.', kind: BubbleKind.shout),
        talk('Třetí?', kind: BubbleKind.thought),
        talk('Čtvrtá.'),
      ];
      for (final size in [portrait, landscape]) {
        final out = layoutBubbles(size, bubbles);
        final bounds = Offset.zero & size;
        for (final p in out) {
          expect(
            bounds.contains(p.rect.topLeft),
            isTrue,
            reason: '${p.rect} in $size',
          );
          expect(p.rect.right, lessThanOrEqualTo(size.width + 0.01));
          if (p.tailTip != null) expect(bounds.contains(p.tailTip!), isTrue);
        }
        if (size == portrait) {
          for (var i = 0; i < out.length; i++) {
            for (var j = i + 1; j < out.length; j++) {
              expect(
                overlaps(out[i].rect, out[j].rect),
                isFalse,
                reason: '${out[i].rect} vs ${out[j].rect}',
              );
            }
          }
        }
      }
    });

    test('default tail goes 48 px down and 40 px toward the panel centre', () {
      final out = layoutBubbles(portrait, [talk('vlevo'), talk('vpravo')]);
      final l = out[0], r = out[1];
      expect(l.tailBase!.dy, closeTo(l.rect.bottom, 0.01));
      expect(l.tailTip!.dy - l.rect.bottom, closeTo(48, 0.01));
      expect(l.tailTip!.dx - l.rect.center.dx, closeTo(40, 0.01));
      expect(r.tailTip!.dx - r.rect.center.dx, closeTo(-40, 0.01));
    });

    test('layout scales with the panel width (reference width 800)', () {
      final big = layoutBubbles(portrait, [narr, talk('Ahoj, jak se máš?')]);
      final small = layoutBubbles(
        Size(portrait.width / 2, portrait.height / 2),
        [narr, talk('Ahoj, jak se máš?')],
      );
      for (var i = 0; i < big.length; i++) {
        expect(small[i].rect.left * 2, closeTo(big[i].rect.left, 2));
        expect(small[i].rect.top * 2, closeTo(big[i].rect.top, 2));
        expect(small[i].rect.width * 2, closeTo(big[i].rect.width, 3));
        expect(
          small[i].style.fontSize! * 2,
          closeTo(big[i].style.fontSize!, 0.01),
        );
      }
    });

    test('shout uses a bigger font than speech (30 vs 26 px at 800)', () {
      final out = layoutBubbles(portrait, [
        talk('a'),
        talk('b', kind: BubbleKind.shout),
      ]);
      expect(out[0].style.fontSize, 26);
      expect(out[1].style.fontSize, 30);
      expect(out[1].style.fontFamily, 'DynaPuff');
      expect(out[0].style.fontFamily, 'Nunito');
    });
  });

  group('bbox path (characters[].bbox)', () {
    test('bubble avoids the speaker box and the tail aims at the head', () {
      // Speaker stands in the left half.
      const vesna = PanelCharacter(
        id: 'c_vesna',
        bbox: Rect.fromLTWH(0.02, 0.05, 0.45, 0.9),
      );
      final out = layoutBubbles(
        portrait,
        [talk('Kdo sem píše?')],
        characters: [vesna],
      );
      final b = out.single;
      // Without a bbox the first bubble would go left; the left corner covers the speaker.
      expect(b.rect.right, closeTo(800 - 22, 0.01));
      final box = Rect.fromLTWH(
        0.02 * 800,
        0.05 * 1169,
        0.45 * 800,
        0.9 * 1169,
      );
      // Tip points left toward the speaker and not further than 120 px from the base.
      expect(b.tailTip!.dx, lessThan(b.tailBase!.dx));
      expect((b.tailTip! - b.tailBase!).distance, lessThanOrEqualTo(120.01));
      final head = Offset(
        box.right - box.width * 0.25,
        box.top + box.height * 0.15,
      );
      final before = (b.tailBase! - head).distance;
      final after = (b.tailTip! - head).distance;
      expect(after, lessThan(before));
    });

    test('speaker on the right → bubble on the left', () {
      const kos = PanelCharacter(
        id: 'c_kos',
        bbox: Rect.fromLTWH(0.55, 0.0, 0.43, 1.0),
      );
      final out = layoutBubbles(
        portrait,
        [narr, talk('Pozor!', who: 'c_kos')],
        characters: [kos],
      );
      final t = out.firstWhere((p) => p.kind == BubbleKind.speech);
      expect(t.rect.left, closeTo(22, 0.01));
      expect(t.tailTip!.dx, greaterThan(t.tailBase!.dx));
    });

    test('explicit anchor wins', () {
      final out = layoutBubbles(portrait, [
        talk('Tady', anchor: const Offset(0.5, 0.9)),
      ]);
      final b = out.single;
      expect(b.tailTip!.dy, greaterThan(b.rect.bottom));
      final target = const Offset(400, 0.9 * 1169);
      expect(
        (b.tailTip! - target).distance,
        lessThan((b.tailBase! - target).distance),
      );
    });

    test('bbox parsing: list/map, normalized or pixels', () {
      expect(
        PanelCharacter.parseBbox([0.1, 0.2, 0.3, 0.4], 0, 0),
        const Rect.fromLTWH(0.1, 0.2, 0.3, 0.4),
      );
      final px = PanelCharacter.parseBbox(
        {'x': 83.2, 'y': 121.6, 'w': 416, 'h': 608},
        832,
        1216,
      )!;
      expect(px.left, closeTo(0.1, 1e-9));
      expect(px.top, closeTo(0.1, 1e-9));
      expect(px.width, closeTo(0.5, 1e-9));
      expect(PanelCharacter.parseBbox([10, 10, 50, 50], 0, 0), isNull);
      expect(PanelCharacter.parseBbox(null, 1, 1), isNull);
    });
  });

  group('shapes', () {
    test('every kind yields a closed path covering its box', () {
      for (final kind in BubbleKind.values) {
        final out = layoutBubbles(portrait, [talk('Ahoj světe', kind: kind)]);
        final path = bubblePath(out.single);
        final bounds = path.getBounds();
        expect(
          bounds.contains(out.single.rect.center),
          isTrue,
          reason: '$kind',
        );
        expect(path.contains(out.single.rect.center), isTrue, reason: '$kind');
        if (kind == BubbleKind.speech || kind == BubbleKind.shout) {
          // The tail is part of the outline.
          expect(
            bounds.bottom,
            greaterThan(out.single.rect.bottom + 20),
            reason: '$kind',
          );
        }
      }
    });
  });

  testWidgets(
    'PanelView renders bubbles and SFX over the image; long-press edits',
    (tester) async {
      int? edited;
      final panel = Panel.fromJson({
        'index': 0,
        'status': 'ready',
        'image_url': '/media/x.png',
        'width': 832,
        'height': 1216,
        'shot': 'medium',
        'gap_after': 'small',
        'bubbles': [
          {'speaker_id': null, 'text': 'Poštovní věž.', 'kind': 'narration'},
          {'speaker_id': 'c_vesna', 'text': 'Kdo sem píše?', 'kind': 'speech'},
        ],
        'sfx': [
          {'text': 'škrt', 'style': 'soft'},
        ],
        'characters': [],
      });
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: SizedBox(
                width: 400,
                child: PanelView(
                  panel: panel,
                  image: MemoryImage(_png),
                  onEditBubble: (i) => edited = i,
                ),
              ),
            ),
          ),
        ),
      );
      expect(find.text('Poštovní věž.'), findsOneWidget);
      expect(find.text('Kdo sem píše?'), findsOneWidget);
      expect(find.text('škrt'), findsNWidgets(2)); // stroke + fill
      final size = tester.getSize(find.byType(PanelView));
      expect(size.width / size.height, closeTo(832 / 1216, 0.01));
      await tester.longPress(find.text('Kdo sem píše?'));
      expect(edited, 1);
    },
  );

  testWidgets('bubble text fits its measured box under a Material theme', (
    tester,
  ) async {
    // Material's DefaultTextStyle carries letterSpacing; the bubble style must not inherit it.
    final panel = Panel.fromJson({
      'index': 0,
      'status': 'ready',
      'image_url': '/x',
      'width': 1216,
      'height': 832,
      'bubbles': [
        {
          'text': 'Poštovní věž. Ticho jen v šustění papíru.',
          'kind': 'narration',
        },
      ],
    });
    await tester.pumpWidget(
      MaterialApp(
        theme: ThemeData(
          textTheme: const TextTheme(bodyMedium: TextStyle(letterSpacing: 3)),
        ),
        home: Scaffold(
          body: SizedBox(
            width: 520,
            child: PanelView(panel: panel, image: MemoryImage(_png)),
          ),
        ),
      ),
    );
    final text = find.text('Poštovní věž. Ticho jen v šustění papíru.');
    final para = tester.renderObject<RenderParagraph>(text);
    final box = layoutBubbles(
      const Size(520, 520 * 832 / 1216),
      panel.bubbles,
    ).single;
    // Height the text really needs at the width it got must fit the measured box.
    final needed = para.getMaxIntrinsicHeight(para.size.width);
    expect(needed, lessThanOrEqualTo(box.textRect.height + 0.5));
  });

  testWidgets('failed panel shows a placeholder with regenerate', (
    tester,
  ) async {
    var regen = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: PanelView(
            panel: const Panel(index: 2, status: 'failed', shot: 'wide'),
            onRegenerate: () => regen++,
          ),
        ),
      ),
    );
    expect(find.text('Panel 3 se nepodařilo nakreslit'), findsOneWidget);
    await tester.tap(find.text('Vygenerovat znovu'));
    expect(regen, 1);
  });

  group('faces', () {
    // A close-up: the face fills the upper middle of the panel, where the corners used to go.
    const face = Rect.fromLTRB(0.2, 0.05, 0.8, 0.45);
    Rect px(Rect f) => Rect.fromLTRB(
      f.left * portrait.width,
      f.top * portrait.height,
      f.right * portrait.width,
      f.bottom * portrait.height,
    );

    test('bubbles keep off a face and stay in reading order', () {
      final out = layoutBubbles(
        portrait,
        [narr, talk('Kdo to řekl?'), talk('Já.', who: 'c_mia')],
        faces: const [face],
      );
      expect(out, hasLength(3));
      for (final p in out) {
        expect(overlaps(p.rect, px(face)), isFalse, reason: p.bubble.text);
      }
      for (var i = 1; i < out.length; i++) {
        expect(out[i].rect.top, greaterThanOrEqualTo(out[i - 1].rect.top));
        expect(overlaps(out[i].rect, out[i - 1].rect), isFalse);
      }
    });

    test('the tail aims at the face edge, not into it', () {
      final out = layoutBubbles(
        portrait,
        [talk('Ahoj!', who: 'nikdo')],
        faces: const [face],
      );
      final tip = out.single.tailTip!;
      expect(px(face).contains(tip), isFalse);
    });

    test('a small face far away leaves the top corners free', () {
      const far = Rect.fromLTRB(0.45, 0.7, 0.5, 0.75);
      final out = layoutBubbles(portrait, [talk('Haló?')], faces: const [far]);
      expect(out.single.rect.top, lessThan(60));
    });

    test('Panel.faces parses normalized boxes and skips junk', () {
      final p = Panel.fromJson({
        'index': 0,
        'faces': [
          [0.1, 0.2, 0.3, 0.4],
          [0.5],
          'x',
          [0.6, 0.6, 0.6, 0.9],
        ],
      });
      expect(p.faces, [const Rect.fromLTRB(0.1, 0.2, 0.3, 0.4)]);
      expect(Panel.fromJson({'index': 0}).faces, isEmpty);
    });
  });
}

final _png = Uri.parse(
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==',
).data!.contentAsBytes();
