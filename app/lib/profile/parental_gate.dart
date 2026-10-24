// Parental gate (App Store guideline 1.3 / Play Families): a simple arithmetic question a young
// child cannot answer, shown before every purchase and before switching the profile to Adults.

import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n/ui_strings.dart';

/// One question: "a × b".
class GateChallenge {
  final int a;
  final int b;
  const GateChallenge(this.a, this.b);

  int get answer => a * b;

  /// Two factors 3–9, never both under 5 (no 3 × 4 a child knows by heart).
  factory GateChallenge.random([Random? rng]) {
    final r = rng ?? Random();
    final a = 3 + r.nextInt(7);
    var b = 3 + r.nextInt(7);
    if (a < 5 && b < 5) b += 4;
    return GateChallenge(a, b);
  }
}

/// Produces the next question; tests override it with a fixed one.
final gateChallengeProvider = Provider<GateChallenge Function()>(
  (ref) => GateChallenge.random,
);

/// Shows the gate; true when the grown-up answered right. A wrong answer gets a new question.
Future<bool> showParentalGate(BuildContext context, WidgetRef ref) async {
  final next = ref.read(gateChallengeProvider);
  final lang = ref.read(uiLanguageProvider);
  final ok = await showDialog<bool>(
    context: context,
    builder: (_) => _GateDialog(next: next, lang: lang),
  );
  return ok == true;
}

class _GateDialog extends StatefulWidget {
  final GateChallenge Function() next;
  final String lang;
  const _GateDialog({required this.next, required this.lang});

  @override
  State<_GateDialog> createState() => _GateDialogState();
}

class _GateDialogState extends State<_GateDialog> {
  late GateChallenge _q = widget.next();
  final _ctrl = TextEditingController();
  bool _wrong = false;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _submit() {
    if (int.tryParse(_ctrl.text.trim()) == _q.answer) {
      Navigator.pop(context, true);
      return;
    }
    setState(() {
      _wrong = true;
      _q = widget.next();
      _ctrl.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final l = widget.lang;
    return AlertDialog(
      key: const ValueKey('parental-gate'),
      title: Text(tr(l, 'gate.title')),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            tr(l, 'gate.question', {'a': _q.a, 'b': _q.b}),
            key: const ValueKey('gate-question'),
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('gate-answer'),
            controller: _ctrl,
            autofocus: true,
            keyboardType: TextInputType.number,
            inputFormatters: [FilteringTextInputFormatter.digitsOnly],
            decoration: InputDecoration(
              hintText: tr(l, 'gate.hint'),
              errorText: _wrong ? tr(l, 'gate.wrong') : null,
            ),
            onSubmitted: (_) => _submit(),
          ),
        ],
      ),
      actions: [
        TextButton(
          key: const ValueKey('gate-cancel'),
          onPressed: () => Navigator.pop(context, false),
          child: Text(tr(l, 'store.cancel')),
        ),
        FilledButton(
          key: const ValueKey('gate-submit'),
          onPressed: _submit,
          child: Text(tr(l, 'gate.continue')),
        ),
      ],
    );
  }
}
