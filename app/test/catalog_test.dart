// catalog.json schema 1 and 2, URL composition from base_urls, CatalogRepository cache/refresh.

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:webtoon/shop/catalog.dart';
import 'package:webtoon/shop/catalog_repository.dart';

import 'shop_fakes.dart';

Map<String, dynamic> schema1() => {
  'schema': 1,
  'version': 3,
  'generated_at': '2026-10-23T08:00:00Z',
  'base_url': 'https://lioilsources.github.io/webtoon-content',
  'packs': [
    {
      'id': 'romance-1',
      'title': 'Romance I',
      'stories': 2,
      'parts': [
        {'path': 'packs/romance-1-v1-a.zip', 'bytes': 10, 'sha256': 'AA'},
      ],
      'free': false,
      'product_id': 'pack_romance_1',
      'languages': ['cs'],
      'audience': 'adult',
      'version': 1,
    },
    {
      'id': 'kids-1',
      'title': 'Kids',
      'stories': 1,
      'parts': [],
      'free': true,
      'product_id': 'ignored_for_free',
      'languages': ['cs'],
      'audience': 'kids',
      'version': 1,
    },
  ],
  'stories': [
    {
      'id': 'cp_1',
      'pack_id': 'romance-1',
      'world_id': 'w',
      'title': 'One',
      'title_i18n': {'en': 'One EN'},
      'cover': 'covers/cp_1.webp',
      'episodes': 1,
      'audience': 'adult',
    },
  ],
};

void main() {
  group('Catalog.parse', () {
    test('schema 1: base_url → pages, path parts, type from audience', () {
      final c = Catalog.parse(schema1());
      expect(c.schema, 1);
      expect(c.version, 3);
      expect(
        c.baseUrls.pages,
        'https://lioilsources.github.io/webtoon-content/',
      );
      final r = c.pack('romance-1')!;
      expect(r.type, 'harlequin');
      expect(r.productId, 'pack_romance_1');
      expect(
        r.parts.single.urlFor(c.baseUrls),
        'https://lioilsources.github.io/webtoon-content/packs/romance-1-v1-a.zip',
      );
      expect(r.parts.single.sha256, 'aa');
      final k = c.pack('kids-1')!;
      expect(k.free, isTrue);
      expect(k.productId, isNull, reason: 'a free pack never has a product');
      expect(k.type, 'kids');
      expect(c.types.map((t) => t.id), containsAll(['harlequin', 'kids']));
      expect(c.type('harlequin')!.audience, 'adult');
      expect(c.stories.single.type, 'harlequin');
      expect(c.stories.single.titleIn('en'), 'One EN');
      expect(c.bundles, isEmpty);
      expect(c.productIds, {'pack_romance_1'});
    });

    test('schema 2: types, release parts, bundles, gamebooks, product ids', () {
      final c = testCatalog();
      expect(c.schema, 2);
      expect(c.types.map((t) => t.id).toList(), [
        'kids',
        'superhero',
        'harlequin',
      ]);
      expect(c.type('kids')!.titleIn('en'), 'Kids');
      expect(c.type('kids')!.titleIn('ja'), 'Kids', reason: 'English fallback');
      final k = c.pack('kids-1')!;
      expect(k.type, 'kids');
      expect(k.parts.map((p) => p.part), ['a', 'b']);
      expect(
        k.parts.first.urlFor(c.baseUrls),
        'https://example.test/releases/download/pack-kids-1-v1/kids-1-a.zip',
      );
      expect(k.totalBytes, 2000);
      expect(c.pack('superhero-1')!.free, isTrue);
      expect(c.bundle('bundle_all')!.covers.all, isTrue);
      expect(c.bundle('bundle_kids')!.covers.types, ['kids']);
      expect(c.bundleTypes(c.bundle('bundle_all')!), [
        'kids',
        'superhero',
        'harlequin',
      ]);
      expect(c.gamebooks.single.kitProductId, 'kit_drak');
      expect(c.productIds, {
        'pack_kids_1',
        'pack_harlequin_1',
        'bundle_kids',
        'bundle_harlequin',
        'bundle_all',
        'gamebook_drak',
        'kit_drak',
      });
      expect(c.storiesOf('kids-1').single.id, 'cp_k1');
      expect(
        c.baseUrls.page('covers/x.webp'),
        'https://example.test/content/covers/x.webp',
      );
    });

    test('r2 wins over releases; an explicit part url wins over both', () {
      final j = catalogJson();
      (j['base_urls'] as Map)['r2'] = 'https://cdn.example.test';
      ((j['packs'] as List).first as Map)['parts'] = [
        part('kids', 1, 'a'),
        {...part('kids', 1, 'b'), 'url': 'https://mirror.test/b.zip'},
      ];
      final c = Catalog.parse(j);
      final parts = c.pack('kids-1')!.parts;
      expect(
        parts[0].urlFor(c.baseUrls),
        'https://cdn.example.test/pack-kids-1-v1/kids-1-a.zip',
      );
      expect(parts[1].urlFor(c.baseUrls), 'https://mirror.test/b.zip');
    });

    test('unknown schema and non-objects are refused', () {
      expect(
        () => Catalog.parse({'schema': 3}),
        throwsA(isA<CatalogException>()),
      );
      expect(() => Catalog.parse([]), throwsA(isA<CatalogException>()));
    });
  });

  group('CatalogRepository', () {
    late Directory tmp;
    setUp(() => tmp = Directory.systemTemp.createTempSync('webtoon_catalog_'));
    tearDown(() => tmp.deleteSync(recursive: true));

    CatalogRepository repo(http.Client client) => CatalogRepository(
      client: client,
      url: 'https://default.test/catalog.json',
      cacheDir: () async => tmp,
    );

    test(
      'first refresh caches; offline later returns the cached copy',
      () async {
        final urls = <String>[];
        var online = true;
        final client = MockClient((req) async {
          urls.add(req.url.toString());
          if (!online) throw const SocketException('offline');
          return http.Response.bytes(
            utf8.encode(jsonEncode(catalogJson(version: 5))),
            200,
          );
        });
        final r = repo(client);
        expect(await r.loadCached(), isNull);
        final c = await r.refresh();
        expect(c.version, 5);
        expect(File('${tmp.path}/catalog.json').existsSync(), isTrue);
        expect(urls.single, 'https://default.test/catalog.json');

        online = false;
        final r2 = repo(client);
        expect((await r2.loadCached())!.version, 5);
        expect(
          r2.refreshUrl,
          'https://example.test/content/catalog.json',
          reason: 'the cached base_urls.pages decides',
        );
        expect((await r2.refresh()).version, 5);
      },
    );

    test('an older catalog never replaces a newer cache', () async {
      var serve = 7;
      final client = MockClient(
        (req) async => http.Response.bytes(
          utf8.encode(jsonEncode(catalogJson(version: serve))),
          200,
        ),
      );
      final r = repo(client);
      expect((await r.refresh()).version, 7);
      serve = 6;
      expect((await r.refresh()).version, 7);
      expect((await repo(client).loadCached())!.version, 7);
      serve = 8;
      expect((await r.refresh()).version, 8);
    });

    test('offline without a cache throws; HTTP errors too', () async {
      final r = repo(MockClient((_) async => http.Response('nope', 503)));
      await expectLater(r.refresh(), throwsA(anything));
    });
  });
}
