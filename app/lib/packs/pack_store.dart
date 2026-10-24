// Content packs (../PACK_FORMAT.md): zips with pack.json + media, extracted into the app's
// support directory. The reader works from these offline; nothing here talks to the backend.

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:isolate';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter/services.dart' show ByteData, rootBundle;
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../models/episode.dart';
import '../models/json.dart';
import '../models/world.dart';

/// Something is wrong with a pack (not a zip, bad schema, checksum mismatch, …).
class PackException implements Exception {
  final String message;
  const PackException(this.message);

  @override
  String toString() => message;
}

/// Extraction progress: [done] of [total] files written.
typedef PackProgress = void Function(int done, int total);

/// A story (= campaign) in a pack; `stories[]` of pack.json. [cover] is an absolute file path
/// (or null when the pack has none).
class PackStory {
  final String id;
  final String packId;
  final String worldId;
  final String title;
  final Map<String, String> titleI18n;
  final List<String> episodeIds;
  final String? cover;
  final List<String> languages;

  /// Pack type of the story (kids, harlequin, superhero, …); null in packs exported before
  /// catalog schema 2.
  final String? type;

  const PackStory({
    required this.id,
    required this.packId,
    required this.worldId,
    required this.title,
    this.titleI18n = const {},
    this.episodeIds = const [],
    this.cover,
    this.languages = const [],
    this.type,
  });

  String titleIn(String? lang) =>
      lang == null ? title : (titleI18n[lang] ?? title);
}

/// pack.json, with media paths resolved against the directory the pack is installed in.
class PackManifest {
  static const supportedSchema = 1;

  final int schema;
  final String id;
  final String title;
  final int version;

  /// `part` of a split pack (`"a"`, `"b"`, …); null for a single zip.
  final String? part;
  final DateTime? generatedAt;
  final List<WorldSummary> worlds;
  final List<PackStory> stories;
  final List<Episode> episodes;

  const PackManifest({
    required this.schema,
    required this.id,
    required this.title,
    required this.version,
    this.part,
    this.generatedAt,
    this.worlds = const [],
    this.stories = const [],
    this.episodes = const [],
  });

  /// Directory name under the packs root: `<id>` or `<id>-<part>`.
  String get dirName => part == null || part!.isEmpty ? id : '$id-$part';

  /// Parses pack.json. Relative `image_url` / `video_url` / `cover` paths become absolute
  /// paths under [dir] so the rest of the app never needs to know which pack a file is in.
  static PackManifest parse(Map<String, dynamic> j, {required String dir}) {
    final schema = integer(j['schema']);
    if (schema != supportedSchema) {
      throw PackException('Nepodporovaná verze balíčku (schema $schema).');
    }
    final id = str(j['id']);
    if (!RegExp(r'^[a-z0-9-]+$').hasMatch(id)) {
      throw PackException('Balíček má neplatné id „$id“.');
    }
    final part = strOrNull(j['part']);
    if (part != null && !RegExp(r'^[a-z0-9]+$').hasMatch(part)) {
      throw PackException('Balíček má neplatnou část „$part“.');
    }
    String? media(Object? v) {
      final s = strOrNull(v);
      if (s == null) return null;
      if (s.startsWith('http://') || s.startsWith('https://')) return s;
      if (p.isAbsolute(s)) return s;
      return p.join(dir, s);
    }

    final episodes = <Episode>[];
    for (final e in objList(j['episodes'])) {
      final panels = [
        for (final panel in objList(e['panels']))
          {
            ...panel,
            'image_url': media(panel['image_url']),
            'video_url': media(panel['video_url']),
          },
      ];
      episodes.add(Episode.fromJson({...e, 'panels': panels}));
    }
    return PackManifest(
      schema: schema,
      id: id,
      title: str(j['title'], id),
      version: integer(j['version']),
      part: part,
      generatedAt: date(j['generated_at']),
      worlds: objList(j['worlds']).map(WorldSummary.fromJson).toList(),
      stories: [
        for (final s in objList(j['stories']))
          PackStory(
            id: str(s['id']),
            packId: id,
            worldId: str(s['world_id']),
            title: str(s['title']),
            titleI18n: strMap(s['title_i18n']),
            episodeIds: strList(s['episodes']),
            cover: media(s['cover']),
            languages: strList(s['languages']),
            type: strOrNull(s['type']),
          ),
      ],
      episodes: episodes,
    );
  }
}

