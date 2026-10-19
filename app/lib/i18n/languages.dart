// Reader languages: Lexify's set (../DuolingoCards, langDisplayName), shown by their own names
// so a reader finds theirs whatever the UI language is.

import 'dart:ui' show Locale;

/// Order of the language menu (after "Originál").
const kReaderLanguages = [
  'cs',
  'en',
  'de',
  'it',
  'fr',
  'pl',
  'pt-BR',
  'ja',
  'ko',
  'vi',
  'ru',
  'uk',
];

const _native = {
  'cs': 'Čeština',
  'en': 'English',
  'de': 'Deutsch',
  'it': 'Italiano',
  'fr': 'Français',
  'pl': 'Polski',
  'pt-BR': 'Português (Brasil)',
  'ja': '日本語',
  'ko': '한국어',
  'vi': 'Tiếng Việt',
  'ru': 'Русский',
  'uk': 'Українська',
};

/// Native name of a language code; the code itself when unknown.
String langDisplayName(String code) => _native[code] ?? code;

/// Reader language for a device locale: `pt_BR`/`pt` → `pt-BR`, otherwise the bare language
/// code when it is one of [kReaderLanguages]; null when the device language is not offered.
String? readerLanguageFor(Locale locale) {
  final lang = locale.languageCode.toLowerCase();
  if (lang == 'pt') return 'pt-BR';
  return kReaderLanguages.contains(lang) ? lang : null;
}
