// Store test doubles: a schema-2 catalog, a catalog repository without network, a pack installer
// without files, and the provider overrides that make the reader app hermetic.

import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:webtoon/profile/parental_gate.dart';
import 'package:webtoon/profile/reader_profile.dart';
import 'package:webtoon/screens/store_screen.dart';
import 'package:webtoon/shop/catalog.dart';
import 'package:webtoon/shop/catalog_repository.dart';
import 'package:webtoon/shop/entitlements.dart';
import 'package:webtoon/shop/pack_downloader.dart';
import 'package:webtoon/shop/shop_controller.dart';
import 'package:webtoon/shop/store_gateway.dart';

import 'fake_api.dart' show kTinyPng;

Map<String, dynamic> part(String type, int n, String p, {int bytes = 1000}) => {
  'part': p,
  'release': 'pack-$type-$n-v1',
  'asset': '$type-$n-$p.zip',
  'bytes': bytes,
  'sha256': 'ab' * 32,
  'stories': 25,
};

Map<String, dynamic> pack(
  String type,
  int n, {
  String audience = 'kids',
  bool free = false,
  bool bundled = false,
  String? title,
}) => {
  'id': bundled ? 'starter' : '$type-$n',
  'type': type,
  'n': n,
  'title': title ?? '$type $n',
  'title_i18n': {'cs': title ?? '$type $n', 'en': title ?? '$type $n'},
  if (!free && !bundled) 'product_id': 'pack_${type}_$n',
  'free': free || bundled,
  'bundled': bundled,
  'version': 1,
  'stories': bundled ? 15 : 50,
  'audience': audience,
  'languages': ['cs', 'en'],
  'cover': 'covers/cp_${type}_$n.webp',
  'previews': [for (var i = 0; i < 4; i++) 'covers/cp_${type}_${n}_$i.webp'],
  'parts': bundled ? [] : [part(type, n, 'a'), part(type, n, 'b')],
};

/// Kids (paid), harlequin (paid, adult), superhero (free), the bundled starter, three bundles
/// and one gamebook.
Map<String, dynamic> catalogJson({
  int version = 5,
  List<Map<String, dynamic>>? extraPacks,
}) => {
  'schema': 2,
  'version': version,
  'generated_at': '2026-10-24T08:00:00Z',
  'base_urls': {
    'pages': 'https://example.test/content/',
    'releases': 'https://example.test/releases/download/',
    'r2': null,
  },
  'types': [
    {
      'id': 'kids',
      'title_i18n': {'cs': 'Pro děti', 'en': 'Kids'},
      'audience': 'kids',
      'icon': 'child_care',
    },
    {
      'id': 'superhero',
      'title_i18n': {'cs': 'Superhrdinové', 'en': 'Superheroes'},
      'audience': 'kids',
      'icon': 'bolt',
    },
    {
      'id': 'harlequin',
      'title_i18n': {'cs': 'Romantika', 'en': 'Romance'},
      'audience': 'adult',
      'icon': 'favorite',
    },
  ],
  'packs': [
    pack('kids', 1, title: 'Děti I'),
    pack('superhero', 1, free: true, title: 'Hrdinové I'),
    pack('harlequin', 1, audience: 'adult', title: 'Romance I'),
    ...?extraPacks,
  ],
  'bundles': [
    {
      'id': 'bundle_kids',
      'product_id': 'bundle_kids',
      'price_tier': 'bundle_type',
      'title_i18n': {'cs': 'Vše pro děti'},
      'covers': {
        'types': ['kids'],
      },
    },
    {
      'id': 'bundle_harlequin',
      'product_id': 'bundle_harlequin',
      'price_tier': 'bundle_type',
      'title_i18n': {'cs': 'Vše romantické'},
      'covers': {
        'types': ['harlequin'],
      },
    },
    {
      'id': 'bundle_all',
      'product_id': 'bundle_all',
      'price_tier': 'bundle_all',
      'title_i18n': {'cs': 'Úplně vše'},
      'covers': 'all',
    },
  ],
  'gamebooks': [
    {
      'id': 'drak',
      'product_id': 'gamebook_drak',
      'kit_product_id': 'kit_drak',
      'type': 'kids',
      'status': 'planned',
      'graph': null,
      'lore': null,
    },
  ],
  'stories': [
    {
      'id': 'cp_k1',
      'pack_id': 'kids-1',
      'type': 'kids',
      'world_id': 'w_k',
      'title': 'Drak a lucerna',
      'cover': 'covers/cp_k1.webp',
      'episodes': 1,
      'audience': 'kids',
    },
    {
      'id': 'cp_h1',
      'pack_id': 'harlequin-1',
      'type': 'harlequin',
      'world_id': 'w_h',
      'title': 'Santorini',
      'cover': 'covers/cp_h1.webp',
      'episodes': 1,
      'audience': 'adult',
    },
  ],
};

