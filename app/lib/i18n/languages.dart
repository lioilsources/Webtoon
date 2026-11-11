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

const _flags = {
  'cs': '🇨🇿',
  'en': '🇬🇧',
  'de': '🇩🇪',
  'it': '🇮🇹',
  'fr': '🇫🇷',
  'pl': '🇵🇱',
  'pt-BR': '🇧🇷',
  'ja': '🇯🇵',
  'ko': '🇰🇷',
  'vi': '🇻🇳',
  'ru': '🇷🇺',
  'uk': '🇺🇦',
};

/// Flag emoji of a reader language; empty when unknown.
String langFlag(String code) => _flags[code] ?? '';

/// Native name of a language code; the code itself when unknown.
String langDisplayName(String code) => _native[code] ?? code;

/// Reader language for a device locale: `pt_BR`/`pt` → `pt-BR`, otherwise the bare language
/// code when it is one of [kReaderLanguages]; null when the device language is not offered.
String? readerLanguageFor(Locale locale) {
  final lang = locale.languageCode.toLowerCase();
  if (lang == 'pt') return 'pt-BR';
  return kReaderLanguages.contains(lang) ? lang : null;
}

/// Interface languages: the 12 reader languages plus 33 more (ui_strings_more.dart). Only the
/// reader languages have translated stories; the rest translate the app around them.
const kUiLanguages = [
  'cs',
  'en',
  'ar',
  'bn',
  'ca',
  'da',
  'de',
  'el',
  'es',
  'fi',
  'fr',
  'gu',
  'he',
  'hi',
  'hr',
  'hu',
  'id',
  'it',
  'ja',
  'kn',
  'ko',
  'ml',
  'mr',
  'ms',
  'nb',
  'nl',
  'or',
  'pa',
  'pl',
  'pt-BR',
  'pt-PT',
  'ro',
  'ru',
  'sk',
  'sl',
  'sv',
  'ta',
  'te',
  'th',
  'tr',
  'uk',
  'ur',
  'vi',
  'zh-Hans',
  'zh-Hant',
];

/// Languages written right to left: the interface mirrors, the comic panels do not.
const kRtlLanguages = {'ar', 'he', 'ur'};

/// Interface language for a device locale, only when it is *not* a reader language (those
/// are handled by [readerLanguageFor]); null when the app is not translated into it.
String? uiLanguageFor(Locale locale) {
  final lang = locale.languageCode.toLowerCase();
  String? code;
  switch (lang) {
    case 'pt':
      code = locale.countryCode == 'PT' ? 'pt-PT' : 'pt-BR';
    case 'zh':
      final hant =
          locale.scriptCode == 'Hant' ||
          const {'TW', 'HK', 'MO'}.contains(locale.countryCode);
      code = hant ? 'zh-Hant' : 'zh-Hans';
    case 'no' || 'nn' || 'nb':
      code = 'nb';
    case 'iw':
      code = 'he';
    case 'in':
      code = 'id';
    default:
      code = lang;
  }
  return kUiLanguages.contains(code) ? code : null;
}

/// The Flutter [Locale] of an interface language code (`pt-PT`, `zh-Hant`, `ar`).
Locale localeOfUi(String code) {
  final parts = code.split('-');
  if (parts.length == 1) return Locale(code);
  return parts[1].length == 4
      ? Locale.fromSubtags(languageCode: parts[0], scriptCode: parts[1])
      : Locale(parts[0], parts[1]);
}
