// "Můj hlas" (Settings): buy voice_clone, read the consent sentence and a short text into the microphone
// (5–30 s, a teleprompter as in Hajánek), upload, wait until the clone is ready, delete. The exported video
// then speaks the player's character in this voice (lib/export).

import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import '../i18n/ui_strings.dart';
import '../profile/parental_gate.dart';
import '../shop/shop_controller.dart';
import 'voice_api.dart';
import 'voice_controller.dart';

const minRecordSeconds = 5, maxRecordSeconds = 30;

/// Mono AAC at 48 kHz with every voice processing off: noise suppression and AGC change the timbre the
/// clone should learn (Hajánek's settings). VOICE_RECOGNITION has AGC and noise reduction off on Android.
const recordConfig = RecordConfig(
  encoder: AudioEncoder.aacLc,
  bitRate: 128000,
  sampleRate: 48000,
  numChannels: 1,
  autoGain: false,
  echoCancel: false,
  noiseSuppress: false,
  androidConfig: AndroidRecordConfig(
    audioSource: AndroidAudioSource.voiceRecognition,
  ),
);

/// What the player reads: the consent first (the server keeps it), then a text longer than 30 s, so nobody
/// runs out; Czech sounds (ř, ch, ě, ů, long vowels) and some direct speech for the intonation.
String consentSentence(String name) =>
    'Jsem $name a souhlasím, aby Toonfork z této nahrávky vytvořil můj hlas pro moje videa.';

const kRecordingText = [
  'V malé kavárně na rohu voněla káva a čerstvý chleba.',
  'Číšník přinesl dvě polévky a usmál se: „Dobrou chuť!“',
  'Venku pršelo a po skle stékaly dlouhé kapky.',
  '„Myslíš, že to stihneme?“ zeptala se a podívala se na hodinky.',
  '„Určitě,“ řekl jsem. „Máme ještě čtvrt hodiny.“',
  'Přes ulici přeběhl pes s mokrým ocasem a zmizel za rohem.',
  'Na stole ležel otevřený komiks s barevnými bublinami.',
  'Každá stránka byla jako nové dobrodružství.',
  'Zaplatili jsme, oblékli si kabáty a vyšli do deště.',
  'A příběh pokračoval, krok za krokem, až do večera.',
];

class VoiceScreen extends ConsumerStatefulWidget {
  const VoiceScreen({super.key});

  @override
  ConsumerState<VoiceScreen> createState() => _VoiceScreenState();
}

class _VoiceScreenState extends ConsumerState<VoiceScreen> {
  final _name = TextEditingController();
  bool _consent = false;
  AudioRecorder? _recorder;
  Timer? _ticker;
  int _elapsed = 0; // tenths of a second
  String? _file;
  String? _micError;

  bool get _recording => _ticker != null;

  @override
  void dispose() {
    _ticker?.cancel();
    _recorder?.dispose();
    _name.dispose();
    super.dispose();
  }

  Future<void> _start(String ui) async {
    final r = _recorder ??= AudioRecorder();
    if (!await r.hasPermission()) {
      setState(() => _micError = tr(ui, 'voice.micDenied'));
      return;
    }
    final path = '${(await getTemporaryDirectory()).path}/voice_sample.m4a';
    final f = File(path);
    if (f.existsSync()) f.deleteSync();
    await r.start(recordConfig, path: path);
    setState(() {
      _micError = null;
      _file = null;
      _elapsed = 0;
      _ticker = Timer.periodic(const Duration(milliseconds: 100), (_) {
        setState(() => _elapsed++);
        if (_elapsed >= maxRecordSeconds * 10) _stop();
      });
    });
  }

  Future<void> _stop() async {
    _ticker?.cancel();
    final path = await _recorder?.stop();
    if (mounted) {
      setState(() {
        _ticker = null;
        _file = _elapsed >= minRecordSeconds * 10 ? path : null;
      });
    }
  }

  Future<void> _buy() async {
    if (!await showParentalGate(context, ref)) return;
    await ref.read(shopProvider.notifier).buy(kVoiceProduct);
  }

