import 'package:flutter/cupertino.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/theme/text_styles.dart';

/// 主符号（渐变双 R 飘带）。最小 24。
class BrandSymbol extends StatelessWidget {
  const BrandSymbol({super.key, this.size = 72});

  final double size;

  @override
  Widget build(BuildContext context) {
    return SvgPicture.asset(
      'svg/115rex-symbol-gradient.svg',
      package: 'brand',
      width: size,
      height: size,
      fit: BoxFit.contain,
    );
  }
}

/// App 图标形态（渐变底板 + 白符号），用于启动强调位。
class BrandAppIcon extends StatelessWidget {
  const BrandAppIcon({super.key, this.size = 88});

  final double size;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(size * 0.223), // iOS squircle 近似
      child: SvgPicture.asset(
        'svg/115rex-app-icon.svg',
        package: 'brand',
        width: size,
        height: size,
        fit: BoxFit.cover,
      ),
    );
  }
}

/// 横版字标：符号 + 产品名（不出现旧品牌字样）。
class BrandWordmark extends StatelessWidget {
  const BrandWordmark({
    super.key,
    this.symbolSize = 36,
    this.compact = false,
  });

  final double symbolSize;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        BrandSymbol(size: symbolSize),
        SizedBox(width: compact ? AppSpace.space2 : AppSpace.space3),
        Text(
          '115REX',
          style: (compact
                  ? AppTextStyle.heading3(context)
                  : AppTextStyle.heading2(context))
              .copyWith(
            fontWeight: FontWeight.w700,
            letterSpacing: -0.6,
            color: palette.textPrimary,
          ),
        ),
      ],
    );
  }
}
