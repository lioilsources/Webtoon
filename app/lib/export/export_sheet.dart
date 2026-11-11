// "Video pro TikTok / YouTube": the reader's export sheet. Options (this episode or the whole story, dub,
// music, a system voice per speaker), then progress, then the system share sheet.

import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart';
import 'package:toonfork_export/toonfork_export.dart';

import '../i18n/ui_strings.dart';
import '../models/campaign.dart';
import '../models/episode.dart';
import '../models/world.dart';
import '../providers/providers.dart';
import '../voice/voice_api.dart' show kVoiceCloning;
import '../voice/voice_controller.dart';
import 'export_plan.dart';
import 'video_exporter.dart';
import 'voices.dart';

/// Behind `--dart-define=EXPORT_VIDEO=true` until it has been tried on real phones.
const kExportVideo = bool.fromEnvironment('EXPORT_VIDEO');

/// Free strips are never exported (as m0/shorts.py: the lxf_ prefix of rules/base/pack.yaml).
bool canExport(World? w) =>
    kExportVideo && !(w?.id.startsWith('lxf_') ?? false);

Future<void> showExportSheet(
  BuildContext context, {
  required List<EpisodeSummary> episodes,
  required String focusId,
  required World? world,
  required String? lang,
}) => showModalBottomSheet<void>(
  context: context,
  isScrollControlled: true,
  showDragHandle: true,
  builder: (_) => ExportSheet(
    episodes: episodes,
    focusId: focusId,
    world: world,
    lang: lang,
  ),
);

class ExportSheet extends ConsumerStatefulWidget {
  final List<EpisodeSummary> episodes;
  final String focusId;
  final World? world;
  final String? lang;
  const ExportSheet({
    super.key,
    required this.episodes,
    required this.focusId,
    required this.world,
    required this.lang,
  });

  @override
  ConsumerState<ExportSheet> createState() => _ExportSheetState();
}

class _ExportSheetState extends ConsumerState<ExportSheet> {
  bool _story = false;
  bool _dub = true;
  bool _music = true;
  List<Episode>? _loaded;
  List<SystemVoice> _voices = const [];
  Cast? _cast;
  Map<String, String> _firstLine = {};
  VideoExporter? _exporter;
  ExportProgress? _progress;
  String? _result;
  String? _error;

  /// The language the story is shown in, and the one the voices speak.
  String get _sourceLang => _loaded?.first.sourceLanguage ?? 'cs';
  String get _speakLang => widget.lang ?? _sourceLang;

  @override
  void initState() {
    super.initState();
    _load();
  }

  List<EpisodeSummary> get _scope => _story
      ? widget.episodes
      : widget.episodes.where((e) => e.id == widget.focusId).toList();

