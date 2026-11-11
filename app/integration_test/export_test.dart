// End-to-end check of the video export on a real platform (macOS, an iPhone simulator, an Android device):
// the first episode of the starter pack → mp4 with system voices, subtitles and music.
//
//   flutter test integration_test/export_test.dart -d macos
//
// Prints the path of the video (inside the app's container on macOS) as `EXPORT_RESULT <path>`.
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:path_provider/path_provider.dart';
import 'package:toonfork_export/toonfork_export.dart';
import 'package:webtoon/api/local_webtoon_api.dart';
import 'package:webtoon/export/export_plan.dart';
import 'package:webtoon/export/video_exporter.dart';
import 'package:webtoon/export/voices.dart';
import 'package:webtoon/packs/pack_store.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('starter episode → mp4 with dub, subtitles and music', (t) async {
    final root = Directory(
      '${(await getTemporaryDirectory()).path}/export_test_packs',
    );
    final store = PackStore(root: root);
    await t.runAsync(() async {
      await store.ensureStarter();
      await store.load();
    });
    final api = LocalWebtoonApi(store);
    late String path;
    await t.runAsync(() async {
      final campaigns = await api.listCampaigns();
      expect(campaigns, isNotEmpty);
      final c = await api.getCampaign(campaigns.first.id);
      final ep = await api.getEpisode(c.episodes.first.id);
      final world = await api.getWorld(c.worldId);
      final voices = await ToonforkExport.voices(ep.sourceLanguage);
      // ignore: avoid_print
      print(
        'voices for ${ep.sourceLanguage}: ${voices.map((v) => '${v.name}(${v.gender},${v.quality})').join(', ')}',
      );
      final cast = assignCast(
        lines: [for (final p in ep.panels) ...panelLines(ep.id, p, null)],
        world: world,
        systemVoices: voices,
      );
      final sw = Stopwatch()..start();
      path = await VideoExporter().run(
        ExportOptions(
          episodes: [ep],
          lang: null,
          ttsLang: ep.sourceLanguage,
          dub: true,
          music: musicFor(world.id),
          cast: cast,
          endText: 'Konec\nToonfork',
          fileName: 'export_test.mp4',
        ),
        (p) {
          if (p.fraction == 0 || p.phase == ExportPhase.frames) {
            // ignore: avoid_print
            print(
              'progress ${p.phase.name} ${(p.fraction * 100).round()} % at ${sw.elapsed.inSeconds} s',
            );
          }
        },
      );
      // ignore: avoid_print
      print(
        'EXPORT_RESULT $path (${sw.elapsed.inSeconds} s, ${File(path).lengthSync()} bytes)',
      );
    });
    expect(File(path).lengthSync(), greaterThan(100000));
  }, timeout: const Timeout(Duration(minutes: 20)));
}
