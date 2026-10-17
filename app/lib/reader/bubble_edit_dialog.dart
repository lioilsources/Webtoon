import 'package:flutter/material.dart';

import '../models/episode.dart';
import '../theme.dart';
import 'bubble_layout.dart';

const _kindLabel = {
  BubbleKind.speech: 'Řeč',
  BubbleKind.thought: 'Myšlenka',
  BubbleKind.shout: 'Výkřik',
  BubbleKind.narration: 'Vypravěč',
};

/// Edit a bubble's text (bubbles are an overlay, so no image is regenerated).
/// Returns the new text, or null when cancelled.
Future<String?> showBubbleEditDialog(
  BuildContext context, {
  required Bubble bubble,
  String? speakerName,
}) => showDialog<String>(
  context: context,
  builder: (_) => _BubbleEditDialog(bubble: bubble, speakerName: speakerName),
);

class _BubbleEditDialog extends StatefulWidget {
  final Bubble bubble;
  final String? speakerName;
  const _BubbleEditDialog({required this.bubble, this.speakerName});

  @override
  State<_BubbleEditDialog> createState() => _BubbleEditDialogState();
}

class _BubbleEditDialogState extends State<_BubbleEditDialog> {
  late final TextEditingController _c = TextEditingController(
    text: widget.bubble.text,
  );

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  void _save() {
    final t = _c.text.trim();
    if (t.isEmpty) return;
    Navigator.of(context).pop(t);
  }

  @override
  Widget build(BuildContext context) {
    final b = widget.bubble;
    final who = b.isNarration
        ? _kindLabel[b.kind]!
        : '${_kindLabel[b.kind]} · ${widget.speakerName ?? b.speakerId ?? '?'}';
    return AlertDialog(
      title: const Text('Upravit bublinu'),
      content: SizedBox(
        width: 420,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(who, style: ComicFonts.ui(700).copyWith(fontSize: 13)),
            const SizedBox(height: 10),
            TextField(
              key: const ValueKey('bubble-edit-field'),
              controller: _c,
              autofocus: true,
              minLines: 2,
              maxLines: 6,
              maxLength: 300,
              style: bubbleTextStyle(
                b.kind,
                0.7,
              ).copyWith(color: Theme.of(context).colorScheme.onSurface),
              onSubmitted: (_) => _save(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Zrušit'),
        ),
        FilledButton(
          key: const ValueKey('bubble-edit-save'),
          onPressed: _save,
          child: const Text('Uložit'),
        ),
      ],
    );
  }
}
