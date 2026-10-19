// Lenient JSON accessors: the backend passes LLM-produced fields through, so types can vary
// (e.g. `emotion` is a string or a list of strings).

String str(Object? v, [String fallback = '']) {
  if (v == null) return fallback;
  if (v is String) return v;
  if (v is List) return v.map((e) => '$e').join(', ');
  return '$v';
}

String? strOrNull(Object? v) {
  if (v == null) return null;
  final s = str(v);
  return s.isEmpty ? null : s;
}

int integer(Object? v, [int fallback = 0]) {
  if (v is int) return v;
  if (v is num) return v.toInt();
  if (v is String) return int.tryParse(v) ?? fallback;
  return fallback;
}

double? dbl(Object? v) {
  if (v is num) return v.toDouble();
  if (v is String) return double.tryParse(v);
  return null;
}

Map<String, dynamic> obj(Object? v) =>
    v is Map ? v.map((k, val) => MapEntry('$k', val)) : <String, dynamic>{};

List<Map<String, dynamic>> objList(Object? v) =>
    v is List ? v.whereType<Map>().map(obj).toList() : const [];

List<String> strList(Object? v) {
  if (v is List) return v.where((e) => e != null).map((e) => '$e').toList();
  if (v is String && v.isNotEmpty) return [v];
  return const [];
}

DateTime? date(Object? v) => v is String ? DateTime.tryParse(v) : null;

/// `{"en": "…", "de": "…"}` → map of non-empty strings (translations, `i18n`).
Map<String, String> strMap(Object? v) => {
  if (v is Map)
    for (final e in v.entries)
      if (e.value is String && (e.value as String).isNotEmpty)
        e.key.toString(): e.value as String,
};
