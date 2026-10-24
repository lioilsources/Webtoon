// Gamebooks — LATER PHASE, only a stub.
//
// What exists today: catalog.json `gamebooks[]` (lib/shop/catalog.dart CatalogGamebook), the store
// products `gamebook_<id>` (1.99 USD) and `kit_<id>` (3.99 USD, gamebook + editor kit) and their
// entitlements (Entitlements.unlocksGamebook / unlocksKit). The store screen does not list
// gamebooks yet, so nothing can be bought before the reader exists.
//
// TODO(gamebook): the branching reader itself:
//   - format: a zip like a content pack (PACK_FORMAT.md) whose `gamebook.json` holds the graph —
//     nodes = episodes (panels as in pack.json), edges = choices with conditions/state, plus
//     `lore` (characters, places, rules) for the editor kit;
//   - reader: walk the graph, keep per-reader state (visited nodes, flags), save slots;
//   - editor kit: author's own branches over the bought gamebook's lore (Studio-like UI, offline);
//   - catalog: fill `graph` / `lore` (today null) with the asset names, like pack parts.

/// Placeholder of the future `gamebook.json` (schema 0 = not designed yet).
class GamebookFormat {
  static const schema = 0;

  /// Node id → episode id; edges come later.
  final Map<String, String> nodes;
  const GamebookFormat({this.nodes = const {}});
}
