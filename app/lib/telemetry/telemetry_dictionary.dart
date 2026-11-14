// The one event dictionary of the reader, mirrored in ../docs/telemetry.md (test/telemetry_test.dart
// keeps them equal). Adding an event or a property is a change to the privacy policy.
//
// Nothing about the content of a story (ids, titles, bubbles, choices) and nothing the reader
// types (own branches, gate answers) is ever a value here.

import 'package:ol1n_telemetry/ol1n_telemetry.dart';

import '../i18n/languages.dart';

/// The app version this build reports; test/telemetry_test.dart keeps it equal to `version:`
/// in pubspec.yaml.
const kAppVersion = '1.0.0';

/// Route name → screen. Pushed reader routes carry these names (RouteSettings); the home
/// route `/` is the current tab or the start screen ([ToonforkScreenObserver]).
const kScreenRoutes = {
  '/reader': 'reader',
  '/pack': 'pack_detail',
  '/gamebook': 'gamebook',
  '/gamebook/revisit': 'gamebook_revisit',
  '/gamebook/preview': 'gamebook_preview',
  '/branches': 'branch_editor',
  '/branches/node': 'branch_node',
};

/// Screens of the home route: the start-up splash, the first-launch profile chooser, the tabs.
const kHomeScreens = {
  'splash',
  'profile_chooser',
  'library',
  'store',
  'settings',
};

/// Bubble language values: a reader language, or `original`.
final kBubbleLanguages = {'original', ...kReaderLanguages};

/// Product kinds by product id prefix (docs/store-products.md).
const kProductKinds = {'pack', 'bundle', 'gamebook', 'kit', 'other'};

/// `pack_5_2` → `pack`, `kit_sara` → `kit`.
String productKind(String productId) {
  final prefix = productId.split('_').first;
  return kProductKinds.contains(prefix) ? prefix : 'other';
}

/// Actions of the branch editor (beta).
const kBranchActions = {
  'new_branch',
  'delete_branch',
  'add_image',
  'remove_image',
  'move_image',
  'bubbles',
  'add_choice',
  'remove_choice',
  'play',
  'export',
};

final toonforkDictionary = TelemetryDictionary(
  appVersion: kAppVersion,
  languages: kReaderLanguages.toSet(),
  screens: {...kHomeScreens, ...kScreenRoutes.values},
  features: {
    'history',
    'bubble_language',
    'gamebook_map',
    'gamebook_back',
    'gamebook_revisit',
    'gamebook_restart',
    'branch_editor',
    'app_icon',
    'restore_purchases',
    'reinstall_starter',
    'pack_delete',
  },
  errorKinds: {
    'pack_load',
    'reader_load',
    'catalog',
    'download',
    'purchase',
    'restore',
  },
  common: {'bubbles': EnumProp(kBubbleLanguages)},
  events: {
    ...TelemetryDictionary.flow(
      'episode_read',
      results: {'skip'},
      start: {
        'index': const IntProp(1000),
        'from': const EnumProp({
          'library',
          'next_story',
          'history',
          'continue',
        }),
      },
      end: {'index': const IntProp(1000), 'last': const BoolProp()},
    ),
    'gamebook_open': {'resume': const BoolProp(), 'found': const IntProp(100)},
    'gamebook_choice': {
      'kind': const EnumProp({'choice', 'own', 'next'}),
      'step': const IntProp(10000),
    },
    'gamebook_ending': {
      'ending': const EnumProp({'good', 'retry', 'own'}),
      'first': const BoolProp(),
      'found': const IntProp(100),
      'total': const IntProp(100),
    },
    'branch_edit': {'action': const EnumProp(kBranchActions)},
    'purchase_gate': {'passed': const BoolProp()},
    ...TelemetryDictionary.flow(
      'purchase',
      start: {'product': const EnumProp(kProductKinds)},
    ),
    ...TelemetryDictionary.flow(
      'pack_download',
      start: {
        'kind': const EnumProp({'pack', 'gamebook'}),
        'update': const BoolProp(),
      },
    ),
    'packs_ready': {'ms': const IntProp(600000), 'extracted': const BoolProp()},
  },
);
