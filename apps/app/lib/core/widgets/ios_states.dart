import 'package:flutter/cupertino.dart';
import 'package:rex_app/core/icons/ios_icon.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/theme/text_styles.dart';
import 'package:rex_app/core/widgets/ios_button.dart';

/// 加载态：居中指示器 + 可选说明，禁止全屏白底大转圈。
class IosLoading extends StatelessWidget {
  const IosLoading({super.key, this.label});

  final String? label;

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 64),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CupertinoActivityIndicator(radius: 12),
            if (label != null) ...[
              const SizedBox(height: AppSpace.space3),
              Text(
                label!,
                style: AppTextStyle.caption(context).copyWith(
                  color: palette.textSecondary,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class IosEmptyState extends StatelessWidget {
  const IosEmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.message,
    this.action,
  });

  final String icon;
  final String title;
  final String? message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.space8,
        vertical: 48,
      ),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            IosIcon(icon, size: 44, color: palette.textTertiary),
            const SizedBox(height: AppSpace.space4),
            Text(
              title,
              style: AppTextStyle.heading3(context).copyWith(
                fontWeight: FontWeight.w600,
              ),
              textAlign: TextAlign.center,
            ),
            if (message != null) ...[
              const SizedBox(height: AppSpace.space2),
              Text(
                message!,
                style: AppTextStyle.caption(context),
                textAlign: TextAlign.center,
              ),
            ],
            if (action != null) ...[
              const SizedBox(height: AppSpace.space6),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}

class IosErrorState extends StatelessWidget {
  const IosErrorState({
    super.key,
    required this.message,
    this.onRetry,
  });

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.space8,
        vertical: 48,
      ),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            IosIcon(
              IosSf.arrowClockwise,
              size: 36,
              color: palette.textTertiary,
            ),
            const SizedBox(height: AppSpace.space4),
            Text(
              message,
              style: AppTextStyle.body(context).copyWith(
                color: palette.textSecondary,
              ),
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: AppSpace.space6),
              IosButton(
                onPressed: onRetry,
                expanded: false,
                child: const Text('重试'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
