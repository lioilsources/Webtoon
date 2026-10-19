import 'package:flutter/material.dart';

import '../models/episode.dart';
import '../theme.dart';

/// What the editor asked for in the "Rozhýbat" sheet; `null` fields mean "unchanged".
class MotionEdit {
  final bool animate;
  final String motion;
  final int loopSeconds;
  final bool reseed;

  const MotionEdit({
    required this.animate,
    required this.motion,
    required this.loopSeconds,
    this.reseed = false,
  });

  /// PATCH body for the backend (see README „Pohyblivá políčka“).
  Map<String, dynamic> toPatch() => {
    'animate': animate,
    if (animate) 'motion': motion,
    if (animate) 'loop_seconds': loopSeconds,
    if (reseed) 'reseed_video': true,
  };
}

/// Render-time hint shown next to the length picker (comfy.VideoEstimateSeconds).
int motionEstimateSeconds(int loopSeconds) => switch (loopSeconds) {
  1 => 100,
  3 => 200,
  _ => 155,
};

String motionEstimateLabel(int loopSeconds) {
  final s = motionEstimateSeconds(loopSeconds);
  final min = (s / 60)
      .toStringAsFixed(s % 60 == 0 ? 0 : 1)
      .replaceAll('.', ',');
  return '≈ $min min renderu';
}

/// Bottom sheet: turn the panel into a 1–3 s loop, write what moves, pick the length.
/// Returns the edit, or null when dismissed.
Future<MotionEdit?> showMotionSheet(
  BuildContext context, {
  required Panel panel,
}) => showModalBottomSheet<MotionEdit>(
  context: context,
  isScrollControlled: true,
  showDragHandle: true,
  builder: (_) => _MotionSheet(panel: panel),
);

class _MotionSheet extends StatefulWidget {
  final Panel panel;
  const _MotionSheet({required this.panel});

  @override
  State<_MotionSheet> createState() => _MotionSheetState();
}

class _MotionSheetState extends State<_MotionSheet> {
  late bool _animate = widget.panel.animate;
  late int _loop = widget.panel.loopSeconds.clamp(1, 3);
  late final TextEditingController _motion = TextEditingController(
    text: widget.panel.motion,
  );

  @override
  void dispose() {
    _motion.dispose();
    super.dispose();
  }

  bool get _valid => !_animate || _motion.text.trim().isNotEmpty;

  void _save({bool reseed = false}) {
    if (!_valid) return;
    Navigator.of(context).pop(
      MotionEdit(
        animate: _animate,
        motion: _motion.text.trim(),
        loopSeconds: _loop,
        reseed: reseed,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.panel;
    final theme = Theme.of(context);
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        4,
        20,
        20 + MediaQuery.viewInsetsOf(context).bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Panel ${p.index + 1}',
            style: ComicFonts.title().copyWith(fontSize: 20),
          ),
          SwitchListTile(
            key: const ValueKey('motion-switch'),
            contentPadding: EdgeInsets.zero,
            title: const Text('Rozhýbat'),
            subtitle: const Text(
              'Krátká smyčka místo statického obrázku. Bubliny zůstávají.',
            ),
            value: _animate,
            onChanged: (v) => setState(() => _animate = v),
          ),
          if (_animate) ...[
            TextField(
              key: const ValueKey('motion-field'),
              controller: _motion,
              minLines: 2,
              maxLines: 4,
              maxLength: 120,
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(
                labelText: 'Pohyb',
                helperText:
                    'Anglicky, do 15 slov: co se hýbe + okolí + „static camera“. Žádný polibek, svlékání ani dvě postavy v akci.',
                helperMaxLines: 3,
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                SegmentedButton<int>(
                  key: const ValueKey('motion-length'),
                  segments: const [
                    ButtonSegment(value: 1, label: Text('1 s')),
                    ButtonSegment(value: 2, label: Text('2 s')),
                    ButtonSegment(value: 3, label: Text('3 s')),
                  ],
                  selected: {_loop},
                  onSelectionChanged: (s) => setState(() => _loop = s.first),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Text(
                    motionEstimateLabel(_loop),
                    key: const ValueKey('motion-estimate'),
                    style: theme.textTheme.bodySmall,
                  ),
                ),
              ],
            ),
            if (p.videoStatus == 'failed' && p.videoError.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(
                  'Minule to neprošlo: ${p.videoError}',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.error,
                  ),
                ),
              ),
          ],
          const SizedBox(height: 16),
          Row(
            children: [
              if (p.animate && _animate)
                OutlinedButton.icon(
                  key: const ValueKey('motion-reseed'),
                  onPressed: p.isVideoPending
                      ? null
                      : () => _save(reseed: true),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Znovu'),
                ),
              if (p.animate && !_animate)
                OutlinedButton.icon(
                  key: const ValueKey('motion-static'),
                  onPressed: _save,
                  icon: const Icon(Icons.image_outlined),
                  label: const Text('Statický'),
                ),
              const Spacer(),
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Zrušit'),
              ),
              const SizedBox(width: 8),
              FilledButton(
                key: const ValueKey('motion-save'),
                onPressed: _valid ? _save : null,
                child: const Text('Uložit'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
