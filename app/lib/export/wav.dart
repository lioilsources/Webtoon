// Minimal wav I/O for the video export: system TTS writes whatever format it likes (16-bit or float, 22–48 kHz,
// mono or stereo); everything is brought to 48 kHz mono float here and written back as 16-bit.

import 'dart:io';
import 'dart:math' as math;
import 'dart:typed_data';

const kExportRate = 48000;

/// Samples of [bytes] (a RIFF wav) as 48 kHz mono, -1…1.
Float32List decodeWav(Uint8List bytes) {
  final b = ByteData.sublistView(bytes);
  if (bytes.length < 12 ||
      String.fromCharCodes(bytes.sublist(0, 4)) != 'RIFF' ||
      String.fromCharCodes(bytes.sublist(8, 12)) != 'WAVE') {
    throw const FormatException('not a wav file');
  }
  var format = 1, channels = 1, rate = kExportRate, bits = 16;
  Uint8List? data;
  var i = 12;
  while (i + 8 <= bytes.length) {
    final id = String.fromCharCodes(bytes.sublist(i, i + 4));
    var size = b.getUint32(i + 4, Endian.little);
    final start = i + 8;
    if (start + size > bytes.length || size == 0xFFFFFFFF) {
      size = bytes.length - start; // streamed writers leave the size unset
    }
    if (id == 'fmt ') {
      format = b.getUint16(start, Endian.little);
      channels = b.getUint16(start + 2, Endian.little);
      rate = b.getUint32(start + 4, Endian.little);
      bits = b.getUint16(start + 14, Endian.little);
      if (format == 0xFFFE && size >= 26) {
        format = b.getUint16(
          start + 24,
          Endian.little,
        ); // WAVE_FORMAT_EXTENSIBLE sub-format
      }
    } else if (id == 'data') {
      data = Uint8List.sublistView(bytes, start, start + size);
    }
    i = start + size + (size & 1);
  }
  if (data == null) throw const FormatException('wav without data');
  final d = ByteData.sublistView(data);
  final bps = bits ~/ 8;
  final frames = data.length ~/ (bps * channels);
  final mono = Float32List(frames);
  for (var f = 0; f < frames; f++) {
    var s = 0.0;
    for (var c = 0; c < channels; c++) {
      final o = (f * channels + c) * bps;
      s += switch ((format, bits)) {
        (3, 32) => d.getFloat32(o, Endian.little),
        (1, 16) => d.getInt16(o, Endian.little) / 32768,
        (1, 24) =>
          ((d.getUint8(o) | d.getUint8(o + 1) << 8 | d.getInt8(o + 2) << 16) /
              8388608),
        (1, 32) => d.getInt32(o, Endian.little) / 2147483648,
        (1, 8) => (d.getUint8(o) - 128) / 128,
        _ => throw FormatException('wav format $format/$bits bit'),
      };
    }
    mono[f] = s / channels;
  }
  return rate == kExportRate ? mono : resample(mono, rate, kExportRate);
}

/// Linear resampling; speech and music both survive it fine at these rates.
Float32List resample(Float32List x, int from, int to) {
  if (x.isEmpty) return x;
  final n = (x.length * to / from).floor();
  final out = Float32List(n);
  final step = from / to;
  for (var i = 0; i < n; i++) {
    final p = i * step;
    final k = p.floor();
    final t = p - k;
    final a = x[math.min(k, x.length - 1)],
        c = x[math.min(k + 1, x.length - 1)];
    out[i] = a + (c - a) * t;
  }
  return out;
}

Uint8List encodeWav(Float32List x, {int rate = kExportRate}) {
  final out = ByteData(44 + x.length * 2);
  void tag(int o, String s) {
    for (var i = 0; i < 4; i++) {
      out.setUint8(o + i, s.codeUnitAt(i));
    }
  }

  tag(0, 'RIFF');
  out.setUint32(4, 36 + x.length * 2, Endian.little);
  tag(8, 'WAVE');
  tag(12, 'fmt ');
  out.setUint32(16, 16, Endian.little);
  out.setUint16(20, 1, Endian.little);
  out.setUint16(22, 1, Endian.little);
  out.setUint32(24, rate, Endian.little);
  out.setUint32(28, rate * 2, Endian.little);
  out.setUint16(32, 2, Endian.little);
  out.setUint16(34, 16, Endian.little);
  tag(36, 'data');
  out.setUint32(40, x.length * 2, Endian.little);
  for (var i = 0; i < x.length; i++) {
    out.setInt16(
      44 + i * 2,
      (x[i].clamp(-1.0, 1.0) * 32767).round(),
      Endian.little,
    );
  }
  return out.buffer.asUint8List();
}

Future<Float32List> readWav(String path) async =>
    decodeWav(await File(path).readAsBytes());

/// Trims the silence TTS leaves around a line (keeps [keep] s on each side).
Float32List trimSilence(
  Float32List x, {
  double keep = 0.04,
  double floor = 0.01,
}) {
  var a = 0, b = x.length;
  while (a < b && x[a].abs() < floor) {
    a++;
  }
  while (b > a && x[b - 1].abs() < floor) {
    b--;
  }
  final k = (keep * kExportRate).round();
  return Float32List.sublistView(
    x,
    math.max(0, a - k),
    math.min(x.length, b + k),
  );
}

/// The classic cheap robot: ring modulation, plus a little short echo.
Float32List robotize(Float32List x, {double hz = 55}) {
  final out = Float32List(x.length);
  final delay = (0.018 * kExportRate).round();
  for (var i = 0; i < x.length; i++) {
    final ring = x[i] * math.sin(2 * math.pi * hz * i / kExportRate);
    final echo = i >= delay ? out[i - delay] * 0.35 : 0.0;
    out[i] = (0.55 * x[i] + 0.65 * ring + echo).clamp(-1.0, 1.0);
  }
  return out;
}
