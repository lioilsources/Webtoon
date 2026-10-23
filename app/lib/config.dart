// Build-time configuration (`--dart-define`).
//
//   # Reader (default): offline, from content packs; no backend
//   flutter run -d macos
//
//   # Studio: today's thin client of the Go backend + author tools
//   flutter run -d macos \
//     --dart-define=WEBTOON_STUDIO=true \
//     --dart-define=WEBTOON_API=http://localhost:8095 \
//     --dart-define=WEBTOON_USER=player \
//     [--dart-define=WEBTOON_OPEN_CAMPAIGN=cp_…]

/// `WEBTOON_STUDIO=true`: talk to the backend and show the author tools. Otherwise the app
/// is the offline reader over installed packs (lib/packs).
const bool kStudioBuild = bool.fromEnvironment('WEBTOON_STUDIO');

/// Backend URL, user and polling for Studio builds.
class AppConfig {
  /// Base URL of the Go backend (no trailing slash). Default = backend's `LISTEN_ADDR` :8095.
  final String apiBase;

  /// Sent as `X-User-ID` (the backend auth is a stub until Ol1nLLM accounts land).
  final String userId;

  /// How often an episode that is still generating is polled.
  final Duration pollInterval;

  /// Dev shortcut: open this campaign's reader on launch (`WEBTOON_OPEN_CAMPAIGN`).
  final String? openCampaign;

  const AppConfig({
    required this.apiBase,
    required this.userId,
    this.pollInterval = const Duration(seconds: 2),
    this.openCampaign,
  });

  factory AppConfig.fromEnvironment() {
    const api = String.fromEnvironment(
      'WEBTOON_API',
      defaultValue: 'http://localhost:8095',
    );
    const user = String.fromEnvironment('WEBTOON_USER', defaultValue: 'player');
    const open = String.fromEnvironment('WEBTOON_OPEN_CAMPAIGN');
    return AppConfig(
      apiBase: _trimSlash(api),
      userId: user,
      openCampaign: open.isEmpty ? null : open,
    );
  }

  static String _trimSlash(String s) =>
      s.endsWith('/') ? s.substring(0, s.length - 1) : s;

  /// `image_url` from the API is either absolute (MEDIA_BASE_URL set to a CDN) or `/media/...`.
  String resolveMedia(String url) {
    if (url.startsWith('http://') || url.startsWith('https://')) return url;
    return '$apiBase${url.startsWith('/') ? '' : '/'}$url';
  }
}
