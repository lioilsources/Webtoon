// Gamebook graphs as Studio edits them (GET/PUT /gamebooks/{id}, backend/internal/api/gamebooks.go):
// graph.yaml as JSON with its key order (jsonDecode keeps it), plus which nodes are drawn.

import 'json.dart';

class GamebookSummary {
  final String id;
  final String title;
  final int nodes;
  final int drawn;
  const GamebookSummary({
    required this.id,
    required this.title,
    this.nodes = 0,
    this.drawn = 0,
  });

  factory GamebookSummary.fromJson(Map<String, dynamic> j) => GamebookSummary(
    id: str(j['id']),
    title: str(j['title']),
    nodes: integer(j['nodes']),
    drawn: integer(j['drawn']),
  );
}

class NamedId {
  final String id;
  final String name;
  const NamedId(this.id, this.name);
}

class GamebookDoc {
  final String id;

  /// graph.yaml as an ordered map; the editor changes `nodes` (and nothing it does not show).
  final Map<String, dynamic> graph;

  /// Node id → drawn (imported); drawn nodes cannot be removed.
  final Map<String, bool> drawn;
  final List<NamedId> characters;
  final List<NamedId> locations;

  /// What draws the missing nodes (m0 pipeline via the Spark broker, run by hand).
  final String drawCommand;

  const GamebookDoc({
    required this.id,
    required this.graph,
    this.drawn = const {},
    this.characters = const [],
    this.locations = const [],
    this.drawCommand = '',
  });

  factory GamebookDoc.fromJson(Map<String, dynamic> j) => GamebookDoc(
    id: str(j['id']),
    graph: obj(j['graph']),
    drawn: {for (final e in obj(j['drawn']).entries) e.key: e.value == true},
    characters: [
      for (final c in objList(j['characters']))
        NamedId(str(c['id']), str(c['name'])),
    ],
    locations: [
      for (final l in objList(j['locations']))
        NamedId(str(l['id']), str(l['name'])),
    ],
    drawCommand: str(j['draw_command']),
  );
}
