import 'package:flutter/cupertino.dart';
import 'package:rex_app/core/theme/design_tokens.dart';

/// 语义色入口。页面只从这里取色，禁止散落 Color(0x…)。
class AppPalette {
  const AppPalette._({
    required this.background,
    required this.surface,
    required this.surfaceSecondary,
    required this.primary,
    required this.primarySubtle,
    required this.brandViolet,
    required this.onPrimary,
    required this.textPrimary,
    required this.textSecondary,
    required this.textTertiary,
    required this.separator,
    required this.success,
    required this.warning,
    required this.danger,
  });

  final Color background;
  final Color surface;
  final Color surfaceSecondary;
  final Color primary;
  final Color primarySubtle;
  final Color brandViolet;
  final Color onPrimary;
  final Color textPrimary;
  final Color textSecondary;
  final Color textTertiary;
  final Color separator;
  final Color success;
  final Color warning;
  final Color danger;

  /// 文档模板里的页面底色别名（= background）。
  Color get mist => background;

  static AppPalette of(BuildContext context) {
    final brightness = MediaQuery.platformBrightnessOf(context);
    return brightness == Brightness.dark ? dark : light;
  }

  static const light = AppPalette._(
    background: AppColorsLight.background,
    surface: AppColorsLight.surface,
    surfaceSecondary: AppColorsLight.surfaceSecondary,
    primary: AppColorsLight.primary,
    primarySubtle: AppColorsLight.primarySubtle,
    brandViolet: AppColorsLight.brandViolet,
    onPrimary: AppColorsLight.onPrimary,
    textPrimary: AppColorsLight.textPrimary,
    textSecondary: AppColorsLight.textSecondary,
    textTertiary: AppColorsLight.textTertiary,
    separator: AppColorsLight.separator,
    success: AppColorsLight.success,
    warning: AppColorsLight.warning,
    danger: AppColorsLight.danger,
  );

  static const dark = AppPalette._(
    background: AppColorsDark.background,
    surface: AppColorsDark.surface,
    surfaceSecondary: AppColorsDark.surfaceSecondary,
    primary: AppColorsDark.primary,
    primarySubtle: AppColorsDark.primarySubtle,
    brandViolet: AppColorsDark.brandViolet,
    onPrimary: AppColorsDark.onPrimary,
    textPrimary: AppColorsDark.textPrimary,
    textSecondary: AppColorsDark.textSecondary,
    textTertiary: AppColorsDark.textTertiary,
    separator: AppColorsDark.separator,
    success: AppColorsDark.success,
    warning: AppColorsDark.warning,
    danger: AppColorsDark.danger,
  );
}
