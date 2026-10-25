// Editor kit (beta, ../../docs/gamebook.md): the reader writes own branches into a bought
// gamebook, offline. A branch node is a remix — images of the book with the reader's own
// bubbles — and ends in choices (to any node) or an ending. Nothing is drawn or sent anywhere;
// "Odeslat autorovi" copies the branches as JSON for the author to draw them properly.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/episode.dart';
import '../providers/providers.dart';
import '../reader/panel_view.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'gamebook.dart';
import 'gamebook_screen.dart';
import 'gamebook_state.dart';

const _maxBubbles = 3;
const _maxBubbleChars = 120;
const _maxChoiceChars = 60;

/// "Moje větve": the reader's branches of one gamebook.
class BranchEditorScreen extends ConsumerWidget {
  final String gamebookId;
  const BranchEditorScreen({super.key, required this.gamebookId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final g = ref.watch(packStoreProvider).gamebook(gamebookId);
    final branches = ref.watch(branchesProvider(gamebookId));
    final scheme = Theme.of(context).colorScheme;
    if (g == null) {
      return Scaffold(
        appBar: AppBar(),
        body: const EmptyState(
          icon: Icons.menu_book_outlined,
          title: 'Gamebook není stažený.',
        ),
      );
    }
    final notifier = ref.read(branchesProvider(gamebookId).notifier);
    return Scaffold(
      appBar: AppBar(
        title: const Text('Moje větve'),
        actions: [
          IconButton(
            key: const ValueKey('branches-export'),
            tooltip: 'Odeslat autorovi',
            icon: const Icon(Icons.outbox_rounded),
            onPressed: branches.nodes.isEmpty
                ? null
                : () async {
                    final version =
                        ref
                            .read(packStoreProvider)
                            .installed(g.packId)
                            ?.manifest
                            .version ??
                        0;
                    await Clipboard.setData(
                      ClipboardData(
                        text: branches.exportFor(g, version: version),
                      ),
                    );
                    if (!context.mounted) return;
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text(
                          'Větve jsou zkopírované. Vlož je do e-mailu nebo zprávy autorovi.',
                        ),
                      ),
                    );
                  },
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        key: const ValueKey('branch-new'),
        onPressed: () => _newBranch(context, ref, g, branches),
        icon: const Icon(Icons.add_rounded),
        label: const Text('Nová větev'),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
        children: [
          Text(
            'Přidej do knihy vlastní odbočku: vyber, kde začne, poskládej ji z obrázků knihy '
            'a napiš bubliny. Větve vidíš jen ty; autorovi je můžeš poslat.',
            style: TextStyle(color: scheme.onSurfaceVariant),
          ),
          const SizedBox(height: 16),
          if (branches.nodes.isEmpty)
            const Padding(
              padding: EdgeInsets.only(top: 48),
              child: EmptyState(
                icon: Icons.alt_route_rounded,
                title: 'Zatím žádná větev',
                subtitle: 'Začni tlačítkem „Nová větev“.',
              ),
            ),
          for (final h in branches.hooks)
            _HookCard(
              key: ValueKey('hook-${h.fromNode}-${h.choice.id}'),
              from:
                  g.node(h.fromNode)?.title ??
                  branches.node(h.fromNode)?.title ??
                  h.fromNode,
              hook: h,
              target: branches.node(h.choice.to),
              onEdit: () => _openNode(context, h.choice.to),
              onPlay: () => _play(context, h.choice.to),
              onDelete: () async {
                if (!await _confirm(
                  context,
                  'Smazat odbočku „${h.choice.text}“?',
                )) {
                  return;
                }
                var b = branches.removeHook(h);
                // its node goes too unless another choice still leads there
                final still =
                    b.hooks.any((x) => x.choice.to == h.choice.to) ||
                    b.nodes.any(
                      (n) => n.choices.any((c) => c.to == h.choice.to),
                    );
                if (!still) b = b.removeNode(h.choice.to);
                await notifier.update(b);
              },
            ),
          if (branches.nodes.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              'Moje uzly',
              style: ComicFonts.ui(
                800,
              ).copyWith(fontSize: 13, color: scheme.onSurfaceVariant),
            ),
            for (final n in branches.nodes)
              ListTile(
                key: ValueKey('branch-node-${n.id}'),
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.edit_note_rounded),
                title: Text(n.title.isEmpty ? 'Bez názvu' : n.title),
                subtitle: Text(
                  '${n.panels.length} obr. · ${n.isEnding ? 'konec' : '${n.choices.length} volby'}',
                ),
                trailing: const Icon(Icons.chevron_right_rounded),
                onTap: () => _openNode(context, n.id),
              ),
          ],
        ],
      ),
    );
  }

  void _openNode(BuildContext context, String nodeId) =>
      Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) =>
              NodeEditorScreen(gamebookId: gamebookId, nodeId: nodeId),
        ),
      );

  void _play(BuildContext context, String nodeId) => Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => GamebookScreen(
        gamebookId: gamebookId,
        startAt: nodeId,
        preview: true,
      ),
    ),
  );

  Future<void> _newBranch(
    BuildContext context,
    WidgetRef ref,
    Gamebook g,
    GamebookBranches branches,
  ) async {
    final res = await showDialog<(String, String)>(
      context: context,
      builder: (_) => _NewBranchDialog(gamebook: g),
    );
    if (res == null) return;
    final (from, text) = res;
    final id = branches.newNodeId();
    final b = branches
        .putNode(BranchNode(id: id, title: text))
        .addHook(
          BranchHook(
            fromNode: from,
            choice: GamebookChoice(id: 'c_$id', text: text, to: id),
          ),
        );
    await ref.read(branchesProvider(gamebookId).notifier).update(b);
    if (context.mounted) _openNode(context, id);
  }
}

