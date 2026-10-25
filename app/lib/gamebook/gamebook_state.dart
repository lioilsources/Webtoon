// Per-reader state of a gamebook, kept on the device only:
//   <application support>/gamebooks/<id>/progress.json  — where the reader is, the path behind them,
//                                                          visited nodes and the endings found;
//   <application support>/gamebooks/<id>/branches.json  — the reader's own branches (editor kit).
// Flags are never stored: they are the `sets` of every node on the path, so going back or
// retrying an ending can never leave a stale flag behind.

import 'dart:convert';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';

import '../models/episode.dart';
import '../models/json.dart';
import 'gamebook.dart';

/// Where the reader is in one gamebook.
class GamebookProgress {
  /// Current node (official or own branch node).
  final String node;

  /// Nodes read before [node], oldest first (choices taken in between are implied).
  final List<String> path;
  final Set<String> visited;
  final Set<String> endingsFound;

  const GamebookProgress({
    required this.node,
    this.path = const [],
    this.visited = const {},
    this.endingsFound = const {},
  });

  factory GamebookProgress.start(Gamebook g) =>
      GamebookProgress(node: g.start, visited: {g.start});

  /// The flags in force at [node]: everything the path has set.
  Set<String> flags(Gamebook g) => {
    for (final id in path) ...?g.node(id)?.sets,
  };

  /// Reads on to [to] (a choice or `next`).
  GamebookProgress go(String to) => GamebookProgress(
    node: to,
    path: [...path, node],
    visited: {...visited, to},
    endingsFound: endingsFound,
  );

  /// One node back (no-op at the start).
  GamebookProgress back() => path.isEmpty
      ? this
      : GamebookProgress(
          node: path.last,
          path: path.sublist(0, path.length - 1),
          visited: visited,
          endingsFound: endingsFound,
        );

  /// A good ending counts once it is reached.
  GamebookProgress found(String ending) => GamebookProgress(
    node: node,
    path: path,
    visited: visited,
    endingsFound: {...endingsFound, ending},
  );

  /// A retry ending: back to [to] as it was first reached (its path cut there), or from the
  /// start when the path never passed it.
  GamebookProgress retry(String to) {
    final i = path.lastIndexOf(to);
    return GamebookProgress(
      node: to,
      path: i < 0 ? const [] : path.sublist(0, i),
      visited: {...visited, to},
      endingsFound: endingsFound,
    );
  }

  /// From the start again; visited nodes and found endings stay.
  GamebookProgress restart(Gamebook g) => GamebookProgress(
    node: g.start,
    visited: {...visited, g.start},
    endingsFound: endingsFound,
  );

  factory GamebookProgress.fromJson(Map<String, dynamic> j) => GamebookProgress(
    node: str(j['node']),
    path: strList(j['path']),
    visited: strList(j['visited']).toSet(),
    endingsFound: strList(j['endings_found']).toSet(),
  );

  Map<String, dynamic> toJson() => {
    'node': node,
    'path': path,
    'visited': visited.toList(),
    'endings_found': endingsFound.toList(),
  };
}

/// One panel of an own branch node: an image of the gamebook (by its episode and panel index)
/// with the reader's own bubbles.
class BranchPanel {
  final String episodeId;
  final int panelIndex;
  final List<Bubble> bubbles;

  const BranchPanel({
    required this.episodeId,
    required this.panelIndex,
    this.bubbles = const [],
  });

  BranchPanel withBubbles(List<Bubble> b) =>
      BranchPanel(episodeId: episodeId, panelIndex: panelIndex, bubbles: b);

  factory BranchPanel.fromJson(Map<String, dynamic> j) => BranchPanel(
    episodeId: str(j['episode']),
    panelIndex: integer(j['panel']),
    bubbles: objList(j['bubbles']).map(Bubble.fromJson).toList(),
  );

  Map<String, dynamic> toJson() => {
    'episode': episodeId,
    'panel': panelIndex,
    'bubbles': [for (final b in bubbles) b.toJson()],
  };
}

/// A node the reader made: panels, then choices to any node, or an ending.
class BranchNode {
  static const prefix = 'my_';

  final String id;
  final String title;
  final List<BranchPanel> panels;
  final List<GamebookChoice> choices;

  /// No choices means the branch ends here (a good ending of the reader's own).
  const BranchNode({
    required this.id,
    this.title = '',
    this.panels = const [],
    this.choices = const [],
  });

  bool get isEnding => choices.isEmpty;

  BranchNode copyWith({
    String? title,
    List<BranchPanel>? panels,
    List<GamebookChoice>? choices,
  }) => BranchNode(
    id: id,
    title: title ?? this.title,
    panels: panels ?? this.panels,
    choices: choices ?? this.choices,
  );

  factory BranchNode.fromJson(Map<String, dynamic> j) => BranchNode(
    id: str(j['id']),
    title: str(j['title']),
    panels: objList(j['panels']).map(BranchPanel.fromJson).toList(),
    choices: objList(j['choices']).map(GamebookChoice.fromJson).toList(),
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'title': title,
    'panels': [for (final x in panels) x.toJson()],
    'choices': [for (final c in choices) c.toJson()],
  };
}

/// A new choice the reader added to an official node, leading into an own branch.
class BranchHook {
  final String fromNode;
  final GamebookChoice choice;
  const BranchHook({required this.fromNode, required this.choice});

  factory BranchHook.fromJson(Map<String, dynamic> j) => BranchHook(
    fromNode: str(j['from']),
    choice: GamebookChoice.fromJson(obj(j['choice'])),
  );

  Map<String, dynamic> toJson() => {
    'from': fromNode,
    'choice': choice.toJson(),
  };
}