/// A pack (or one part of a split pack) on disk.
class InstalledPack {
  final Directory dir;
  final PackManifest manifest;
  const InstalledPack(this.dir, this.manifest);

  String get id => manifest.id;
}

/// Installs packs and keeps every installed pack.json in memory (a few hundred episodes is
/// fine). Packs live in `<application support>/packs/<id>[-<part>]/`.
class PackStore {
  static const starterAsset = 'assets/packs/starter.zip';
  static const starterId = 'starter';

  Directory? _root;
  final Future<ByteData> Function(String key) _loadAsset;

  List<InstalledPack> _packs = const [];
  bool _loaded = false;

  /// [root] defaults to `getApplicationSupportDirectory()/packs`; tests pass a temp dir.
  /// [loadAsset] defaults to the app bundle.
  PackStore({Directory? root, Future<ByteData> Function(String key)? loadAsset})
    : _loadAsset = loadAsset ?? rootBundle.load {
    _root = root;
  }

  Future<Directory> rootDir() async {
    _root ??= Directory(
      p.join((await getApplicationSupportDirectory()).path, 'packs'),
    );
    return _root!;
  }

  /// True once [load] has run (even when nothing is installed).
  bool get loaded => _loaded;

  /// Every installed pack / part, in install order (starter first when present).
  List<InstalledPack> get packs => _packs;

  /// Worlds across all packs, de-duplicated by id (the first pack wins).
  List<WorldSummary> get worlds {
    final seen = <String>{};
    return [
      for (final pk in _packs)
        for (final w in pk.manifest.worlds)
          if (seen.add(w.id)) w,
    ];
  }

  /// Stories across all packs, in pack order (= library order).
  List<PackStory> get stories {
    final seen = <String>{};
    return [
      for (final pk in _packs)
        for (final s in pk.manifest.stories)
          if (seen.add(s.id)) s,
    ];
  }

  WorldSummary? world(String id) {
    for (final w in worlds) {
      if (w.id == id) return w;
    }
    return null;
  }

  PackStory? story(String id) {
    for (final s in stories) {
      if (s.id == id) return s;
    }
    return null;
  }

  Episode? episode(String id) {
    for (final pk in _packs) {
      for (final e in pk.manifest.episodes) {
        if (e.id == id) return e;
      }
    }
    return null;
  }

  InstalledPack? installed(String id, {String? part}) {
    for (final pk in _packs) {
      if (pk.id == id && (part == null || pk.manifest.part == part)) return pk;
    }
    return null;
  }

  /// Reads every `<root>/*/pack.json`. Directories without a readable pack.json are skipped
  /// (a crashed install leaves only `.tmp-*`, which is removed here).
  Future<void> load() async {
    final root = await rootDir();
    final packs = <InstalledPack>[];
    if (await root.exists()) {
      final dirs = await root.list().where((e) => e is Directory).toList();
      dirs.sort((a, b) => a.path.compareTo(b.path));
      for (final d in dirs) {
        final name = p.basename(d.path);
        if (name.startsWith('.tmp-')) {
          await d.delete(recursive: true);
          continue;
        }
        final f = File(p.join(d.path, 'pack.json'));
        if (!await f.exists()) continue;
        try {
          final j = obj(jsonDecode(await f.readAsString()));
          packs.add(
            InstalledPack(d as Directory, PackManifest.parse(j, dir: d.path)),
          );
        } on FormatException {
          continue;
        } on PackException {
          continue;
        }
      }
    }
    // Starter first, then the rest alphabetically — the library follows this order.
    packs.sort((a, b) {
      final sa = a.id == starterId ? 0 : 1, sb = b.id == starterId ? 0 : 1;
      return sa != sb ? sa - sb : a.dir.path.compareTo(b.dir.path);
    });
    _packs = packs;
    _loaded = true;
  }