Catalog testCatalog({
  int version = 5,
  List<Map<String, dynamic>>? extraPacks,
}) => Catalog.parse(catalogJson(version: version, extraPacks: extraPacks));

/// No disk, no network: [catalog] is "downloaded"; null = offline with an empty cache.
class FakeCatalogRepository extends CatalogRepository {
  Catalog? catalog;
  int refreshes = 0;
  FakeCatalogRepository(this.catalog);

  @override
  Future<Catalog?> loadCached() async => null;

  @override
  Future<Catalog> refresh() async {
    refreshes++;
    if (catalog == null) throw Exception('offline');
    return catalog!;
  }
}

/// Installs instantly (two progress steps), remembers what is installed.
class FakeInstaller implements PackInstaller {
  final Set<String> installed;
  final List<String> downloads = [];
  Object? failWith;

  /// When set, the download waits for it (to see the progress state in a test).
  Completer<void>? gate;

  FakeInstaller([Set<String>? installed]) : installed = installed ?? {};

  @override
  Stream<DownloadProgress> download(
    Catalog catalog,
    CatalogPack pack,
    Entitlements e,
  ) async* {
    downloads.add(pack.id);
    if (!e.unlocksPack(catalog, pack)) throw StateError('not unlocked');
    yield DownloadProgress(
      packId: pack.id,
      phase: DownloadPhase.downloading,
      received: 500,
      total: 2000,
    );
    if (gate != null) await gate!.future;
    if (failWith != null) throw failWith!;
    installed.add(pack.id);
    yield DownloadProgress(
      packId: pack.id,
      phase: DownloadPhase.done,
      received: 2000,
      total: 2000,
    );
  }

  @override
  bool isInstalled(CatalogPack pack) => installed.contains(pack.id);

  @override
  Future<void> remove(CatalogPack pack) async => installed.remove(pack.id);
}

/// Overrides for a hermetic reader app: profile (null = first launch), fake store, fixed
/// parental-gate question 6 × 7 = 42, covers from memory.
List<Override> shopOverrides({
  ReaderProfile? profile = ReaderProfile.adults,
  Catalog? catalog,
  bool offline = false,
  FakeStoreGateway? gateway,
  FakeInstaller? installer,
  MemoryEntitlementStore? entitlements,
  MemoryProfileStore? profileStore,
}) => [
  profileStoreProvider.overrideWithValue(
    profileStore ?? MemoryProfileStore(profile),
  ),
  storeGatewayProvider.overrideWithValue(gateway ?? FakeStoreGateway()),
  catalogRepositoryProvider.overrideWithValue(
    FakeCatalogRepository(offline ? null : (catalog ?? testCatalog())),
  ),
  packInstallerProvider.overrideWithValue(installer ?? FakeInstaller()),
  entitlementStoreProvider.overrideWithValue(
    entitlements ?? MemoryEntitlementStore(),
  ),
  gateChallengeProvider.overrideWithValue(() => const GateChallenge(6, 7)),
  coverImageProvider.overrideWithValue((_) => MemoryImage(kTinyPng)),
];
