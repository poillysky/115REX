import 'package:flutter/material.dart';

/// RexHub brand tokens — shared by all screens and reusable widgets.
abstract final class RexColors {
  static const brand = Color(0xFF176BFF);
  static const brandBright = Color(0xFF25BFFF);
  static const brandViolet = Color(0xFF7047F5);
  static const brandSubtle = Color(0xFFEAF2FF);

  static const background = Color(0xFFF3F4F6);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceSecondary = Color(0xFFF6F7F9);

  static const textPrimary = Color(0xFF171A22);
  static const textSecondary = Color(0xFF7D8594);
  static const separator = Color(0xFFE5E8EE);

  static const success = Color(0xFF16845B);
  static const warning = Color(0xFFB96B08);
  static const error = Color(0xFFD83B45);
}

abstract final class RexSpacing {
  static const x1 = 4.0;
  static const x2 = 8.0;
  static const x3 = 12.0;
  static const x4 = 16.0;
  static const x5 = 20.0;
  static const x6 = 24.0;
  static const x8 = 32.0;
  static const x10 = 40.0;
}

abstract final class RexRadius {
  static const sm = 8.0;
  static const md = 12.0;
  static const lg = 16.0;
  static const xl = 22.0;
  static const xxl = 28.0;
  static const pill = 999.0;
}

abstract final class RexType {
  static const pageTitle = TextStyle(
    fontSize: 30, height: 1.15, fontWeight: FontWeight.w700,
    letterSpacing: -0.7, color: RexColors.textPrimary,
  );
  static const sectionTitle = TextStyle(
    fontSize: 22, height: 1.25, fontWeight: FontWeight.w600,
    letterSpacing: -0.35, color: RexColors.textPrimary,
  );
  static const cardTitle = TextStyle(
    fontSize: 18, height: 1.3, fontWeight: FontWeight.w600,
    color: RexColors.textPrimary,
  );
  static const body = TextStyle(
    fontSize: 16, height: 1.45, fontWeight: FontWeight.w400,
    color: RexColors.textPrimary,
  );
  static const caption = TextStyle(
    fontSize: 13, height: 1.35, fontWeight: FontWeight.w400,
    color: RexColors.textSecondary,
  );
}

/// Material theme helper for shared widgets. Do not replace an existing
/// CupertinoApp just to use this; reuse the color/type tokens with CupertinoTheme.
abstract final class RexTheme {
  static ThemeData get light => ThemeData(
    useMaterial3: true,
    scaffoldBackgroundColor: RexColors.background,
    colorScheme: ColorScheme.fromSeed(
      seedColor: RexColors.brand,
      brightness: Brightness.light,
      surface: RexColors.surface,
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.transparent,
      foregroundColor: RexColors.textPrimary,
      elevation: 0,
      centerTitle: false,
      titleTextStyle: RexType.sectionTitle,
    ),
    cardTheme: CardThemeData(
      color: RexColors.surface,
      elevation: 0,
      margin: EdgeInsets.zero,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(RexRadius.xl),
      ),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: RexColors.surfaceSecondary,
      contentPadding: const EdgeInsets.symmetric(
        horizontal: RexSpacing.x4, vertical: RexSpacing.x4,
      ),
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(RexRadius.lg),
        borderSide: BorderSide.none,
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(RexRadius.lg),
        borderSide: BorderSide.none,
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(RexRadius.lg),
        borderSide: const BorderSide(color: RexColors.brand, width: 1.4),
      ),
    ),
  );
}
