import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/episode.dart';
import '../models/world.dart';
import '../providers/episode_provider.dart';
import '../providers/language_provider.dart';
import '../providers/providers.dart';
import '../theme.dart';
import 'bubble_edit_dialog.dart';
import 'bubble_layout.dart';
import 'motion_sheet.dart';
import 'panel_view.dart';

/// Max width of the strip: webtoons are narrow; on a wide window the strip is centred.
const double kStripMaxWidth = 800;

/// Gap after a panel at the current strip width (compose.py GAPS scaled from width 800).
double gapHeight(GapSize g, double stripWidth) =>
    g.atWidth800 * stripWidth / kReferenceWidth;

/// One episode in the reader: title, generating progress, panels with gaps, and what the
/// player chose next (for episodes that are not the last one).
class EpisodeView extends ConsumerWidget {
  final String episodeId;
  final World? world;
  final bool editable;

  /// What was chosen to get to the *next* episode (shown under this one).
  final String? nextChosenText;

  /// Built under the panels once the episode is loaded (the offline reader puts the
  /// recorded choice + "Další díl" here).
  final Widget Function(Episode episode)? footer;

  const EpisodeView({
    super.key,
    required this.episodeId,
    this.world,
    this.editable = false,
    this.nextChosenText,
    this.footer,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final st = ref.watch(episodeProvider(episodeId));
    final ep = st.episode;
    final api = ref.watch(apiProvider);
    if (ep == null) {
      return _Frame(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 80),
          child: Center(
            child: st.error != null
                ? _ErrorBox(
                    message: st.error!,
                    onRetry: () =>
                        ref.read(episodeProvider(episodeId).notifier).refresh(),
                  )
                : const CircularProgressIndicator(),
          ),
        ),
      );
    }
    final notifier = ref.read(episodeProvider(episodeId).notifier);
    // Bubbles in the reader's language when this episode is fully translated into it;
    // edits still address the original panel (bubble indexes are the same).
    final lang = ep.displayLanguage(ref.watch(readerLanguageProvider));
    return _Frame(
      child: LayoutBuilder(
        builder: (context, c) {
          final width = c.maxWidth;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              EpisodeHeader(episode: ep, language: lang),
              if (ep.status.inProgress || ep.panels.any((p) => p.isPending))
                GeneratingBanner(episode: ep),
              if (ep.status == EpisodeStatus.failed && ep.panelsReady == 0)
                FailedEpisodeCard(episode: ep),
              if (st.error != null)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                  child: _ErrorBox(message: st.error!),
                ),
              for (final p in ep.panels) ...[
                PanelView(
                  key: ValueKey('panel-${ep.id}-${p.index}'),
                  panel: p.localized(lang),
                  image: p.imageUrl == null
                      ? null
                      : api.panelImage(p.imageUrl!),
                  video: p.videoUrl == null
                      ? null
                      : api.panelImage(p.videoUrl!),
                  panelsTotal: ep.panelsTotal,
                  busy: st.busyPanels.contains(p.index),
                  onEditBubble: editable
                      ? (bi) => _edit(context, notifier, p, bi)
                      : null,
                  onRegenerate: editable
                      ? () => notifier.regenerate(p.index)
                      : null,
                  onMotion: editable && p.isReady
                      ? () => _motion(context, notifier, p)
                      : null,
                ),
                SizedBox(height: gapHeight(p.gapAfter, width)),
              ],
              if (nextChosenText != null) ChosenNote(text: nextChosenText!),
              if (footer != null) footer!(ep),
            ],
          );
        },
      ),
    );
  }

  Future<void> _motion(
    BuildContext context,
    EpisodeNotifier notifier,
    Panel panel,
  ) async {
    final edit = await showMotionSheet(context, panel: panel);
    if (edit == null) return;
    final unchanged =
        !edit.reseed &&
        edit.animate == panel.animate &&
        (!edit.animate ||
            (edit.motion == panel.motion &&
                edit.loopSeconds == panel.loopSeconds));
    if (unchanged) return;
    final ok = await notifier.setMotion(panel.index, edit.toPatch());
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Pohyb panelu se nepodařilo uložit.')),
      );
    }
  }

  Future<void> _edit(
    BuildContext context,
    EpisodeNotifier notifier,
    Panel panel,
    int bubbleIndex,
  ) async {
    final b = panel.bubbles[bubbleIndex];
    final speaker = world?.character(b.speakerId)?.name;
    final text = await showBubbleEditDialog(
      context,
      bubble: b,
      speakerName: speaker,
    );
    if (text == null || text == b.text) return;
    final ok = await notifier.editBubble(panel.index, bubbleIndex, text);
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Text bubliny se nepodařilo uložit.')),
      );
    }
  }
}

