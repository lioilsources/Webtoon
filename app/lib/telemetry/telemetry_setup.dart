// Anonymous usage statistics of the reader (docs/telemetry.md, package ol1n_telemetry).
//
// - Studio builds (`WEBTOON_STUDIO=true`) never call [Telemetry.init]: nothing is measured there.
// - The Kids profile is never measured (plan §4.14): measuring is suspended in it, and also
//   before the first-launch profile choice (the phone may be a child's). Only Adults resume it.
// - Without TELEMETRY_KEY / TELEMETRY_HOST the client builds no sink and does nothing.

import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:ol1n_telemetry/ol1n_telemetry.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:visibility_detector/visibility_detector.dart';

import '../i18n/ui_strings.dart';
import '../providers/language_provider.dart';
import '../shop/store_gateway.dart' show kFakeIap;
import 'telemetry_dictionary.dart';

/// App id in StoreMetrics (`apps.yaml`).
const kTelemetryApp = 'webtoon';

/// `TELEMETRY_TESTER=true` or a fake-IAP dev build marks the events as a tester's.
const kTelemetryTester = bool.fromEnvironment('TELEMETRY_TESTER') || kFakeIap;

/// The client's few values (`telemetry_*` keys) next to the app's own in SharedPreferences.
class PrefsTelemetryStore implements TelemetryStore {
  PrefsTelemetryStore(this._prefs);
  final SharedPreferences _prefs;

  @override
  Future<String?> read(String key) async => _prefs.getString(key);

  @override
  Future<void> write(String key, String value) => _prefs.setString(key, value);

  @override
  Future<void> remove(String key) => _prefs.remove(key);
}

/// Starts measuring for the reader. [adults] is the saved profile: anything else (Kids, or no
/// choice yet) starts suspended. Never awaits the client; returns at once on failure.
Future<void> startTelemetry(
  ProviderContainer container, {
  required bool adults,
}) async {
  final SharedPreferences prefs;
  try {
    prefs = await SharedPreferences.getInstance();
  } catch (_) {
    return; // no plugin on this platform: stay silent
  }
  unawaited(
    Telemetry.init(
      app: kTelemetryApp,
      appVersion: kAppVersion,
      dictionary: toonforkDictionary,
      store: PrefsTelemetryStore(prefs),
      lang: () => container.read(uiLanguageProvider),
      tester: kTelemetryTester,
      // Anything the app saved before (profile, language, purchases): not a new install.
      hadDataBefore: () =>
          prefs.getKeys().any((k) => !k.startsWith('telemetry_')),
      common: () => telemetryCommon(container.read(readerLanguageProvider)),
      suspended: !adults,
    ),
  );
}

/// The app's own common properties for the bubble language [lang] (null = original).
Map<String, Object> telemetryCommon(String? lang) => {
  'bubbles': lang != null && kBubbleLanguages.contains(lang)
      ? lang
      : 'original',
};

/// The reader profile changed (or was loaded): only Adults are measured.
void telemetryProfile({required bool adults}) {
  if (adults) {
    Telemetry.resume();
  } else {
    Telemetry.suspend('kids');
  }
}

/// Screens from route names; the home route `/` is whatever [reportHomeScreen] said last.
class ToonforkScreenObserver extends TelemetryNavigatorObserver {
  ToonforkScreenObserver() : super(kScreenRoutes);

  static String home = 'splash';

  @override
  String screenOf(Route<dynamic> route) =>
      route.settings.name == Navigator.defaultRouteName
      ? home
      : super.screenOf(route);
}

/// The home route now shows [screen] (a tab, the splash or the profile chooser). Reported only
/// while the home route is on top; a pop back to it reports it through the observer.
void reportHomeScreen(BuildContext context, String screen) {
  ToonforkScreenObserver.home = screen;
  WidgetsBinding.instance.addPostFrameCallback((_) {
    if (!context.mounted) return;
    if (ModalRoute.of(context)?.isCurrent ?? true) Telemetry.screen(screen);
  });
}

/// One reader visit: an `episode_read` flow per episode, from its start to its end block
/// (`ok`), to a jump elsewhere (`skip`) or to leaving the reader (`cancel`). The first episode
/// read to its end on this install is the activation.
class EpisodeReading {
  TelemetryFlow? _flow;
  int? _index;
  final Set<int> _done = {};

  bool get _open => _flow != null && !_flow!.ended;

  /// The reader shows episode [index] (1-based) because of [from].
  void open(int index, String from) {
    if (_open && _index == index) return;
    _end('skip');
    // Read to its end already in this visit (episodes shorter than the screen are all seen at
    // once): nothing new to measure.
    if (_done.contains(index)) {
      _flow = null;
      _index = null;
      return;
    }
    _index = index;
    _flow = Telemetry.flow('episode_read', {
      'index': index.clamp(0, 1000),
      'from': from,
    }, () => {'index': index.clamp(0, 1000), 'last': false});
  }

  /// The end block of episode [index] came into view; [last] = the story's last episode.
  /// An end block further down means the reader scrolled through the episodes before it: each
  /// of them ends `ok` first, in order.
  void reachedEnd(int index, {required bool last}) {
    if (_done.contains(index)) return;
    while (_open && _index! < index) {
      final i = _index!;
      _done.add(i);
      _finish(i, last: false);
    }
    _done.add(index);
    if (_open && _index == index) _finish(index, last: last);
  }

  void _finish(int index, {required bool last}) {
    _flow!.end('ok', {'index': index.clamp(0, 1000), 'last': last});
    Telemetry.activation();
    if (!last) open(index + 1, 'continue');
  }

  /// The reader closed.
  void close() => _end('cancel');

  void _end(String result) {
    if (!_open) return;
    _flow!.end(result, {'index': _index!.clamp(0, 1000), 'last': false});
  }
}

/// [child] with [onSeen] called once it is at least half visible. Only in builds that measure:
/// elsewhere (local builds, tests, Studio) it is [child] itself, with no detector.
Widget whenSeen(Key key, Widget child, VoidCallback onSeen) {
  if (!Telemetry.isConfigured) return child;
  return VisibilityDetector(
    key: key,
    onVisibilityChanged: (info) {
      if (info.visibleFraction >= 0.5) onSeen();
    },
    child: child,
  );
}
