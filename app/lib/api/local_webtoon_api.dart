import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/widgets.dart';

import '../models/author.dart';
import '../models/campaign.dart';
import '../models/episode.dart';
import '../models/gamebook_graph.dart';
import '../models/world.dart';
import '../packs/pack_store.dart';
import 'webtoon_api.dart';

/// The reader's API over installed packs (../PACK_FORMAT.md): worlds, stories (as campaigns)
/// and episodes come from pack.json, images from the pack directory. Nothing can be generated
/// or edited here — every author/generation method throws [UnsupportedError].
class LocalWebtoonApi implements WebtoonApi {
  final PackStore store;

  /// Reader profile filter (Kids hides adult stories); null shows everything.
  final bool Function(PackStory story)? storyFilter;

  const LocalWebtoonApi(this.store, {this.storyFilter});

  Iterable<PackStory> get _stories =>
      storyFilter == null ? store.stories : store.stories.where(storyFilter!);

  @override
  String get userId => 'reader';

  @override
  bool get canEdit => false;

  /// A failed future (not a synchronous throw), like any other API error.
  static Future<Never> _unsupported(String what) async =>
      throw UnsupportedError('$what is not available offline (pack reader)');

  @override
  Future<List<WorldSummary>> listWorlds() async {
    if (storyFilter == null) return store.worlds;
    final shown = {for (final s in _stories) s.worldId};
    return [
      for (final w in store.worlds)
        if (shown.contains(w.id)) w,
    ];
  }

  @override
  Future<World> getWorld(String id) async {
    final w = store.world(id);
    if (w == null) throw const ApiException('Nenalezeno.', statusCode: 404);
    return World(
      id: w.id,
      ownerId: w.ownerId,
      title: w.title,
      synopsis: w.synopsis,
      tone: w.tone,
      audience: w.audience,
      language: w.language,
      styleId: w.styleId,
      visibility: 'public',
    );
  }

  CampaignSummary _summary(PackStory s) => CampaignSummary(
    id: s.id,
    worldId: s.worldId,
    worldTitle: store.world(s.worldId)?.title ?? '',
    title: s.title,
    status: 'ready',
    episodes: s.episodeIds.length,
    lastEpisodeStatus: 'ready',
  );

  @override
  Future<List<CampaignSummary>> listCampaigns({String? worldId}) async => [
    for (final s in _stories)
      if (worldId == null || s.worldId == worldId) _summary(s),
  ];

  @override
  Future<Campaign> getCampaign(String id) async {
    final s = store.story(id);
    if (s == null) throw const ApiException('Nenalezeno.', statusCode: 404);
    final episodes = <EpisodeSummary>[];
    var idx = 0;
    for (final eid in s.episodeIds) {
      idx++;
      final e = store.episode(eid);
      episodes.add(
        e == null
            ? EpisodeSummary(id: eid, index: idx, status: EpisodeStatus.ready)
            : EpisodeSummary(
                id: e.id,
                index: e.index,
                title: e.title,
                status: e.status,
                panelsReady: e.panelsReady,
                panelsTotal: e.panelsTotal,
                chosen: e.chosen,
                titleI18n: e.titleI18n,
              ),
      );
    }
    return Campaign(
      id: s.id,
      worldId: s.worldId,
      // The reader "is the player" of every story: the end-of-episode block is shown.
      playerId: userId,
      title: s.title,
      status: 'ready',
      episodes: episodes,
    );
  }

  @override
  Future<Episode> getEpisode(String id) async {
    final e = store.episode(id);
    if (e == null) throw const ApiException('Nenalezeno.', statusCode: 404);
    return e;
  }

  /// Pack media are absolute file paths (PackManifest.parse); http URLs still work.
  @override
  ImageProvider panelImage(String imageUrl) =>
      imageUrl.startsWith('http://') || imageUrl.startsWith('https://')
      ? NetworkImage(imageUrl)
      : FileImage(File(imageUrl));

