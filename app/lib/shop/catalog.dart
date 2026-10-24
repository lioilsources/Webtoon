// catalog.json of the webtoon-content repo (../../PACK_FORMAT.md, schema 1 and 2): what can be
// downloaded or bought. The store sells only unlocks; the content itself comes from the URLs
// composed here out of `base_urls`, so moving the zips (GitHub Releases → R2) is a catalog change.

import '../models/json.dart';

/// Something is wrong with catalog.json (unknown schema, not an object, …).
class CatalogException implements Exception {
  final String message;
  const CatalogException(this.message);

  @override
  String toString() => message;
}

/// `base_urls`: pages (catalog, covers), releases (zips), r2 (optional zip mirror that wins).
class BaseUrls {
  final String pages;
  final String releases;
  final String? r2;

  const BaseUrls({required this.pages, this.releases = '', this.r2});

  static String _slash(String s) => s.isEmpty || s.endsWith('/') ? s : '$s/';

  factory BaseUrls.fromJson(Map<String, dynamic> j) => BaseUrls(
    pages: _slash(str(j['pages'])),
    releases: _slash(str(j['releases'])),
    r2: strOrNull(j['r2']) == null ? null : _slash(str(j['r2'])),
  );

  /// A path relative to the Pages site (covers, previews); absolute URLs pass through.
  String page(String path) => _isAbsolute(path) ? path : '$pages$path';
}

bool _isAbsolute(String s) =>
    s.startsWith('http://') || s.startsWith('https://');

/// Localised title: the language, else English, else Czech, else [fallback].
String _pick(Map<String, String> i18n, String? lang, String fallback) =>
    (lang == null ? null : i18n[lang]) ?? i18n['en'] ?? i18n['cs'] ?? fallback;

/// A pack type (kids, harlequin, superhero, …).
class CatalogType {
  final String id;
  final Map<String, String> titleI18n;
  final String audience;
  final String icon;

  const CatalogType({
    required this.id,
    this.titleI18n = const {},
    this.audience = 'kids',
    this.icon = '',
  });

  String titleIn(String? lang) => _pick(titleI18n, lang, id);

  factory CatalogType.fromJson(Map<String, dynamic> j) => CatalogType(
    id: str(j['id']),
    titleI18n: strMap(j['title_i18n']),
    audience: str(j['audience'], 'kids'),
    icon: str(j['icon']),
  );
}

/// One zip of a pack.
class CatalogPart {
  /// `a`, `b`, … (null for a schema-1 single zip).
  final String? part;

  /// Schema 2: GitHub release tag + asset name; the URL is composed from `base_urls`.
  final String? release;
  final String? asset;

  /// Schema 1 (or a Pages-hosted part): path relative to `base_urls.pages`.
  final String? path;

  /// Explicit URL; wins over everything else.
  final String? url;
  final int bytes;
  final String sha256;
  final int stories;

  const CatalogPart({
    this.part,
    this.release,
    this.asset,
    this.path,
    this.url,
    this.bytes = 0,
    this.sha256 = '',
    this.stories = 0,
  });

  factory CatalogPart.fromJson(Map<String, dynamic> j) => CatalogPart(
    part: strOrNull(j['part']),
    release: strOrNull(j['release']),
    asset: strOrNull(j['asset']),
    path: strOrNull(j['path']),
    url: strOrNull(j['url']),
    bytes: integer(j['bytes']),
    sha256: str(j['sha256']).toLowerCase(),
    stories: integer(j['stories']),
  );

  /// Where the zip is downloaded from (PACK_FORMAT.md "URL zipu").
  String urlFor(BaseUrls base) {
    if (url != null) return url!;
    if (release != null && asset != null) {
      final host = base.r2 ?? base.releases;
      return '$host$release/$asset';
    }
    if (path != null) return base.page(path!);
    throw const CatalogException('Část balíčku nemá adresu.');
  }

  /// File name for the download (temp file, logs).
  String get fileName {
    final name = asset ?? (path ?? url ?? 'part.zip').split('/').last;
    return name.isEmpty ? 'part.zip' : name;
  }
}

class CatalogPack {
  final String id;
  final String type;
  final int n;
  final String title;
  final Map<String, String> titleI18n;
  final bool free;
  final String? productId;

  /// Also inside the app (the starter): never downloaded.
  final bool bundled;
  final int version;
  final int stories;
  final int bytes;
  final String audience;
  final List<String> languages;
  final String? cover;
  final List<String> previews;
  final List<CatalogPart> parts;

  const CatalogPack({
    required this.id,
    required this.type,
    this.n = 0,
    required this.title,
    this.titleI18n = const {},
    this.free = false,
    this.productId,
    this.bundled = false,
    this.version = 1,
    this.stories = 0,
    this.bytes = 0,
    this.audience = 'kids',
    this.languages = const [],
    this.cover,
    this.previews = const [],
    this.parts = const [],
  });

