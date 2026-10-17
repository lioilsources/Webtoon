// World / character / location as returned by GET /worlds and GET /worlds/{id}
// (backend/internal/api/worlds.go, backend/internal/domain/domain.go).

import 'json.dart';

class WorldSummary {
  final String id;
  final String ownerId;
  final String title;
  final String synopsis;
  final String tone;
  final String audience;
  final String language;
  final String styleId;
  final String visibility;

  const WorldSummary({
    required this.id,
    this.ownerId = '',
    required this.title,
    this.synopsis = '',
    this.tone = '',
    this.audience = 'teen',
    this.language = 'cs',
    this.styleId = '',
    this.visibility = 'private',
  });

  factory WorldSummary.fromJson(Map<String, dynamic> j) => WorldSummary(
    id: str(j['id']),
    ownerId: str(j['owner_id']),
    title: str(j['title']),
    synopsis: str(j['synopsis']),
    tone: str(j['tone']),
    audience: str(j['audience'], 'teen'),
    language: str(j['language'], 'cs'),
    styleId: str(j['style_id']),
    visibility: str(j['visibility'], 'private'),
  );

  bool isMine(String userId) => ownerId == userId;
}

class Permissions {
  final bool canAddCharacters;
  final bool canCreateCharacter;
  final bool canChangeLocation;
  final List<String> allowedLocations;
  final int maxEpisodes;

  const Permissions({
    this.canAddCharacters = false,
    this.canCreateCharacter = false,
    this.canChangeLocation = false,
    this.allowedLocations = const [],
    this.maxEpisodes = 0,
  });

  factory Permissions.fromJson(Map<String, dynamic> j) => Permissions(
    canAddCharacters: j['can_add_characters'] == true,
    canCreateCharacter: j['can_create_character'] == true,
    canChangeLocation: j['can_change_location'] == true,
    allowedLocations: strList(j['allowed_locations']),
    maxEpisodes: integer(j['max_episodes']),
  );

  Map<String, dynamic> toJson() => {
    'can_add_characters': canAddCharacters,
    'can_create_character': canCreateCharacter,
    'can_change_location': canChangeLocation,
    'allowed_locations': allowedLocations,
    'max_episodes': maxEpisodes,
  };

  /// The "director" block at the end of an episode is shown only when the world allows any of it.
  bool get allowsDirector => canAddCharacters || canChangeLocation;
}

/// IP-Adapter settings of a character (used only when `identity_level == ip_adapter`).
class IpAdapterConfig {
  static const presets = [
    'PLUS (high strength)',
    'PLUS FACE (portraits)',
    'STANDARD (medium strength)',
    'VIT-G (medium strength)',
  ];
  static const defaults = IpAdapterConfig();

  final String preset;
  final double weight;
  final double endAt;

  const IpAdapterConfig({
    this.preset = 'PLUS (high strength)',
    this.weight = 0.6,
    this.endAt = 0.8,
  });

  static IpAdapterConfig? fromJson(Object? v) {
    if (v is! Map) return null;
    final j = obj(v);
    return IpAdapterConfig(
      preset: str(j['preset'], defaults.preset),
      weight: dbl(j['weight']) ?? defaults.weight,
      endAt: dbl(j['end_at']) ?? defaults.endAt,
    );
  }

  Map<String, dynamic> toJson() => {
    'preset': preset,
    'weight': weight,
    'end_at': endAt,
  };

  IpAdapterConfig copyWith({String? preset, double? weight, double? endAt}) =>
      IpAdapterConfig(
        preset: preset ?? this.preset,
        weight: weight ?? this.weight,
        endAt: endAt ?? this.endAt,
      );
}

class Character {
  final String id;
  final String ownerId;
  final String name;
  final String role; // npc | playable | player_created
  final String description;
  final String personality;
  final String speechStyle;
  final String countTag; // 1girl | 1boy | ''
  final String tagPrompt;
  final List<String> referenceImages; // paths relative to MEDIA_DIR
  final List<String> referenceUrls; // same order, servable URLs
  final String identityLevel; // prompt | ip_adapter | lora
  final String identityAsset;
  final IpAdapterConfig? ipAdapter;

  const Character({
    required this.id,
    this.ownerId = '',
    required this.name,
    this.role = 'npc',
    this.description = '',
    this.personality = '',
    this.speechStyle = '',
    this.countTag = '',
    this.tagPrompt = '',
    this.referenceImages = const [],
    this.referenceUrls = const [],
    this.identityLevel = 'prompt',
    this.identityAsset = '',
    this.ipAdapter,
  });

  factory Character.fromJson(Map<String, dynamic> j) => Character(
    id: str(j['id']),
    ownerId: str(j['owner_id']),
    name: str(j['name']),
    role: str(j['role'], 'npc'),
    description: str(j['description']),
    personality: str(j['personality']),
    speechStyle: str(j['speech_style']),
    countTag: str(j['count_tag']),
    tagPrompt: str(j['tag_prompt']),
    referenceImages: strList(j['reference_images']),
    referenceUrls: strList(j['reference_urls']),
    identityLevel: str(j['identity_level'], 'prompt'),
    identityAsset: str(j['identity_asset']),
    ipAdapter: IpAdapterConfig.fromJson(j['ip_adapter']),
  );