class _HookCard extends StatelessWidget {
  final String from;
  final BranchHook hook;
  final BranchNode? target;
  final VoidCallback onEdit;
  final VoidCallback onPlay;
  final VoidCallback onDelete;

  const _HookCard({
    super.key,
    required this.from,
    required this.hook,
    required this.target,
    required this.onEdit,
    required this.onPlay,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: ComicCard(
        onTap: onEdit,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Za: $from',
              style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13),
            ),
            const SizedBox(height: 4),
            Text(
              '„${hook.choice.text}“',
              style: ComicFonts.title().copyWith(fontSize: 20),
            ),
            const SizedBox(height: 4),
            Text(
              target == null
                  ? 'uzel chybí'
                  : '${target!.panels.length} obrázků',
              style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13),
            ),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton.icon(
                  onPressed: onPlay,
                  icon: const Icon(Icons.play_arrow_rounded),
                  label: const Text('Zahrát'),
                ),
                IconButton(
                  tooltip: 'Smazat',
                  onPressed: onDelete,
                  icon: const Icon(Icons.delete_outline_rounded),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _NewBranchDialog extends StatefulWidget {
  final Gamebook gamebook;
  const _NewBranchDialog({required this.gamebook});

  @override
  State<_NewBranchDialog> createState() => _NewBranchDialogState();
}

class _NewBranchDialogState extends State<_NewBranchDialog> {
  String? _from;
  final _text = TextEditingController();

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final g = widget.gamebook;
    final starts = [
      for (final id in g.order)
        if (!g.node(id)!.isEnding) g.node(id)!,
    ];
    final ok = _from != null && _text.text.trim().isNotEmpty;
    return AlertDialog(
      title: const Text('Nová větev'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          DropdownButtonFormField<String>(
            key: const ValueKey('branch-from'),
            initialValue: _from,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Kde odbočí'),
            items: [
              for (final n in starts)
                DropdownMenuItem(
                  value: n.id,
                  child: Text(n.title, overflow: TextOverflow.ellipsis),
                ),
            ],
            onChanged: (v) => setState(() => _from = v),
          ),
          const SizedBox(height: 12),
          TextField(
            key: const ValueKey('branch-choice'),
            controller: _text,
            maxLength: _maxChoiceChars,
            decoration: const InputDecoration(
              labelText: 'Nová volba',
              hintText: 'např. Zeptat se Murra na tajemství',
            ),
            onChanged: (_) => setState(() {}),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Zrušit'),
        ),
        FilledButton(
          key: const ValueKey('branch-create'),
          onPressed: ok
              ? () => Navigator.pop(context, (_from!, _text.text.trim()))
              : null,
          child: const Text('Vytvořit'),
        ),
      ],
    );
  }
}

/// One own node: title, images with bubbles, then choices or "konec".
class NodeEditorScreen extends ConsumerWidget {
  final String gamebookId;
  final String nodeId;
  const NodeEditorScreen({
    super.key,
    required this.gamebookId,
    required this.nodeId,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final g = ref.watch(packStoreProvider).gamebook(gamebookId);
    final branches = ref.watch(branchesProvider(gamebookId));
    final node = branches.node(nodeId);
    if (g == null || node == null) {
      return Scaffold(
        appBar: AppBar(),
        body: const EmptyState(
          icon: Icons.help_outline_rounded,
          title: 'Uzel neexistuje.',
        ),
      );
    }
    final api = ref.watch(apiProvider);
    final store = ref.watch(packStoreProvider);
    final notifier = ref.read(branchesProvider(gamebookId).notifier);
    final scheme = Theme.of(context).colorScheme;
    Future<void> save(BranchNode n) => notifier.update(branches.putNode(n));
    return Scaffold(
      appBar: AppBar(
        title: const Text('Upravit uzel'),
        actions: [
          IconButton(
            key: const ValueKey('node-play'),
            tooltip: 'Zahrát',
            icon: const Icon(Icons.play_arrow_rounded),
            onPressed: () => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => GamebookScreen(
                  gamebookId: gamebookId,
                  startAt: nodeId,
                  preview: true,
                ),
              ),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(0, 12, 0, 48),
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: TextFormField(
              key: ValueKey('node-title-$nodeId'),
              initialValue: node.title,
              maxLength: _maxChoiceChars,
              decoration: const InputDecoration(labelText: 'Název uzlu'),
              onChanged: (v) => save(node.copyWith(title: v)),
            ),
          ),
          for (final (i, bp) in node.panels.indexed) ...[
            if (sourcePanel(store.episode(bp.episodeId), bp) case final p?)
              PanelView(
                key: ValueKey('edit-panel-$i'),
                panel: p,
                image: p.imageUrl == null ? null : api.panelImage(p.imageUrl!),
              ),
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 4, 8, 12),
              child: Row(
                children: [
                  TextButton.icon(
                    key: ValueKey('edit-bubbles-$i'),
                    onPressed: () async {
                      final b = await showDialog<List<Bubble>>(
                        context: context,
                        builder: (_) =>
                            _BubblesDialog(lore: g.lore, bubbles: bp.bubbles),
                      );
                      if (b == null) return;
                      await save(
                        node.copyWith(
                          panels: [
                            for (final (j, x) in node.panels.indexed)
                              j == i ? x.withBubbles(b) : x,
                          ],
                        ),
                      );
                    },
                    icon: const Icon(Icons.chat_bubble_outline_rounded),
                    label: Text('Bubliny (${bp.bubbles.length})'),
                  ),
                  const Spacer(),
                  IconButton(
                    tooltip: 'Výš',
                    onPressed: i == 0
                        ? null
                        : () => save(
                            node.copyWith(panels: _swap(node.panels, i, i - 1)),
                          ),
                    icon: const Icon(Icons.arrow_upward_rounded),
                  ),
                  IconButton(
                    tooltip: 'Níž',
                    onPressed: i == node.panels.length - 1
                        ? null
                        : () => save(
                            node.copyWith(panels: _swap(node.panels, i, i + 1)),
                          ),
                    icon: const Icon(Icons.arrow_downward_rounded),
                  ),
                  IconButton(
                    key: ValueKey('remove-panel-$i'),
                    tooltip: 'Odebrat',
                    onPressed: () => save(
                      node.copyWith(panels: [...node.panels]..removeAt(i)),
                    ),
                    icon: const Icon(Icons.delete_outline_rounded),
                  ),
                ],
              ),
            ),
          ],
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: OutlinedButton.icon(
              key: const ValueKey('add-panel'),
              onPressed: () async {
                final picked = await _pickPanel(context, ref, g);
                if (picked == null) return;
                await save(node.copyWith(panels: [...node.panels, picked]));
              },
              icon: const Icon(Icons.add_photo_alternate_outlined),
              label: const Text('Přidat obrázek z knihy'),
            ),
          ),
          const SizedBox(height: 24),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'Na konci',
                  style: ComicFonts.title().copyWith(fontSize: 22),
                ),
                const SizedBox(height: 4),
                if (node.choices.isEmpty)
                  Text(
                    'Bez voleb tady větev končí.',
                    style: TextStyle(color: scheme.onSurfaceVariant),
                  ),
                for (final c in node.choices)
                  ListTile(
                    key: ValueKey('node-choice-${c.id}'),
                    contentPadding: EdgeInsets.zero,
                    title: Text(c.text),
                    subtitle: Text(
                      '→ ${g.node(c.to)?.title ?? branches.node(c.to)?.title ?? c.to}',
                    ),
                    trailing: IconButton(
                      icon: const Icon(Icons.close_rounded),
                      onPressed: () => save(
                        node.copyWith(
                          choices: [
                            for (final x in node.choices)
                              if (x.id != c.id) x,
                          ],
                        ),
                      ),
                    ),
                  ),
                const SizedBox(height: 8),
                OutlinedButton.icon(
                  key: const ValueKey('add-choice'),
                  onPressed: node.choices.length >= 3
                      ? null
                      : () => _addChoice(context, ref, g, branches, node),
                  icon: const Icon(Icons.alt_route_rounded),
                  label: const Text('Přidat volbu'),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  static List<BranchPanel> _swap(List<BranchPanel> l, int a, int b) {
    final out = [...l];
    final t = out[a];
    out[a] = out[b];
    out[b] = t;
    return out;
  }

  Future<void> _addChoice(
    BuildContext context,
    WidgetRef ref,
    Gamebook g,
    GamebookBranches branches,
    BranchNode node,
  ) async {
    final res = await showDialog<(String, String?)>(
      context: context,
      builder: (_) =>
          _ChoiceDialog(gamebook: g, branches: branches, self: node.id),
    );
    if (res == null) return;
    var (text, to) = res;
    var b = branches;
    if (to == null) {
      // "nový uzel": an empty own node to fill next
      to = b.newNodeId();
      b = b.putNode(BranchNode(id: to, title: text));
    }
    final id = 'c_${node.id}_${node.choices.length + 1}';
    b = b.putNode(
      node.copyWith(
        choices: [
          ...node.choices,
          GamebookChoice(id: id, text: text, to: to),
        ],
      ),
    );
    await ref.read(branchesProvider(gamebookId).notifier).update(b);
  }

  Future<BranchPanel?> _pickPanel(
    BuildContext context,
    WidgetRef ref,
    Gamebook g,
  ) {
    final store = ref.read(packStoreProvider);
    final api = ref.read(apiProvider);
    // the book's images in reading order (node order), each episode's panels in order
    final eps = [
      for (final id in g.order) ?store.episode(g.node(id)!.episodeId),
    ];
    return showModalBottomSheet<BranchPanel>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.85,
        builder: (ctx, scroll) => GridView.count(
          key: const ValueKey('panel-picker'),
          controller: scroll,
          crossAxisCount: 3,
          padding: const EdgeInsets.all(8),
          mainAxisSpacing: 6,
          crossAxisSpacing: 6,
          children: [
            for (final e in eps)
              for (final p in e.panels)
                if (p.imageUrl != null)
                  InkWell(
                    key: ValueKey('pick-${e.id}-${p.index}'),
                    onTap: () => Navigator.pop(
                      ctx,
                      BranchPanel(episodeId: e.id, panelIndex: p.index),
                    ),
                    child: ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image(
                        image: api.panelImage(p.imageUrl!),
                        fit: BoxFit.cover,
                      ),
                    ),
                  ),
          ],
        ),
      ),
    );
  }
}

