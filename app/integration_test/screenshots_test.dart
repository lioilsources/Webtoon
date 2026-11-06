// App Store / Google Play screenshots. Drives the reader UI once per language (UI + bubble
// language switched per pass, no rebuild) and, at every shot, asks the host helper to capture
// the device screen (`xcrun simctl io … screenshot` / `adb exec-out screencap`), so the shots
// carry the real (overridden, clean) status bar.
//
// Do not run this directly; the host helper boots the device, serves the staged Sára gamebook
// and the /shot endpoint, and writes store/screenshots/<set>/<locale>/NN_<name>.png:
//
//   python3 store/screenshots/tools/stage_sara.py            # once: Sára with the repo translations
//   python3 store/screenshots/tools/shoot.py ios-6.9         # iPhone 17 Pro Max, 1320×2868
//   python3 store/screenshots/tools/shoot.py ios-13          # iPad Pro 13" (M5), 2064×2752
//   python3 store/screenshots/tools/shoot.py play-phone      # Pixel_10 AVD at 1080×2160
//   python3 store/screenshots/tools/shoot.py play-tablet-10  # Pixel_10 AVD at 1600×2560
//   … [--langs cs,en]                                        # a subset (default: all 12)
//   python3 store/screenshots/tools/feature_graphic.py       # play-feature-graphic.png
//
// It runs `flutter test integration_test/screenshots_test.dart -d <device>
//   --dart-define=WEBTOON_FAKE_IAP=true --dart-define=SHOT_HOST=http://<host>:<port>
//   --dart-define=SHOT_LANGS=cs,en,…` (assets/packs/starter.zip must be the real starter pack).
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:integration_test/integration_test.dart';
import 'package:webtoon/app.dart';
import 'package:webtoon/gamebook/gamebook_state.dart';
import 'package:webtoon/packs/pack_store.dart';
import 'package:webtoon/profile/reader_profile.dart';
import 'package:webtoon/providers/language_provider.dart';
import 'package:webtoon/shop/entitlements.dart';
import 'package:webtoon/shop/shop_controller.dart';

const _host = String.fromEnvironment(
  'SHOT_HOST',
  defaultValue: 'http://127.0.0.1:8777',
);
const _langs = String.fromEnvironment(
  'SHOT_LANGS',
  defaultValue: 'cs,en,de,it,fr,pl,pt-BR,ja,ko,vi,ru,uk',
);

/// Reader shots (02 / 05 in another language / 06): the story and how far down its first episode to scroll (logical px).
const _story1 = String.fromEnvironment(
  'SHOT_STORY1',
  defaultValue: 'cp_bbbb4754d5d6',
);
const _scroll1 = int.fromEnvironment('SHOT_SCROLL1', defaultValue: 0);
const _story2 = String.fromEnvironment(
  'SHOT_STORY2',
  defaultValue: 'cp_453636948126',
);
const _scroll2 = int.fromEnvironment('SHOT_SCROLL2', defaultValue: 0);
const _story3 = String.fromEnvironment(
  'SHOT_STORY3',
  defaultValue: 'cp_148884fb7087',
);
const _scroll3 = int.fromEnvironment('SHOT_SCROLL3', defaultValue: 0);

/// Which language the "other language" shot (05) shows the bubbles in, per UI language.
const _otherLang = {'cs': 'en', 'en': 'ja'};

class _MemoryLanguageStore implements LanguageStore {
  String? value;
  _MemoryLanguageStore(this.value);
  @override
  Future<String?> load() async => value;
  @override
  Future<void> save(String v) async => value = v;
}

/// Sára opened at "Zhasínající město" (n2, reached through the mirror): its chapter end offers
/// two choices under four wide panels.
class _MemoryGamebookRepository extends GamebookRepository {
  final Map<String, GamebookProgress> _p = {
    'sara': const GamebookProgress(
      node: 'n2',
      path: ['n0', 'n1b'],
      visited: {'n0', 'n1b', 'n2'},
      knownNodes: {
        'n0', 'n1a', 'n1b', 'n2', 'n3a', 'n3b', 'n4', //
        'end_light', 'end_friends', 'end_cold',
      },
    ),
  };
  @override
  Future<GamebookProgress?> loadProgress(String id) async => _p[id];
  @override
  Future<void> saveProgress(String id, GamebookProgress p) async => _p[id] = p;
}

