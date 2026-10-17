import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/world.dart';
import '../providers/providers.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'world_detail_screen.dart';

/// Worlds: public ones plus the user's own (GET /worlds).
class WorldsScreen extends ConsumerWidget {
  const WorldsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final worlds = ref.watch(worldsProvider);
    final userId = ref.watch(apiProvider).userId;
    return Scaffold(
      appBar: AppBar(title: const Text('Světy')),
      body: worlds.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorRetry(
          message: '$e',
          onRetry: () => ref.invalidate(worldsProvider),
        ),
        data: (list) {
          if (list.isEmpty) {
            return const EmptyState(
              icon: Icons.public_off_rounded,
              title: 'Zatím tu nejsou žádné světy',
            );
          }
          final mine = list.where((w) => w.isMine(userId)).toList();
          final others = list.where((w) => !w.isMine(userId)).toList();
          return RefreshIndicator(
            onRefresh: () => ref.refresh(worldsProvider.future),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              children: [
                if (mine.isNotEmpty) ...[
                  const _Section('Moje světy'),
                  for (final w in mine) _WorldCard(world: w, mine: true),
                ],
                if (others.isNotEmpty) ...[
                  if (mine.isNotEmpty) const _Section('Veřejné světy'),
                  for (final w in others) _WorldCard(world: w, mine: false),
                ],
              ],
            ),
          );
        },
      ),
    );
  }
}

class _Section extends StatelessWidget {
  final String text;
  const _Section(this.text);

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 8, 4, 12),
    child: Text(text, style: Theme.of(context).textTheme.titleLarge),
  );
}

class _WorldCard extends StatelessWidget {
  final WorldSummary world;
  final bool mine;
  const _WorldCard({required this.world, required this.mine});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: ComicCard(
        key: ValueKey('world-${world.id}'),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => WorldDetailScreen(worldId: world.id),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    world.title,
                    style: ComicFonts.title().copyWith(
                      fontSize: 24,
                      height: 1.1,
                    ),
                  ),
                ),
                if (mine)
                  const Tag(
                    'Můj',
                    color: ComicColors.accent,
                    textColor: Colors.white,
                  ),
              ],
            ),
            if (world.synopsis.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                world.synopsis,
                maxLines: 3,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: scheme.onSurfaceVariant, height: 1.35),
              ),
            ],
            const SizedBox(height: 12),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                Tag(audienceLabel(world.audience)),
                if (world.tone.isNotEmpty) Tag(world.tone),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
