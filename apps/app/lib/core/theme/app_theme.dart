import 'package:flutter/cupertino.dart';
import 'package:rex_app/core/theme/app_palette.dart';

/// Cupertino 主题。不能 const —— 冻结后切深色不刷新（01 §8.8）。
abstract final class AppTheme {
  static CupertinoThemeData resolve(BuildContext context) {
    final brightness = MediaQuery.platformBrightnessOf(context);
    return brightness == Brightness.dark ? dark : light;
  }

  static CupertinoThemeData get light => _build(AppPalette.light, Brightness.light);

  static CupertinoThemeData get dark => _build(AppPalette.dark, Brightness.dark);

  static CupertinoThemeData _build(AppPalette palette, Brightness brightness) {
    return CupertinoThemeData(
      brightness: brightness,
      primaryColor: palette.primary,
      primaryContrastingColor: palette.onPrimary,
      scaffoldBackgroundColor: palette.background,
      barBackgroundColor: palette.background,
      textTheme: CupertinoTextThemeData(
        primaryColor: palette.textPrimary,
        textStyle: TextStyle(
          color: palette.textPrimary,
          fontSize: 16,
          decoration: TextDecoration.none,
        ),
        navTitleTextStyle: TextStyle(
          color: palette.textPrimary,
          fontSize: 17,
          fontWeight: FontWeight.w600,
          decoration: TextDecoration.none,
        ),
        navLargeTitleTextStyle: TextStyle(
          color: palette.textPrimary,
          fontSize: 34,
          fontWeight: FontWeight.w700,
          letterSpacing: -0.6,
          decoration: TextDecoration.none,
        ),
        actionTextStyle: TextStyle(
          color: palette.primary,
          fontSize: 17,
          decoration: TextDecoration.none,
        ),
      ),
    );
  }
}
