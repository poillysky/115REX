import 'package:flutter/cupertino.dart';
import 'package:rex_app/core/theme/app_gradients.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/theme/text_styles.dart';
import 'package:rex_app/core/widgets/brand_mark.dart';

/// 启动页：居中 App 图标 + 字标，底部 brandGradientSoft 氛围（海报 / 09 §5）。
class LaunchPage extends StatelessWidget {
  const LaunchPage({super.key});

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return CupertinoPageScaffold(
      backgroundColor: palette.surface,
      child: DecoratedBox(
        decoration: BoxDecoration(gradient: AppGradients.soft(context)),
        child: SafeArea(
          child: Stack(
            children: [
              Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const BrandAppIcon(size: 96),
                    const SizedBox(height: AppSpace.space5),
                    Text(
                      '115REX',
                      style: AppTextStyle.display(context).copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: AppSpace.space2),
                    Text(
                      '影视终端 · 资源整合',
                      style: AppTextStyle.caption(context),
                    ),
                    const SizedBox(height: AppSpace.space8),
                    CupertinoActivityIndicator(
                      radius: 11,
                      color: palette.primary,
                    ),
                  ],
                ),
              ),
              Positioned(
                left: 0,
                right: 0,
                bottom: 0,
                height: 120,
                child: IgnorePointer(
                  child: DecoratedBox(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          palette.surface.withValues(alpha: 0),
                          palette.primarySubtle.withValues(alpha: 0.55),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
