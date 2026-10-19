import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/config.dart';
import 'package:webtoon/i18n/languages.dart';
import 'package:webtoon/models/episode.dart';
import 'package:webtoon/providers/language_provider.dart';
import 'package:webtoon/providers/providers.dart';
import 'package:webtoon/reader/bubble_layout.dart';
import 'package:webtoon/screens/reader_screen.dart';

import 'fake_api.dart';

class MemoryLanguageStore implements LanguageStore {
  String? saved;
  MemoryLanguageStore([this.saved]);
  @override
  Future<String?> load() async => saved;
  @override
  Future<void> save(String value) async => saved = value;
}

Map<String, dynamic> translatedEpisode() {
  Map<String, dynamic> bubble(int i) => {
    'speaker_id': 'c_vesna',
    'text': 'Bublina $i',
    'kind': 'speech',
    'i18n': {'en': 'Bubble $i', 'ja': 'バブル $i'},
  };
  final ep = episodeJson(
    'ep_1',
    panels: [
      panelJson(0, bubbles: [bubble(0)]),
      panelJson(1, bubbles: [bubble(1)]),
    ],
    choices: [
      {
        'id': 'c1',
        'kind': 'closed',
        'text': 'Otevřít dopis.',
        'i18n': {'en': 'Open the letter.'},
      },
      {
        'id': 'free',
        'kind': 'free',
        'text': 'Nebo napiš, co uděláš…',
        'i18n': {'en': 'Or write what you do…'},
      },
    ],
  );
  return {
    ...ep,
    'title_i18n': {'en': 'A letter without an address'},
    'source_language': 'cs',
    'languages': ['en'], // ja is incomplete (title and choices missing)
  };
}

Widget app(FakeWebtoonApi api, LanguageStore store, {String? device}) =>
    ProviderScope(
      overrides: [
        apiProvider.overrideWithValue(api),
        configProvider.overrideWithValue(
          const AppConfig(
            apiBase: 'http://test',
            userId: 'player',
            pollInterval: Duration(milliseconds: 100),
          ),
        ),
        languageStoreProvider.overrideWithValue(store),
        deviceLanguageProvider.overrideWithValue(device),
      ],
      child: const MaterialApp(home: ReaderScreen(campaignId: 'cp_1')),
    );

FakeWebtoonApi fakeApi() => FakeWebtoonApi(
  worlds: [testWorld()],
  campaigns: {
    'cp_1': testCampaign(['ep_1']),
  },
  episodeScripts: {
    'ep_1': [translatedEpisode()],
  },
);

void main() {
  group('model fallback', () {
    final ep = Episode.fromJson(translatedEpisode());

    test('translated text or the original', () {
      final b = ep.panels[0].bubbles[0];
      expect(b.textIn('en'), 'Bubble 0');
      expect(b.textIn('de'), 'Bublina 0');
      expect(b.textIn(null), 'Bublina 0');
      expect(ep.panels[1].localized('en').bubbles[0].text, 'Bubble 1');
      expect(ep.choices[0].localized('fr').text, 'Otevřít dopis.');
      expect(ep.titleIn('en'), 'A letter without an address');
    });

    test('an episode shows a language only when it is complete', () {
      expect(ep.displayLanguage('en'), 'en');
      expect(ep.displayLanguage('ja'), isNull);
      expect(ep.displayLanguage('cs'), isNull); // source = original
      expect(ep.displayLanguage(null), isNull);
    });

    test('editing a bubble drops its translations', () {
      final b = ep.panels[0].bubbles[0];
      expect(b.copyWith(text: 'Jiný text').i18n, isEmpty);
      expect(b.copyWith(text: 'Bublina 0').i18n['en'], 'Bubble 0');
      expect(b.toJson().containsKey('i18n'), isFalse);
    });

    test('device locale → reader language', () {
      expect(readerLanguageFor(const Locale('pt', 'BR')), 'pt-BR');
      expect(readerLanguageFor(const Locale('de', 'AT')), 'de');
      expect(readerLanguageFor(const Locale('sv')), isNull);
      expect(langDisplayName('uk'), 'Українська');
    });
  });

  test('long translations shrink the font instead of overflowing the panel', () {
    const size = Size(400, 280);
    final short = layoutBubbles(size, [const Bubble(text: 'Ahoj!')]);
    final long = layoutBubbles(size, [
      const Bubble(
        text:
            'Donaudampfschifffahrtsgesellschaftskapitänsmütze und noch viel mehr '
            'Text, der in der Übersetzung deutlich länger geworden ist als im Original, '
            'damit er die Sprechblase sprengen würde.',
      ),
    ]);
    expect(long.single.style.fontSize!, lessThan(short.single.style.fontSize!));
    expect(long.single.rect.bottom, lessThanOrEqualTo(size.height));
  });

  testWidgets('language menu switches bubbles, title and choices; remembered', (
    tester,
  ) async {
    final store = MemoryLanguageStore();
    await tester.pumpWidget(app(fakeApi(), store));
    await tester.pumpAndSettle();
    expect(find.text('Bublina 0'), findsOneWidget);
    expect(find.text('Dopis bez adresy'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('language-button')));
    await tester.pumpAndSettle();
    expect(find.text('Originál (Čeština)'), findsOneWidget);
    // ja is offered but disabled: the episode is not fully translated into it.
    final ja = tester.widget<PopupMenuItem<String>>(
      find.byKey(const ValueKey('lang-ja')),
    );
    expect(ja.enabled, isFalse);
    await tester.tap(find.byKey(const ValueKey('lang-en')));
    await tester.pumpAndSettle();

    expect(find.text('Bubble 0'), findsOneWidget);
    expect(find.text('Bublina 0'), findsNothing);
    expect(find.text('A letter without an address'), findsOneWidget);
    expect(
      find.text('EN'),
      findsOneWidget,
    ); // app bar shows the active language
    expect(store.saved, 'en');
    await tester.scrollUntilVisible(
      find.text('Open the letter.'),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Open the letter.'), findsOneWidget);

    // Back to the original.
    await tester.tap(find.byKey(const ValueKey('language-button')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('lang-')));
    await tester.pumpAndSettle();
    expect(store.saved, '');
    expect(find.text('Otevřít dopis.'), findsOneWidget);
  });

  testWidgets('saved choice wins over the device language', (tester) async {
    await tester.pumpWidget(
      app(fakeApi(), MemoryLanguageStore('en'), device: 'de'),
    );
    await tester.pumpAndSettle();
    expect(find.text('Bubble 0'), findsOneWidget);
  });

  testWidgets(
    'device language is used when nothing was chosen; untranslated → original',
    (tester) async {
      await tester.pumpWidget(
        app(fakeApi(), MemoryLanguageStore(), device: 'en'),
      );
      await tester.pumpAndSettle();
      expect(find.text('Bubble 0'), findsOneWidget);
      await tester.pumpWidget(
        app(fakeApi(), MemoryLanguageStore(), device: 'de'),
      );
      await tester.pumpAndSettle();
      expect(find.text('Bublina 0'), findsOneWidget);
    },
  );
}