/// branches.json: everything the reader wrote into one gamebook.
class GamebookBranches {
  static const schema = 1;

  final List<BranchNode> nodes;
  final List<BranchHook> hooks;
  const GamebookBranches({this.nodes = const [], this.hooks = const []});

  BranchNode? node(String id) {
    for (final n in nodes) {
      if (n.id == id) return n;
    }
    return null;
  }

  /// Own choices added to [nodeId] (official or own).
  List<GamebookChoice> hooksAt(String nodeId) => [
    for (final h in hooks)
      if (h.fromNode == nodeId) h.choice,
  ];

  /// A fresh node id, `my_1`, `my_2`, …
  String newNodeId() {
    var i = nodes.length + 1;
    while (node('${BranchNode.prefix}$i') != null) {
      i++;
    }
    return '${BranchNode.prefix}$i';
  }

  GamebookBranches putNode(BranchNode n) => GamebookBranches(
    nodes: [
      for (final x in nodes)
        if (x.id != n.id) x,
      n,
    ]..sort((a, b) => _num(a.id).compareTo(_num(b.id))),
    hooks: hooks,
  );

  /// Removes the node, the hooks into it and every own choice that pointed at it.
  GamebookBranches removeNode(String id) => GamebookBranches(
    nodes: [
      for (final x in nodes)
        if (x.id != id)
          x.copyWith(
            choices: [
              for (final c in x.choices)
                if (c.to != id) c,
            ],
          ),
    ],
    hooks: [
      for (final h in hooks)
        if (h.choice.to != id) h,
    ],
  );

  GamebookBranches addHook(BranchHook h) =>
      GamebookBranches(nodes: nodes, hooks: [...hooks, h]);

  GamebookBranches removeHook(BranchHook h) => GamebookBranches(
    nodes: nodes,
    hooks: [
      for (final x in hooks)
        if (!(x.fromNode == h.fromNode && x.choice.id == h.choice.id)) x,
    ],
  );

  static int _num(String id) =>
      int.tryParse(id.substring(BranchNode.prefix.length)) ?? 0;

  factory GamebookBranches.fromJson(Map<String, dynamic> j) => GamebookBranches(
    nodes: objList(j['nodes']).map(BranchNode.fromJson).toList(),
    hooks: objList(j['hooks']).map(BranchHook.fromJson).toList(),
  );

  Map<String, dynamic> toJson() => {
    'schema': schema,
    'nodes': [for (final n in nodes) n.toJson()],
    'hooks': [for (final h in hooks) h.toJson()],
  };

  /// What "Odeslat autorovi" copies: the branches plus which gamebook (and version) they are for.
  String exportFor(Gamebook g, {int version = 0}) =>
      const JsonEncoder.withIndent('  ').convert({
        'gamebook': g.id,
        'gamebook_version': version,
        'exported_at': DateTime.now().toUtc().toIso8601String(),
        ...toJson(),
      });
}

/// progress.json / branches.json under `<root>/<gamebook id>/`.
class GamebookRepository {
  Directory? _root;

  /// [root] defaults to `getApplicationSupportDirectory()/gamebooks`; tests pass a temp dir.
  GamebookRepository({Directory? root}) {
    _root = root;
  }

  Future<Directory> _dir(String id) async {
    _root ??= Directory(
      p.join((await getApplicationSupportDirectory()).path, 'gamebooks'),
    );
    return Directory(p.join(_root!.path, id));
  }

  Future<Map<String, dynamic>?> _read(String id, String name) async {
    final f = File(p.join((await _dir(id)).path, name));
    if (!await f.exists()) return null;
    try {
      return obj(jsonDecode(await f.readAsString()));
    } on FormatException {
      return null;
    }
  }

  Future<void> _write(String id, String name, Map<String, dynamic> j) async {
    final d = await _dir(id);
    await d.create(recursive: true);
    final tmp = File(p.join(d.path, '$name.tmp'));
    await tmp.writeAsString(jsonEncode(j));
    await tmp.rename(p.join(d.path, name));
  }

  Future<GamebookProgress?> loadProgress(String id) async {
    final j = await _read(id, 'progress.json');
    return j == null ? null : GamebookProgress.fromJson(j);
  }

  Future<void> saveProgress(String id, GamebookProgress pr) =>
      _write(id, 'progress.json', pr.toJson());

  Future<GamebookBranches> loadBranches(String id) async {
    final j = await _read(id, 'branches.json');
    return j == null ? const GamebookBranches() : GamebookBranches.fromJson(j);
  }

  Future<void> saveBranches(String id, GamebookBranches b) =>
      _write(id, 'branches.json', b.toJson());
}

final gamebookRepositoryProvider = Provider<GamebookRepository>(
  (ref) => GamebookRepository(),
);

/// The reader's own branches of one gamebook; edits save at once.
class BranchesNotifier extends StateNotifier<GamebookBranches> {
  final GamebookRepository repo;
  final String gamebookId;
  bool loaded = false;

  BranchesNotifier(this.repo, this.gamebookId)
    : super(const GamebookBranches()) {
    _load();
  }

  Future<void> _load() async {
    final b = await repo.loadBranches(gamebookId);
    if (!mounted) return;
    loaded = true;
    state = b;
  }

  Future<void> update(GamebookBranches b) async {
    state = b;
    await repo.saveBranches(gamebookId, b);
  }
}

final branchesProvider =
    StateNotifierProvider.family<BranchesNotifier, GamebookBranches, String>(
      (ref, id) => BranchesNotifier(ref.watch(gamebookRepositoryProvider), id),
    );
