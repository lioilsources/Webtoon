// Noto Sans JP / KR as fallback fonts for translated bubbles, loaded only when needed.

import 'package:flutter/services.dart';

const kNotoJP = 'NotoSansJP';
const kNotoKR = 'NotoSansKR';

/// Families every comic text style falls back to: Nunito covers Latin, Vietnamese and
/// Cyrillic (DynaPuff and Baloo 2 do not), the Noto fonts cover kana, kanji and hangul once
/// [ensureFontsFor] has loaded them; until then the platform's own fallback draws them.
const kComicFallback = ['Nunito', kNotoJP, kNotoKR];

const _assets = {
  'ja': (kNotoJP, 'assets/fonts/NotoSansJP-Variable.ttf'),
  'ko': (kNotoKR, 'assets/fonts/NotoSansKR-Variable.ttf'),
};

final _loaded = <String, Future<void>>{};

/// Loads the bundled font a language needs (ja, ko); a no-op for every other language and
/// on a second call. Never throws: without the font the platform fallback is used.
Future<void> ensureFontsFor(String? lang) {
  final a = _assets[lang];
  if (a == null) return Future.value();
  return _loaded.putIfAbsent(a.$1, () async {
    try {
      await (FontLoader(a.$1)..addFont(rootBundle.load(a.$2))).load();
    } catch (_) {}
  });
}
