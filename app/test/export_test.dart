import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:webtoon/export/export_plan.dart';
import 'package:webtoon/export/voices.dart';
import 'package:webtoon/export/wav.dart';
import 'package:webtoon/models/episode.dart';
import 'package:webtoon/models/world.dart';
import 'package:toonfork_export/toonfork_export.dart';

Panel _panel(int i, List<Bubble> bubbles, {bool loop = false}) => Panel(
  index: i,
  status: 'ready',
  imageUrl: '/p$i.png',
  width: 832,
  height: 1216,
  bubbles: bubbles,
  videoUrl: loop ? '/p$i.webp' : null,
  videoStatus: loop ? 'ready' : '',
);

Episode _ep(List<Panel> panels) => Episode(
  id: 'ep1',
  campaignId: 'cp1',
  index: 1,
  title: 'Guláš',
  status: EpisodeStatus.ready,
  panels: panels,
);

void main() {
  final ep = _ep([
    _panel(0, [
      const Bubble(text: 'U KN DLÍKU 2089', kind: BubbleKind.narration),
    ]),
    _panel(1, [
      const Bubble(speakerId: 'jana', text: 'Ahoj.'),
      const Bubble(text: 'Večer.', kind: BubbleKind.narration),
      const Bubble(speakerId: 'robot', text: 'Dobrou chuť.'),
    ]),
    _panel(2, const [], loop: true),
  ]);
  LineRole role(ExportLine l) => l.kind == BubbleKind.narration
      ? LineRole.narration
      : l.speakerId == 'robot'
      ? LineRole.machine
      : LineRole.speech;

  test('narration is read first, then the speech in bubble order', () {
    final lines = panelLines('ep1', ep.panels[1], null);
    expect(lines.map((l) => l.text), ['Večer.', 'Ahoj.', 'Dobrou chuť.']);
    expect(lines.first.key, 'ep1/1/1');
  });

  test(
    'silent plan: title card, panels by reading time, end card; crossfades overlap',
    () {
      final plan = buildPlan(
        episodes: [ep],
        lang: null,
        endText: 'Konec',
        roleOf: role,
      );
      expect(plan.segments.length, 5);
      expect(plan.segments.first, isA<CardSegment>());
      expect((plan.segments.last as CardSegment).big, isTrue);
      final p1 = plan.segments[2] as PanelSegment;
      expect(
        p1.duration,
        inInclusiveRange(ExportTiming.readMin, ExportTiming.readMax),
      );
      expect(p1.voice, isEmpty);
      expect((plan.segments[3] as PanelSegment).duration, ExportTiming.loopMin);
      final sum = plan.segments.fold<double>(0, (s, g) => s + g.duration);
      expect(plan.duration, closeTo(sum - 4 * ExportTiming.fade, 1e-9));
    },
  );

  test(
    'voiced plan: lines one after another, the panel stays while they are spoken',
    () {
      final plan = buildPlan(
        episodes: [ep],
        lang: null,
        endText: 'Konec',
        roleOf: role,
        lineSeconds: (l) =>
            l.text == 'Ahoj.' ? null : 2.0, // one line the TTS refused
      );
      final p1 = plan.segments[2] as PanelSegment;
      final want = [
        ExportTiming.lead,
        ExportTiming.lead + 2 + ExportTiming.gap,
        ExportTiming.lead +
            2 +
            ExportTiming.gap +
            ExportTiming.readBase +
            ExportTiming.gap,
      ];
      for (var i = 0; i < want.length; i++) {
        expect(p1.cues[i].start, closeTo(want[i], 1e-9));
      }
      expect(p1.voice.map((v) => v.$2), ['ep1/1/1', 'ep1/1/2']);
      expect(
        p1.duration,
        closeTo(p1.cues.last.start + 2 + ExportTiming.tail, 1e-9),
      );
      expect(p1.cues.last.role, LineRole.machine);
      final placed = plan.placedVoice;
      expect(
        placed.first.$1,
        closeTo(plan.startOf(1) + ExportTiming.lead, 1e-9),
      );
    },
  );

  test(
    'cueAt shows the first line before it starts and the latest one after',
    () {
      final p1 =
          buildPlan(
                episodes: [ep],
                lang: null,
                endText: '',
                roleOf: role,
              ).segments[2]
              as PanelSegment;
      expect(cueAt(p1.cues, 0)!.line.text, 'Večer.');
      expect(cueAt(p1.cues, 100)!.line.text, 'Dobrou chuť.');
    },
  );

  test('wav: 16-bit stereo 24 kHz in, 48 kHz mono out, and back', () {
    final frames = 2400; // 0.1 s
    final d = ByteData(44 + frames * 4);
    void tag(int o, String s) {
      for (var i = 0; i < 4; i++) {
        d.setUint8(o + i, s.codeUnitAt(i));
      }
    }

    tag(0, 'RIFF');
    d.setUint32(4, 36 + frames * 4, Endian.little);
    tag(8, 'WAVE');
    tag(12, 'fmt ');
    d.setUint32(16, 16, Endian.little);
    d.setUint16(20, 1, Endian.little);
    d.setUint16(22, 2, Endian.little);
    d.setUint32(24, 24000, Endian.little);
    d.setUint32(28, 24000 * 4, Endian.little);
    d.setUint16(32, 4, Endian.little);
    d.setUint16(34, 16, Endian.little);
    tag(36, 'data');
    d.setUint32(40, frames * 4, Endian.little);
    for (var i = 0; i < frames; i++) {
      final v = (math.sin(i / 10) * 16000).round();
      d.setInt16(44 + i * 4, v, Endian.little);
      d.setInt16(46 + i * 4, v, Endian.little);
    }
    final x = decodeWav(d.buffer.asUint8List());
    expect(x.length, 4800);
    expect(x[200], closeTo(math.sin(100 / 10) * 16000 / 32768, 0.01));
    final back = decodeWav(encodeWav(x));
    expect(back.length, x.length);
    expect(back[200], closeTo(x[200], 1e-3));
  });

  test('trimSilence keeps a little air around the line', () {
    final x = Float32List(48000);
    for (var i = 20000; i < 30000; i++) {
      x[i] = 0.5;
    }
    final t = trimSilence(x);
    expect(t.length, 10000 + 2 * (0.04 * kExportRate).round());
  });

  test(
    'cast: characters are people with distinct voices, unknown speakers are robots',
    () {
      final world = World(
        id: 'w',
        title: 'W',
        characters: const [
          Character(id: 'olin', name: 'Olin', countTag: '1boy'),
          Character(id: 'jana', name: 'Jana', countTag: '1girl'),
        ],
      );
      final cast = assignCast(
        lines: [
          const ExportLine(
            key: 'a',
            text: 'x',
            speakerId: 'olin',
            kind: BubbleKind.speech,
          ),
          const ExportLine(
            key: 'b',
            text: 'x',
            speakerId: 'jana',
            kind: BubbleKind.speech,
          ),
          const ExportLine(
            key: 'c',
            text: 'x',
            speakerId: 'robot',
            kind: BubbleKind.speech,
          ),
        ],
        world: world,
        systemVoices: const [
          SystemVoice(id: 'zuzana', name: 'Zuzana', lang: 'cs-CZ', gender: 'f'),
          SystemVoice(id: 'jakub', name: 'Jakub', lang: 'cs-CZ', gender: 'm'),
        ],
      );
      expect(cast.voices['olin']!.voiceId, 'jakub');
      expect(cast.voices['jana']!.voiceId, 'zuzana');
      expect(cast.voices['robot']!.robot, isTrue);
      expect(
        cast.roleOf(
          const ExportLine(
            key: 'c',
            text: 'x',
            speakerId: 'robot',
            kind: BubbleKind.speech,
          ),
        ),
        LineRole.machine,
      );
      expect(cast.voices.containsKey(Cast.narratorKey), isTrue);
    },
  );

  test(
    'cast from a pack (no character sheets): everyone is a person until the player picks a robot',
    () {
      final cast = assignCast(
        lines: const [
          ExportLine(
            key: 'a',
            text: 'x',
            speakerId: 'c1',
            kind: BubbleKind.speech,
          ),
          ExportLine(
            key: 'b',
            text: 'x',
            speakerId: 'c2',
            kind: BubbleKind.speech,
          ),
        ],
        world: null,
        systemVoices: const [
          SystemVoice(id: 'zuzana', name: 'Zuzana', lang: 'cs-CZ', gender: 'f'),
        ],
      );
      const l2 = ExportLine(
        key: 'b',
        text: 'x',
        speakerId: 'c2',
        kind: BubbleKind.speech,
      );
      expect(cast.voices['c1']!.robot, isFalse);
      expect(
        cast.voices['c1']!.pitch,
        isNot(cast.voices['c2']!.pitch),
      ); // one voice, two people
      final robot = cast.replace('c2', cast.voices['c2']!.asRobot(true));
      expect(robot.roleOf(l2), LineRole.machine);
      expect(robot.voiceFor(l2).robot, isTrue);
      final back = robot.replace('c2', robot.voices['c2']!.asRobot(false));
      expect(back.roleOf(l2), LineRole.speech);
      expect(back.voices['c2']!.pitch, cast.voices['c2']!.pitch);
    },
  );
}