  // --- generation / editing: not offline ----------------------------------------

  @override
  Future<CreatedCampaign> createCampaign({
    required String worldId,
    String? playerCharacterId,
    String? title,
  }) => _unsupported('createCampaign');

  @override
  Future<String> continueCampaign(
    String campaignId, {
    String? choiceId,
    String? freeText,
    DirectorRequest? director,
  }) => _unsupported('continueCampaign');

  @override
  Future<Panel> updateBubbles(
    String episodeId,
    int panel,
    List<Bubble> bubbles,
  ) => _unsupported('updateBubbles');

  @override
  Future<Panel> regeneratePanel(String episodeId, int panel) =>
      _unsupported('regeneratePanel');

  @override
  Future<Panel> updatePanelMotion(
    String episodeId,
    int panel,
    Map<String, dynamic> patch,
  ) => _unsupported('updatePanelMotion');

  // --- author (M3): not offline -------------------------------------------------

  @override
  Future<List<WorldSummary>> listMyWorlds() => _unsupported('listMyWorlds');

  @override
  Future<List<StylePreset>> listStylePresets() =>
      _unsupported('listStylePresets');

  @override
  Future<World> createWorld({
    required String title,
    required String styleId,
    Map<String, dynamic> fields = const {},
  }) => _unsupported('createWorld');

  @override
  Future<World> updateWorld(String worldId, Map<String, dynamic> patch) =>
      _unsupported('updateWorld');

  @override
  Future<WorldStats> getWorldStats(String worldId) =>
      _unsupported('getWorldStats');

  @override
  Future<List<GamebookSummary>> listGamebooks() =>
      _unsupported('listGamebooks');

  @override
  Future<GamebookDoc> getGamebook(String id) => _unsupported('getGamebook');

  @override
  Future<GamebookDoc> saveGamebook(String id, Map<String, dynamic> graph) =>
      _unsupported('saveGamebook');

  @override
  Future<Character> createCharacter(
    String worldId,
    Map<String, dynamic> fields,
  ) => _unsupported('createCharacter');

  @override
  Future<Character> updateCharacter(
    String worldId,
    String characterId,
    Map<String, dynamic> patch,
  ) => _unsupported('updateCharacter');

  @override
  Future<void> deleteCharacter(String worldId, String characterId) =>
      _unsupported('deleteCharacter');

  @override
  Future<TagSuggestion> suggestCharacterTags(
    String worldId,
    String characterId, {
    String? description,
  }) => _unsupported('suggestCharacterTags');

  @override
  Future<CharacterSheet> createSheet(
    String worldId,
    String characterId, {
    int seeds = 4,
  }) => _unsupported('createSheet');

  @override
  Future<List<CharacterSheet>> listSheets(String worldId, String characterId) =>
      _unsupported('listSheets');

  @override
  Future<CharacterSheet> getSheet(String sheetId) => _unsupported('getSheet');

  @override
  Future<Character> uploadCharacterReference(
    String worldId,
    String characterId,
    Uint8List bytes,
    String filename,
  ) => _unsupported('uploadCharacterReference');

  @override
  Future<Location> createLocation(
    String worldId,
    Map<String, dynamic> fields,
  ) => _unsupported('createLocation');

  @override
  Future<Location> updateLocation(
    String worldId,
    String locationId,
    Map<String, dynamic> patch,
  ) => _unsupported('updateLocation');

  @override
  Future<void> deleteLocation(String worldId, String locationId) =>
      _unsupported('deleteLocation');

  @override
  Future<TagSuggestion> suggestLocationTags(
    String worldId,
    String locationId, {
    String? description,
  }) => _unsupported('suggestLocationTags');

  @override
  Future<Location> uploadLocationReference(
    String worldId,
    String locationId,
    Uint8List bytes,
    String filename,
  ) => _unsupported('uploadLocationReference');
}
