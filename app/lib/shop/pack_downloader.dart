// Downloads a pack's zips (GitHub Releases / R2, URL from the catalog's base_urls), resumable:
// each part goes to `<downloads>/<asset>.part`; a retry continues with an HTTP Range request.
// The finished file is checked against the catalog's sha256 and only then installed with
// PackStore.installFromFile. Only unlocked packs (free, owned, or covered by an owned bundle)
// are ever downloaded.

import 'dart:async';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../packs/pack_store.dart';
import 'catalog.dart';
import 'entitlements.dart';

enum DownloadPhase { downloading, verifying, installing, done }

class DownloadProgress {
  final String packId;
  final DownloadPhase phase;

  /// 1-based part being processed, of [parts].
  final int part;
  final int parts;
  final int received;
  final int total;

  const DownloadProgress({
    required this.packId,
    required this.phase,
    this.part = 0,
    this.parts = 0,
    this.received = 0,
    this.total = 0,
  });

  /// 0..1 over the whole pack; null when the size is unknown.
  double? get fraction => phase == DownloadPhase.done
      ? 1
      : (total > 0 ? (received / total).clamp(0, 1) : null);
}

/// The pack-level operations the store screen needs (a fake replaces it in widget tests).
abstract class PackInstaller {
  /// Downloads and installs every missing part; progress on the stream, errors as stream errors.
  Stream<DownloadProgress> download(
    Catalog catalog,
    CatalogPack pack,
    Entitlements entitlements,
  );

  /// All parts installed in (at least) the catalog's version.
  bool isInstalled(CatalogPack pack);

  /// Some version of the pack is on the device (an older one = an update is due).
  bool hasAnyVersion(CatalogPack pack);

  Future<void> remove(CatalogPack pack);
}

class PackDownloader implements PackInstaller {
  final PackStore store;
  final http.Client _client;
  final Future<Directory> Function() _dir;

  /// Extra attempts per part after a dropped connection (each resumes where it stopped).
  final int retries;

  PackDownloader(
    this.store, {
    http.Client? client,
    Future<Directory> Function()? downloadDir,
    this.retries = 3,
  }) : _client = client ?? http.Client(),
       _dir =
           downloadDir ??
           (() async => Directory(
             p.join((await getApplicationSupportDirectory()).path, 'downloads'),
           ));

  @override
  bool isInstalled(CatalogPack pack) {
    if (pack.parts.isEmpty) {
      final pk = store.installed(pack.id);
      return pk != null && pk.manifest.version >= pack.version;
    }
    return pack.parts.every(_partInstalled(pack));
  }

  bool Function(CatalogPart) _partInstalled(CatalogPack pack) => (part) {
    final pk = store.installed(pack.id, part: part.part);
    return pk != null && pk.manifest.version >= pack.version;
  };

  @override
  bool hasAnyVersion(CatalogPack pack) => store.installed(pack.id) != null;

  @override
  Future<void> remove(CatalogPack pack) => store.remove(pack.id);

  @override
  Stream<DownloadProgress> download(
    Catalog catalog,
    CatalogPack pack,
    Entitlements entitlements,
  ) {
    final out = StreamController<DownloadProgress>();
    () async {
      try {
        await _download(catalog, pack, entitlements, out.add);
      } catch (e, st) {
        out.addError(e, st);
      } finally {
        await out.close();
      }
    }();
    return out.stream;
  }

  Future<void> _download(
    Catalog catalog,
    CatalogPack pack,
    Entitlements entitlements,
    void Function(DownloadProgress) emit,
  ) async {
    if (pack.bundled) {
      throw const PackException('Tento balíček je součástí aplikace.');
    }
    if (!entitlements.unlocksPack(catalog, pack)) {
      throw const PackException('Balíček není odemčený.');
    }
    if (pack.parts.isEmpty) {
      throw const PackException('Balíček v katalogu nemá žádnou část.');
    }
    final dir = await _dir();
    await dir.create(recursive: true);
    final total = pack.totalBytes;
    var before = 0; // bytes of the parts already done
    final todo = pack.parts;
    for (var i = 0; i < todo.length; i++) {
      final part = todo[i];
      if (_partInstalled(pack)(part)) {
        before += part.bytes;
        continue;
      }
      void progress(DownloadPhase phase, int got) => emit(
        DownloadProgress(
          packId: pack.id,
          phase: phase,
          part: i + 1,
          parts: todo.length,
          received: before + got,
          total: total,
        ),
      );
      final file = File(
        p.join(dir.path, '${pack.id}-v${pack.version}-${part.fileName}.part'),
      );
      await _fetch(
        part.urlFor(catalog.baseUrls),
        file,
        part.bytes,
        (got) => progress(DownloadPhase.downloading, got),
      );
      progress(DownloadPhase.verifying, part.bytes);
      if (part.sha256.isNotEmpty) {
        final got = (await sha256.bind(file.openRead()).first).toString();
        if (got != part.sha256) {
          await file.delete();
          throw const PackException(
            'Stažený balíček je poškozený (kontrolní součet nesouhlasí).',
          );
        }
      }
      progress(DownloadPhase.installing, part.bytes);
      try {
        await store.installFromFile(file.path);
      } finally {
        if (await file.exists()) await file.delete();
      }
      before += part.bytes;
    }
    emit(
      DownloadProgress(
        packId: pack.id,
        phase: DownloadPhase.done,
        part: todo.length,
        parts: todo.length,
        received: total,
        total: total,
      ),
    );
  }

  /// Downloads [url] into [file], continuing an existing partial file with `Range`.
  Future<void> _fetch(
    String url,
    File file,
    int expected,
    void Function(int got) onBytes,
  ) async {
    for (var attempt = 0; ; attempt++) {
      try {
        await _fetchOnce(url, file, expected, onBytes);
        return;
      } on PackException {
        rethrow;
      } catch (e) {
        if (attempt >= retries) {
          throw PackException('Stahování se přerušilo: $e');
        }
      }
    }
  }

  Future<void> _fetchOnce(
    String url,
    File file,
    int expected,
    void Function(int got) onBytes,
  ) async {
    var have = await file.exists() ? await file.length() : 0;
    if (expected > 0 && have == expected) {
      return; // complete from an earlier run
    }
    if (expected > 0 && have > expected) {
      await file.delete();
      have = 0;
    }
    final req = http.Request('GET', Uri.parse(url));
    if (have > 0) req.headers['Range'] = 'bytes=$have-';
    final res = await _client.send(req);
    if (res.statusCode == 416 && have > 0) {
      await res.stream.drain<void>();
      return; // the server says we already have everything
    }
    final FileMode mode;
    if (res.statusCode == 206 && have > 0) {
      mode = FileMode.append;
    } else if (res.statusCode == 200) {
      mode = FileMode.write; // no range support: start over
      have = 0;
    } else {
      await res.stream.drain<void>();
      throw PackException('Stahování selhalo (HTTP ${res.statusCode}).');
    }
    final sink = file.openWrite(mode: mode);
    var got = have;
    onBytes(got);
    try {
      await for (final chunk in res.stream) {
        sink.add(chunk);
        got += chunk.length;
        onBytes(got);
      }
    } finally {
      await sink.flush();
      await sink.close();
    }
    if (expected > 0 && got < expected) {
      throw HttpException('spojení skončilo po $got z $expected B');
    }
  }
}
