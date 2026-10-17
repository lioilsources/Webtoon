// Episode / panel / bubble as returned by GET /episodes/{id} (backend/internal/api/episodes.go).

import 'dart:ui' show Offset, Rect;

import 'json.dart';

enum BubbleKind {
  speech,
  thought,
  shout,
  narration;

  static BubbleKind parse(String s) => BubbleKind.values.firstWhere(
    (k) => k.name == s,
    orElse: () => BubbleKind.speech,
  );
}

class Bubble {
  final String? speakerId;
  final String text;
  final BubbleKind kind;

  /// Optional explicit tail target (§2 Panel.bubbles.anchor), normalized 0..1 in the panel.
  final Offset? anchor;

  const Bubble({
    this.speakerId,
    required this.text,
    this.kind = BubbleKind.speech,
    this.anchor,
  });

  factory Bubble.fromJson(Map<String, dynamic> j) {
    final a = obj(j['anchor']);
    final ax = dbl(a['x']), ay = dbl(a['y']);
    return Bubble(
      speakerId: strOrNull(j['speaker_id']),
      text: str(j['text']),
      kind: BubbleKind.parse(str(j['kind'], 'speech')),
      anchor: ax != null && ay != null ? Offset(ax, ay) : null,
    );
  }

  /// Body for PATCH /episodes/{id}/panels/{n} (domain.Bubble).
  Map<String, dynamic> toJson() => {
    'speaker_id': speakerId,
    'text': text,
    'kind': kind.name,
  };

  Bubble copyWith({String? text, BubbleKind? kind}) => Bubble(
    speakerId: speakerId,
    text: text ?? this.text,
    kind: kind ?? this.kind,
    anchor: anchor,
  );

  bool get isNarration => kind == BubbleKind.narration;
}

class Sfx {
  final String text;
  final String style; // bold | soft | shaky | … (free-form from the LLM)

  /// Optional explicit position (normalized 0..1), for when the backend starts sending one.
  final Offset? position;

  const Sfx({required this.text, this.style = '', this.position});

  factory Sfx.fromJson(Map<String, dynamic> j) {
    final p = obj(j['position']);
    final px = dbl(p['x']), py = dbl(p['y']);
    return Sfx(
      text: str(j['text']),
      style: str(j['style']),
      position: px != null && py != null ? Offset(px, py) : null,
    );
  }
}

class PanelCharacter {
  final String id;
  final String emotion;
  final String action;

  /// Speaker box normalized to 0..1 of the panel image. Not produced yet (§5.4 postprocess);
  /// accepted as `[x, y, w, h]` or `{x, y, w, h}`, in 0..1 or in image pixels.
  final Rect? bbox;

  const PanelCharacter({
    required this.id,
    this.emotion = '',
    this.action = '',
    this.bbox,
  });

  factory PanelCharacter.fromJson(
    Map<String, dynamic> j, {
    int imageWidth = 0,
    int imageHeight = 0,
  }) => PanelCharacter(
    id: str(j['id']),
    emotion: str(j['emotion']),
    action: str(j['action']),
    bbox: parseBbox(j['bbox'], imageWidth, imageHeight),
  );

  static Rect? parseBbox(Object? v, int w, int h) {
    double? x, y, bw, bh;
    if (v is List && v.length == 4) {
      x = dbl(v[0]);
      y = dbl(v[1]);
      bw = dbl(v[2]);
      bh = dbl(v[3]);
    } else if (v is Map) {
      final m = obj(v);
      x = dbl(m['x']);
      y = dbl(m['y']);
      bw = dbl(m['w'] ?? m['width']);
      bh = dbl(m['h'] ?? m['height']);
    }
    if (x == null || y == null || bw == null || bh == null) return null;
    final pixels = x > 1 || y > 1 || bw > 1 || bh > 1;
    if (pixels) {
      if (w <= 0 || h <= 0) return null;
      x /= w;
      bw /= w;
      y /= h;
      bh /= h;
    }
    return Rect.fromLTWH(x, y, bw, bh);
  }
}

enum GapSize {
  small,
  medium,
  large;

  static GapSize parse(String s) => GapSize.values.firstWhere(
    (g) => g.name == s,
    orElse: () => GapSize.medium,
  );

  /// m0/compose.py GAPS at strip width 800.
  double get atWidth800 => switch (this) {
    GapSize.small => 40,
    GapSize.medium => 140,
    GapSize.large => 320,
  };
}

class Panel {
  final int index;
  final String status; // pending | rendering | ready | failed
  final String? imageUrl;
  final int width;
  final int height;
  final String shot;
  final String locationId;
  final GapSize gapAfter;
  final List<Bubble> bubbles;
  final List<Sfx> sfx;
  final List<PanelCharacter> characters;
  final String error;

  const Panel({
    required this.index,
    this.status = 'pending',
    this.imageUrl,
    this.width = 0,
    this.height = 0,
    this.shot = 'medium',
    this.locationId = '',
    this.gapAfter = GapSize.medium,
    this.bubbles = const [],
    this.sfx = const [],
    this.characters = const [],
    this.error = '',
  });

