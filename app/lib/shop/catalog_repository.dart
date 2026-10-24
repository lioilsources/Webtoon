// catalog.json: last good copy cached on disk, refreshed from GitHub Pages on start when online.
// A downloaded catalog replaces the cache only when its `version` is higher (an older CDN copy
// never rolls the store back).

import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import 'catalog.dart';

/// Default catalog URL; `--dart-define=WEBTOON_CATALOG_URL=…` for a staging copy. Once a catalog
/// is cached, its `base_urls.pages` decides where the next one comes from.
const String kCatalogUrl = String.fromEnvironment(
  'WEBTOON_CATALOG_URL',
  defaultValue: 'https://lioilsources.github.io/webtoon-content/catalog.json',
);

class CatalogRepository {
  final http.Client _client;
  final String url;
  final Future<Directory> Function() _dir;
  final Duration timeout;

  Catalog? _cached;

  CatalogRepository({
    http.Client? client,
    this.url = kCatalogUrl,
    Future<Directory> Function()? cacheDir,
    this.timeout = const Duration(seconds: 15),
  }) : _client = client ?? http.Client(),
       _dir = cacheDir ?? getApplicationSupportDirectory;

  Catalog? get cached => _cached;

  Future<File> _file() async =>
      File(p.join((await _dir()).path, 'catalog.json'));

  /// The cached copy, or null when there is none (first start offline) or it is unreadable.
  Future<Catalog?> loadCached() async {
    try {
      final f = await _file();
      if (!await f.exists()) return null;
      return _cached = Catalog.parse(jsonDecode(await f.readAsString()));
    } catch (_) {
      return null;
    }
  }

  /// Where the next catalog comes from: the cached catalog's Pages site, else [url].
  String get refreshUrl {
    final pages = _cached?.baseUrls.pages ?? '';
    return pages.isEmpty ? url : '${pages}catalog.json';
  }

  /// Downloads catalog.json; keeps and caches it when newer than the cached one. Returns the
  /// catalog in force afterwards. Throws when offline and nothing is cached.
  Future<Catalog> refresh() async {
    _cached ??= await loadCached();
    try {
      final res = await _client.get(Uri.parse(refreshUrl)).timeout(timeout);
      if (res.statusCode != 200) {
        throw HttpException('catalog.json: HTTP ${res.statusCode}');
      }
      final body = utf8.decode(res.bodyBytes);
      final fresh = Catalog.parse(jsonDecode(body));
      if (_cached == null || fresh.version > _cached!.version) {
        _cached = fresh;
        try {
          final f = await _file();
          await f.parent.create(recursive: true);
          final tmp = File('${f.path}.tmp');
          await tmp.writeAsString(body);
          await tmp.rename(f.path);
        } catch (_) {
          // No disk cache (tests, read-only dir): the in-memory copy still works.
        }
      }
      return _cached!;
    } catch (e) {
      if (_cached != null) return _cached!;
      rethrow;
    }
  }
}
