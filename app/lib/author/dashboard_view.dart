import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/world.dart';
import '../providers/providers.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'author_widgets.dart';

/// Author dashboard (GET /worlds/{id}/stats): campaigns, where players stopped, choice
/// distribution per episode, canon progress, player-created characters.
class WorldDashboard extends ConsumerWidget {
  final World world;
  final VoidCallback onPlay;
  const WorldDashboard({super.key, required this.world, required this.onPlay});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(worldStatsProvider(world.id));
    return stats.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => ErrorRetry(
        message: '$e',
        onRetry: () => ref.invalidate(worldStatsProvider(world.id)),
      ),
      data: (s) => RefreshIndicator(
        onRefresh: () => ref.refresh(worldStatsProvider(world.id).future),
        child: ListView(
          key: const ValueKey('dashboard'),
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 40),
          children: [
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                _Tile('Kampaně', s.campaigns),
                _Tile('Hráči', s.players),
                _Tile('Díly', s.episodes),
                _Tile('Hotové díly', s.episodesReady),
                _Tile('Selhané díly', s.episodesFailed),
                _Tile('Panely', s.panelsReady),
                _Tile('Postavy hráčů', s.playerCreatedCount),
              ],
            ),
            const SectionTitle('Kde hráči skončili'),
            if (s.stoppedAt.isEmpty)
              const Hint('Zatím žádné kampaně.')
            else
              _Bars(
                rows: [
                  for (final b in s.stoppedAt)
                    (b.key == 0 ? 'bez dílu' : '${b.key}. díl', b.count),
                ],
              ),
            const SectionTitle('Volby po dílech'),
            if (s.choicesByEpisode.isEmpty)
              const Hint('Zatím nikdo nevolil.')
            else
              for (final e in s.choicesByEpisode) ...[
                Text(
                  'Po ${e.episode}. dílu (${e.total}×)',
                  style: ComicFonts.ui(800),
                ),
                const SizedBox(height: 4),
                _Bars(
                  rows: [
                    for (final c
                        in (e.choices.entries.toList()
                          ..sort((a, b) => a.key.compareTo(b.key))))
                      (_choiceLabel(c.key), c.value),
                  ],
                  total: e.total,
                ),
                const SizedBox(height: 12),
              ],
            if (s.byKind.isNotEmpty) ...[
              Hint(
                'Celkem: uzavřené volby ${s.byKind['closed'] ?? 0}×, '
                'volný text ${s.byKind['free'] ?? 0}×.',
              ),
            ],
            const SectionTitle('Kánon'),
            if (world.canonNodes.isEmpty)
              const Hint('Svět nemá kanonické uzly.')
            else
              _Bars(
                rows: [
                  for (final n in world.canonNodes)
                    (n.text, s.canonReached[n.id] ?? 0),
                ],
                total: s.campaigns,
              ),
            const SectionTitle('Postavy vytvořené hráči'),
            if (s.playerCreated.isEmpty)
              const Hint('Žádné.')
            else
              for (final c in s.playerCreated)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: ComicCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(c.name, style: ComicFonts.title()),
                        Text(
                          'hráč ${c.ownerId}',
                          style: ComicFonts.ui(
                            700,
                          ).copyWith(fontSize: 12, color: ComicColors.accent),
                        ),
                        if (c.description.isNotEmpty) Text(c.description),
                      ],
                    ),
                  ),
                ),
            const SizedBox(height: 24),
            FilledButton.icon(
              key: const ValueKey('play-own-dashboard'),
              onPressed: onPlay,
              icon: const Icon(Icons.play_arrow_rounded),
              label: const Text('Zahraj si vlastní svět'),
            ),
          ],
        ),
      ),
    );
  }
}

String _choiceLabel(String id) => switch (id) {
  'free' => 'volný text',
  final c when c.startsWith('c') => '${c.substring(1)}. volba',
  final c => c,
};

class _Tile extends StatelessWidget {
  final String label;
  final int value;
  const _Tile(this.label, this.value);

  @override
  Widget build(BuildContext context) => SizedBox(
    width: 112,
    child: ComicCard(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$value',
            style: ComicFonts.title().copyWith(
              fontSize: 28,
              color: ComicColors.accent,
            ),
          ),
          Text(label, style: ComicFonts.ui(700).copyWith(fontSize: 12)),
        ],
      ),
    ),
  );
}

/// Horizontal bars: label, bar proportional to count/total (total = max when omitted).
class _Bars extends StatelessWidget {
  final List<(String, int)> rows;
  final int? total;
  const _Bars({required this.rows, this.total});

  @override
  Widget build(BuildContext context) {
    final max = total != null && total! > 0
        ? total!
        : rows.fold<int>(1, (m, r) => r.$2 > m ? r.$2 : m);
    final scheme = Theme.of(context).colorScheme;
    return Column(
      children: [
        for (final (label, n) in rows)
          Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(
              children: [
                SizedBox(
                  width: 120,
                  child: Text(
                    label,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13),
                  ),
                ),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(6),
                    child: LinearProgressIndicator(
                      value: max == 0 ? 0 : n / max,
                      minHeight: 14,
                      backgroundColor: scheme.surfaceContainerHighest,
                      color: ComicColors.accent,
                    ),
                  ),
                ),
                SizedBox(
                  width: 36,
                  child: Text(
                    '$n',
                    textAlign: TextAlign.right,
                    style: ComicFonts.ui(800),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
