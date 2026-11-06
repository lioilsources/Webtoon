import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n/ui_strings.dart';

import '../packs/pack_bootstrap.dart';
import '../theme.dart';

/// Shown while the starter pack is being extracted on first launch (or re-extracted).
class PackSplash extends ConsumerWidget {
  final PackBootstrapState state;
  final VoidCallback onRetry;
  const PackSplash({super.key, required this.state, required this.onRetry});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final lang = ref.watch(uiLanguageProvider);
    final scheme = Theme.of(context).colorScheme;
    final error = state.phase == PackPhase.error;
    final label = switch (state.phase) {
      PackPhase.loading => tr(lang, 'splash.loading'),
      PackPhase.extracting =>
        state.total > 0
            ? tr(lang, 'splash.preparingN', {
                'done': state.done,
                'total': state.total,
              })
            : tr(lang, 'splash.preparing'),
      PackPhase.ready => tr(lang, 'common.done'),
      PackPhase.error => tr(lang, 'splash.failed'),
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
                    trError(lang, state.error),
                    textAlign: TextAlign.center,
                    style: TextStyle(color: scheme.error, fontSize: 13),
                  ),
                  const SizedBox(height: 16),
                  OutlinedButton(
                    key: const ValueKey('pack-splash-retry'),
                    onPressed: onRetry,
                    child: Text(tr(lang, 'store.retry')),
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