  /// Installs the zip at [path]. With [expectedSha256] (hex, from catalog.json) the file is
  /// checked first. Replaces an installed pack with the same id and part, then reloads.
  Future<InstalledPack> installFromFile(
    String path, {
    String? expectedSha256,
    PackProgress? onProgress,
  }) async {
    final f = File(path);
    if (!await f.exists()) throw PackException('Soubor $path neexistuje.');
    return installFromBytes(
      await f.readAsBytes(),
      expectedSha256: expectedSha256,
      onProgress: onProgress,
    );
  }

  /// Installs a bundled zip (e.g. [starterAsset]).
  Future<InstalledPack> installFromAsset(
    String key, {
    PackProgress? onProgress,
  }) async {
    final data = await _loadAsset(key);
    return installFromBytes(
      data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes),
      onProgress: onProgress,
    );
  }

  Future<InstalledPack> installFromBytes(
    Uint8List bytes, {
    String? expectedSha256,
    PackProgress? onProgress,
  }) async {
    if (expectedSha256 != null) {
      final got = sha256.convert(bytes).toString();
      if (got != expectedSha256.toLowerCase()) {
        throw const PackException(
          'Stažený balíček je poškozený (kontrolní součet nesouhlasí).',
        );
      }
    }
    final root = await rootDir();
    await root.create(recursive: true);
    // Validate before touching the disk: parsing is cheap, the manifest is small.
    final manifest = PackManifest.parse(peekManifest(bytes), dir: '');
    final tmp = Directory(
      p.join(
        root.path,
        '.tmp-${manifest.dirName}-${DateTime.now().millisecondsSinceEpoch}',
      ),
    );
    await tmp.create(recursive: true);
    try {
      await _extractInIsolate(bytes, tmp.path, onProgress);
    } catch (e) {
      await tmp.delete(recursive: true);
      if (e is PackException) rethrow;
      throw PackException('Balíček se nepodařilo rozbalit: $e');
    }
    final target = Directory(p.join(root.path, manifest.dirName));
    if (await target.exists()) await target.delete(recursive: true);
    await tmp.rename(target.path);
    await load();
    return installed(manifest.id, part: manifest.part)!;
  }

  /// Removes every part of pack [id] and reloads.
  Future<void> remove(String id) async {
    for (final pk in _packs.where((pk) => pk.id == id).toList()) {
      if (await pk.dir.exists()) await pk.dir.delete(recursive: true);
    }
    await load();
  }

  /// Bytes on disk under the packs root.
  Future<int> storageBytes() async {
    final root = await rootDir();
    if (!await root.exists()) return 0;
    var total = 0;
    await for (final e in root.list(recursive: true, followLinks: false)) {
      if (e is File) total += await e.length();
    }
    return total;
  }

  /// The bundled starter's manifest (version check without extracting); null when the asset
  /// is missing or not a pack.
  Future<PackManifest?> starterManifest() async {
    final Uint8List bytes;
    try {
      bytes = await _assetBytes(starterAsset);
    } catch (_) {
      return null;
    }
    try {
      return PackManifest.parse(peekManifest(bytes), dir: '');
    } on PackException {
      return null;
    }
  }

  /// Extracts the bundled starter on first launch, or when the bundled version is newer than
  /// the installed one (pack.json `version`); [force] re-extracts regardless. Loads the packs
  /// either way. Returns true when the starter was (re)installed.
  Future<bool> ensureStarter({
    PackProgress? onProgress,
    bool force = false,
  }) async {
    if (!_loaded) await load();
    final Uint8List bytes;
    try {
      bytes = await _assetBytes(starterAsset);
    } catch (_) {
      return false; // no starter bundled (dev build without assets/packs/starter.zip)
    }
    final PackManifest bundled;
    try {
      bundled = PackManifest.parse(peekManifest(bytes), dir: '');
    } on PackException {
      return false; // placeholder or broken asset: keep what is installed
    }
    final current = installed(bundled.id, part: bundled.part);
    if (!force &&
        current != null &&
        current.manifest.version >= bundled.version) {
      return false;
    }
    await installFromBytes(bytes, onProgress: onProgress);
    return true;
  }

  Future<Uint8List> _assetBytes(String key) async {
    final data = await _loadAsset(key);
    return data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes);
  }

  /// pack.json out of a zip in memory, without extracting anything else.
  static Map<String, dynamic> peekManifest(Uint8List bytes) {
    final Archive archive;
    try {
      archive = ZipDecoder().decodeBytes(bytes, verify: false);
    } catch (_) {
      throw const PackException('Soubor není platný zip balíček.');
    }
    final entry = archive.files.where((f) => f.isFile && f.name == 'pack.json');
    if (entry.isEmpty) {
      throw const PackException('V balíčku chybí pack.json.');
    }
    final text = utf8.decode(entry.first.readBytes() ?? Uint8List(0));
    try {
      return obj(jsonDecode(text));
    } on FormatException {
      throw const PackException('pack.json není platný JSON.');
    }
  }

  /// Writes every file of the zip under [dir] on a background isolate; progress comes back
  /// over a port so the splash can show it.
  static Future<void> _extractInIsolate(
    Uint8List bytes,
    String dir,
    PackProgress? onProgress,
  ) async {
    final port = ReceivePort();
    final sub = port.listen((msg) {
      if (msg is List && msg.length == 2 && onProgress != null) {
        onProgress(msg[0] as int, msg[1] as int);
      }
    });
    try {
      await _runExtract(bytes, dir, port.sendPort);
    } finally {
      await sub.cancel();
      port.close();
    }
  }

  /// Separate method on purpose: the closure given to [Isolate.run] carries its whole
  /// lexical scope to the isolate, and here that scope is only sendable values. Inlined in
  /// [_extractInIsolate] it would drag `onProgress` (a closure into the widget tree) along
  /// and fail with "object is unsendable".
  static Future<void> _runExtract(Uint8List bytes, String dir, SendPort send) =>
      Isolate.run(() => extractZip(bytes, dir, send));

  /// Extracts [bytes] into [dir]. Entries that would escape [dir] are refused.
  /// Runs in an isolate; [progress] receives `[done, total]`.
  static void extractZip(Uint8List bytes, String dir, SendPort? progress) {
    final archive = ZipDecoder().decodeBytes(bytes, verify: false);
    final files = archive.files.where((f) => f.isFile).toList();
    var done = 0;
    for (final f in files) {
      final rel = p.posix.normalize(f.name);
      if (rel.startsWith('/') || rel == '..' || rel.startsWith('../')) {
        throw PackException('Balíček obsahuje nepovolenou cestu „${f.name}“.');
      }
      final out = File(p.joinAll([dir, ...p.posix.split(rel)]));
      out.parent.createSync(recursive: true);
      out.writeAsBytesSync(f.readBytes() ?? Uint8List(0));
      done++;
      if (progress != null && (done % 8 == 0 || done == files.length)) {
        progress.send([done, files.length]);
      }
    }
  }
}

/// "12,3 MB" for the settings screen.
String formatBytes(int bytes) {
  if (bytes < 1024) return '$bytes B';
  final kb = bytes / 1024;
  if (kb < 1024) return '${kb.toStringAsFixed(0)} kB';
  final mb = kb / 1024;
  if (mb < 1024) return '${mb.toStringAsFixed(1).replaceAll('.', ',')} MB';
  return '${(mb / 1024).toStringAsFixed(2).replaceAll('.', ',')} GB';
}
