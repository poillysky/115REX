import 'package:flutter/cupertino.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';

/// 字阶工厂：带 context，颜色随深浅色刷新。不指定 fontFamily。
abstract final class AppTextStyle {
  static TextStyle display(BuildContext context) => TextStyle(
        fontSize: AppFontSize.display,
        fontWeight: AppFontWeight.display,
        letterSpacing: AppTracking.display,
        color: AppPalette.of(context).textPrimary,
      );

  static TextStyle heading1(BuildContext context) => TextStyle(
        fontSize: AppFontSize.heading1,
        fontWeight: AppFontWeight.heading1,
        letterSpacing: AppTracking.heading1,
        color: AppPalette.of(context).textPrimary,
      );

  static TextStyle heading2(BuildContext context) => TextStyle(
        fontSize: AppFontSize.heading2,
        fontWeight: AppFontWeight.heading2,
        letterSpacing: AppTracking.heading2,
        color: AppPalette.of(context).textPrimary,
      );

  static TextStyle heading3(BuildContext context) => TextStyle(
        fontSize: AppFontSize.heading3,
        fontWeight: AppFontWeight.heading3,
        letterSpacing: AppTracking.heading3,
        color: AppPalette.of(context).textPrimary,
      );

  static TextStyle body(BuildContext context) => TextStyle(
        fontSize: AppFontSize.body,
        fontWeight: AppFontWeight.body,
        color: AppPalette.of(context).textPrimary,
      );

  static TextStyle label(BuildContext context) => TextStyle(
        fontSize: AppFontSize.label,
        fontWeight: AppFontWeight.label,
        color: AppPalette.of(context).textPrimary,
      );

  static TextStyle caption(BuildContext context) => TextStyle(
        fontSize: AppFontSize.caption,
        fontWeight: AppFontWeight.caption,
        color: AppPalette.of(context).textSecondary,
      );

  static TextStyle navTitle(BuildContext context) => TextStyle(
        fontSize: AppFontSize.heading3,
        fontWeight: FontWeight.w600,
        color: AppPalette.of(context).textPrimary,
      );

  /// 时间码 / 集数 / 百分比：等宽数字，避免刷新时抖动。
  static TextStyle timecode(BuildContext context) => TextStyle(
        fontSize: AppFontSize.caption,
        fontWeight: FontWeight.w500,
        fontFeatures: const [FontFeature.tabularFigures()],
        color: AppPalette.of(context).textSecondary,
      );
}