void main() {
  final binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy = LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;

  /// Pumps frames for [d] of wall-clock time (images decode, loops play, routes finish).
  Future<void> idle(WidgetTester t, [int ms = 600]) async {
    final end = DateTime.now().add(Duration(milliseconds: ms));
    while (DateTime.now().isBefore(end)) {
      await t.pump(const Duration(milliseconds: 50));
    }
  }

  Future<void> waitFor(WidgetTester t, Finder f, {int seconds = 60}) async {
    final end = DateTime.now().add(Duration(seconds: seconds));
    while (f.evaluate().isEmpty) {
      if (DateTime.now().isAfter(end)) {
        throw StateError('timed out waiting for $f');
      }
      await t.pump(const Duration(milliseconds: 100));
    }
  }

  /// Asks the host to capture the screen as <locale>/<name>.png.
  Future<void> shot(WidgetTester t, String lang, String name) async {
    await idle(t, 1500);
    // The emulator's host link drops a request now and then: retry.
    http.Response? res;
    for (var attempt = 0; res == null; attempt++) {
      try {
        res = await http.get(Uri.parse('$_host/shot?lang=$lang&name=$name'));
      } on http.ClientException {
        if (attempt >= 4) rethrow;
        await idle(t, 1000);
      }
    }
    if (res.statusCode != 200) {
      throw StateError('shot $name: ${res.statusCode} ${res.body}');
    }
    debugPrint('SHOT $lang $name ok');
  }

  Future<void> back(WidgetTester t) async {
    await t.pageBack();
    await idle(t, 800);
  }

  testWidgets('store screenshots', (t) async {
    // Sára (kids gamebook) with the repo's translations, from the host helper.
    final zip = await http.get(Uri.parse('$_host/gamebook-sara.zip'));
    expect(zip.statusCode, 200, reason: 'run stage_sara.py and shoot.py');
    await PackStore().installFromBytes(zip.bodyBytes);
    // No system keyboard / overlays in the shots.
    await SystemChannels.textInput.invokeMethod<void>('TextInput.hide');

    for (final lang in _langs.split(',')) {
      final store = _MemoryLanguageStore(lang);
      await t.pumpWidget(
        ProviderScope(
          key: ValueKey('scope-$lang'),
          overrides: [
            deviceLanguageProvider.overrideWithValue(lang),
            languageStoreProvider.overrideWithValue(store),
            profileStoreProvider.overrideWithValue(
              MemoryProfileStore(ReaderProfile.kids),
            ),
            entitlementStoreProvider.overrideWithValue(
              MemoryEntitlementStore(),
            ),
            gamebookRepositoryProvider.overrideWithValue(
              _MemoryGamebookRepository(),
            ),
          ],
          child: const WebtoonApp(),
        ),
      );
      await waitFor(t, find.byKey(const ValueKey('library-list')));
      final ctx = t.element(find.byType(WebtoonApp));
      final container = ProviderScope.containerOf(ctx);
      expect(container.read(readerLanguageProvider), lang);
      await idle(t, 2500);

      // 01 Library.
      await shot(t, lang, '01_library');

      // 02 Reader.
      await _openStory(t, _story1, _scroll1, idle, waitFor);
      await shot(t, lang, '02_reader');
      await back(t);

      // 03 Gamebook chapter end with its choices.
      await _reveal(t, 'gamebook-sara');
      await t.tap(find.byKey(const ValueKey('gamebook-sara')));
      await idle(t, 3000);
      await t.scrollUntilVisible(
        find.byKey(const ValueKey('gamebook-choice-lake')),
        800,
        scrollable: find.byType(Scrollable).first,
        maxScrolls: 100,
      );
      await t.drag(find.byType(Scrollable).first, const Offset(0, -2000));
      await idle(t, 1500);
      // At the very end the choice card floats above empty space; pull the page down so the
      // card sits at the bottom edge and more of the panel above (and its bubble) shows.
      final last = t.getRect(
        find.byKey(const ValueKey('gamebook-choice-lake')),
      );
      final view = t.view;
      final height = view.physicalSize.height / view.devicePixelRatio;
      final inset = view.padding.bottom / view.devicePixelRatio;
      final slack = height - inset - 12 - (last.bottom + 32);
      if (slack > 0) {
        final sc = t.state<ScrollableState>(find.byType(Scrollable).first);
        sc.position.jumpTo(sc.position.pixels - slack);
      }
      await idle(t, 2000);
      await shot(t, lang, '03_gamebook');
      await back(t);

      // 04 Store.
      await t.tap(find.byKey(const ValueKey('tab-store')));
      await waitFor(t, find.byKey(const ValueKey('store-list')));
      await idle(t, 4000); // covers from Pages
      await shot(t, lang, '04_store');
      await t.tap(find.byIcon(Icons.auto_stories_outlined));
      await idle(t, 800);

      // 05 Another story with its bubbles (and the UI) in another language.
      final other = _otherLang[lang] ?? 'en';
      await container.read(readerLanguageProvider.notifier).select(other);
      await idle(t, 800);
      await _openStory(t, _story2, _scroll2, idle, waitFor);
      await shot(t, lang, '05_language');
      await back(t);
      await container.read(readerLanguageProvider.notifier).select(lang);
      await idle(t, 800);

      // 06 A second story.
      await _openStory(t, _story3, _scroll3, idle, waitFor);
      await shot(t, lang, '06_reader');
      await back(t);
    }
  });
}

Future<void> _openStory(
  WidgetTester t,
  String id,
  int scroll,
  Future<void> Function(WidgetTester, [int]) idle,
  Future<void> Function(WidgetTester, Finder, {int seconds}) waitFor,
) async {
  await _reveal(t, 'story-$id');
  await t.tap(find.byKey(ValueKey('story-$id')));
  await waitFor(t, find.byKey(const ValueKey('reader-scroll')));
  await idle(t, 2000);
  if (scroll > 0) {
    final s = find.byKey(const ValueKey('reader-scroll'));
    final state = t.state<ScrollableState>(
      find.descendant(of: s, matching: find.byType(Scrollable)).first,
    );
    state.position.jumpTo(scroll.toDouble());
  }
  await idle(t, 2500);
}

/// Scrolls the library so the widget keyed [key] is in the middle of the screen.
Future<void> _reveal(WidgetTester t, String key) async {
  final list = find.byKey(const ValueKey('library-list'));
  final state = t.state<ScrollableState>(
    find.descendant(of: list, matching: find.byType(Scrollable)).first,
  );
  state.position.jumpTo(0);
  await t.pump();
  final f = find.byKey(ValueKey(key));
  while (f.evaluate().isEmpty) {
    state.position.jumpTo(state.position.pixels + 300);
    await t.pump();
  }
  await Scrollable.ensureVisible(t.element(f), alignment: 0.4);
  await t.pump(const Duration(milliseconds: 300));
}