  Future<void> _delete(String ui) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(tr(ui, 'voice.deleteTitle')),
        content: Text(tr(ui, 'voice.deleteBody')),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: Text(tr(ui, 'export.cancel')),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(tr(ui, 'voice.delete')),
          ),
        ],
      ),
    );
    if (ok == true) await ref.read(voiceProvider.notifier).delete();
  }

  @override
  Widget build(BuildContext context) {
    final ui = ref.watch(uiLanguageProvider);
    final shop = ref.watch(shopProvider);
    final voice = ref.watch(voiceProvider);
    final owned = shop.entitlements.receipts.containsKey(kVoiceProduct);
    final price = shop.products[kVoiceProduct]?.price;
    final theme = Theme.of(context);
    final v = voice.voice;

    final children = <Widget>[
      Text(tr(ui, 'voice.intro'), style: theme.textTheme.bodyLarge),
      const SizedBox(height: 16),
    ];
    if (!owned) {
      children.add(
        FilledButton.icon(
          key: const ValueKey('voice-buy'),
          onPressed: shop.buying.contains(kVoiceProduct) || price == null
              ? null
              : _buy,
          icon: const Icon(Icons.mic_rounded),
          label: Text(
            price == null
                ? tr(ui, 'voice.unavailable')
                : tr(ui, 'voice.buy', {'price': price}),
          ),
        ),
      );
    } else if (v != null) {
      final (icon, text) = switch (v.status) {
        VoiceStatus.ready => (
          Icons.check_circle_rounded,
          tr(ui, 'voice.ready'),
        ),
        VoiceStatus.queued => (
          Icons.hourglass_top_rounded,
          tr(ui, 'voice.queued'),
        ),
        VoiceStatus.failed => (
          Icons.error_outline_rounded,
          tr(ui, 'voice.failed'),
        ),
      };
      children.addAll([
        ListTile(
          key: const ValueKey('voice-status'),
          contentPadding: EdgeInsets.zero,
          leading: Icon(icon),
          title: Text(text),
        ),
        if (v.status == VoiceStatus.ready)
          Text(tr(ui, 'voice.useInExport'), style: theme.textTheme.bodyMedium),
        const SizedBox(height: 16),
        OutlinedButton.icon(
          key: const ValueKey('voice-delete'),
          onPressed: voice.busy ? null : () => _delete(ui),
          icon: const Icon(Icons.delete_outline_rounded),
          label: Text(tr(ui, 'voice.delete')),
        ),
      ]);
    } else {
      final name = _name.text.trim();
      children.addAll([
        TextField(
          key: const ValueKey('voice-name'),
          controller: _name,
          enabled: !_recording,
          decoration: InputDecoration(labelText: tr(ui, 'voice.name')),
          onChanged: (_) => setState(() {}),
        ),
        CheckboxListTile(
          key: const ValueKey('voice-consent'),
          contentPadding: EdgeInsets.zero,
          value: _consent,
          onChanged: _recording
              ? null
              : (c) => setState(() => _consent = c ?? false),
          title: Text(tr(ui, 'voice.consent')),
        ),
        const SizedBox(height: 8),
        Text(tr(ui, 'voice.tips'), style: theme.textTheme.bodySmall),
        const SizedBox(height: 12),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: _Prompter(
              lines: [
                consentSentence(name.isEmpty ? '…' : name),
                ...kRecordingText,
              ],
              elapsedTenths: _elapsed,
              running: _recording,
            ),
          ),
        ),
        const SizedBox(height: 12),
        LinearProgressIndicator(value: _elapsed / (maxRecordSeconds * 10)),
        const SizedBox(height: 4),
        Text(
          '${(_elapsed / 10).toStringAsFixed(0)} / $maxRecordSeconds s',
          textAlign: TextAlign.end,
        ),
        if (_micError != null)
          Text(_micError!, style: TextStyle(color: theme.colorScheme.error)),
        const SizedBox(height: 12),
        if (_recording)
          FilledButton.icon(
            key: const ValueKey('voice-stop'),
            onPressed: _elapsed >= minRecordSeconds * 10 ? _stop : null,
            icon: const Icon(Icons.stop_rounded),
            label: Text(tr(ui, 'voice.stop')),
          )
        else
          FilledButton.icon(
            key: const ValueKey('voice-record'),
            onPressed: name.isEmpty || !_consent || voice.busy
                ? null
                : () => _start(ui),
            icon: const Icon(Icons.fiber_manual_record_rounded),
            label: Text(
              tr(ui, _file == null ? 'voice.record' : 'voice.recordAgain'),
            ),
          ),
        if (_file != null && !_recording) ...[
          const SizedBox(height: 8),
          FilledButton.tonalIcon(
            key: const ValueKey('voice-upload'),
            onPressed: voice.busy
                ? null
                : () => ref
                      .read(voiceProvider.notifier)
                      .upload(File(_file!), consentSentence(name)),
            icon: const Icon(Icons.cloud_upload_rounded),
            label: Text(tr(ui, 'voice.upload')),
          ),
        ],
      ]);
    }
    if (voice.busy) {
      children.add(
        const Padding(
          padding: EdgeInsets.only(top: 12),
          child: LinearProgressIndicator(),
        ),
      );
    }
    if (voice.error != null) {
      children.add(
        Padding(
          padding: const EdgeInsets.only(top: 12),
          child: Text(
            trError(ui, voice.error),
            style: TextStyle(color: theme.colorScheme.error),
          ),
        ),
      );
    }
    children.addAll([
      const SizedBox(height: 24),
      Text(tr(ui, 'voice.privacy'), style: theme.textTheme.bodySmall),
    ]);

    return Scaffold(
      appBar: AppBar(title: Text(tr(ui, 'voice.title'))),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: children,
      ),
    );
  }
}

/// The text to read, the current line highlighted and paced by letters (≈ 14 letters a second, then a
/// short pause per line), like a karaoke screen.
class _Prompter extends StatelessWidget {
  final List<String> lines;
  final int elapsedTenths;
  final bool running;
  const _Prompter({
    required this.lines,
    required this.elapsedTenths,
    required this.running,
  });

  int get _current {
    if (!running) return 0;
    var t = elapsedTenths / 10.0;
    for (var i = 0; i < lines.length; i++) {
      t -= lines[i].length / 14 + 0.7;
      if (t < 0) return i;
    }
    return lines.length - 1;
  }

  @override
  Widget build(BuildContext context) {
    final cur = _current;
    final s = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (var i = cur; i < lines.length && i < cur + 4; i++)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              lines[i],
              style: i == cur
                  ? s.titleMedium?.copyWith(fontWeight: FontWeight.w800)
                  : s.bodyMedium?.copyWith(color: Theme.of(context).hintColor),
            ),
          ),
      ],
    );
  }
}
