import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/world.dart';
import '../packs/pack_store.dart';
import '../providers/language_provider.dart';
import '../providers/providers.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'reader_screen.dart';

/// Reader mode: every story of the installed packs, grouped by world (cover + title); a tap
/// opens the reader at episode 1.
class LibraryScreen extends ConsumerWidget {
  const LibraryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Rebuild after a (re)install: the bootstrap state flips back to ready.
    ref.watch(packBootstrapProvider);
    final store = ref.watch(packStoreProvider);
    final lang = ref.watch(readerLanguageProvider);
    final worlds = store.worlds;
    final stories = store.stories;
    final byWorld = <String, List<PackStory>>{};
    for (final s in stories) {
      (byWorld[s.worldId] ??= []).add(s);
    }
    // Stories whose world is not in any pack still show, under a plain heading.
    final orphan = [
      for (final s in stories)
        if (!worlds.any((w) => w.id == s.worldId)) s,
    ];
    return Scaffold(
      appBar: AppBar(title: const Text('Knihovna')),
      body: stories.isEmpty
          ? const EmptyState(
              key: ValueKey('library-empty'),
              icon: Icons.auto_stories_outlined,
              title: 'Knihovna je prázdná',
              subtitle:
                  'Žádný balíček s příběhy není nainstalovaný. '
                  'Zkus „Obnovit starter“ v Nastavení.',
            )
          : ListView(
              key: const ValueKey('library-list'),
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              children: [
                for (final w in worlds)
                  if (byWorld[w.id]?.isNotEmpty ?? false) ...[
                    _WorldHeader(world: w),
                    _StoryGrid(stories: byWorld[w.id]!, language: lang),
                  ],
                if (orphan.isNotEmpty) ...[
                  const _PlainHeader('Další příběhy'),
                  _StoryGrid(stories: orphan, language: lang),
                ],
              ],
            ),
    );
  }
}

class _WorldHeader extends StatelessWidget {
  final WorldSummary world;
  const _WorldHeader({required this.world});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      key: ValueKey('library-world-${world.id}'),
      padding: const EdgeInsets.fromLTRB(4, 16, 4, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  world.title,
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
              const SizedBox(width: 8),
              AudienceBadge(
                key: ValueKey('audience-${world.id}'),
                audience: world.audience,
              ),
            ],
          ),
          if (world.synopsis.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              world.synopsis,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(color: scheme.onSurfaceVariant, height: 1.3),
            ),
          ],
        ],
      ),
    );
  }
}

class _PlainHeader extends StatelessWidget {
  final String text;
  const _PlainHeader(this.text);

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.fromLTRB(4, 16, 4, 10),
    child: Text(text, style: Theme.of(context).textTheme.headlineSmall),
  );
}

/// `audience` of a world as a coloured tag (kids green, teen violet, adult red).
class AudienceBadge extends StatelessWidget {
  final String audience;
  const AudienceBadge({super.key, required this.audience});

  @override
  Widget build(BuildContext context) {
    final color = switch (audience) {
      'kids' => const Color(0xFF2E9E5B),
      'adult' => const Color(0xFFC84A3C),
      _ => ComicColors.accent,
    };
    return Tag(
      audienceLabel(audience),
      color: color,
      textColor: Colors.white,
    );
  }
}

/// Cover cards in as many columns as fit (~150 px each, max 6).
class _StoryGrid extends StatelessWidget {
  final List<PackStory> stories;
  final String? language;
  const _StoryGrid({required this.stories, required this.language});

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, c) {
      final columns = (c.maxWidth / 150).floor().clamp(2, 6);
      return GridView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: 8),
        gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: columns,
          mainAxisSpacing: 14,
          crossAxisSpacing: 14,
          // Cover 416×608 plus two lines of title and the episode count under it.
          childAspectRatio: 416 / (608 + 210),
        ),
        itemCount: stories.length,
        itemBuilder: (_, i) => StoryCard(story: stories[i], language: language),
      );
    },
  );
}

class StoryCard extends StatelessWidget {
  final PackStory story;
  final String? language;
  const StoryCard({super.key, required this.story, this.language});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final comic = ComicTheme.of(context);
    final n = story.episodeIds.length;
    return Material(
      color: Colors.transparent,
      child: InkWell(
        key: ValueKey('story-${story.id}'),
        borderRadius: BorderRadius.circular(14),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) =>
                ReaderScreen(campaignId: story.id, startAtFirst: true),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // The cover takes whatever the cell leaves after the two text lines, so a large
            // text scale shrinks the cover instead of overflowing.
            Expanded(
              child: Ink(
                decoration: comic.card(
                  color: scheme.surfaceContainerHighest,
                  radius: 14,
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: SizedBox.expand(
                    child: story.cover == null
                        ? _noCover(scheme)
                        : Image.file(
                            File(story.cover!),
                            fit: BoxFit.cover,
                            errorBuilder: (_, _, _) => _noCover(scheme),
                          ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              story.titleIn(language),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: ComicFonts.title().copyWith(fontSize: 16, height: 1.15),
            ),
            const SizedBox(height: 2),
            Text(
              _episodes(n),
              style: ComicFonts.ui(
                700,
              ).copyWith(fontSize: 12, color: scheme.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }

  Widget _noCover(ColorScheme scheme) => Center(
    child: Icon(
      Icons.auto_stories_outlined,
      size: 40,
      color: scheme.onSurfaceVariant,
    ),
  );

  static String _episodes(int n) => switch (n) {
    1 => '1 díl',
    2 || 3 || 4 => '$n díly',
    _ => '$n dílů',
  };
}
