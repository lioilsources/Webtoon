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

  /// The "director" block at the end of an episode is shown only when the world allows any of it.
  bool get allowsDirector => canAddCharacters || canChangeLocation;
}

class Character {
  final String id;
  final String ownerId;
  final String name;
  final String role; // npc | playable | player_created
  final String description;
  final String personality;
  final String speechStyle;

  const Character({
    required this.id,
    this.ownerId = '',
    required this.name,
    this.role = 'npc',
    this.description = '',
    this.personality = '',
    this.speechStyle = '',
  });

  factory Character.fromJson(Map<String, dynamic> j) => Character(
    id: str(j['id']),
    ownerId: str(j['owner_id']),
    name: str(j['name']),
    role: str(j['role'], 'npc'),
    description: str(j['description']),
    personality: str(j['personality']),
    speechStyle: str(j['speech_style']),
  );

  /// Mirrors POST /campaigns: playable, or player_created by this user.
  bool playableBy(String userId) =>
      role == 'playable' || (role == 'player_created' && ownerId == userId);
}

class Location {
  final String id;
  final String name;
  final String description;
  final String mood;

  const Location({
    required this.id,
    required this.name,
    this.description = '',
    this.mood = '',
  });

  factory Location.fromJson(Map<String, dynamic> j) => Location(
    id: str(j['id']),
    name: str(j['name']),
    description: str(j['description']),
    mood: str(j['mood']),
  );
}

class World extends WorldSummary {
  final List<Character> characters;
  final List<Location> locations;
  final Permissions permissions;
  final List<String> rules;

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
  });

  factory World.fromJson(Map<String, dynamic> j) {
    final s = WorldSummary.fromJson(j);
    final bible = obj(j['bible']);
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
