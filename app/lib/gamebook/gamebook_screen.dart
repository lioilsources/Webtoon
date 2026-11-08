import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../i18n/ui_strings.dart';
import '../models/episode.dart';
import '../providers/providers.dart';
import '../providers/language_provider.dart';
import '../reader/episode_view.dart';
import '../reader/panel_view.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'branch_editor_screen.dart';
import 'gamebook.dart';
import 'gamebook_state.dart';

/// Reads one gamebook offline: one node at a time, its choices at the end (only those whose
/// condition holds, plus the reader's own branches), endings with "Začít znovu" / "Zkusit znovu".
/// [startAt] + [preview] play an own branch from the editor without touching the saved progress.
class GamebookScreen extends ConsumerStatefulWidget {
  final String gamebookId;
  final String? startAt;
  final bool preview;
  final bool kitUnlocked;

  const GamebookScreen({
    super.key,
    required this.gamebookId,
    this.startAt,
    this.preview = false,
    this.kitUnlocked = false,
  });

  @override
  ConsumerState<GamebookScreen> createState() => _GamebookScreenState();
}

class _GamebookScreenState extends ConsumerState<GamebookScreen> {
  GamebookProgress? _progress;

  Gamebook? get _book =>
      ref.read(packStoreProvider).gamebook(widget.gamebookId);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final g = _book;
    if (g == null) return;
    GamebookProgress? pr;
    if (widget.startAt != null) {
      pr = GamebookProgress(node: widget.startAt!, visited: {widget.startAt!});
    } else {
      pr = await ref.read(gamebookRepositoryProvider).loadProgress(g.id);
    }
    if (!mounted) return;
    final branches = ref.read(branchesProvider(g.id));
    final known =
        pr != null &&
        (g.node(pr.node) != null || branches.node(pr.node) != null);
    // A node an update removed (never on purpose: export-pack refuses it) restarts the book
    // but keeps what was found.
    final next = pr == null
        ? GamebookProgress.start(g)
        : (known ? pr : pr.restart(g)).withKnown(g);
    setState(() => _progress = next);
    final fresh = next.newNodes(g);
    final ui = ref.read(uiLanguageProvider);
    if (fresh.isNotEmpty && !widget.preview) {
      ScaffoldMessenger.maybeOf(context)?.showSnackBar(
        SnackBar(
          key: const ValueKey('gamebook-new-nodes'),
          content: Text(
            fresh.length == 1
                ? tr(ui, 'gamebook.newNode')
                : tr(ui, 'gamebook.newNodes', {'n': fresh.length}),
          ),
        ),
      );
    }
  }

  Future<void> _set(GamebookProgress pr) async {
    setState(() => _progress = pr);
    if (!widget.preview) {
      await ref
          .read(gamebookRepositoryProvider)
          .saveProgress(widget.gamebookId, pr);
    }
  }

  @override
  Widget build(BuildContext context) {
    final g = ref.watch(packStoreProvider).gamebook(widget.gamebookId);
    final branches = ref.watch(branchesProvider(widget.gamebookId));
    final pr = _progress;
    final ui = ref.watch(uiLanguageProvider);
    if (g == null) {
      return Scaffold(
        appBar: AppBar(),
        body: EmptyState(
          icon: Icons.menu_book_outlined,
          title: tr(ui, 'gamebook.notDownloaded'),
        ),
      );
    }
    final lang = ref.watch(readerLanguageProvider);
    final official = pr == null ? null : g.node(pr.node);
    final own = pr == null ? null : branches.node(pr.node);
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.preview ? tr(ui, 'gamebook.preview') : g.titleIn(lang),
          overflow: TextOverflow.ellipsis,
        ),
        actions: [
          if (pr != null && pr.path.isNotEmpty)
            IconButton(
              key: const ValueKey('gamebook-back'),
              tooltip: tr(ui, 'gamebook.back'),
              icon: const Icon(Icons.undo_rounded),
              onPressed: () => _set(pr.back()),
            ),
          if (pr != null && !widget.preview)
            IconButton(
              key: const ValueKey('gamebook-map'),
              tooltip: tr(ui, 'gamebook.map'),
              icon: const Icon(Icons.map_outlined),
              onPressed: () => _showMap(context, g, pr),
            ),
          if (widget.kitUnlocked && !widget.preview)
            IconButton(
              key: const ValueKey('gamebook-editor'),
              tooltip: tr(ui, 'gamebook.myBranches'),
              icon: const Icon(Icons.edit_note_rounded),
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute<void>(
                  builder: (_) => BranchEditorScreen(gamebookId: g.id),
                ),
              ),
            ),
        ],
      ),
      body: pr == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              key: ValueKey('gamebook-node-${pr.node}-${pr.path.length}'),
              padding: const EdgeInsets.only(bottom: 24),
              children: [
                if (official != null)
                  EpisodeView(
                    key: ValueKey('gamebook-episode-${official.episodeId}'),
                    episodeId: official.episodeId,
                    footer: (_) => _end(g, branches, pr, official: official),
                  )
                else if (own != null) ...[
                  BranchNodeView(gamebookId: g.id, node: own),
                  _end(g, branches, pr, own: own),
                ] else
                  EmptyState(
                    icon: Icons.help_outline_rounded,
                    title: tr(ui, 'gamebook.missingNode'),
                  ),
              ],
            ),
    );
  }

  Widget _end(
    Gamebook g,
    GamebookBranches branches,
    GamebookProgress pr, {
    GamebookNode? official,
    BranchNode? own,
  }) {
    final flags = pr.flags(g);
    final lang = ref.read(readerLanguageProvider);
    final choices =
        [
              if (official != null)
                for (final c in official.choices)
                  if (evalCondition(c.condition, flags)) c,
              if (own != null) ...own.choices,
              ...branches.hooksAt(pr.node),
            ]
            .where((c) => g.node(c.to) != null || branches.node(c.to) != null)
            .toList();
    if (official?.ending == GamebookEnding.good &&
        !pr.endingsFound.contains(pr.node)) {
      // counted when shown, so the end card already says "2 z 2"
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted && _progress?.node == pr.node) _set(pr.found(pr.node));
      });
    }
    return GamebookNodeEnd(
      choices: [
        for (final c in choices)
          (c, own == null && official != null && !official.choices.contains(c)),
      ],
      language: lang,
      next: official?.next,
      ending:
          official?.ending ??
          (own != null && own.isEnding && choices.isEmpty
              ? GamebookEnding.good
              : GamebookEnding.none),
      ownEnding: own != null,
      found: {
        ...pr.endingsFound,
        if (official?.ending == GamebookEnding.good) pr.node,
      }.where((id) => g.node(id)?.ending == GamebookEnding.good).length,
      total: g.endings,
      onGo: (to) => _set(pr.go(to)),
      onRetry: official?.retryTo == null
          ? null
          : () => _set(pr.retry(official!.retryTo!)),
      onRestart: widget.preview ? null : () => _set(pr.restart(g)),
      onClose: widget.preview ? () => Navigator.of(context).pop() : null,
    );
  }

  void _showMap(BuildContext context, Gamebook g, GamebookProgress pr) {
    final scheme = Theme.of(context).colorScheme;
    final ui = ref.read(uiLanguageProvider);
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (ctx) => ListView(
        key: const ValueKey('gamebook-map-sheet'),
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
        children: [
          Text(
            tr(ui, 'gamebook.map'),
            style: ComicFonts.title().copyWith(fontSize: 24),
          ),
          const SizedBox(height: 4),
          Text(
            tr(ui, 'gamebook.endingsFound', {
              'found': pr.endingsFound
                  .where((id) => g.node(id)?.ending == GamebookEnding.good)
                  .length,
              'total': g.endings,
            }),
            style: TextStyle(color: scheme.onSurfaceVariant),
          ),
          if (pr.visited.length > 1) ...[
            const SizedBox(height: 2),
            Text(
              tr(ui, 'gamebook.revisitHint'),
              style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13),
            ),
          ],
          const SizedBox(height: 12),
          for (final id in g.order)
            ListTile(
              key: ValueKey('map-node-$id'),
              dense: true,
              // a chapter already read opens again, read-only: the progress stays where it is
              onTap: pr.visited.contains(id)
                  ? () {
                      Navigator.pop(ctx);
                      Navigator.of(context).push(
                        MaterialPageRoute<void>(
                          builder: (_) => GamebookRevisitScreen(
                            gamebookId: g.id,
                            chapters: [
                              for (final n in g.order)
                                if (pr.visited.contains(n)) n,
                            ],
                            start: id,
                          ),
                        ),
                      );
                    }
                  : null,
              leading: Icon(
                id == pr.node
                    ? Icons.place_rounded
                    : g.node(id)!.ending == GamebookEnding.good
                    ? Icons.emoji_events_rounded
                    : Icons.circle,
                size: id == pr.node ? 24 : 14,
                color: pr.visited.contains(id)
                    ? ComicColors.accent
                    : scheme.outlineVariant,
              ),
              // unvisited nodes stay a secret; ones an update added say so
              title: Text(pr.visited.contains(id) ? g.node(id)!.title : '???'),
              trailing: pr.newNodes(g).contains(id)
                  ? Tag(tr(ui, 'gamebook.new'), key: const ValueKey('map-new'))
                  : null,
            ),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            key: const ValueKey('gamebook-restart'),
            onPressed: () {
              Navigator.pop(ctx);
              _set(pr.restart(g));
            },
            icon: const Icon(Icons.replay_rounded),
            label: Text(tr(ui, 'gamebook.restart')),
          ),
        ],
      ),
    );
  }
}

