import 'package:flutter/material.dart';

import '../models/campaign.dart';
import '../models/episode.dart';
import '../theme.dart';
import '../widgets/common.dart';

/// End of an episode in the offline reader when the story goes on: the choices as they were
/// offered, the one that was taken (`chosen` of the next episode) highlighted, the rest
/// muted and not tappable, and "Další díl". Nothing here generates anything.
class LocalEpisodeEnd extends StatelessWidget {
  final List<Choice> choices;
  final Chosen? chosen;
  final VoidCallback onNext;

  const LocalEpisodeEnd({
    super.key,
    required this.choices,
    required this.chosen,
    required this.onNext,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final comic = ComicTheme.of(context);
    final closed = choices.where((c) => !c.isFree).toList();
    final takenId = chosen?.choiceId;
    final matched = closed.any((c) => c.id == takenId);
    // A free-text answer (or a choice no longer in the list) is shown as its own row.
    final extra = !matched && (chosen?.text.isNotEmpty ?? false)
        ? chosen!.text
        : null;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 36),
      child: Container(
        key: const ValueKey('local-episode-end'),
        padding: const EdgeInsets.all(20),
        decoration: comic.card(color: scheme.surface, radius: 22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              'Co udělá dál?',
              style: ComicFonts.title().copyWith(fontSize: 28, height: 1.1),
            ),
            const SizedBox(height: 14),
            for (final c in closed) ...[
              _RecordedChoice(
                key: ValueKey('choice-${c.id}'),
                text: c.text,
                taken: c.id == takenId,
              ),
              const SizedBox(height: 10),
            ],
            if (extra != null) ...[
              _RecordedChoice(
                key: const ValueKey('choice-chosen'),
                text: extra,
                taken: true,
              ),
              const SizedBox(height: 10),
            ],
            const SizedBox(height: 4),
            FilledButton.icon(
              key: const ValueKey('next-episode'),
              onPressed: onNext,
              icon: const Icon(Icons.arrow_downward_rounded),
              label: const Text('Další díl'),
            ),
          ],
        ),
      ),
    );
  }
}

class _RecordedChoice extends StatelessWidget {
  final String text;
  final bool taken;
  const _RecordedChoice({super.key, required this.text, required this.taken});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final comic = ComicTheme.of(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      decoration: BoxDecoration(
        color: taken
            ? ComicColors.accent.withValues(alpha: 0.14)
            : scheme.surfaceContainerHighest.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: taken
              ? ComicColors.accent
              : scheme.outlineVariant.withValues(alpha: 0.7),
          width: taken ? 2.5 : 1.5,
        ),
        boxShadow: taken
            ? [BoxShadow(color: comic.shadow, offset: const Offset(3, 3))]
            : const [],
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              text,
              style: ComicFonts.ui(taken ? 800 : 600).copyWith(
                fontSize: 16,
                color: taken
                    ? scheme.onSurface
                    : scheme.onSurfaceVariant.withValues(alpha: 0.7),
              ),
            ),
          ),
          Icon(
            taken ? Icons.check_circle_rounded : Icons.radio_button_unchecked,
            color: taken
                ? ComicColors.accent
                : scheme.outlineVariant.withValues(alpha: 0.7),
          ),
        ],
      ),
    );
  }
}

/// After the last episode of a story in the offline reader: "Konec" and another story to
/// read next (same world when there is one).
class LocalStoryEnd extends StatelessWidget {
  final CampaignSummary? suggestion;
  final ValueChanged<CampaignSummary> onOpen;

  const LocalStoryEnd({super.key, this.suggestion, required this.onOpen});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final s = suggestion;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 48),
      child: Column(
        key: const ValueKey('story-end'),
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 8),
          Text(
            'Konec',
            textAlign: TextAlign.center,
            style: ComicFonts.title().copyWith(fontSize: 34),
          ),
          const SizedBox(height: 4),
          Text(
            'Tady příběh končí.',
            textAlign: TextAlign.center,
            style: TextStyle(color: scheme.onSurfaceVariant),
          ),
          if (s != null) ...[
            const SizedBox(height: 24),
            Text(
              'Další příběh',
              style: ComicFonts.ui(
                800,
              ).copyWith(fontSize: 13, color: scheme.onSurfaceVariant),
            ),
            const SizedBox(height: 8),
            ComicCard(
              key: const ValueKey('next-story'),
              onTap: () => onOpen(s),
              child: Row(
                children: [
                  const Icon(Icons.auto_stories_rounded, size: 32),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          s.title.isNotEmpty ? s.title : s.worldTitle,
                          style: ComicFonts.title().copyWith(fontSize: 20),
                        ),
                        if (s.worldTitle.isNotEmpty && s.worldTitle != s.title)
                          Text(
                            s.worldTitle,
                            style: TextStyle(color: scheme.onSurfaceVariant),
                          ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right_rounded),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}