  factory Panel.fromJson(Map<String, dynamic> j) {
    final w = integer(j['width']), h = integer(j['height']);
    return Panel(
      index: integer(j['index']),
      status: str(j['status'], 'pending'),
      imageUrl: strOrNull(j['image_url']),
      width: w,
      height: h,
      shot: str(j['shot'], 'medium'),
      locationId: str(j['location_id']),
      gapAfter: GapSize.parse(str(j['gap_after'], 'medium')),
      bubbles: objList(j['bubbles']).map(Bubble.fromJson).toList(),
      sfx: objList(j['sfx']).map(Sfx.fromJson).toList(),
      characters: objList(j['characters'])
          .map((c) => PanelCharacter.fromJson(c, imageWidth: w, imageHeight: h))
          .toList(),
      error: str(j['error']),
    );
  }

  bool get isReady => status == 'ready' && imageUrl != null;
  bool get isFailed => status == 'failed';
  bool get isPending => status == 'pending' || status == 'rendering';

  /// width / height. Before the image exists, use the size the worker will render
  /// (styles.json shot_size: wide/establishing are landscape 1216×832, the rest 832×1216).
  double get aspect {
    if (width > 0 && height > 0) return width / height;
    return (shot == 'wide' || shot == 'establishing') ? 1216 / 832 : 832 / 1216;
  }

  Panel copyWith({List<Bubble>? bubbles, String? status}) => Panel(
    index: index,
    status: status ?? this.status,
    imageUrl: imageUrl,
    width: width,
    height: height,
    shot: shot,
    locationId: locationId,
    gapAfter: gapAfter,
    bubbles: bubbles ?? this.bubbles,
    sfx: sfx,
    characters: characters,
    error: error,
  );
}

class Choice {
  final String id;
  final String kind; // closed | free | director
  final String text;

  const Choice({required this.id, required this.kind, required this.text});

  factory Choice.fromJson(Map<String, dynamic> j) => Choice(
    id: str(j['id']),
    kind: str(j['kind'], 'closed'),
    text: str(j['text']),
  );

  bool get isFree => kind == 'free';
}

/// What the player picked to get to an episode (`chosen`).
class Chosen {
  final String choiceId;
  final String kind;
  final String text;

  const Chosen({this.choiceId = '', this.kind = '', this.text = ''});

  static Chosen? fromJson(Object? v) {
    if (v is! Map) return null;
    final j = obj(v);
    return Chosen(
      choiceId: str(j['choice_id']),
      kind: str(j['kind']),
      text: str(j['text']),
    );
  }
}

enum EpisodeStatus {
  queued,
  generating,
  ready,
  failed;

  static EpisodeStatus parse(String s) => EpisodeStatus.values.firstWhere(
    (e) => e.name == s,
    orElse: () => EpisodeStatus.queued,
  );

  bool get inProgress => this == queued || this == generating;
}

class Episode {
  final String id;
  final String campaignId;
  final int index;
  final String title;
  final EpisodeStatus status;
  final int panelsReady;
  final int panelsTotal;
  final int creditsCost;
  final List<Panel> panels;
  final List<Choice> choices;
  final Chosen? chosen;
  final List<String> warnings;
  final String error;

  const Episode({
    required this.id,
    this.campaignId = '',
    this.index = 1,
    this.title = '',
    this.status = EpisodeStatus.queued,
    this.panelsReady = 0,
    this.panelsTotal = 0,
    this.creditsCost = 0,
    this.panels = const [],
    this.choices = const [],
    this.chosen,
    this.warnings = const [],
    this.error = '',
  });

  factory Episode.fromJson(Map<String, dynamic> j) => Episode(
    id: str(j['id']),
    campaignId: str(j['campaign_id']),
    index: integer(j['index'], 1),
    title: str(j['title']),
    status: EpisodeStatus.parse(str(j['status'], 'queued')),
    panelsReady: integer(j['panels_ready']),
    panelsTotal: integer(j['panels_total']),
    creditsCost: integer(j['credits_cost']),
    panels: objList(j['panels']).map(Panel.fromJson).toList(),
    choices: objList(j['choices']).map(Choice.fromJson).toList(),
    chosen: Chosen.fromJson(j['chosen']),
    warnings: strList(j['warnings']),
    error: str(j['error']),
  );

  /// Keep polling while the storyboard or any panel (incl. a regenerated one) is in flight.
  bool get needsPolling => status.inProgress || panels.any((p) => p.isPending);

  List<Choice> get closedChoices => choices.where((c) => !c.isFree).toList();

  Choice? get freeChoice {
    for (final c in choices) {
      if (c.isFree) return c;
    }
    return null;
  }

  Episode copyWith({List<Panel>? panels}) => Episode(
    id: id,
    campaignId: campaignId,
    index: index,
    title: title,
    status: status,
    panelsReady: panelsReady,
    panelsTotal: panelsTotal,
    creditsCost: creditsCost,
    panels: panels ?? this.panels,
    choices: choices,
    chosen: chosen,
    warnings: warnings,
    error: error,
  );

  Episode withPanel(Panel p) =>
      copyWith(panels: [for (final x in panels) x.index == p.index ? p : x]);
}
