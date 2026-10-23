import 'package:flutter/material.dart';

import '../packs/pack_bootstrap.dart';
import '../theme.dart';

/// Shown while the starter pack is being extracted on first launch (or re-extracted).
class PackSplash extends StatelessWidget {
  final PackBootstrapState state;
  final VoidCallback onRetry;
  const PackSplash({super.key, required this.state, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final error = state.phase == PackPhase.error;
    final label = switch (state.phase) {
      PackPhase.loading => 'Načítám příběhy…',
      PackPhase.extracting =>
        state.total > 0
            ? 'Připravuji příběhy… ${state.done}/${state.total}'
            : 'Připravuji příběhy…',
      PackPhase.ready => 'Hotovo',
      PackPhase.error => 'Příběhy se nepodařilo připravit',
    };
    return Scaffold(
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 360),
            child: Column(
              key: const ValueKey('pack-splash'),
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Webtoon',
                  textAlign: TextAlign.center,
                  style: ComicFonts.title().copyWith(fontSize: 40),
                ),
                const SizedBox(height: 24),
                Text(
                  label,
                  textAlign: TextAlign.center,
                  style: ComicFonts.ui(700).copyWith(fontSize: 16),
                ),
                const SizedBox(height: 14),
                if (!error)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                      value: state.progress,
                      minHeight: 10,
                      color: ComicColors.accent,
                      backgroundColor: ComicColors.accent.withValues(
                        alpha: 0.15,
                      ),
                    ),
                  ),
                if (error) ...[
                  Text(
                    state.error ?? '',
                    textAlign: TextAlign.center,
                    style: TextStyle(color: scheme.error, fontSize: 13),
                  ),
                  const SizedBox(height: 16),
                  OutlinedButton(
                    key: const ValueKey('pack-splash-retry'),
                    onPressed: onRetry,
                    child: const Text('Zkusit znovu'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