/// Re-reading the chapters already unlocked ("Moje cesta" → a visited chapter): one chapter at a
/// time with previous / next among the visited ones, in the book's order. Read-only: no choices,
/// and the saved progress is not touched.
class GamebookRevisitScreen extends ConsumerStatefulWidget {
  final String gamebookId;
  final List<String> chapters;
  final String start;
  const GamebookRevisitScreen({
    super.key,
    required this.gamebookId,
    required this.chapters,
    required this.start,
  });

  @override
  ConsumerState<GamebookRevisitScreen> createState() =>
      _GamebookRevisitScreenState();
}

class _GamebookRevisitScreenState extends ConsumerState<GamebookRevisitScreen> {
  late int _i = widget.chapters.indexOf(widget.start).clamp(0, 1 << 30);

  @override
  Widget build(BuildContext context) {
    final g = ref.watch(packStoreProvider).gamebook(widget.gamebookId);
    final ui = ref.watch(uiLanguageProvider);
    final node = g?.node(widget.chapters[_i]);
    if (g == null || node == null) {
      return Scaffold(
        appBar: AppBar(),
        body: EmptyState(
          icon: Icons.menu_book_outlined,
          title: tr(ui, 'gamebook.missingNode'),
        ),
      );
    }
    final hasPrev = _i > 0, hasNext = _i < widget.chapters.length - 1;
    return Scaffold(
      appBar: AppBar(title: Text(node.title, overflow: TextOverflow.ellipsis)),
      body: ListView(
        key: ValueKey('revisit-${node.id}'),
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          EpisodeView(
            key: ValueKey('revisit-episode-${node.episodeId}'),
            episodeId: node.episodeId,
            footer: (_) => Padding(
              padding: const EdgeInsets.fromLTRB(16, 20, 16, 8),
              child: Row(
                children: [
                  if (hasPrev)
                    Expanded(
                      child: OutlinedButton.icon(
                        key: const ValueKey('revisit-prev'),
                        onPressed: () => setState(() => _i--),
                        icon: const Icon(Icons.chevron_left_rounded),
                        label: Text(tr(ui, 'gamebook.prevChapter')),
                      ),
                    ),
                  if (hasPrev && hasNext) const SizedBox(width: 12),
                  if (hasNext)
                    Expanded(
                      child: FilledButton.icon(
                        key: const ValueKey('revisit-next'),
                        onPressed: () => setState(() => _i++),
                        icon: const Icon(Icons.chevron_right_rounded),
                        label: Text(tr(ui, 'gamebook.nextChapter')),
                      ),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// An own branch node: the chosen gamebook images with the reader's bubbles. Bubbles are laid
/// out like any panel's (off faces, bubble_layout.dart), since they carry no anchors.
class BranchNodeView extends ConsumerWidget {
  final String gamebookId;
  final BranchNode node;
  const BranchNodeView({
    super.key,
    required this.gamebookId,
    required this.node,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final api = ref.watch(apiProvider);
    final store = ref.watch(packStoreProvider);
    final ui = ref.watch(uiLanguageProvider);
    return LayoutBuilder(
      builder: (context, c) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 20, 16, 12),
            child: Row(
              children: [
                Tag(tr(ui, 'gamebook.myBranch')),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    node.title.isEmpty ? tr(ui, 'common.untitled') : node.title,
                    style: ComicFonts.title().copyWith(fontSize: 26),
                  ),
                ),
              ],
            ),
          ),
          for (final (i, bp) in node.panels.indexed) ...[
            if (sourcePanel(store.episode(bp.episodeId), bp) case final p?)
              PanelView(
                key: ValueKey('branch-panel-${node.id}-$i'),
                panel: p,
                image: p.imageUrl == null ? null : api.panelImage(p.imageUrl!),
                video: p.videoUrl == null ? null : api.panelImage(p.videoUrl!),
              ),
            SizedBox(height: gapHeight(GapSize.small, c.maxWidth)),
          ],
        ],
      ),
    );
  }
}

/// The gamebook image behind [bp] with [bp]'s bubbles; null when the episode is gone.
Panel? sourcePanel(Episode? e, BranchPanel bp) {
  if (e == null) return null;
  for (final p in e.panels) {
    if (p.index == bp.panelIndex) return p.copyWith(bubbles: bp.bubbles);
  }
  return null;
}

/// End of a node: its choices (own ones marked), "Pokračovat" for a linear node, or an ending.
class GamebookNodeEnd extends ConsumerWidget {
  /// (choice, isOwn)
  final List<(GamebookChoice, bool)> choices;
  final String? language;
  final String? next;
  final GamebookEnding ending;
  final bool ownEnding;
  final int found;
  final int total;
  final ValueChanged<String> onGo;
  final VoidCallback? onRetry;
  final VoidCallback? onRestart;
  final VoidCallback? onClose;

  const GamebookNodeEnd({
    super.key,
    required this.choices,
    required this.onGo,
    this.language,
    this.next,
    this.ending = GamebookEnding.none,
    this.ownEnding = false,
    this.found = 0,
    this.total = 0,
    this.onRetry,
    this.onRestart,
    this.onClose,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ui = ref.watch(uiLanguageProvider);
    final scheme = Theme.of(context).colorScheme;
    final comic = ComicTheme.of(context);
    final children = <Widget>[];
    if (choices.isNotEmpty) {
      children.add(
        Text(
          tr(ui, 'gamebook.whatNow'),
          style: ComicFonts.title().copyWith(fontSize: 28, height: 1.1),
        ),
      );
      children.add(const SizedBox(height: 14));
      for (final (c, own) in choices) {
        children.add(
          _ChoiceButton(
            key: ValueKey('gamebook-choice-${c.id}'),
            text: c.textIn(language),
            own: own,
            onTap: () => onGo(c.to),
          ),
        );
        children.add(const SizedBox(height: 10));
      }
    } else if (next != null) {
      children.add(
        FilledButton.icon(
          key: const ValueKey('gamebook-next'),
          onPressed: () => onGo(next!),
          icon: const Icon(Icons.arrow_downward_rounded),
          label: Text(tr(ui, 'gate.continue')),
        ),
      );
    } else if (ending == GamebookEnding.retry) {
      children.addAll([
        Text(
          tr(ui, 'gamebook.deadEnd'),
          style: ComicFonts.title().copyWith(fontSize: 28),
        ),
        const SizedBox(height: 6),
        Text(
          tr(ui, 'gamebook.deadEndHint'),
          style: TextStyle(color: scheme.onSurfaceVariant),
        ),
        const SizedBox(height: 14),
        if (onRetry != null)
          FilledButton.icon(
            key: const ValueKey('gamebook-retry'),
            onPressed: onRetry,
            icon: const Icon(Icons.replay_rounded),
            label: Text(tr(ui, 'store.retry')),
          ),
      ]);
    } else {
      children.addAll([
        Text(
          tr(ui, ownEnding ? 'gamebook.branchEnd' : 'common.end'),
          style: ComicFonts.title().copyWith(fontSize: 32),
        ),
        if (!ownEnding && total > 0) ...[
          const SizedBox(height: 6),
          Text(
            tr(ui, 'gamebook.endingsFound', {'found': found, 'total': total}),
            key: const ValueKey('gamebook-endings'),
            style: TextStyle(color: scheme.onSurfaceVariant),
          ),
        ],
        const SizedBox(height: 14),
      ]);
    }
    if (choices.isEmpty && next == null) {
      if (onRestart != null) {
        children.add(
          OutlinedButton.icon(
            key: const ValueKey('gamebook-restart-end'),
            onPressed: onRestart,
            icon: const Icon(Icons.restart_alt_rounded),
            label: Text(tr(ui, 'gamebook.restart')),
          ),
        );
      }
      if (onClose != null) {
        children.add(
          OutlinedButton(
            key: const ValueKey('gamebook-close'),
            onPressed: onClose,
            child: Text(tr(ui, 'gamebook.backToEditor')),
          ),
        );
      }
    }
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 36),
      child: Container(
        key: const ValueKey('gamebook-end'),
        padding: const EdgeInsets.all(20),
        decoration: comic.card(color: scheme.surface, radius: 22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: children,
        ),
      ),
    );
  }
}

class _ChoiceButton extends StatelessWidget {
  final String text;
  final bool own;
  final VoidCallback onTap;
  const _ChoiceButton({
    super.key,
    required this.text,
    required this.own,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final comic = ComicTheme.of(context);
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Ink(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
          decoration: BoxDecoration(
            // Opaque: a translucent fill lets the hard shadow show through and hides the text.
            color: Color.alphaBlend(
              ComicColors.accent.withValues(alpha: own ? 0.06 : 0.14),
              scheme.surface,
            ),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: ComicColors.accent, width: 2.5),
            boxShadow: [
              BoxShadow(color: comic.shadow, offset: const Offset(3, 3)),
            ],
          ),
          child: Row(
            children: [
              if (own) ...[
                const Icon(Icons.edit_rounded, size: 18),
                const SizedBox(width: 8),
              ],
              Expanded(
                child: Text(
                  text,
                  style: ComicFonts.ui(
                    800,
                  ).copyWith(fontSize: 16, color: scheme.onSurface),
                ),
              ),
              const Icon(Icons.chevron_right_rounded),
            ],
          ),
        ),
      ),
    );
  }
}