/// Centres the strip at [kStripMaxWidth] on the reader background.
class _Frame extends StatelessWidget {
  final Widget child;
  const _Frame({required this.child});

  @override
  Widget build(BuildContext context) => Center(
    child: ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: kStripMaxWidth),
      child: child,
    ),
  );
}

class EpisodeHeader extends StatelessWidget {
  final Episode episode;

  /// Title language (null = original).
  final String? language;
  const EpisodeHeader({super.key, required this.episode, this.language});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final title = episode.title.isNotEmpty
        ? episode.titleIn(language)
        : (episode.status.inProgress ? 'Nový díl' : 'Bez názvu');
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 36, 20, 22),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
            decoration: BoxDecoration(
              color: ComicColors.accent,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              'DÍL ${episode.index}',
              style: ComicFonts.ui(
                900,
              ).copyWith(color: Colors.white, fontSize: 12, letterSpacing: 1.4),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            title,
            key: ValueKey('episode-title-${episode.id}'),
            style: ComicFonts.title().copyWith(
              fontSize: 34,
              height: 1.05,
              color: scheme.onSurface,
            ),
          ),
        ],
      ),
    );
  }
}

/// "Generuje se" state: queued → writing the storyboard → drawing panels k/n.
class GeneratingBanner extends StatelessWidget {
  final Episode episode;
  const GeneratingBanner({super.key, required this.episode});

  @override
  Widget build(BuildContext context) {
    final comic = ComicTheme.of(context);
    final scheme = Theme.of(context).colorScheme;
    final waiting = episode.error.startsWith('waiting');
    final total = episode.panelsTotal;
    final ready = episode.panelsReady;
    final (label, double? value) = switch (episode.status) {
      EpisodeStatus.queued => ('Díl čeká ve frontě…', null),
      EpisodeStatus.generating when total == 0 => ('Píšu scénář dílu…', null),
      _ => ('Kreslím panely $ready/$total', total == 0 ? null : ready / total),
    };
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
      child: Container(
        key: const ValueKey('generating-banner'),
        padding: const EdgeInsets.all(16),
        decoration: comic.card(color: scheme.surface),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.auto_awesome, color: ComicColors.accent),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    label,
                    style: ComicFonts.ui(800).copyWith(fontSize: 16),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: value,
                minHeight: 10,
                color: ComicColors.accent,
                backgroundColor: ComicColors.accent.withValues(alpha: 0.15),
              ),
            ),
            if (waiting) ...[
              const SizedBox(height: 10),
              Text(
                'Generovací server je teď mimo provoz (běží podle rozvrhu). '
                'Díl se dokončí, jakmile bude zase k dispozici.',
                style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class FailedEpisodeCard extends StatelessWidget {
  final Episode episode;
  const FailedEpisodeCard({super.key, required this.episode});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final comic = ComicTheme.of(context);
    final moderation = episode.error.contains('moderation');
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
      child: Container(
        key: const ValueKey('failed-episode'),
        padding: const EdgeInsets.all(16),
        decoration: comic.card(color: scheme.errorContainer),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Díl se nepodařilo vytvořit',
              style: ComicFonts.title().copyWith(
                fontSize: 20,
                color: scheme.onErrorContainer,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              moderation
                  ? 'Tvoje odpověď neprošla kontrolou obsahu. Zkus to jinak.'
                  : 'Zkus zvolit pokračování znovu.',
              style: TextStyle(color: scheme.onErrorContainer),
            ),
            if (episode.error.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(
                episode.error,
                style: TextStyle(
                  color: scheme.onErrorContainer.withValues(alpha: 0.7),
                  fontSize: 12,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// "Zvoleno: …" between an episode and the next one.
class ChosenNote extends StatelessWidget {
  final String text;
  const ChosenNote({super.key, required this.text});

  @override
  Widget build(BuildContext context) {
    final comic = ComicTheme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 28),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: comic.card(
          color: ComicColors.accent.withValues(alpha: 0.12),
          radius: 14,
        ),
        child: Row(
          children: [
            const Icon(
              Icons.subdirectory_arrow_right,
              color: ComicColors.accent,
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text.rich(
                TextSpan(
                  children: [
                    TextSpan(text: 'Zvoleno: ', style: ComicFonts.ui(800)),
                    TextSpan(text: text),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorBox extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;
  const _ErrorBox({required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          message,
          textAlign: TextAlign.center,
          style: TextStyle(color: scheme.error),
        ),
        if (onRetry != null) ...[
          const SizedBox(height: 10),
          OutlinedButton(onPressed: onRetry, child: const Text('Zkusit znovu')),
        ],
      ],
    );
  }
}
