// Who speaks with which system voice in an exported video. People (the world's characters) get distinct
// voices by gender where the system says it; machines and other unknown speakers get the robot; narration a
// calm narrator. One system voice is common on Android, so pitch keeps the speakers apart anyway.

import 'package:toonfork_export/toonfork_export.dart';

import '../models/world.dart';
import 'export_plan.dart';

/// [CastVoice.voiceId] of the player's own cloned voice (lib/voice), fetched from the server.
const kMyVoiceId = '__my_voice__';

class CastVoice {
  /// System voice id, or null = the language's default voice.
  final String? voiceId;
  final double rate;
  final double pitch;
  final bool robot;

  bool get mine => voiceId == kMyVoiceId;

  /// The pitch this speaker has as a person (kept while it is a robot, for switching back).
  final double personPitch;
  const CastVoice({
    this.voiceId,
    this.rate = 1,
    this.pitch = 1,
    this.robot = false,
    double? personPitch,
  }) : personPitch = personPitch ?? pitch;

  CastVoice withVoice(String? id) => CastVoice(
    voiceId: id,
    rate: rate,
    pitch: pitch,
    robot: robot,
    personPitch: personPitch,
  );

  /// The robot: deep, a little slow, ring-modulated (wav.dart robotize).
  CastVoice asRobot(bool on) => CastVoice(
    voiceId: voiceId,
    rate: on ? 0.95 : 1,
    pitch: on ? 0.75 : personPitch,
    robot: on,
    personPitch: personPitch,
  );
}

class Cast {
  /// speaker id → voice; narration under [narratorKey].
  final Map<String, CastVoice> voices;
  final Set<String> people;
  const Cast(this.voices, this.people);

  static const narratorKey = '';

  CastVoice voiceFor(ExportLine l) =>
      voices[l.kind.name == 'narration' ? narratorKey : l.speakerId] ??
      voices[narratorKey]!;

  LineRole roleOf(ExportLine l) => l.kind.name == 'narration'
      ? LineRole.narration
      : (l.speakerId.isEmpty || people.contains(l.speakerId))
      ? LineRole.speech
      : LineRole.machine;

  /// [robot] also moves the speaker between people and machines (subtitle colour).
  Cast replace(String speaker, CastVoice v) => Cast(
    {...voices, speaker: v},
    speaker == narratorKey
        ? people
        : v.robot
        ? ({...people}..remove(speaker))
        : {...people, speaker},
  );
}

/// Female / male from the character sheet ('1girl' / '1boy'), else unknown.
String genderOf(Character c) => switch (c.countTag) {
  '1girl' => 'f',
  '1boy' => 'm',
  _ => '',
};

Cast assignCast({
  required Iterable<ExportLine> lines,
  required World? world,
  required List<SystemVoice> systemVoices,
}) {
  final chars = {
    for (final c in world?.characters ?? const <Character>[]) c.id: c,
  };
  final speakers = <String>[];
  for (final l in lines) {
    if (l.kind.name != 'narration' &&
        l.speakerId.isNotEmpty &&
        !speakers.contains(l.speakerId)) {
      speakers.add(l.speakerId);
    }
  }
  final best = [...systemVoices]
    ..sort((a, b) => b.quality.compareTo(a.quality));
  List<SystemVoice> of(String g) => best.where((v) => v.gender == g).toList();
  final used = <String, int>{};
  String? pick(String gender) {
    final pool = gender.isEmpty
        ? best
        : (of(gender).isNotEmpty ? of(gender) : best);
    if (pool.isEmpty) return null;
    final n = used[gender] = (used[gender] ?? -1) + 1;
    return pool[n % pool.length].id;
  }

  // Packs carry no character sheets: then everyone is a person and the player picks the robots.
  final people = {
    for (final s in speakers)
      if (chars.isEmpty || chars.containsKey(s)) s,
  };
  final voices = <String, CastVoice>{};
  var unknownPeople = 0;
  for (final s in speakers) {
    if (!people.contains(s)) {
      // a waiter robot, a drone, a loudspeaker: deep and robotic
      voices[s] = CastVoice(
        voiceId: pick('m'),
        pitch: 0.75,
        rate: 0.95,
        robot: true,
      );
      continue;
    }
    var g = chars[s] == null ? '' : genderOf(chars[s]!);
    if (g.isEmpty) g = unknownPeople++ % 2 == 0 ? 'm' : 'f';
    // the same system voice for both sexes still sounds like two people with the pitch apart
    voices[s] = CastVoice(voiceId: pick(g), pitch: g == 'f' ? 1.12 : 0.9);
  }
  voices[Cast.narratorKey] = CastVoice(
    voiceId: pick(''),
    pitch: 0.95,
    rate: 0.97,
  );
  return Cast(voices, people);
}
