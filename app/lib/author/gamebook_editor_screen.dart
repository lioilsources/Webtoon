// Studio: the author's gamebook graph editor (docs/gamebook.md). Edits data/gamebooks/<id>/graph.yaml
// through the backend — nodes, their beats (what the storyboard is written from), choices with flag
// conditions, endings. Drawing the new nodes stays the m0 pipeline (LLM + ComfyUI via the Spark broker);
// the editor shows which nodes are drawn, the command that draws the rest, and never removes a drawn node.

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/gamebook_graph.dart';
import '../models/json.dart';
import '../providers/providers.dart';
import '../theme.dart';
import '../widgets/common.dart';

final gamebooksProvider = FutureProvider.autoDispose<List<GamebookSummary>>(
  (ref) => ref.watch(apiProvider).listGamebooks(),
);

/// "Gamebooky" in Tvořit: every graph of the backend's repo.
class GamebooksScreen extends ConsumerWidget {
  const GamebooksScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final list = ref.watch(gamebooksProvider);
    return Scaffold(
      appBar: AppBar(title: const Text('Gamebooky')),
      body: list.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => ErrorRetry(
          message: '$e',
          onRetry: () => ref.invalidate(gamebooksProvider),
        ),
        data: (books) => books.isEmpty
            ? const EmptyState(
                icon: Icons.alt_route_rounded,
                title: 'Žádný gamebook',
                subtitle:
                    'Gamebook začíná souborem data/gamebooks/<id>/graph.yaml.',
              )
            : ListView(
                padding: const EdgeInsets.all(16),
                children: [
                  for (final b in books)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: ComicCard(
                        key: ValueKey('gamebook-graph-${b.id}'),
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute<void>(
                            builder: (_) => GraphEditorScreen(gamebookId: b.id),
                          ),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.account_tree_rounded, size: 32),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    b.title,
                                    style: ComicFonts.title().copyWith(
                                      fontSize: 20,
                                    ),
                                  ),
                                  Text(
                                    '${b.nodes} uzlů · nakresleno ${b.drawn}',
                                  ),
                                ],
                              ),
                            ),
                            const Icon(Icons.chevron_right_rounded),
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

/// The graph of one gamebook: nodes in book order with their state; edits stay local until "Uložit".
class GraphEditorScreen extends ConsumerStatefulWidget {
  final String gamebookId;
  const GraphEditorScreen({super.key, required this.gamebookId});

  @override
  ConsumerState<GraphEditorScreen> createState() => _GraphEditorScreenState();
}

class _GraphEditorScreenState extends ConsumerState<GraphEditorScreen> {
  GamebookDoc? _doc;
  Map<String, dynamic>? _graph;
  String? _error;
  bool _dirty = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await ref.read(apiProvider).getGamebook(widget.gamebookId);
      if (!mounted) return;
      setState(() {
        _doc = d;
        _graph = _copy(d.graph);
        _dirty = false;
        _error = null;
      });
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  static Map<String, dynamic> _copy(Map<String, dynamic> m) =>
      obj(jsonDecode(jsonEncode(m)));

  Map<String, dynamic> get _nodes => obj(_graph!['nodes']);

