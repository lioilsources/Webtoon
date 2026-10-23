// Builds the fixture pack (test/fixtures/pack.json + 1×1 PNGs for every media/cover path)
// as a zip, the way `webtoon export-pack` would.

import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:webtoon/packs/pack_store.dart';

import 'fake_api.dart' show kTinyPng;

/// pack.json of the fixture, optionally with another `version` / `id`.
Map<String, dynamic> fixtureManifest({int? version, String? id}) {
  final j =
      jsonDecode(File('test/fixtures/pack.json').readAsStringSync())
          as Map<String, dynamic>;
  if (version != null) j['version'] = version;
  if (id != null) j['id'] = id;
  return j;
}

/// Every media / cover path the manifest references.
List<String> mediaPaths(Map<String, dynamic> j) => [
  for (final s in (j['stories'] as List).cast<Map>())
    if (s['cover'] != null) s['cover'] as String,
  for (final e in (j['episodes'] as List).cast<Map>())
    for (final p in (e['panels'] as List).cast<Map>()) ...[
      if (p['image_url'] != null) p['image_url'] as String,
      if (p['video_url'] != null) p['video_url'] as String,
    ],
];

/// Zip bytes of [manifest] with a tiny PNG at every media path.
Uint8List fixtureZip(Map<String, dynamic> manifest) {
  final a = Archive();
  a.addFile(ArchiveFile.string('pack.json', jsonEncode(manifest)));
  for (final path in mediaPaths(manifest)) {
    a.addFile(ArchiveFile.bytes(path, kTinyPng));
  }
  return ZipEncoder().encodeBytes(a);
}

/// Writes the fixture zip into [dir] and returns it.
File writeFixtureZip(Directory dir, {int? version, String? id}) {
  final f = File('${dir.path}/fixture.zip');
  f.writeAsBytesSync(fixtureZip(fixtureManifest(version: version, id: id)));
  return f;
}

/// A store on a fresh temp dir with the fixture pack installed and loaded.
Future<(PackStore, Directory)> installedFixtureStore() async {
  final tmp = Directory.systemTemp.createTempSync('webtoon_packs_');
  final store = PackStore(root: Directory('${tmp.path}/packs'));
  await store.installFromFile(writeFixtureZip(tmp).path);
  return (store, tmp);
}
