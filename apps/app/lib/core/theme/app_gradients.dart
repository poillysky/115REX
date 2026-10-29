import 'package:flutter/cupertino.dart';
import 'package:rex_app/core/theme/app_palette.dart';

/// 品牌渐变停靠点（docs/02 §3.1.1，与 tools/generate_tokens.py 一致）。
abstract final class AppGradients {
  static const brandStopsLight = <Color>[
    Color(0xFF25C4FF),
    Color(0xFF168BFF),
    Color(0xFF315BFF),
    Color(0xFF8B35F6),
  ];

  static const brandStopsDark = <Color>[
    Color(0xFF1AA8E0),
    Color(0xFF2A78E8),
    Color(0xFF4A5AE8),
    Color(0xFF9A55F0),
  ];

  static const brandStops = [0.0, 0.36, 0.67, 1.0];

  /// Logo / 功能图标底板 / 播放主控。方向 135°（左上→右下）。
  static LinearGradient brand(BuildContext context) {
    final dark = MediaQuery.platformBrightnessOf(context) == Brightness.dark;
    return LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: dark ? brandStopsDark : brandStopsLight,
      stops: brandStops,
    );
  }

  /// 登录 / 启动氛围：primarySubtle → surface，极低对比。
  static LinearGradient soft(BuildContext context) {
    final palette = AppPalette.of(context);
    return LinearGradient(
      begin: Alignment.topCenter,
      end: Alignment.bottomCenter,
      colors: [palette.primarySubtle, palette.surface],
    );
  }
}
