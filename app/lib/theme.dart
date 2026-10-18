import 'package:flutter/material.dart';

/// Bundled OFL fonts (assets/fonts, same as m0/compose.py). They are variable fonts, so the
/// weight is set through the `wght` axis as well as [FontWeight].
class ComicFonts {
  static const nunito = 'Nunito';
  static const dynaPuff = 'DynaPuff';
  static const baloo = 'Baloo2';

  static TextStyle _v(String family, int weight, {FontStyle? style}) =>
      TextStyle(
        fontFamily: family,
        fontWeight: FontWeight.values[(weight ~/ 100 - 1).clamp(0, 8)],
        fontVariations: [FontVariation.weight(weight.toDouble())],
        fontStyle: style,
      );

  /// Speech bubble: Nunito Bold.
  static TextStyle speech() => _v(nunito, 700);

  /// Thought bubble: Nunito Italic SemiBold.
  static TextStyle thought() => _v(nunito, 600, style: FontStyle.italic);

  /// Shout bubble and SFX: DynaPuff Bold.
  static TextStyle shout() => _v(dynaPuff, 700);

  /// Narration box and titles: Baloo 2 Medium / Bold.
  static TextStyle narration() => _v(baloo, 500);
  static TextStyle title() => _v(baloo, 700);

  static TextStyle ui([int weight = 600]) => _v(nunito, weight);
}

/// Comic palette: ink outlines on paper, a violet accent (m0 choices block) and SFX yellow.
class ComicColors {
  static const ink = Color(0xFF141418);
  static const paper = Color(0xFFFBF7EE);
  static const night = Color(0xFF121116);
  static const nightSurface = Color(0xFF1D1B24);
  static const accent = Color(0xFF7856C8);
  static const sfxYellow = Color(0xFFFFDC3C);
  static const narrationBox = Color(0xFFFFF8E1);
  static const bubble = Colors.white;
}

/// Ink outline + hard offset shadow, the "comic card" look. Light: ink on paper; dark: pale
/// ink on night.
@immutable
class ComicTheme extends ThemeExtension<ComicTheme> {
  final Color outline;
  final Color shadow;
  final Color readerBackground;

  const ComicTheme({
    required this.outline,
    required this.shadow,
    required this.readerBackground,
  });

  static ComicTheme of(BuildContext context) =>
      Theme.of(context).extension<ComicTheme>() ?? light;

  static const light = ComicTheme(
    outline: ComicColors.ink,
    shadow: ComicColors.ink,
    readerBackground: Colors.white,
  );

  static const dark = ComicTheme(
    outline: Color(0xFFE7E2F4),
    shadow: Color(0xFF000000),
    readerBackground: Color(0xFF0B0A0E),
  );

  @override
  ComicTheme copyWith({
    Color? outline,
    Color? shadow,
    Color? readerBackground,
  }) => ComicTheme(
    outline: outline ?? this.outline,
    shadow: shadow ?? this.shadow,
    readerBackground: readerBackground ?? this.readerBackground,
  );

  @override
  ComicTheme lerp(ComicTheme? other, double t) {
    if (other == null) return this;
    return ComicTheme(
      outline: Color.lerp(outline, other.outline, t)!,
      shadow: Color.lerp(shadow, other.shadow, t)!,
      readerBackground: Color.lerp(
        readerBackground,
        other.readerBackground,
        t,
      )!,
    );
  }

  BoxDecoration card({Color? color, double radius = 16}) => BoxDecoration(
    color: color,
    borderRadius: BorderRadius.circular(radius),
    border: Border.all(color: outline, width: 2),
    boxShadow: [BoxShadow(color: shadow, offset: const Offset(4, 4))],
  );
}

ThemeData buildTheme(Brightness brightness) {
  final dark = brightness == Brightness.dark;
  final scheme = ColorScheme.fromSeed(
    seedColor: ComicColors.accent,
    brightness: brightness,
    surface: dark ? ComicColors.nightSurface : Colors.white,
  );
  final comic = dark ? ComicTheme.dark : ComicTheme.light;
  final base = ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: dark ? ComicColors.night : ComicColors.paper,
    fontFamily: ComicFonts.nunito,
    extensions: [comic],
  );
  final shape = RoundedRectangleBorder(
    borderRadius: BorderRadius.circular(14),
    side: BorderSide(color: comic.outline, width: 2),
  );
  return base.copyWith(
    // ComicFonts styles carry no color; without onSurface they fall back to black, which is
    // unreadable in dark mode (dropdown items use titleMedium, chips the labelStyle below).
    textTheme: base.textTheme.copyWith(
      headlineMedium: ComicFonts.title().copyWith(
        fontSize: 30,
        height: 1.1,
        color: scheme.onSurface,
      ),
      headlineSmall: ComicFonts.title().copyWith(
        fontSize: 24,
        height: 1.15,
        color: scheme.onSurface,
      ),
      titleLarge: ComicFonts.title().copyWith(
        fontSize: 21,
        height: 1.2,
        color: scheme.onSurface,
      ),
      titleMedium: ComicFonts.ui(
        700,
      ).copyWith(fontSize: 16, color: scheme.onSurface),
    ),
    appBarTheme: AppBarTheme(
      backgroundColor: dark ? ComicColors.night : ComicColors.paper,
      foregroundColor: scheme.onSurface,
      elevation: 0,
      scrolledUnderElevation: 0,
      centerTitle: false,
      titleTextStyle: ComicFonts.title().copyWith(
        fontSize: 22,
        color: scheme.onSurface,
      ),
      shape: Border(bottom: BorderSide(color: comic.outline, width: 2)),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: ComicColors.accent,
        foregroundColor: Colors.white,
        shape: shape,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        textStyle: ComicFonts.ui(800).copyWith(fontSize: 16),
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: scheme.onSurface,
        backgroundColor: scheme.surface,
        shape: shape,
        side: BorderSide(color: comic.outline, width: 2),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
        textStyle: ComicFonts.ui(700).copyWith(fontSize: 15),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: scheme.surface,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: comic.outline, width: 2),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: BorderSide(color: comic.outline, width: 2),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(14),
        borderSide: const BorderSide(color: ComicColors.accent, width: 2.5),
      ),
    ),
    chipTheme: base.chipTheme.copyWith(
      side: BorderSide(color: comic.outline, width: 1.5),
      labelStyle: ComicFonts.ui(
        700,
      ).copyWith(fontSize: 13, color: scheme.onSurface),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: dark ? ComicColors.nightSurface : Colors.white,
      indicatorColor: ComicColors.accent.withValues(alpha: 0.22),
      labelTextStyle: WidgetStatePropertyAll(
        ComicFonts.ui(700).copyWith(fontSize: 12),
      ),
    ),
  );
}
