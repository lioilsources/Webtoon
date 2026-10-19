import 'dart:ui' show PlatformDispatcher;

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../i18n/cjk_fonts.dart';
import '../i18n/languages.dart';

/// Where the reader's language choice is kept between runs; tests override it.
abstract class LanguageStore {
  /// Saved choice: a language code, '' for "original", null when the reader never chose.
  Future<String?> load();
  Future<void> save(String value);
}

class PrefsLanguageStore implements LanguageStore {
  static const _key = 'reader_language';

  @override
  Future<String?> load() async {
    try {
      return (await SharedPreferences.getInstance()).getString(_key);
    } catch (_) {
      return null; // no plugin (tests, unsupported platform): just don't remember
    }
  }

  @override
  Future<void> save(String value) async {
    try {
      await (await SharedPreferences.getInstance()).setString(_key, value);
    } catch (_) {}
  }
}

final languageStoreProvider = Provider<LanguageStore>(
  (ref) => PrefsLanguageStore(),
);

/// Device language when the reader offers it (overridable in tests).
final deviceLanguageProvider = Provider<String?>(
  (ref) => readerLanguageFor(PlatformDispatcher.instance.locale),
);

/// The language the reader wants bubbles in; null = original. Each episode shows it only
/// when it is fully translated (Episode.displayLanguage), otherwise its original.
final readerLanguageProvider =
    StateNotifierProvider<ReaderLanguageNotifier, String?>(
      (ref) => ReaderLanguageNotifier(
        ref.watch(languageStoreProvider),
        ref.watch(deviceLanguageProvider),
      ),
    );

class ReaderLanguageNotifier extends StateNotifier<String?> {
  final LanguageStore _store;
  bool _chosen = false;

  /// Starts with the device language; a saved choice replaces it once loaded.
  ReaderLanguageNotifier(this._store, String? device) : super(device) {
    ensureFontsFor(device);
    _store.load().then((v) async {
      if (v == null || _chosen) return;
      final lang = v.isEmpty ? null : v;
      await ensureFontsFor(lang);
      if (!_chosen && mounted) state = lang;
    });
  }

  /// [lang] null = original. Japanese and Korean switch once their font is loaded, so the
  /// bubbles are measured with the glyphs they are drawn with.
  Future<void> select(String? lang) async {
    _chosen = true;
    _store.save(lang ?? '');
    await ensureFontsFor(lang);
    if (mounted) state = lang;
  }
}