  Future<void> _load() async {
    final api = ref.read(apiProvider);
    try {
      final eps = [for (final e in _scope) await api.getEpisode(e.id)];
      final voices = await ToonforkExport.voices(
        widget.lang ?? (eps.isEmpty ? 'cs' : eps.first.sourceLanguage),
      );
      if (!mounted) return;
      final lines = [
        for (final ep in eps)
          for (final p in ep.panels) ...panelLines(ep.id, p, widget.lang),
      ];
      setState(() {
        _loaded = eps;
        _voices = voices;
        _firstLine = {};
        for (final l in lines) {
          _firstLine.putIfAbsent(l.speakerId, () => l.text);
        }
        _cast = assignCast(
          lines: lines,
          world: widget.world,
          systemVoices: voices,
        );
      });
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  /// The character's name, or (packs carry no character sheets) "Character 2 · „first line…“".
  String _speakerName(String id, String ui) {
    if (id == Cast.narratorKey) return tr(ui, 'export.narrator');
    final c = widget.world?.characters.where((c) => c.id == id).firstOrNull;
    if (c != null) return c.name;
    final n =
        _cast!.voices.keys
            .where((k) => k != Cast.narratorKey)
            .toList()
            .indexOf(id) +
        1;
    final first = _firstLine[id] ?? '';
    final hint = first.length > 28 ? '${first.substring(0, 27)}…' : first;
    return '${tr(ui, 'export.speaker', {'n': n})}${hint.isEmpty ? '' : ' · „$hint“'}';
  }

  Future<void> _start(String ui) async {
    final eps = _loaded, cast = _cast;
    if (eps == null || cast == null) return;
    final ex = _exporter = VideoExporter();
    setState(() {
      _progress = const ExportProgress(ExportPhase.voices, 0);
      _error = null;
      _result = null;
    });
    try {
      final path = await ex.run(
        ExportOptions(
          episodes: eps,
          lang: widget.lang,
          ttsLang: _speakLang,
          dub: _dub,
          music: _music ? musicFor(widget.world?.id ?? eps.first.id) : null,
          cast: cast,
          endText: tr(ui, 'export.end'),
          fileName: 'toonfork-${eps.first.id}${_story ? '-story' : ''}.mp4',
          fetchMyVoice: (lines, dir, onProgress, cancelled) => ref
              .read(voiceProvider.notifier)
              .fetchLines(
                'cs',
                lines,
                dir,
                onProgress: onProgress,
                cancelled: cancelled,
              ),
        ),
        (p) {
          if (mounted) setState(() => _progress = p);
        },
      );
      if (mounted) setState(() => _result = path);
    } on ExportCancelled {
      if (mounted) setState(() => _progress = null);
    } catch (e) {
      if (mounted) {
        setState(() {
          _progress = null;
          _error = tr(ui, 'export.failed', {'error': e});
        });
      }
    } finally {
      _exporter = null;
    }
  }

  Future<void> _share(BuildContext context) async {
    final box = context.findRenderObject() as RenderBox?;
    await SharePlus.instance.share(
      ShareParams(
        files: [XFile(_result!, mimeType: 'video/mp4')],
        sharePositionOrigin: box == null
            ? null
            : box.localToGlobal(Offset.zero) & box.size,
      ),
    );
  }

  @override
  void dispose() {
    _exporter?.cancel();
    super.dispose();
  }

  String _phaseText(String ui, ExportProgress p) => switch (p.phase) {
    ExportPhase.voices => tr(ui, 'export.phase.voices'),
    ExportPhase.music => tr(ui, 'export.phase.music'),
    ExportPhase.frames => tr(ui, 'export.phase.frames', {
      'p': (p.fraction * 100).round(),
    }),
    ExportPhase.done => tr(ui, 'export.done'),
  };

  @override
  Widget build(BuildContext context) {
    final ui = ref.watch(uiLanguageProvider);
    final busy = _progress != null && _result == null;
    // the own voice speaks Czech only (chatterbox-cs on the server)
    final myVoice =
        kVoiceCloning && ref.watch(voiceProvider).ready && _speakLang == 'cs';
    final cast = _cast;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          20,
          0,
          20,
          20 + MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                tr(ui, 'export.title'),
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 12),
              if (widget.episodes.length > 1)
                SegmentedButton<bool>(
                  key: const ValueKey('export-scope'),
                  segments: [
                    ButtonSegment(
                      value: false,
                      label: Text(tr(ui, 'export.scopeEpisode')),
                    ),
                    ButtonSegment(
                      value: true,
                      label: Text(tr(ui, 'export.scopeStory')),
                    ),
                  ],
                  selected: {_story},
                  onSelectionChanged: busy
                      ? null
                      : (s) {
                          setState(() {
                            _story = s.first;
                            _loaded = null;
                          });
                          _load();
                        },
                ),
              SwitchListTile(
                key: const ValueKey('export-dub'),
                contentPadding: EdgeInsets.zero,
                title: Text(tr(ui, 'export.dub')),
                subtitle: Text(tr(ui, 'export.dubHint')),
                value: _dub && _voices.isNotEmpty,
                onChanged: busy || _voices.isEmpty
                    ? null
                    : (v) => setState(() => _dub = v),
              ),
              SwitchListTile(
                key: const ValueKey('export-music'),
                contentPadding: EdgeInsets.zero,
                title: Text(tr(ui, 'export.music')),
                value: _music,
                onChanged: busy ? null : (v) => setState(() => _music = v),
              ),
              if (_dub && cast != null && _voices.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  tr(ui, 'export.voices'),
                  style: Theme.of(context).textTheme.titleMedium,
                ),
                for (final speaker in cast.voices.keys)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<String?>(
                            key: ValueKey('export-voice-$speaker'),
                            initialValue: cast.voices[speaker]!.voiceId,
                            isExpanded: true,
                            decoration: InputDecoration(
                              labelText: _speakerName(speaker, ui),
                              isDense: true,
                            ),
                            items: [
                              DropdownMenuItem(
                                value: null,
                                child: Text(tr(ui, 'export.defaultVoice')),
                              ),
                              if (myVoice)
                                DropdownMenuItem(
                                  value: kMyVoiceId,
                                  child: Text(tr(ui, 'export.myVoice')),
                                ),
                              for (final v in _voices)
                                DropdownMenuItem(
                                  value: v.id,
                                  child: Text(
                                    '${v.name}${v.quality > 0 ? ' ★' : ''}',
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                            ],
                            onChanged: busy
                                ? null
                                : (id) => setState(
                                    () => _cast = cast.replace(
                                      speaker,
                                      cast.voices[speaker]!.withVoice(id),
                                    ),
                                  ),
                          ),
                        ),
                        if (speaker != Cast.narratorKey) ...[
                          const SizedBox(width: 8),
                          FilterChip(
                            key: ValueKey('export-robot-$speaker'),
                            label: Text(tr(ui, 'export.robot')),
                            selected: cast.voices[speaker]!.robot,
                            onSelected: busy
                                ? null
                                : (on) => setState(
                                    () => _cast = cast.replace(
                                      speaker,
                                      cast.voices[speaker]!.asRobot(on),
                                    ),
                                  ),
                          ),
                        ],
                      ],
                    ),
                  ),
              ],
              const SizedBox(height: 16),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Text(
                    _error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              if (_progress != null) ...[
                Text(_phaseText(ui, _progress!)),
                const SizedBox(height: 8),
                LinearProgressIndicator(
                  value:
                      _progress!.phase == ExportPhase.frames ||
                          _progress!.phase == ExportPhase.done
                      ? _progress!.fraction
                      : null,
                ),
                const SizedBox(height: 16),
              ],
              if (_result != null)
                Builder(
                  builder: (ctx) => FilledButton.icon(
                    key: const ValueKey('export-share'),
                    onPressed: () => _share(ctx),
                    icon: const Icon(Icons.ios_share_rounded),
                    label: Text(tr(ui, 'export.share')),
                  ),
                )
              else if (busy)
                OutlinedButton(
                  key: const ValueKey('export-cancel'),
                  onPressed: () => _exporter?.cancel(),
                  child: Text(tr(ui, 'export.cancel')),
                )
              else
                FilledButton.icon(
                  key: const ValueKey('export-start'),
                  onPressed: _loaded == null || _cast == null
                      ? null
                      : () => _start(ui),
                  icon: const Icon(Icons.movie_creation_outlined),
                  label: Text(tr(ui, 'export.start')),
                ),
              if (_result != null && Platform.isMacOS)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: SelectableText(
                    _result!,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