class _ChoiceDialog extends StatefulWidget {
  final Gamebook gamebook;
  final GamebookBranches branches;
  final String self;
  const _ChoiceDialog({
    required this.gamebook,
    required this.branches,
    required this.self,
  });

  @override
  State<_ChoiceDialog> createState() => _ChoiceDialogState();
}

class _ChoiceDialogState extends State<_ChoiceDialog> {
  static const _newNode = '__new__';
  String _to = _newNode;
  final _text = TextEditingController();

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final g = widget.gamebook;
    return AlertDialog(
      title: const Text('Nová volba'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextField(
            key: const ValueKey('choice-text'),
            controller: _text,
            maxLength: _maxChoiceChars,
            decoration: const InputDecoration(labelText: 'Text volby'),
            onChanged: (_) => setState(() {}),
          ),
          DropdownButtonFormField<String>(
            key: const ValueKey('choice-target'),
            initialValue: _to,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Vede do'),
            items: [
              const DropdownMenuItem(
                value: _newNode,
                child: Text('+ nový uzel'),
              ),
              for (final n in widget.branches.nodes)
                if (n.id != widget.self)
                  DropdownMenuItem(
                    value: n.id,
                    child: Text(
                      'Moje: ${n.title}',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              for (final id in g.order)
                DropdownMenuItem(
                  value: id,
                  child: Text(
                    g.node(id)!.title,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
            onChanged: (v) => setState(() => _to = v ?? _newNode),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Zrušit'),
        ),
        FilledButton(
          key: const ValueKey('choice-save'),
          onPressed: _text.text.trim().isEmpty
              ? null
              : () => Navigator.pop<(String, String?)>(context, (
                  _text.text.trim(),
                  _to == _newNode ? null : _to,
                )),
          child: const Text('Přidat'),
        ),
      ],
    );
  }
}

/// Up to three bubbles of one image: who speaks (or the narrator), how, and what.
class _BubblesDialog extends StatefulWidget {
  final Lore lore;
  final List<Bubble> bubbles;
  const _BubblesDialog({required this.lore, required this.bubbles});

  @override
  State<_BubblesDialog> createState() => _BubblesDialogState();
}

class _BubblesDialogState extends State<_BubblesDialog> {
  late final List<(String?, BubbleKind, TextEditingController)> _rows = [
    for (final b in widget.bubbles)
      (b.speakerId, b.kind, TextEditingController(text: b.text)),
  ];

  @override
  void dispose() {
    for (final r in _rows) {
      r.$3.dispose();
    }
    super.dispose();
  }

  static const _kinds = {
    BubbleKind.speech: 'řeč',
    BubbleKind.thought: 'myšlenka',
    BubbleKind.shout: 'výkřik',
    BubbleKind.narration: 'vyprávění',
  };

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Bubliny'),
      content: SizedBox(
        width: 420,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final (i, (speaker, kind, ctl)) in _rows.indexed) ...[
                Row(
                  children: [
                    Expanded(
                      child: DropdownButton<String?>(
                        key: ValueKey('bubble-speaker-$i'),
                        value: kind == BubbleKind.narration ? null : speaker,
                        isExpanded: true,
                        hint: const Text('Vypravěč'),
                        items: [
                          const DropdownMenuItem<String?>(
                            value: null,
                            child: Text('Vypravěč'),
                          ),
                          for (final c in widget.lore.characters)
                            DropdownMenuItem<String?>(
                              value: c.id,
                              child: Text(c.name),
                            ),
                        ],
                        onChanged: (v) => setState(() {
                          _rows[i] = (
                            v,
                            v == null
                                ? BubbleKind.narration
                                : (kind == BubbleKind.narration
                                      ? BubbleKind.speech
                                      : kind),
                            ctl,
                          );
                        }),
                      ),
                    ),
                    const SizedBox(width: 8),
                    DropdownButton<BubbleKind>(
                      key: ValueKey('bubble-kind-$i'),
                      value: kind,
                      items: [
                        for (final e in _kinds.entries)
                          DropdownMenuItem(value: e.key, child: Text(e.value)),
                      ],
                      onChanged: (v) => setState(() {
                        if (v == null) return;
                        _rows[i] = (
                          v == BubbleKind.narration ? null : speaker,
                          v,
                          ctl,
                        );
                      }),
                    ),
                    IconButton(
                      tooltip: 'Odebrat',
                      onPressed: () =>
                          setState(() => _rows.removeAt(i).$3.dispose()),
                      icon: const Icon(Icons.close_rounded),
                    ),
                  ],
                ),
                TextField(
                  key: ValueKey('bubble-text-$i'),
                  controller: ctl,
                  maxLength: _maxBubbleChars,
                  maxLines: 2,
                  minLines: 1,
                  decoration: const InputDecoration(hintText: 'Text bubliny'),
                ),
                const SizedBox(height: 8),
              ],
              if (_rows.length < _maxBubbles)
                TextButton.icon(
                  key: const ValueKey('bubble-add'),
                  onPressed: () => setState(
                    () => _rows.add((
                      widget.lore.characters.isEmpty
                          ? null
                          : widget.lore.characters.first.id,
                      widget.lore.characters.isEmpty
                          ? BubbleKind.narration
                          : BubbleKind.speech,
                      TextEditingController(),
                    )),
                  ),
                  icon: const Icon(Icons.add_comment_outlined),
                  label: const Text('Přidat bublinu'),
                ),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Zrušit'),
        ),
        FilledButton(
          key: const ValueKey('bubbles-save'),
          onPressed: () => Navigator.pop(context, [
            for (final (speaker, kind, ctl) in _rows)
              if (ctl.text.trim().isNotEmpty)
                Bubble(speakerId: speaker, text: ctl.text.trim(), kind: kind),
          ]),
          child: const Text('Uložit'),
        ),
      ],
    );
  }
}

Future<bool> _confirm(BuildContext context, String text) async =>
    await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        content: Text(text),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Zrušit'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Smazat'),
          ),
        ],
      ),
    ) ??
    false;