  void _change(void Function(Map<String, dynamic> nodes) f) {
    final nodes = _nodes;
    f(nodes);
    setState(() {
      _graph!['nodes'] = nodes;
      _dirty = true;
    });
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      final d = await ref
          .read(apiProvider)
          .saveGamebook(widget.gamebookId, _graph!);
      if (!mounted) return;
      setState(() {
        _doc = d;
        _graph = _copy(d.graph);
        _dirty = false;
      });
      ref.invalidate(gamebooksProvider);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Graf uložen.')));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          key: const ValueKey('graph-save-error'),
          content: Text('Neuloženo: $e'),
        ),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final doc = _doc;
    final scheme = Theme.of(context).colorScheme;
    if (doc == null || _graph == null) {
      return Scaffold(
        appBar: AppBar(),
        body: _error != null
            ? ErrorRetry(message: _error!, onRetry: _load)
            : const Center(child: CircularProgressIndicator()),
      );
    }
    final nodes = _nodes;
    final undrawn = [
      for (final id in nodes.keys)
        if (doc.drawn[id] != true) id,
    ];
    final review = [
      for (final e in nodes.entries)
        if (obj(obj(e.value)['origin'])['review'] == true) e.key,
    ];
    return PopScope(
      canPop: !_dirty,
      onPopInvokedWithResult: (didPop, _) async {
        if (didPop) return;
        final leave = await _confirm(context, 'Zahodit neuložené změny?');
        if (leave && context.mounted) Navigator.of(context).pop();
      },
      child: Scaffold(
        appBar: AppBar(
          title: Text(
            str(_graph!['title'], doc.id),
            overflow: TextOverflow.ellipsis,
          ),
          actions: [
            TextButton.icon(
              key: const ValueKey('graph-save'),
              onPressed: _dirty && !_saving ? _save : null,
              icon: _saving
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.save_rounded),
              label: const Text('Uložit'),
            ),
          ],
        ),
        floatingActionButton: FloatingActionButton.extended(
          key: const ValueKey('graph-new-node'),
          onPressed: _newNode,
          icon: const Icon(Icons.add_rounded),
          label: const Text('Nový uzel'),
        ),
        body: ListView(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
          children: [
            Text(
              'Start: ${str(_graph!['start'])} · ${nodes.length} uzlů · nakresleno ${nodes.length - undrawn.length}',
              style: TextStyle(color: scheme.onSurfaceVariant),
            ),
            if (review.isNotEmpty) ...[
              const SizedBox(height: 10),
              _Notice(
                icon: Icons.rate_review_outlined,
                text:
                    'Ke kontrole (text od čtenáře): ${review.join(', ')}. '
                    'Po přečtení v uzlu zaškrtni „Přečteno“, jinak se nekreslí.',
              ),
            ],
            if (undrawn.isNotEmpty) ...[
              const SizedBox(height: 10),
              _Notice(
                key: const ValueKey('graph-draw'),
                icon: Icons.brush_rounded,
                text:
                    'Ke kreslení: ${undrawn.join(', ')}. Kreslí se mimo appku (LLM a ComfyUI přes broker Sparku):',
                code: doc.drawCommand,
              ),
            ],
            const SizedBox(height: 12),
            for (final e in nodes.entries)
              _NodeTile(
                key: ValueKey('graph-node-${e.key}'),
                id: e.key,
                node: obj(e.value),
                drawn: doc.drawn[e.key] == true,
                start: e.key == str(_graph!['start']),
                onTap: () => _edit(e.key),
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _newNode() async {
    final ctl = TextEditingController();
    final id = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Nový uzel'),
        content: TextField(
          key: const ValueKey('graph-node-id'),
          controller: ctl,
          autofocus: true,
          decoration: const InputDecoration(
            labelText: 'Id uzlu',
            hintText: 'např. n5 nebo end_hope',
            helperText: 'Malá písmena, číslice, _ ; id se už nikdy nemění',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Zrušit'),
          ),
          FilledButton(
            key: const ValueKey('graph-node-create'),
            onPressed: () => Navigator.pop(ctx, ctl.text.trim()),
            child: const Text('Přidat'),
          ),
        ],
      ),
    );
    // not disposed here: the dialog's closing animation still builds the field (it is collected
    // with the route)
    if (id == null || id.isEmpty) return;
    if (!RegExp(r'^[a-z][a-z0-9_]*$').hasMatch(id) || _nodes.containsKey(id)) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Id „$id“ nejde použít (formát nebo už existuje).'),
          ),
        );
      }
      return;
    }
    _change(
      (nodes) => nodes[id] = {
        'title': id,
        'location': _doc!.locations.isEmpty ? '' : _doc!.locations.first.id,
        'panels': 8,
        'beats': <String>[],
        'ending': 'good',
      },
    );
    _edit(id);
  }

  Future<void> _edit(String id) async {
    final res = await Navigator.of(context).push<_NodeEditResult>(
      MaterialPageRoute(
        builder: (_) => NodeGraphEditScreen(
          id: id,
          node: _copy(obj(_nodes[id])),
          doc: _doc!,
          nodeIds: _nodes.keys.toList(),
          referrers: _referrers(id),
        ),
      ),
    );
    if (res == null) return;
    _change((nodes) {
      if (res.delete) {
        nodes.remove(id);
      } else {
        nodes[id] = res.node;
      }
    });
  }

  /// Nodes whose choices, next or retry_to lead to [id].
  List<String> _referrers(String id) => [
    for (final e in _nodes.entries)
      if (str(obj(e.value)['next']) == id ||
          str(obj(e.value)['retry_to']) == id ||
          objList(obj(e.value)['choices']).any((c) => str(c['to']) == id))
        e.key,
    if (str(_graph!['start']) == id) '(start)',
  ];
}

