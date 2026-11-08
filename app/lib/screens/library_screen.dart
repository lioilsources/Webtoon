import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../gamebook/gamebook_shelf.dart';
import '../i18n/ui_strings.dart';
import '../models/world.dart';
import '../packs/pack_store.dart';
import '../providers/language_provider.dart';
import '../profile/reader_profile.dart';
import '../providers/providers.dart';
import '../shop/shop_controller.dart' show packsRevisionProvider;
import '../shop/update_banner.dart';
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
    // … and after a download / delete in Obchod.
    ref.watch(packsRevisionProvider);
    final store = ref.watch(packStoreProvider);
    final lang = ref.watch(readerLanguageProvider);
    final ui = ref.watch(uiLanguageProvider);
    // Kids profile: no adult worlds, no harlequin stories.
    final profile = ref.watch(readerProfileProvider.select((p) => p.profile));
    final stories = [
      for (final s in store.stories)
        if (storyVisibleIn(store, profile, s)) s,
    ];
    final gamebooks = visibleGamebooks(ref);
    final worlds = store.worlds;
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
      appBar: AppBar(title: Text(tr(ui, 'library.title'))),
      body: stories.isEmpty && gamebooks.isEmpty
          ? EmptyState(
              key: const ValueKey('library-empty'),
              icon: Icons.auto_stories_outlined,
              title: tr(ui, 'library.empty'),
              subtitle: tr(ui, 'library.emptyHint'),
            )
          : ListView(
              key: const ValueKey('library-list'),
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
              children: [
                const UpdateBanner(),
                if (gamebooks.isNotEmpty) GamebookShelf(gamebooks: gamebooks),
                ..._worldSections(
                  [
                    for (final w in _translatedFirst(worlds, byWorld, lang))
                      if (byWorld[w.id]?.isNotEmpty ?? false) w,
                  ],
                  byWorld,
                  lang,
                ),
                if (orphan.isNotEmpty) ...[
                  _PlainHeader(tr(ui, 'library.otherStories')),
                  _StoryGrid(stories: orphan, language: lang),
                ],
              ],
            ),
    );
  }
}

/// A world with several stories keeps its own section (header + grid). Runs of worlds with a
/// single story share one grid of world cards instead, so a tablet is not a column of lone covers
/// with an empty right half.
List<Widget> _worldSections(
  List<WorldSummary> worlds,
  Map<String, List<PackStory>> byWorld,
  String? lang,
) {
  // All single-story worlds first, in one grid (a run broken by a multi-story world would leave
  // half a tablet row empty), then the multi-story worlds with their own sections.
  final singles = [
    for (final w in worlds)
      if (byWorld[w.id]!.length == 1) w,
  ];
  return [
    if (singles.isNotEmpty)
      _WorldCardGrid(worlds: singles, byWorld: byWorld, language: lang),
    for (final w in worlds)
      if (byWorld[w.id]!.length > 1) ...[
        _WorldHeader(world: w, language: lang, stories: byWorld[w.id]!),
        _StoryGrid(stories: byWorld[w.id]!, language: lang),
      ],
  ];
}

/// Single-story worlds as cover cards (world title, audience tag on the cover), as many columns
/// as fit (~170 px each, 2 to 6).
class _WorldCardGrid extends StatelessWidget {
  final List<WorldSummary> worlds;
  final Map<String, List<PackStory>> byWorld;
  final String? language;
  const _WorldCardGrid({
    required this.worlds,
    required this.byWorld,
    required this.language,
  });

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.only(top: 16),
    child: LayoutBuilder(
      builder: (context, c) {
        final columns = (c.maxWidth / 170).floor().clamp(2, 6);
        return GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          padding: const EdgeInsets.only(bottom: 8),
          gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
            crossAxisCount: columns,
            mainAxisSpacing: 18,
            crossAxisSpacing: 14,
            childAspectRatio: 416 / (608 + 210),
          ),
          itemCount: worlds.length,
          itemBuilder: (_, i) {
            final w = worlds[i];
            final stories = byWorld[w.id]!;
            return KeyedSubtree(
              key: ValueKey('library-world-${w.id}'),
              child: StoryCard(
                story: stories.first,
                language: language,
                title: _WorldHeader(
                  world: w,
                  language: language,
                  stories: stories,
                )._title,
                badge: AudienceBadge(
                  key: ValueKey('audience-${w.id}'),
                  audience: w.audience,
                ),
              ),
            );
          },
        );
      },
    ),
  );
}

/// Reading in another language than a world's own: worlds whose stories have a title in that
/// language come first, untranslated ones after them (stable, otherwise the packs' order).
List<WorldSummary> _translatedFirst(
  List<WorldSummary> worlds,
  Map<String, List<PackStory>> byWorld,
  String? lang,
) {
  if (lang == null) return worlds;
  bool translated(WorldSummary w) =>
      lang == w.language ||
      w.titleI18n.containsKey(lang) ||
      (byWorld[w.id] ?? const []).any((s) => s.titleI18n.containsKey(lang));
  return [
    for (final w in worlds)
      if (translated(w)) w,
    for (final w in worlds)
      if (!translated(w)) w,
  ];
}

class _WorldHeader extends StatelessWidget {
  final WorldSummary world;
  final String? language;
  final List<PackStory> stories;
  const _WorldHeader({
    required this.world,
    required this.language,
    required this.stories,
  });

  /// The world's own translation, else the title of its first story translated into the reading
  /// language (worlds of today's packs carry no title_i18n; their stories do), else the original.
  String get _title {
    final lang = language;
    if (lang == null || lang == world.language) return world.title;
    final own = world.titleI18n[lang];
    if (own != null) return own;
    for (final s in stories) {
      final t = s.titleI18n[lang];
      if (t != null) return t;
    }
    return world.title;
  }

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
                  _title,
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
          if (world.synopsisIn(language)?.isNotEmpty ?? false) ...[
            const SizedBox(height: 4),
            Text(
              world.synopsisIn(language)!,
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
class AudienceBadge extends ConsumerWidget {
  final String audience;
  const AudienceBadge({super.key, required this.audience});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ui = ref.watch(uiLanguageProvider);
    final color = switch (audience) {
      'kids' => const Color(0xFF2E9E5B),
      'adult' => const Color(0xFFC84A3C),
      _ => ComicColors.accent,
    };
    final label = switch (audience) {
      'kids' || 'teen' || 'adult' => tr(ui, 'audience.$audience'),
      _ => audienceLabel(audience),
    };
    return Tag(label, color: color, textColor: Colors.white);
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

class StoryCard extends ConsumerWidget {
  final PackStory story;
  final String? language;

  /// Shown instead of the story title (a single-story world card shows its world's title).
  final String? title;

  /// Overlaid on the cover's top-right corner (the world's audience tag).
  final Widget? badge;
  const StoryCard({
    super.key,
    required this.story,
    this.language,
    this.title,
    this.badge,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ui = ref.watch(uiLanguageProvider);
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
                  child: Stack(
                    fit: StackFit.expand,
                    children: [
                      story.cover == null
                          ? _noCover(scheme)
                          : Image.file(
                              File(story.cover!),
                              fit: BoxFit.cover,
                              errorBuilder: (_, _, _) => _noCover(scheme),
                            ),
                      if (badge != null)
                        Positioned(top: 8, right: 8, child: badge!),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              title ?? story.titleIn(language),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: ComicFonts.title().copyWith(fontSize: 16, height: 1.15),
            ),
            const SizedBox(height: 2),
            Text(
              trPlural(ui, 'library.episodes', n),
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
}