  /// Mirrors POST /campaigns: playable, or player_created by this user.
  bool playableBy(String userId) =>
      role == 'playable' || (role == 'player_created' && ownerId == userId);

  List<String> get tags => splitTags(tagPrompt);
}

/// `tag_prompt` "a, b, c" → ["a", "b", "c"].
List<String> splitTags(String s) =>
    s.split(',').map((t) => t.trim()).where((t) => t.isNotEmpty).toList();

class Location {
  final String id;
  final String name;
  final String description;
  final String mood;
  final String tagPrompt;
  final List<String> referenceImages;
  final List<String> referenceUrls;

  const Location({
    required this.id,
    required this.name,
    this.description = '',
    this.mood = '',
    this.tagPrompt = '',
    this.referenceImages = const [],
    this.referenceUrls = const [],
  });

  factory Location.fromJson(Map<String, dynamic> j) => Location(
    id: str(j['id']),
    name: str(j['name']),
    description: str(j['description']),
    mood: str(j['mood']),
    tagPrompt: str(j['tag_prompt']),
    referenceImages: strList(j['reference_images']),
    referenceUrls: strList(j['reference_urls']),
  );

  List<String> get tags => splitTags(tagPrompt);
}

class CanonNode {
  final String id; // '' = new, the backend assigns one
  final String text;
  const CanonNode({this.id = '', required this.text});

  factory CanonNode.fromJson(Map<String, dynamic> j) =>
      CanonNode(id: str(j['id']), text: str(j['text']));

  Map<String, dynamic> toJson() => {if (id.isNotEmpty) 'id': id, 'text': text};
}

class World extends WorldSummary {
  final List<Character> characters;
  final List<Location> locations;
  final Permissions permissions;
  final List<String> rules;
  final List<String> factions;

  /// The whole `bible` object (the editor changes rules/factions and keeps the rest).
  final Map<String, dynamic> bible;
  final List<CanonNode> canonNodes;
  final List<String> constraints;

  const World({
    required super.id,
    super.ownerId,
    required super.title,
    super.synopsis,
    super.tone,
    super.audience,
    super.language,
    super.styleId,
    super.visibility,
    this.characters = const [],
    this.locations = const [],
    this.permissions = const Permissions(),
    this.rules = const [],
    this.factions = const [],
    this.bible = const {},
    this.canonNodes = const [],
    this.constraints = const [],
  });

  factory World.fromJson(Map<String, dynamic> j) {
    final s = WorldSummary.fromJson(j);
    final bible = obj(j['bible']);
    final canon = obj(j['canon']);
    return World(
      id: s.id,
      ownerId: s.ownerId,
      title: s.title,
      synopsis: s.synopsis,
      tone: s.tone,
      audience: s.audience,
      language: s.language,
      styleId: s.styleId,
      visibility: s.visibility,
      characters: objList(j['characters']).map(Character.fromJson).toList(),
      locations: objList(j['locations']).map(Location.fromJson).toList(),
      permissions: Permissions.fromJson(obj(j['permissions'])),
      rules: strList(bible['rules']),
      factions: bible['factions'] is List
          ? (bible['factions'] as List)
                .map(_factionText)
                .where((f) => f.isNotEmpty)
                .toList()
          : const [],
      bible: bible,
      canonNodes: objList(canon['nodes']).map(CanonNode.fromJson).toList(),
      constraints: canon['constraints'] is List
          ? (canon['constraints'] as List)
                .where((c) => c != null)
                .map((c) => c is Map ? str(c['text'] ?? c['rule']) : '$c')
                .toList()
          : const [],
    );
  }

  List<Character> playableFor(String userId) =>
      characters.where((c) => c.playableBy(userId)).toList();

  Character? character(String? id) {
    for (final c in characters) {
      if (c.id == id) return c;
    }
    return null;
  }

  Location? location(String? id) {
    for (final l in locations) {
      if (l.id == id) return l;
    }
    return null;
  }

  /// permissions.allowed_locations, or every location when unset (same as the backend).
  List<Location> get allowedLocations {
    final ids = permissions.allowedLocations;
    if (ids.isEmpty) return locations;
    return locations.where((l) => ids.contains(l.id)).toList();
  }
}

/// Czech labels for `audience`.
String audienceLabel(String a) => switch (a) {
  'kids' => 'Pro děti',
  'teen' => 'Od 13 let',
  'adult' => 'Pro dospělé',
  _ => a,
};

/// Czech labels for `visibility`.
String visibilityLabel(String v) => switch (v) {
  'private' => 'Soukromý',
  'unlisted' => 'Jen s odkazem',
  'public' => 'Veřejný',
  _ => v,
};

/// Czech labels for a character `role`.
String roleLabel(String r) => switch (r) {
  'npc' => 'NPC',
  'playable' => 'Hratelná',
  'player_created' => 'Od hráče',
  _ => r,
};

/// Czech labels for `identity_level`.
String identityLabel(String l) => switch (l) {
  'prompt' => 'Jen tagy',
  'ip_adapter' => 'IP-Adapter',
  'lora' => 'LoRA',
  _ => l,
};

/// bible.factions items are strings; an object item is shown as "name — description".
String _factionText(Object? v) {
  if (v is Map) {
    final j = obj(v);
    final name = str(j['name']);
    final d = str(j['description']);
    return d.isEmpty ? name : '$name — $d';
  }
  return v == null ? '' : '$v';
}