  String titleIn(String? lang) => _pick(titleI18n, lang, title);

  /// Sum of the parts (or the pack's own `bytes`).
  int get totalBytes {
    final sum = parts.fold<int>(0, (a, p) => a + p.bytes);
    return sum > 0 ? sum : bytes;
  }
}

/// `covers` of a bundle: a list of types, or every type (`"all"`), present and future.
class BundleCoverage {
  final bool all;
  final List<String> types;
  const BundleCoverage({this.all = false, this.types = const []});

  static BundleCoverage fromJson(Object? v) {
    if (v == 'all') return const BundleCoverage(all: true);
    final j = obj(v);
    if (j['types'] == 'all') return const BundleCoverage(all: true);
    return BundleCoverage(types: strList(j['types']));
  }

  bool coversType(String type) => all || types.contains(type);
}

class CatalogBundle {
  final String id;
  final String productId;
  final String priceTier;
  final Map<String, String> titleI18n;
  final BundleCoverage covers;

  const CatalogBundle({
    required this.id,
    required this.productId,
    this.priceTier = '',
    this.titleI18n = const {},
    this.covers = const BundleCoverage(),
  });

  String titleIn(String? lang) => _pick(titleI18n, lang, id);

  factory CatalogBundle.fromJson(Map<String, dynamic> j) {
    final id = str(j['id']);
    return CatalogBundle(
      id: id,
      productId: str(j['product_id'], id),
      priceTier: str(j['price_tier']),
      titleI18n: strMap(j['title_i18n']),
      covers: BundleCoverage.fromJson(j['covers']),
    );
  }
}

/// STUB (later phase): a branching gamebook. Only the store plumbing exists — product ids and
/// entitlements; `graph` / `lore` are kept raw until the gamebook format is designed
/// (see lib/gamebook/gamebook.dart).
class CatalogGamebook {
  final String id;
  final String productId;
  final String? kitProductId;
  final String type;
  final String audience;
  final Map<String, String> titleI18n;
  final String? cover;
  final String status;
  final Object? graph;
  final Object? lore;

  const CatalogGamebook({
    required this.id,
    required this.productId,
    this.kitProductId,
    this.type = '',
    this.audience = 'kids',
    this.titleI18n = const {},
    this.cover,
    this.status = 'planned',
    this.graph,
    this.lore,
  });

  String titleIn(String? lang) => _pick(titleI18n, lang, id);

  factory CatalogGamebook.fromJson(Map<String, dynamic> j) {
    final id = str(j['id']);
    return CatalogGamebook(
      id: id,
      productId: str(j['product_id'], 'gamebook_$id'),
      kitProductId: strOrNull(j['kit_product_id']),
      type: str(j['type']),
      audience: str(j['audience'], 'kids'),
      titleI18n: strMap(j['title_i18n']),
      cover: strOrNull(j['cover']),
      status: str(j['status'], 'planned'),
      graph: j['graph'],
      lore: j['lore'],
    );
  }
}

class CatalogStory {
  final String id;
  final String packId;
  final String type;
  final String worldId;
  final String title;
  final Map<String, String> titleI18n;
  final String? cover;
  final int episodes;
  final String audience;

  const CatalogStory({
    required this.id,
    required this.packId,
    required this.type,
    this.worldId = '',
    required this.title,
    this.titleI18n = const {},
    this.cover,
    this.episodes = 0,
    this.audience = 'kids',
  });

  String titleIn(String? lang) => _pick(titleI18n, lang, title);
}

/// Schema-1 catalogs have no types: derive one from the audience.
String typeForAudience(String audience) =>
    audience == 'adult' ? 'harlequin' : 'kids';

/// Built-in type labels for catalogs without `types` (schema 1) or a pack of an unlisted type.
const _knownTypes = {
  'kids': CatalogType(
    id: 'kids',
    audience: 'kids',
    icon: 'child_care',
    titleI18n: {'cs': 'Pro děti', 'en': 'Kids'},
  ),
  'harlequin': CatalogType(
    id: 'harlequin',
    audience: 'adult',
    icon: 'favorite',
    titleI18n: {'cs': 'Romantika', 'en': 'Romance'},
  ),
  'superhero': CatalogType(
    id: 'superhero',
    audience: 'kids',
    icon: 'bolt',
    titleI18n: {'cs': 'Superhrdinové', 'en': 'Superheroes'},
  ),
};

class Catalog {
  static const supportedSchemas = {1, 2};

