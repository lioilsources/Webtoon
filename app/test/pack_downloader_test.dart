// PackDownloader against a local HTTP server: whole download, resume with Range after a dropped
// connection, bad sha256, entitlement check, already installed parts skipped.

import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/packs/pack_store.dart';
import 'package:webtoon/shop/catalog.dart';
import 'package:webtoon/shop/entitlements.dart';
import 'package:webtoon/shop/pack_downloader.dart';

import 'pack_fixture.dart';

/// Serves [files] by path with Range support; [cutFirst] drops the connection halfway through
/// the first response of each path.
class RangeServer {
  final Map<String, Uint8List> files;
  final bool cutFirst;
  final List<String?> ranges = [];
  final Set<String> _cut = {};
  late HttpServer _server;

  RangeServer(this.files, {this.cutFirst = false});

  String get base => 'http://${_server.address.host}:${_server.port}/';

  Future<void> start() async {
    _server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    _server.listen((req) async {
      final body = files[req.uri.path.substring(1)];
      final range = req.headers.value('range');
      ranges.add(range);
      if (body == null) {
        req.response.statusCode = 404;
        await req.response.close();
        return;
      }
      var start = 0;
      if (range != null) {
        start = int.parse(RegExp(r'bytes=(\d+)-').firstMatch(range)!.group(1)!);
        req.response.statusCode = 206;
        req.response.headers.set(
          'content-range',
          'bytes $start-${body.length - 1}/${body.length}',
        );
      }
      req.response.contentLength = body.length - start;
      if (cutFirst && _cut.add(req.uri.path)) {
        // Half the body, then the socket goes away.
        final socket = await req.response.detachSocket();
        socket.add(body.sublist(start, start + (body.length - start) ~/ 2));
        await socket.flush();
        socket.destroy();
        return;
      }
      req.response.add(body.sublist(start));
      await req.response.close();
    });
  }

  Future<void> stop() => _server.close(force: true);
}

Uint8List partZip(String part) {
  final m = fixtureManifest(id: 'kids-1');
  m['part'] = part;
  return fixtureZip(m);
}

Catalog catalogFor(
  String base,
  Map<String, Uint8List> zips, {
  String? badSha,
}) => Catalog.parse({
  'schema': 2,
  'version': 1,
  'base_urls': {'pages': base, 'releases': base, 'r2': null},
  'packs': [
    {
      'id': 'kids-1',
      'type': 'kids',
      'title': 'Kids 1',
      'product_id': 'pack_kids_1',
      'version': 1,
      'stories': 4,
      'audience': 'kids',
      'parts': [
        for (final e in zips.entries)
          {
            'part': e.key.substring(e.key.length - 5, e.key.length - 4),
            'release': 'pack-kids-1-v1',
            'asset': e.key.split('/').last,
            'bytes': e.value.length,
            'sha256': badSha ?? sha256.convert(e.value).toString(),
          },
      ],
    },
  ],
});

void main() {
  late Directory tmp;
  late PackStore store;
  final owned = const Entitlements().grant(
    Receipt(productId: 'pack_kids_1', grantedAt: DateTime.utc(2026)),
  );
  final zips = {
    'pack-kids-1-v1/kids-1-a.zip': partZip('a'),
    'pack-kids-1-v1/kids-1-b.zip': partZip('b'),
  };

  setUp(() {
    tmp = Directory.systemTemp.createTempSync('webtoon_dl_');
    store = PackStore(root: Directory('${tmp.path}/packs'));
  });
  tearDown(() => tmp.deleteSync(recursive: true));

  PackDownloader downloader({int retries = 3}) => PackDownloader(
    store,
    downloadDir: () async => Directory('${tmp.path}/downloads'),
    retries: retries,
  );

  test('downloads every part, verifies, installs, reports progress', () async {
    final server = RangeServer(zips);
    await server.start();
    addTearDown(server.stop);
    final c = catalogFor(server.base, zips);
    final pack = c.pack('kids-1')!;
    final d = downloader();
    expect(d.isInstalled(pack), isFalse);
    final events = await d.download(c, pack, owned).toList();
    expect(events.last.phase, DownloadPhase.done);
    expect(events.last.fraction, 1);
    expect(events.map((e) => e.phase), containsAll(DownloadPhase.values));
    expect(
      events
          .where((e) => e.phase == DownloadPhase.downloading)
          .map((e) => e.part)
          .toSet(),
      {1, 2},
    );
    expect(store.installed('kids-1', part: 'a'), isNotNull);
    expect(store.installed('kids-1', part: 'b'), isNotNull);
    expect(d.isInstalled(pack), isTrue);
    expect(server.ranges, [null, null]);
    expect(
      Directory('${tmp.path}/downloads').listSync(),
      isEmpty,
      reason: 'temp files removed',
    );

    // Second run: nothing to fetch.
    server.ranges.clear();
    await d.download(c, pack, owned).toList();
    expect(server.ranges, isEmpty);

    await d.remove(pack);
    expect(d.isInstalled(pack), isFalse);
  });

  test('a dropped connection resumes with Range', () async {
    final server = RangeServer(zips, cutFirst: true);
    await server.start();
    addTearDown(server.stop);
    final c = catalogFor(server.base, zips);
    await downloader().download(c, c.pack('kids-1')!, owned).toList();
    expect(store.installed('kids-1', part: 'a'), isNotNull);
    expect(store.installed('kids-1', part: 'b'), isNotNull);
    final half = zips.values.first.length ~/ 2;
    expect(server.ranges, [
      null,
      'bytes=$half-',
      null,
      'bytes=${zips.values.last.length ~/ 2}-',
    ]);
  });

  test(
    'without retries the partial file stays and the next run resumes it',
    () async {
      final server = RangeServer(zips, cutFirst: true);
      await server.start();
      addTearDown(server.stop);
      final c = catalogFor(server.base, zips);
      final pack = c.pack('kids-1')!;
      await expectLater(
        downloader(retries: 0).download(c, pack, owned).toList(),
        throwsA(isA<PackException>()),
      );
      final partial = Directory(
        '${tmp.path}/downloads',
      ).listSync().whereType<File>().single;
      expect(partial.lengthSync(), zips.values.first.length ~/ 2);
      await downloader(retries: 0)
          .download(c, pack, owned)
          .toList()
          .catchError((_) => <DownloadProgress>[]);
      // Part a resumed and installed; part b was cut on its first request.
      expect(store.installed('kids-1', part: 'a'), isNotNull);
      expect(server.ranges.take(2), [
        null,
        'bytes=${zips.values.first.length ~/ 2}-',
      ]);
    },
  );

  test('bad sha256: nothing installed, the temp file is deleted', () async {
    final server = RangeServer(zips);
    await server.start();
    addTearDown(server.stop);
    final c = catalogFor(server.base, zips, badSha: '00' * 32);
    await expectLater(
      downloader().download(c, c.pack('kids-1')!, owned).toList(),
      throwsA(
        isA<PackException>().having(
          (e) => e.message,
          'message',
          contains('kontrolní součet'),
        ),
      ),
    );
    expect(store.packs, isEmpty);
    expect(Directory('${tmp.path}/downloads').listSync(), isEmpty);
  });

  test('no entitlement, no download (no request reaches the server)', () async {
    final server = RangeServer(zips);
    await server.start();
    addTearDown(server.stop);
    final c = catalogFor(server.base, zips);
    await expectLater(
      downloader()
          .download(c, c.pack('kids-1')!, const Entitlements())
          .toList(),
      throwsA(isA<PackException>()),
    );
    expect(server.ranges, isEmpty);
  });
}
