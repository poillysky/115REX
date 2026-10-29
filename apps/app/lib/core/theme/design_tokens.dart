// 由 tools/generate_tokens.py 从 packages/design-tokens/tokens.json 生成，不要手改。

import 'dart:ui';

abstract final class AppColorsLight {
  static const Color background = Color(0xFFF3F4F6);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color surfaceSecondary = Color(0xFFF6F7F9);
  static const Color primary = Color(0xFF176BFF);
  static const Color primarySubtle = Color(0xFFE0F2FE);
  static const Color brandViolet = Color(0xFF8B5CF6);
  static const Color onPrimary = Color(0xFFFFFFFF);
  static const Color textPrimary = Color(0xFF171A22);
  static const Color textSecondary = Color(0xFF6B7280);
  static const Color textTertiary = Color(0xFF6E757F);
  static const Color separator = Color(0xFFE5E8EE);
  static const Color success = Color(0xFF16845B);
  static const Color warning = Color(0xFFB96B08);
  static const Color danger = Color(0xFFD83B45);
}

abstract final class AppColorsDark {
  static const Color background = Color(0xFF000000);
  static const Color surface = Color(0xFF1C1C1E);
  static const Color surfaceSecondary = Color(0xFF2C2C2E);
  static const Color primary = Color(0xFF3D8BFF);
  static const Color primarySubtle = Color(0xFF0E1B2E);
  static const Color brandViolet = Color(0xFFA57BFF);
  static const Color onPrimary = Color(0xFFFFFFFF);
  static const Color textPrimary = Color(0xFFF5F5F7);
  static const Color textSecondary = Color(0xFF98989D);
  static const Color textTertiary = Color(0xFF8E8E93);
  static const Color separator = Color(0xFF38383A);
  static const Color success = Color(0xFF2FBF85);
  static const Color warning = Color(0xFFE8A030);
  static const Color danger = Color(0xFFFF5F63);
}

abstract final class AppSpace {
  static const double space1 = 4.0;
  static const double space2 = 8.0;
  static const double space3 = 12.0;
  static const double space4 = 16.0;
  static const double space5 = 20.0;
  static const double space6 = 24.0;
  static const double space8 = 32.0;
  static const double space10 = 40.0;
}

abstract final class AppRadius {
  static const double radiusSm = 8.0;
  static const double radiusMd = 12.0;
  static const double radiusLg = 16.0;
  static const double radiusXl = 22.0;
  static const double radius2xl = 28.0;
  static const double radiusFull = 999.0;
}

abstract final class AppDuration {
  static const int micro = 120;
  static const int page = 300;
}

abstract final class AppTracking {
  static const double display = -0.7;
  static const double heading1 = -0.6;
  static const double heading2 = -0.45;
  static const double heading3 = -0.35;
  static const double body = 0.0;
  static const double label = 0.0;
  static const double caption = 0.0;
}

abstract final class AppFontSize {
  static const double display = 32.0;
  static const double heading1 = 30.0;
  static const double heading2 = 22.0;
  static const double heading3 = 18.0;
  static const double body = 16.0;
  static const double label = 15.0;
  static const double caption = 13.0;
}

abstract final class AppFontWeight {
  static const FontWeight display = FontWeight.w600;
  static const FontWeight heading1 = FontWeight.w700;
  static const FontWeight heading2 = FontWeight.w600;
  static const FontWeight heading3 = FontWeight.w500;
  static const FontWeight body = FontWeight.w400;
  static const FontWeight label = FontWeight.w500;
  static const FontWeight caption = FontWeight.w400;
}
