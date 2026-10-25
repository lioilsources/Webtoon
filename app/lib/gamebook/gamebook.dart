// Gamebooks (../../docs/gamebook.md): a content pack whose zip also holds `gamebook.json` — the
// graph over its stories. Every node is one pre-drawn episode of pack.json; edges are fixed
// choices with optional flag conditions. Read offline like any pack; never in the library.
//
// Store side: catalog.json `gamebooks[]` (lib/shop/catalog.dart CatalogGamebook), products
// `gamebook_<id>` and `kit_<id>` (gamebook + editor kit, lib/gamebook/branch_editor_screen.dart).

import '../models/json.dart';

/// One choice at the end of a node. [condition] is a flag expression ("a", "a or b",
/// "a and b", "not a"); a choice whose condition fails is not shown.
class GamebookChoice {
  final String id;
  final String text;
  final Map<String, String> textI18n;
  final String to;
  final String condition;

  const GamebookChoice({
    required this.id,
    required this.text,
    required this.to,
    this.textI18n = const {},
    this.condition = '',
  });

  String textIn(String? lang) => lang == null ? text : (textI18n[lang] ?? text);

  factory GamebookChoice.fromJson(Map<String, dynamic> j) => GamebookChoice(
    id: str(j['id']),
    text: str(j['text']),
    textI18n: strMap(j['text_i18n']),
    to: str(j['to']),
    condition: str(j['if']),
  );

  Map<String, dynamic> toJson() => {
    'id': id,
    'text': text,
    if (textI18n.isNotEmpty) 'text_i18n': textI18n,
    'to': to,
    if (condition.isNotEmpty) 'if': condition,
  };
}

enum GamebookEnding { none, good, retry }

class GamebookNode {
  final String id;

  /// pack.json story and its one episode (the drawn node).
  final String storyId;
  final String episodeId;
  final String title;

  /// Node without choices continues here.
  final String? next;
  final List<GamebookChoice> choices;

  /// Flags set once the node is read.
  final List<String> sets;
  final GamebookEnding ending;

  /// A retry ending sends the reader back here.
  final String? retryTo;

  const GamebookNode({
    required this.id,
    required this.storyId,
    required this.episodeId,
    required this.title,
    this.next,
    this.choices = const [],
    this.sets = const [],
    this.ending = GamebookEnding.none,
    this.retryTo,
  });

  bool get isEnding => ending != GamebookEnding.none;

  factory GamebookNode.fromJson(String id, Map<String, dynamic> j) =>
      GamebookNode(
        id: id,
        storyId: str(j['story']),
        episodeId: str(j['episode']),
        title: str(j['title']),
        next: strOrNull(j['next']),
        choices: objList(j['choices']).map(GamebookChoice.fromJson).toList(),
        sets: strList(j['sets']),
        ending: switch (str(j['ending'])) {
          'good' => GamebookEnding.good,
          'retry' => GamebookEnding.retry,
          _ => GamebookEnding.none,
        },
        retryTo: strOrNull(j['retry_to']),
      );
}

class LoreCharacter {
  final String id;
  final String name;
  final String description;
  const LoreCharacter({
    required this.id,
    required this.name,
    this.description = '',
  });
}

class LoreLocation {
  final String id;
  final String name;
  final String description;
  const LoreLocation({
    required this.id,
    required this.name,
    this.description = '',
  });
}

/// What the editor kit writes with: the book's speakers, places and world rules.
class Lore {
  final List<LoreCharacter> characters;
  final List<LoreLocation> locations;
  final List<String> rules;

  const Lore({
    this.characters = const [],
    this.locations = const [],
    this.rules = const [],
  });

  LoreCharacter? character(String? id) {
    for (final c in characters) {
      if (c.id == id) return c;
    }
    return null;
  }

  factory Lore.fromJson(Map<String, dynamic> j) => Lore(
    characters: [
      for (final c in objList(j['characters']))
        LoreCharacter(
          id: str(c['id']),
          name: str(c['name']),
          description: str(c['description']),
        ),
    ],
    locations: [
      for (final l in objList(j['locations']))
        LoreLocation(
          id: str(l['id']),
          name: str(l['name']),
          description: str(l['description']),
        ),
    ],
    rules: strList(j['rules']),
  );
}

/// gamebook.json (schema 1).
class Gamebook {
  static const supportedSchema = 1;

  final String id;

  /// The pack that carries it (pack.json `id`, e.g. `gamebook-sara`).
  final String packId;
  final String title;
  final Map<String, String> titleI18n;
  final String start;

  /// Node ids in the author's order (the path map lists them so).
  final List<String> order;
  final Map<String, GamebookNode> nodes;
  final List<String> flags;

  /// Good endings to find.
  final int endings;
  final Lore lore;

  const Gamebook({
    required this.id,
    required this.packId,
    required this.title,
    required this.start,
    required this.nodes,
    this.titleI18n = const {},
    this.order = const [],
    this.flags = const [],
    this.endings = 0,
    this.lore = const Lore(),
  });

  String titleIn(String? lang) =>
      lang == null ? title : (titleI18n[lang] ?? title);

  GamebookNode? node(String id) => nodes[id];

  /// Throws [FormatException] on a graph the reader cannot walk (unknown start or target).
  factory Gamebook.parse(Map<String, dynamic> j, {required String packId}) {
    final schema = integer(j['schema']);
    if (schema != supportedSchema) {
      throw FormatException('gamebook.json schema $schema');
    }
    final raw = obj(j['nodes']);
    final nodes = {
      for (final e in raw.entries)
        e.key: GamebookNode.fromJson(e.key, obj(e.value)),
    };
    final start = str(j['start']);
    if (!nodes.containsKey(start)) {
      throw FormatException('gamebook start $start is not a node');
    }
    for (final n in nodes.values) {
      for (final t in [n.next, n.retryTo, ...n.choices.map((c) => c.to)]) {
        if (t != null && !nodes.containsKey(t)) {
          throw FormatException('node ${n.id} points to unknown node $t');
        }
      }
    }
    final order = strList(j['order']).where(nodes.containsKey).toList();
    return Gamebook(
      id: str(j['id']),
      packId: packId,
      title: str(j['title']),
      titleI18n: strMap(j['title_i18n']),
      start: start,
      order: order.isEmpty ? nodes.keys.toList() : order,
      nodes: nodes,
      flags: strList(j['flags']),
      endings: integer(j['endings']),
      lore: Lore.fromJson(obj(j['lore'])),
    );
  }
}

/// Evaluates a choice condition over the reader's flags: `a`, `not a`, `a and b`, `a or b`
/// (and binds tighter than or; no parentheses). Empty = always true; an unknown word is a flag.
bool evalCondition(String expr, Set<String> flags) {
  final e = expr.trim();
  if (e.isEmpty) return true;
  return e
      .split(RegExp(r'\s+or\s+'))
      .any(
        (alt) => alt.split(RegExp(r'\s+and\s+')).every((term) {
          final t = term.trim();
          if (t.startsWith('not ')) {
            return !flags.contains(t.substring(4).trim());
          }
          return flags.contains(t);
        }),
      );
}