class _Notice extends StatelessWidget {
  final IconData icon;
  final String text;
  final String? code;
  const _Notice({super.key, required this.icon, required this.text, this.code});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(icon, size: 20),
              const SizedBox(width: 8),
              Expanded(child: Text(text)),
            ],
          ),
          if (code != null && code!.isNotEmpty) ...[
            const SizedBox(height: 8),
            SelectableText(
              code!,
              style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
            ),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () => Clipboard.setData(ClipboardData(text: code!)),
                icon: const Icon(Icons.copy_rounded, size: 16),
                label: const Text('Kopírovat'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _NodeTile extends StatelessWidget {
  final String id;
  final Map<String, dynamic> node;
  final bool drawn;
  final bool start;
  final VoidCallback onTap;
  const _NodeTile({
    super.key,
    required this.id,
    required this.node,
    required this.drawn,
    required this.start,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final choices = objList(node['choices']);
    final ending = str(node['ending']);
    final out = ending.isNotEmpty
        ? (ending == 'good'
              ? 'konec'
              : 'zkusit znovu → ${str(node['retry_to'])}')
        : choices.isNotEmpty
        ? choices
              .map(
                (c) =>
                    '${str(c['to'])}${str(c['if']).isEmpty ? '' : ' [${str(c['if'])}]'}',
              )
              .join(' · ')
        : '→ ${str(node['next'])}';
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        onTap: onTap,
        leading: Icon(
          start
              ? Icons.flag_rounded
              : ending == 'good'
              ? Icons.emoji_events_rounded
              : ending == 'retry'
              ? Icons.replay_rounded
              : choices.isNotEmpty
              ? Icons.alt_route_rounded
              : Icons.arrow_downward_rounded,
        ),
        title: Text(
          '$id · ${str(node['title'])}',
          overflow: TextOverflow.ellipsis,
        ),
        subtitle: Text(out, maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: Tag(
          drawn ? 'nakresleno' : 'ke kreslení',
          color: drawn ? null : ComicColors.accent.withValues(alpha: 0.15),
          textColor: drawn ? scheme.onSurfaceVariant : null,
        ),
      ),
    );
  }
}

class _NodeEditResult {
  final Map<String, dynamic> node;
  final bool delete;
  const _NodeEditResult(this.node, {this.delete = false});
}

enum _Exit { next, choices, good, retry }

/// One node: title, location, beats, flags it sets, and how it ends.
class NodeGraphEditScreen extends StatefulWidget {
  final String id;
  final Map<String, dynamic> node;
  final GamebookDoc doc;
  final List<String> nodeIds;
  final List<String> referrers;

  const NodeGraphEditScreen({
    super.key,
    required this.id,
    required this.node,
    required this.doc,
    required this.nodeIds,
    required this.referrers,
  });

  @override
  State<NodeGraphEditScreen> createState() => _NodeGraphEditScreenState();
}

class _NodeGraphEditScreenState extends State<NodeGraphEditScreen> {
  late final Map<String, dynamic> n = widget.node;
  late final TextEditingController _title = TextEditingController(
    text: str(n['title']),
  );
  late final TextEditingController _sets = TextEditingController(
    text: strList(n['sets']).join(', '),
  );
  late final List<TextEditingController> _beats = [
    for (final b in strList(n['beats'])) TextEditingController(text: b),
  ];
  late final List<(TextEditingController, TextEditingController, String)>
  _choices = [
    for (final c in objList(n['choices']))
      (
        TextEditingController(text: str(c['text'])),
        TextEditingController(text: str(c['if'])),
        str(c['to']),
      ),
  ];
  late _Exit _exit = switch (str(n['ending'])) {
    'good' => _Exit.good,
    'retry' => _Exit.retry,
    _ => objList(n['choices']).isNotEmpty ? _Exit.choices : _Exit.next,
  };
  late String _location = str(n['location']);
  late String _next = str(n['next']);
  late String _retryTo = str(n['retry_to']);
  late int _panels = integer(n['panels'], 8);

  @override
  void dispose() {
    _title.dispose();
    _sets.dispose();
    for (final b in _beats) {
      b.dispose();
    }
    for (final c in _choices) {
      c.$1.dispose();
      c.$2.dispose();
    }
    super.dispose();
  }

  bool get _drawn => widget.doc.drawn[widget.id] == true;
  bool get _review => obj(n['origin'])['review'] == true;

  List<String> get _targets => [
    for (final id in widget.nodeIds)
      if (id != widget.id) id,
  ];

  Map<String, dynamic> _result() {
    final out = <String, dynamic>{...n};
    out['title'] = _title.text.trim();
    out['location'] = _location;
    out['panels'] = _panels;
    out['beats'] = [
      for (final b in _beats)
        if (b.text.trim().isNotEmpty) b.text.trim(),
    ];
    final sets = [
      for (final s in _sets.text.split(','))
        if (s.trim().isNotEmpty) s.trim(),
    ];
    if (sets.isEmpty) {
      out.remove('sets');
    } else {
      out['sets'] = sets;
    }
    for (final k in ['next', 'choices', 'ending', 'retry_to']) {
      out.remove(k);
    }
    switch (_exit) {
      case _Exit.next:
        out['next'] = _next;
      case _Exit.choices:
        out['choices'] = [
          for (final (i, (text, cond, to)) in _choices.indexed)
            {
              'id': i < objList(n['choices']).length
                  ? str(objList(n['choices'])[i]['id'], 'c${i + 1}')
                  : 'c${i + 1}',
              'text': text.text.trim(),
              'to': to,
              if (cond.text.trim().isNotEmpty) 'if': cond.text.trim(),
            },
        ];
      case _Exit.good:
        out['ending'] = 'good';
      case _Exit.retry:
        out['ending'] = 'retry';
        out['retry_to'] = _retryTo;
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final targets = _targets;
    DropdownButtonFormField<String> target(
      String value,
      String label,
      ValueChanged<String> on, {
      Key? key,
    }) => DropdownButtonFormField<String>(
      key: key,
      initialValue: targets.contains(value) ? value : null,
      isExpanded: true,
      decoration: InputDecoration(labelText: label),
      items: [
        for (final t in targets) DropdownMenuItem(value: t, child: Text(t)),
      ],
      onChanged: (v) => setState(() => on(v ?? '')),
    );
    return Scaffold(
      appBar: AppBar(
        title: Text('Uzel ${widget.id}'),
        actions: [
          if (!_drawn)
            IconButton(
              key: const ValueKey('node-delete'),
              tooltip: 'Smazat uzel',
              icon: const Icon(Icons.delete_outline_rounded),
              onPressed: () async {
                if (widget.referrers.isNotEmpty) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text(
                        'Vedou sem: ${widget.referrers.join(', ')}. Nejdřív je přesměruj.',
                      ),
                    ),
                  );
                  return;
                }
                if (await _confirm(context, 'Smazat uzel ${widget.id}?') &&
                    context.mounted) {
                  Navigator.pop(context, _NodeEditResult(n, delete: true));
                }
              },
            ),
          TextButton(
            key: const ValueKey('node-done'),
            onPressed: () => Navigator.pop(context, _NodeEditResult(_result())),
            child: const Text('Hotovo'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 48),
        children: [
          if (_drawn)
            Text(
              'Uzel je nakreslený: změny děje se projeví až po novém nakreslení; volby a konce platí hned po exportu.',
              style: TextStyle(color: scheme.onSurfaceVariant),
            ),
          if (_review)
            CheckboxListTile(
              key: const ValueKey('node-reviewed'),
              contentPadding: EdgeInsets.zero,
              value: false,
              title: const Text(
                'Přečteno (text od čtenáře je v pořádku pro děti)',
              ),
              onChanged: (_) => setState(() => n.remove('origin')),
            ),
          TextField(
            key: const ValueKey('node-title'),
            controller: _title,
            decoration: const InputDecoration(labelText: 'Název'),
          ),
          DropdownButtonFormField<String>(
            key: const ValueKey('node-location'),
            initialValue: widget.doc.locations.any((l) => l.id == _location)
                ? _location
                : null,
            isExpanded: true,
            decoration: const InputDecoration(labelText: 'Lokace'),
            items: [
              for (final l in widget.doc.locations)
                DropdownMenuItem(
                  value: l.id,
                  child: Text('${l.name} (${l.id})'),
                ),
            ],
            onChanged: (v) => setState(() => _location = v ?? ''),
          ),
          Row(
            children: [
              const Text('Panelů'),
              Expanded(
                child: Slider(
                  value: _panels.toDouble().clamp(8, 12),
                  min: 8,
                  max: 12,
                  divisions: 4,
                  label: '$_panels',
                  onChanged: (v) => setState(() => _panels = v.round()),
                ),
              ),
              Text('$_panels'),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Děj po panelech',
            style: ComicFonts.title().copyWith(fontSize: 20),
          ),
          Text(
            'Jedna věta na panel; repliku piš „Jméno: text“ (${widget.doc.characters.map((c) => c.name).join(', ')}).',
            style: TextStyle(color: scheme.onSurfaceVariant, fontSize: 13),
          ),
          for (final (i, b) in _beats.indexed)
            Row(
              children: [
                Expanded(
                  child: TextField(
                    key: ValueKey('node-beat-$i'),
                    controller: b,
                    maxLines: 3,
                    minLines: 1,
                    decoration: InputDecoration(labelText: '${i + 1}.'),
                  ),
                ),
                IconButton(
                  onPressed: () => setState(() => _beats.removeAt(i).dispose()),
                  icon: const Icon(Icons.close_rounded),
                ),
              ],
            ),
          TextButton.icon(
            key: const ValueKey('node-add-beat'),
            onPressed: () =>
                setState(() => _beats.add(TextEditingController())),
            icon: const Icon(Icons.add_rounded),
            label: const Text('Přidat větu'),
          ),
          TextField(
            key: const ValueKey('node-sets'),
            controller: _sets,
            decoration: const InputDecoration(
              labelText: 'Nastaví příznaky',
              helperText: 'čárkou, např. crown_worn, lantern',
            ),
          ),
          const SizedBox(height: 16),
          Text('Na konci', style: ComicFonts.title().copyWith(fontSize: 20)),
          SegmentedButton<_Exit>(
            key: const ValueKey('node-exit'),
            segments: const [
              ButtonSegment(value: _Exit.next, label: Text('Dál')),
              ButtonSegment(value: _Exit.choices, label: Text('Volby')),
              ButtonSegment(value: _Exit.good, label: Text('Konec')),
              ButtonSegment(value: _Exit.retry, label: Text('Znovu')),
            ],
            selected: {_exit},
            onSelectionChanged: (s) => setState(() => _exit = s.first),
          ),
          const SizedBox(height: 8),
          switch (_exit) {
            _Exit.next => target(
              _next,
              'Pokračuje do',
              (v) => _next = v,
              key: const ValueKey('node-next'),
            ),
            _Exit.retry => target(
              _retryTo,
              'Zkusit znovu od',
              (v) => _retryTo = v,
              key: const ValueKey('node-retry-to'),
            ),
            _Exit.good => const Text(
              'Dobrý konec: počítá se do „Nalezené konce“.',
            ),
            _Exit.choices => Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final (i, (text, cond, to)) in _choices.indexed)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(8),
                      child: Column(
                        children: [
                          TextField(
                            key: ValueKey('choice-text-$i'),
                            controller: text,
                            decoration: const InputDecoration(
                              labelText: 'Text volby',
                            ),
                          ),
                          target(
                            to,
                            'Vede do',
                            (v) => _choices[i] = (text, cond, v),
                            key: ValueKey('choice-to-$i'),
                          ),
                          TextField(
                            key: ValueKey('choice-if-$i'),
                            controller: cond,
                            decoration: const InputDecoration(
                              labelText: 'Podmínka (nepovinná)',
                              helperText: 'příznak, not x, a or b, a and b',
                            ),
                          ),
                          Align(
                            alignment: Alignment.centerRight,
                            child: TextButton(
                              onPressed: () => setState(() {
                                final c = _choices.removeAt(i);
                                c.$1.dispose();
                                c.$2.dispose();
                              }),
                              child: const Text('Odebrat volbu'),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                TextButton.icon(
                  key: const ValueKey('node-add-choice'),
                  onPressed: () => setState(
                    () => _choices.add((
                      TextEditingController(),
                      TextEditingController(),
                      '',
                    )),
                  ),
                  icon: const Icon(Icons.alt_route_rounded),
                  label: const Text('Přidat volbu'),
                ),
              ],
            ),
          },
        ],
      ),
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
            child: const Text('Ano'),
          ),
        ],
      ),
    ) ??
    false;
