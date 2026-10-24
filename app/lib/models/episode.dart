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

  /// Original text, in the world's language. Editing always changes this.
  final String text;
  final BubbleKind kind;

  /// Machine translations of [text] by language code (`en`, `pt-BR`, …).
  final Map<String, String> i18n;

  /// Optional explicit tail target (§2 Panel.bubbles.anchor), normalized 0..1 in the panel.
  final Offset? anchor;

  const Bubble({
    this.speakerId,
    required this.text,
    this.kind = BubbleKind.speech,
    this.anchor,
    this.i18n = const {},
  });

  factory Bubble.fromJson(Map<String, dynamic> j) {
    final a = obj(j['anchor']);
    final ax = dbl(a['x']), ay = dbl(a['y']);
    return Bubble(
      speakerId: strOrNull(j['speaker_id']),
      text: str(j['text']),
      kind: BubbleKind.parse(str(j['kind'], 'speech')),
      anchor: ax != null && ay != null ? Offset(ax, ay) : null,
      i18n: strMap(j['i18n']),
    );
  }

  /// Text in [lang], or the original when there is no translation (null = original).
  String textIn(String? lang) => lang == null ? text : (i18n[lang] ?? text);

  /// This bubble as the reader shows it in [lang]; [i18n] stays so edits keep working.
  Bubble localized(String? lang) => lang == null || !i18n.containsKey(lang)
      ? this
      : Bubble(
          speakerId: speakerId,
          text: i18n[lang]!,
          kind: kind,
          anchor: anchor,
          i18n: i18n,
        );

  /// Body for PATCH /episodes/{id}/panels/{n} (domain.Bubble).
  Map<String, dynamic> toJson() => {
    'speaker_id': speakerId,
    'text': text,
    'kind': kind.name,
  };

  /// A changed text drops the translations (the backend retranslates the episode).
  Bubble copyWith({String? text, BubbleKind? kind}) => Bubble(
    speakerId: speakerId,
    text: text ?? this.text,
    kind: kind ?? this.kind,
    anchor: anchor,
    i18n: text == null || text == this.text ? i18n : const {},
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

  /// Face boxes of the image (m0/faces.py), normalized 0..1; bubbles keep off them. Empty = unknown.
  final List<Rect> faces;
  final String error;

  /// Motion panel: a 1–3 s seamless loop rendered from the still (PLAN-motion-panels).
  /// [videoUrl] is set once the loop is ready; the still stays as poster and fallback.
  final bool animate;
  final String motion;
  final int loopSeconds;
  final String videoStatus; // '' | pending | rendering | ready | failed
  final String? videoUrl;
  final String videoError;
  final int estimateSeconds;

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
    this.faces = const [],
    this.error = '',
    this.animate = false,
    this.motion = '',
    this.loopSeconds = 2,
    this.videoStatus = '',
    this.videoUrl,
    this.videoError = '',
    this.estimateSeconds = 0,
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
      faces: parseFaces(j['faces']),
      error: str(j['error']),
      animate: j['animate'] == true,
      motion: str(j['motion']),
      loopSeconds: integer(j['loop_seconds']) == 0
          ? 2
          : integer(j['loop_seconds']),
      videoStatus: str(j['video_status']),
      videoUrl: strOrNull(j['video_url']),
      videoError: str(j['video_error']),
      estimateSeconds: integer(j['estimate_seconds']),
    );
  }

  /// `faces`: [[x0, y0, x1, y1], …] normalized; malformed entries are skipped.
  static List<Rect> parseFaces(Object? v) {
    if (v is! List) return const [];
    final out = <Rect>[];
    for (final f in v) {
      if (f is! List || f.length < 4) continue;
      final c = [for (final x in f.take(4)) dbl(x)];
      if (c.any((x) => x == null)) continue;
      final r = Rect.fromLTRB(c[0]!, c[1]!, c[2]!, c[3]!);
      if (r.width > 0 && r.height > 0) out.add(r);
    }
    return out;
  }

  bool get isReady => status == 'ready' && imageUrl != null;

  /// The loop is being rendered (the still is already shown).
  bool get isVideoPending =>
      animate && (videoStatus == 'pending' || videoStatus == 'rendering');
  bool get hasVideo => animate && videoStatus == 'ready' && videoUrl != null;
  bool get isFailed => status == 'failed';
  bool get isPending => status == 'pending' || status == 'rendering';

  /// width / height. Before the image exists, use the size the worker will render
  /// (styles.json shot_size: wide/establishing are landscape 1216×832, the rest 832×1216).
  double get aspect {
    if (width > 0 && height > 0) return width / height;
    return (shot == 'wide' || shot == 'establishing') ? 1216 / 832 : 832 / 1216;
  }

  /// The panel with every bubble in [lang] (null = original).
  Panel localized(String? lang) => lang == null
      ? this
      : copyWith(bubbles: [for (final b in bubbles) b.localized(lang)]);

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
    faces: faces,
    error: error,
    animate: animate,
    motion: motion,
    loopSeconds: loopSeconds,
    videoStatus: videoStatus,
    videoUrl: videoUrl,
    videoError: videoError,
    estimateSeconds: estimateSeconds,
  );
}

class Choice {
  final String id;
  final String kind; // closed | free | director
  final String text;
  final Map<String, String> i18n;

  const Choice({
    required this.id,
    required this.kind,
    required this.text,
    this.i18n = const {},
  });

  factory Choice.fromJson(Map<String, dynamic> j) => Choice(
    id: str(j['id']),
    kind: str(j['kind'], 'closed'),
    text: str(j['text']),
    i18n: strMap(j['i18n']),
  );

  /// Same choice (same id) labelled in [lang]; the original when not translated.
  Choice localized(String? lang) => lang == null || !i18n.containsKey(lang)
      ? this
      : Choice(id: id, kind: kind, text: i18n[lang]!, i18n: i18n);

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

  /// Translated titles by language.
  final Map<String, String> titleI18n;

  /// Language of the originals (the world's), e.g. `cs`.
  final String sourceLanguage;

  /// Languages the whole episode is translated into (title, every bubble and choice).
  final List<String> languages;

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
    this.titleI18n = const {},
    this.sourceLanguage = 'cs',
    this.languages = const [],
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
    titleI18n: strMap(j['title_i18n']),
    sourceLanguage: str(j['source_language'], 'cs'),
    languages: strList(j['languages']),
  );

  /// The language this episode is shown in for the reader's [preferred] one: the preferred
  /// language when the episode is fully translated into it, otherwise the original (null).
  String? displayLanguage(String? preferred) =>
      preferred != null &&
          preferred != sourceLanguage &&
          languages.contains(preferred)
      ? preferred
      : null;

  String titleIn(String? lang) =>
      lang == null ? title : (titleI18n[lang] ?? title);

  /// Keep polling while the storyboard or any panel (incl. a regenerated one) is in flight.
  bool get needsPolling =>
      status.inProgress || panels.any((p) => p.isPending || p.isVideoPending);

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
    titleI18n: titleI18n,
    sourceLanguage: sourceLanguage,
    languages: languages,
  );

  Episode withPanel(Panel p) =>
      copyWith(panels: [for (final x in panels) x.index == p.index ? p : x]);
}
