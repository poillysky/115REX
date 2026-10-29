import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:rex_app/core/icons/ios_icon.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/app_theme.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/theme/text_styles.dart';
import 'package:rex_app/core/widgets/ios_button.dart';

/// 播放页空壳：沉浸式 + 强制深色；进出成对还原方向与系统 UI（01 §9.3）。
class PlayerPage extends StatefulWidget {
  const PlayerPage({super.key, required this.mediaId});

  final String mediaId;

  @override
  State<PlayerPage> createState() => _PlayerPageState();
}

class _PlayerPageState extends State<PlayerPage> {
  @override
  void initState() {
    super.initState();
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersive);
    SystemChrome.setPreferredOrientations(const [
      DeviceOrientation.landscapeLeft,
      DeviceOrientation.landscapeRight,
      DeviceOrientation.portraitUp,
    ]);
    SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.light);
  }

  @override
  void dispose() {
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.edgeToEdge);
    SystemChrome.setPreferredOrientations(const [
      DeviceOrientation.portraitUp,
    ]);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CupertinoTheme(
      data: AppTheme.dark,
      child: CupertinoPageScaffold(
        backgroundColor: CupertinoColors.black,
        child: SafeArea(
          child: Stack(
            children: [
              Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IosIcon(
                      IosSf.playCircleFill,
                      size: 56,
                      color: AppPalette.dark.textSecondary,
                    ),
                    const SizedBox(height: AppSpace.space4),
                    Text(
                      '播放器骨架',
                      style: AppTextStyle.heading3(context).copyWith(
                        color: AppPalette.dark.textPrimary,
                      ),
                    ),
                    const SizedBox(height: AppSpace.space2),
                    Text(
                      '条目 ${widget.mediaId} · media_kit 阶段 6 接入',
                      style: AppTextStyle.caption(context).copyWith(
                        color: AppPalette.dark.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              Positioned(
                top: AppSpace.space2,
                left: AppSpace.space2,
                child: CupertinoButton(
                  padding: EdgeInsets.zero,
                  minimumSize: const Size(kMinTapTarget, kMinTapTarget),
                  onPressed: () => context.pop(),
                  child: IosIconHitTarget(
                    child: IosIcon(
                      IosSf.chevronBackward,
                      color: AppPalette.dark.textPrimary,
                    ),
                  ),
                ),
              ),
              Positioned(
                bottom: AppSpace.space6,
                left: AppSpace.space6,
                right: AppSpace.space6,
                child: IosButton(
                  onPressed: () => context.pop(),
                  filled: true,
                  child: const Text('返回'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
