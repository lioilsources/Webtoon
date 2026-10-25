import 'dart:convert';
import 'dart:io';
import 'dart:isolate';
import 'dart:typed_data';

import 'package:archive/archive.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter/painting.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/api/local_webtoon_api.dart';
import 'package:webtoon/api/webtoon_api.dart';
import 'package:webtoon/models/episode.dart';
import 'package:webtoon/packs/pack_store.dart';

import 'pack_fixture.dart';

void main() {
  late Directory tmp;
  late PackStore store;

  setUp(() {
    tmp = Directory.systemTemp.createTempSync('webtoon_packs_');
    store = PackStore(root: Directory('${tmp.path}/packs'));
  });

  tearDown(() => tmp.deleteSync(recursive: true));

  group('PackStore', () {
    test('installs a zip into packs/<id>/ and loads pack.json', () async {
      final zip = writeFixtureZip(tmp);
      final pk = await store.installFromFile(zip.path);

      expect(pk.id, 'fixture');
      expect(pk.dir.path, '${tmp.path}/packs/fixture');
      expect(File('${pk.dir.path}/pack.json').existsSync(), isTrue);
      expect(File('${pk.dir.path}/media/ep_j1/p00.webp').existsSync(), isTrue);
      expect(File('${pk.dir.path}/covers/cp_sova.webp').existsSync(), isTrue);
      expect(
        Directory('${tmp.path}/packs').listSync().map((e) => e.path),
        ['${tmp.path}/packs/fixture'],
        reason: 'no .tmp-* left behind',
      );

      expect(store.loaded, isTrue);
      expect(store.packs, hasLength(1));
      expect(store.worlds.map((w) => w.id), ['w_les']);
      expect(store.worlds.single.audience, 'kids');
      expect(store.stories.map((s) => s.id), ['cp_jezek', 'cp_sova']);
      expect(store.story('cp_jezek')!.episodeIds, ['ep_j1', 'ep_j2']);
      expect(
        store.story('cp_jezek')!.titleIn('en'),
        'The Hedgehog and the Lantern',
      );
      expect(
        store.story('cp_jezek')!.cover,
        '${pk.dir.path}/covers/cp_jezek.webp',
      );
      expect(store.episode('ep_s1'), isNotNull);
      expect(store.episode('nope'), isNull);
    });

    test(
      'relative media paths become absolute files in the pack dir',
      () async {
        await store.installFromFile(writeFixtureZip(tmp).path);
        final ep = store.episode('ep_j1')!;
        final dir = store.packs.single.dir.path;
        expect(ep.panels[0].imageUrl, '$dir/media/ep_j1/p00.webp');
        expect(ep.panels[0].videoUrl, '$dir/media/ep_j1/p00_loop.webp');
        expect(ep.panels[0].hasVideo, isTrue);
        expect(ep.panels[1].imageUrl, '$dir/media/ep_j1/p01.webp');
        expect(ep.panels[1].videoUrl, isNull);
        for (final p in ep.panels) {
          expect(File(p.imageUrl!).existsSync(), isTrue, reason: p.imageUrl);
        }
        // Everything else is parsed by the existing models.
        expect(ep.status, EpisodeStatus.ready);
        expect(ep.needsPolling, isFalse);
        expect(
          ep.panels[0].bubbles.single.textIn('en'),
          'Where is my lantern?',
        );
        expect(ep.choices.map((c) => c.id), ['c1', 'c2', 'free']);
        expect(ep.languages, ['en']);
        expect(ep.displayLanguage('en'), 'en');
        expect(store.episode('ep_j2')!.chosen!.choiceId, 'c2');
      },
    );

    test(
      'load() picks up what is on disk; a stale .tmp dir is removed',
      () async {
        await store.installFromFile(writeFixtureZip(tmp).path);
        Directory(
          '${tmp.path}/packs/.tmp-fixture-1',
        ).createSync(recursive: true);
        Directory('${tmp.path}/packs/junk').createSync(recursive: true);

        final again = PackStore(root: Directory('${tmp.path}/packs'));
        expect(again.loaded, isFalse);
        await again.load();
        expect(again.packs.map((p) => p.id), ['fixture']);
        expect(
          again.episode('ep_j1')!.panels[0].imageUrl,
          endsWith('p00.webp'),
        );
        expect(
          Directory('${tmp.path}/packs/.tmp-fixture-1').existsSync(),
          isFalse,
        );
      },
    );

    test('sha256 is verified; a mismatch installs nothing', () async {
      final zip = writeFixtureZip(tmp);
      final bytes = zip.readAsBytesSync();
      await expectLater(
        store.installFromFile(zip.path, expectedSha256: 'deadbeef'),
        throwsA(isA<PackException>()),
      );
      expect(Directory('${tmp.path}/packs/fixture').existsSync(), isFalse);

      final ok = sha256.convert(bytes).toString().toUpperCase();
      final pk = await store.installFromFile(zip.path, expectedSha256: ok);
      expect(pk.id, 'fixture');
    });

    test(
      'rejects a wrong schema, a missing pack.json and path traversal',
      () async {
        final bad = fixtureManifest()..['schema'] = 2;
        await expectLater(
          store.installFromBytes(fixtureZip(bad)),
          throwsA(
            isA<PackException>().having(
              (e) => e.message,
              'message',
              contains('schema 2'),
            ),
          ),
        );

        final noManifest = ZipEncoder().encodeBytes(
          Archive()..addFile(ArchiveFile.string('readme.txt', 'hi')),
        );
        await expectLater(
          store.installFromBytes(noManifest),
          throwsA(isA<PackException>()),
        );

        await expectLater(
          store.installFromBytes(Uint8List.fromList(utf8.encode('not a zip'))),
          throwsA(isA<PackException>()),
        );

        final evil = Archive()
          ..addFile(
            ArchiveFile.string('pack.json', jsonEncode(fixtureManifest())),
          )
          ..addFile(ArchiveFile.string('../escape.txt', 'x'));
        await expectLater(
          store.installFromBytes(ZipEncoder().encodeBytes(evil)),
          throwsA(isA<PackException>()),
        );
        expect(File('${tmp.path}/escape.txt').existsSync(), isFalse);
        expect(File('${tmp.path}/packs/escape.txt').existsSync(), isFalse);
        expect(Directory('${tmp.path}/packs').listSync(), isEmpty);
      },
    );

    test(
      'reinstalling the same id replaces it; parts get their own dir',
      () async {
        await store.installFromBytes(fixtureZip(fixtureManifest(version: 1)));
        await store.installFromBytes(fixtureZip(fixtureManifest(version: 2)));
        expect(store.packs.single.manifest.version, 2);

        final partA = fixtureManifest(id: 'romance-1')..['part'] = 'a';
        await store.installFromBytes(fixtureZip(partA));
        expect(
          Directory(
            '${tmp.path}/packs',
          ).listSync().map((e) => e.path.split('/').last).toList()..sort(),
          ['fixture', 'romance-1-a'],
        );
        expect(store.installed('romance-1', part: 'a'), isNotNull);
        // Same story ids in both packs: the first pack wins, nothing is listed twice.
        expect(store.stories.map((s) => s.id), ['cp_jezek', 'cp_sova']);

        await store.remove('romance-1');
        expect(store.packs.map((p) => p.id), ['fixture']);
      },
    );

    test(
      'ensureStarter: first launch extracts, same version does not, newer does',
      () async {
        var version = 1;
        var loads = 0;
        final s = PackStore(
          root: Directory('${tmp.path}/packs'),
          loadAsset: (key) async {
            loads++;
            expect(key, PackStore.starterAsset);
            return ByteData.sublistView(
              fixtureZip(fixtureManifest(id: 'starter', version: version)),
            );
          },
        );
        final progress = <(int, int)>[];
        expect(
          await s.ensureStarter(onProgress: (d, t) => progress.add((d, t))),
          isTrue,
        );
        expect(s.installed('starter')!.manifest.version, 1);
        expect(progress, isNotEmpty);
        expect(progress.last.$1, progress.last.$2);

        expect(await s.ensureStarter(), isFalse, reason: 'same version');
        expect(await s.ensureStarter(force: true), isTrue, reason: 'forced');

        version = 2;
        expect(await s.ensureStarter(), isTrue, reason: 'newer bundled');
        expect(s.installed('starter')!.manifest.version, 2);
        expect(await s.storageBytes(), greaterThan(0));
        expect(loads, 4);
      },
    );

    test(
      'onProgress may capture unsendable objects (extraction runs in an isolate)',
      () async {
        // In the app onProgress closes over the StateNotifier / widget tree, which cannot be
        // sent to an isolate; the extraction closure must not capture it.
        final unsendable = ReceivePort();
        var calls = 0;
        try {
          await store.installFromBytes(
            fixtureZip(fixtureManifest()),
            onProgress: (d, t) {
              calls++;
              unsendable.sendPort; // keep the capture
            },
          );
        } finally {
          unsendable.close();
        }
        expect(calls, greaterThan(0));
        expect(store.packs, hasLength(1));
      },
    );

    test(
      'ensureStarter without a usable asset keeps what is installed',
      () async {
        final s = PackStore(
          root: Directory('${tmp.path}/packs'),
          loadAsset: (_) async => throw Exception('asset not found'),
        );
        expect(await s.ensureStarter(), isFalse);
        expect(s.loaded, isTrue);
        expect(s.packs, isEmpty);

        final placeholder = PackStore(
          root: Directory('${tmp.path}/packs'),
          loadAsset: (_) async => ByteData.sublistView(
            ZipEncoder().encodeBytes(
              Archive()..addFile(
                ArchiveFile.string(
                  'pack.json',
                  '{"schema": 1, "id": "starter", "version": 0}',
                ),
              ),
            ),
          ),
        );
        expect(await placeholder.ensureStarter(), isTrue);
        expect(placeholder.stories, isEmpty);
      },
    );
  });

  group('LocalWebtoonApi', () {
    late LocalWebtoonApi api;

    setUp(() async {
      await store.installFromFile(writeFixtureZip(tmp).path);
      api = LocalWebtoonApi(store);
    });

    test('cannot edit; worlds and stories map to the reader models', () async {
      expect(api.canEdit, isFalse);
      final worlds = await api.listWorlds();
      expect(worlds.map((w) => w.id), ['w_les']);
      final w = await api.getWorld('w_les');
      expect(w.title, 'Les za humny');
      expect(w.audience, 'kids');
      expect(w.permissions.maxEpisodes, 0);

      final campaigns = await api.listCampaigns();
      expect(campaigns.map((c) => c.id), ['cp_jezek', 'cp_sova']);
      final jezek = campaigns.first;
      expect(jezek.title, 'Ježek a lucerna');
      expect(jezek.worldTitle, 'Les za humny');
      expect(jezek.episodes, 2);
      expect(jezek.status, 'ready');
      expect(jezek.lastEpisodeStatus, 'ready');
      expect(await api.listCampaigns(worldId: 'w_other'), isEmpty);
    });

    test('campaign has the episodes in order with their chosen', () async {
      final c = await api.getCampaign('cp_jezek');
      expect(c.worldId, 'w_les');
      expect(c.playerId, api.userId, reason: 'the reader is the player');
      expect(c.episodes.map((e) => e.id), ['ep_j1', 'ep_j2']);
      expect(c.episodes.map((e) => e.index), [1, 2]);
      expect(c.episodes[0].title, 'Ztracené světlo');
      expect(c.episodes[0].titleIn('en'), 'The Lost Light');
      expect(c.episodes[0].status, EpisodeStatus.ready);
      expect(c.episodes[0].chosen, isNull);
      expect(c.episodes[1].chosen!.text, 'Zeptat se sovy.');
      await expectLater(
        api.getCampaign('cp_missing'),
        throwsA(isA<ApiException>()),
      );
    });

    test('episode and images come from the pack dir', () async {
      final ep = await api.getEpisode('ep_j1');
      expect(ep.panels, hasLength(2));
      expect(ep.panels[1].sfx.single.text, 'ŠUST');
      final img = api.panelImage(ep.panels[0].imageUrl!);
      expect(img, isA<FileImage>());
      expect((img as FileImage).file.existsSync(), isTrue);
      expect(api.panelImage('https://x/y.png'), isA<NetworkImage>());
      await expectLater(api.getEpisode('ep_zzz'), throwsA(isA<ApiException>()));
    });

    test('generation and author calls are unsupported', () async {
      await expectLater(
        api.createCampaign(worldId: 'w_les'),
        throwsA(isA<UnsupportedError>()),
      );
      await expectLater(
        api.continueCampaign('cp_jezek', choiceId: 'c1'),
        throwsA(isA<UnsupportedError>()),
      );
      await expectLater(
        api.updateBubbles('ep_j1', 0, const []),
        throwsA(isA<UnsupportedError>()),
      );
      await expectLater(
        api.regeneratePanel('ep_j1', 0),
        throwsA(isA<UnsupportedError>()),
      );
      await expectLater(
        api.updatePanelMotion('ep_j1', 0, const {}),
        throwsA(isA<UnsupportedError>()),
      );
      await expectLater(api.listMyWorlds(), throwsA(isA<UnsupportedError>()));
      await expectLater(
        api.createWorld(title: 'x', styleId: 'y'),
        throwsA(isA<UnsupportedError>()),
      );
    });
  });

  test('formatBytes', () {
    expect(formatBytes(512), '512 B');
    expect(formatBytes(20 * 1024), '20 kB');
    expect(formatBytes(12 * 1024 * 1024 + 300 * 1024), '12,3 MB');
  });
}