  final int schema;
  final int version;
  final DateTime? generatedAt;
  final BaseUrls baseUrls;
  final List<CatalogType> types;
  final List<CatalogPack> packs;
  final List<CatalogBundle> bundles;
  final List<CatalogGamebook> gamebooks;
  final List<CatalogStory> stories;

  const Catalog({
    required this.schema,
    required this.version,
    this.generatedAt,
    required this.baseUrls,
    this.types = const [],
    this.packs = const [],
    this.bundles = const [],
    this.gamebooks = const [],
    this.stories = const [],
  });

  static Catalog parse(Object? raw) {
    if (raw is! Map) throw const CatalogException('Katalog není objekt.');
    final j = obj(raw);
    final schema = integer(j['schema']);
    if (!supportedSchemas.contains(schema)) {
      throw CatalogException('Nepodporovaná verze katalogu (schema $schema).');
    }
    final base = schema == 1
        ? BaseUrls(pages: BaseUrls._slash(str(j['base_url'])))
        : BaseUrls.fromJson(obj(j['base_urls']));
    final packs = <CatalogPack>[];
    for (final p in objList(j['packs'])) {
      final audience = str(p['audience'], 'kids');
      final id = str(p['id']);
      if (id.isEmpty) continue;
      final free = p['free'] == true;
      final parts = objList(p['parts']).map(CatalogPart.fromJson).toList();
      packs.add(
        CatalogPack(
          id: id,
          type: strOrNull(p['type']) ?? typeForAudience(audience),
          n: integer(p['n']),
          title: str(p['title'], id),
          titleI18n: strMap(p['title_i18n']),
          free: free,
          productId: free ? null : strOrNull(p['product_id']),
          bundled: p['bundled'] == true,
          version: integer(p['version'], 1),
          stories: integer(p['stories']),
          bytes: integer(p['bytes']),
          audience: audience,
          languages: strList(p['languages']),
          cover: strOrNull(p['cover']),
          previews: strList(p['previews']),
          parts: parts,
        ),
      );
    }
    final packType = {for (final p in packs) p.id: p.type};
    final stories = [
      for (final s in objList(j['stories']))
        CatalogStory(
          id: str(s['id']),
          packId: str(s['pack_id']),
          type:
              strOrNull(s['type']) ??
              packType[str(s['pack_id'])] ??
              typeForAudience(str(s['audience'], 'kids')),
          worldId: str(s['world_id']),
          title: str(s['title']),
          titleI18n: strMap(s['title_i18n']),
          cover: strOrNull(s['cover']),
          episodes: integer(s['episodes']),
          audience: str(s['audience'], 'kids'),
        ),
    ];
    final types = objList(j['types']).map(CatalogType.fromJson).toList();
    // Every pack's type is listed, so the store can group by it (schema 1: derived types).
    for (final p in packs) {
      if (!types.any((t) => t.id == p.type)) {
        types.add(
          _knownTypes[p.type] ??
              CatalogType(id: p.type, audience: p.audience, titleI18n: {}),
        );
      }
    }
    return Catalog(
      schema: schema,
      version: integer(j['version']),
      generatedAt: date(j['generated_at']),
      baseUrls: base,
      types: types,
      packs: packs,
      bundles: objList(j['bundles']).map(CatalogBundle.fromJson).toList(),
      gamebooks: objList(j['gamebooks']).map(CatalogGamebook.fromJson).toList(),
      stories: stories,
    );
  }

  CatalogType? type(String id) {
    for (final t in types) {
      if (t.id == id) return t;
    }
    return null;
  }

  CatalogPack? pack(String id) {
    for (final p in packs) {
      if (p.id == id) return p;
    }
    return null;
  }

  CatalogBundle? bundle(String id) {
    for (final b in bundles) {
      if (b.id == id) return b;
    }
    return null;
  }

  List<CatalogPack> packsOfType(String type) => [
    for (final p in packs)
      if (p.type == type) p,
  ];

  List<CatalogStory> storiesOf(String packId) => [
    for (final s in stories)
      if (s.packId == packId) s,
  ];

  /// Audience of a type (types list, else any pack of it).
  String audienceOfType(String type) {
    final t = this.type(type);
    if (t != null) return t.audience;
    for (final p in packs) {
      if (p.type == type) return p.audience;
    }
    return 'kids';
  }

  /// Types a bundle unlocks today ("all" = every listed type; future ones join automatically).
  List<String> bundleTypes(CatalogBundle b) =>
      b.covers.all ? [for (final t in types) t.id] : b.covers.types;

  /// Every store product id of the catalog (for the product-details query).
  Set<String> get productIds => {
    for (final p in packs)
      if (!p.free && p.productId != null) p.productId!,
    for (final b in bundles) b.productId,
    for (final g in gamebooks) ...[g.productId, ?g.kitProductId],
  };
}
