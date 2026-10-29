import 'package:flutter/cupertino.dart';
import 'package:rex_app/core/icons/ios_icon.dart';
import 'package:rex_app/core/theme/app_gradients.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/theme/text_styles.dart';
import 'package:rex_app/core/widgets/ios_button.dart';

/// 功能入口图标：蓝紫渐变底板 + 白色字形（docs/02 §7.3）。
class IosAppIcon extends StatelessWidget {
  const IosAppIcon({
    super.key,
    required this.sfName,
    this.size = 56,
  });

  final String sfName;
  final double size;

  @override
  Widget build(BuildContext context) {
    final radius = size * 0.24;
    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: AppGradients.brand(context),
        borderRadius: BorderRadius.circular(radius),
      ),
      child: SizedBox(
        width: size,
        height: size,
        child: Center(
          child: IosIcon(
            sfName,
            size: size * 0.46,
            color: AppPalette.of(context).onPrimary,
          ),
        ),
      ),
    );
  }
}

/// 功能入口：图标 + 标签，整块可点，热区 ≥ 44。
class IosAppIconLabel extends StatelessWidget {
  const IosAppIconLabel({
    super.key,
    required this.sfName,
    required this.label,
    required this.onTap,
    this.iconSize = 56,
  });

  final String sfName;
  final String label;
  final VoidCallback onTap;
  final double iconSize;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onTap,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minWidth: kMinTapTarget),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            IosAppIcon(sfName: sfName, size: iconSize),
            const SizedBox(height: AppSpace.space2),
            Text(
              label,
              style: AppTextStyle.caption(context).copyWith(
                color: AppPalette.of(context).textPrimary,
                fontWeight: FontWeight.w500,
              ),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
