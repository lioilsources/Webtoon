// Anonymous statistics (../docs/telemetry.md): the package's test kit, plus the app's own rules
// — the Kids profile is never measured, and how an episode counts as read.

import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ol1n_telemetry/ol1n_telemetry.dart';
import 'package:ol1n_telemetry/testing.dart';
import 'package:webtoon/profile/reader_profile.dart';
import 'package:webtoon/telemetry/telemetry_dictionary.dart';
import 'package:webtoon/telemetry/telemetry_setup.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('docs/telemetry.md lists exactly the dictionary', () {
    expect(
      telemetryDocProblems(
        toonforkDictionary,
        File('../docs/telemetry.md').readAsStringSync(),
      ),
      isEmpty,
    );
  });

  test('no property is free text', () {
    expect(telemetryDictionaryProblems(toonforkDictionary), isEmpty);
  });

  test('app version matches pubspec.yaml', () {
    expect(
      telemetryVersionProblems(
        kAppVersion,
        File('pubspec.yaml').readAsStringSync(),
      ),
      isEmpty,
    );
  });

  test('the code sends only dictionary events, and every one of them', () {
    expect(telemetryTrackCallProblems(toonforkDictionary), isEmpty);
  });

  test('no key, no network', () async {
    expect(await telemetryNoKeyProblems(toonforkDictionary), isEmpty);
  });

  test('off means nothing', () async {
    expect(await telemetryOffProblems(toonforkDictionary), isEmpty);
  });

  test('product ids map to product kinds', () {
    expect(productKind('pack_5_2'), 'pack');
    expect(productKind('bundle_all'), 'bundle');
    expect(productKind('gamebook_sara'), 'gamebook');
    expect(productKind('kit_sara'), 'kit');
    expect(productKind('weird'), 'other');
  });

  group('with a sink', () {
    late FakeSink sink;
    var now = DateTime.utc(2026, 11, 14, 10);

    Future<void> start({bool suspended = false}) => Telemetry.init(
      app: kTelemetryApp,
      appVersion: kAppVersion,
      dictionary: toonforkDictionary,
      store: MemoryTelemetryStore(),
      lang: () => 'cs',
      common: () => telemetryCommon(null),
      suspended: suspended,
      sink: sink,
      clock: () => now,
      startTimer: false,
      observeLifecycle: false,
    );

    List<String> names() => [for (final e in Telemetry.debugQueue) e.name];

    setUp(() {
      Telemetry.resetForTest();
      sink = FakeSink();
    });
    tearDown(Telemetry.resetForTest);

    test(
      'a launch without a chosen profile records nothing until Adults',
      () async {
        await start(suspended: true);
        expect(Telemetry.isSuspended, isTrue);
        Telemetry.screen('profile_chooser');
        Telemetry.track('purchase_gate', {'passed': true});
        expect(names(), isEmpty);

        final container = ProviderContainer(
          overrides: [
            profileStoreProvider.overrideWithValue(MemoryProfileStore()),
          ],
        );
        addTearDown(container.dispose);
        await container
            .read(readerProfileProvider.notifier)
            .select(ReaderProfile.adults);
        expect(Telemetry.isSuspended, isFalse);
        expect(names(), ['app_open']);
      },
    );

    test('switching to Kids stops measuring, back to Adults resumes', () async {
      await start();
      final container = ProviderContainer(
        overrides: [
          profileStoreProvider.overrideWithValue(
            MemoryProfileStore(ReaderProfile.adults),
          ),
        ],
      );
      addTearDown(container.dispose);
      final profile = container.read(readerProfileProvider.notifier);
      await pumpEventQueue();
      expect(Telemetry.isSuspended, isFalse);
      Telemetry.screen('settings');
      final before = names().length;

      await profile.select(ReaderProfile.kids);
      expect(Telemetry.isSuspended, isTrue);
      Telemetry.screen('library');
      Telemetry.feature('history');
      final reading = EpisodeReading()..open(1, 'library');
      reading.reachedEnd(1, last: false);
      Telemetry.track('purchase_gate', {'passed': false});
      expect(names().length, before, reason: 'nothing recorded for Kids');

      await profile.select(ReaderProfile.adults);
      expect(Telemetry.isSuspended, isFalse);
      Telemetry.screen('library');
      expect(names().skip(before), ['screen_view']);
    });

    test('a saved Kids profile suspends on load', () async {
      await start();
      final container = ProviderContainer(
        overrides: [
          profileStoreProvider.overrideWithValue(
            MemoryProfileStore(ReaderProfile.kids),
          ),
        ],
      );
      addTearDown(container.dispose);
      container.read(readerProfileProvider);
      await pumpEventQueue();
      expect(Telemetry.isSuspended, isTrue);
    });

    test(
      'episode_read: end block → ok, next one opens; jump → skip; close → cancel',
      () async {
        await start();
        final reading = EpisodeReading()..open(1, 'library');
        now = now.add(const Duration(seconds: 40));
        reading.reachedEnd(1, last: false);
        reading.reachedEnd(1, last: false); // seen again: nothing
        reading.open(2, 'continue'); // "Další díl" onto the one already open
        reading.open(5, 'history');
        reading.open(3, 'history');
        reading.reachedEnd(3, last: true);
        reading.close();

        final reads = [
          for (final e in Telemetry.debugQueue)
            if (e.name.startsWith('episode_read') || e.name == 'activation') e,
        ];
        expect(
          [
            for (final e in reads)
              '${e.name}:${e.props['index'] ?? ''}:${e.props['result'] ?? e.props['from'] ?? ''}',
          ],
          [
            'episode_read_start:1:library',
            'episode_read_end:1:ok',
            'activation::',
            'episode_read_start:2:continue',
            'episode_read_end:2:skip',
            'episode_read_start:5:history',
            'episode_read_end:5:skip',
            'episode_read_start:3:history',
            'episode_read_end:3:ok',
          ],
        );
        expect(reads[1].props['secs'], 40);
        expect(reads.last.props['last'], isTrue);
      },
    );

    test('the bubble language is a common property', () {
      expect(telemetryCommon(null), {'bubbles': 'original'});
      expect(telemetryCommon('pt-BR'), {'bubbles': 'pt-BR'});
      expect(telemetryCommon('xx'), {'bubbles': 'original'});
    });
  });
}
