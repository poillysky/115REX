import 'package:flutter/cupertino.dart';
import 'package:provider/provider.dart';
import 'package:rex_app/application/session_controller.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/theme/text_styles.dart';
import 'package:rex_app/core/widgets/ios_button.dart';
import 'package:rex_app/core/widgets/ios_card.dart';

/// 设置空壳：可退出演示登录。
class SettingsPage extends StatefulWidget {
  const SettingsPage({super.key});

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  final _scroll = ScrollController();

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _confirmSignOut() async {
    final ok = await showCupertinoModalPopup<bool>(
      context: context,
      builder: (context) => CupertinoActionSheet(
        title: const Text('退出登录'),
        message: const Text('将清除本机会话'),
        actions: [
          CupertinoActionSheetAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('退出登录'),
          ),
        ],
        cancelButton: CupertinoActionSheetAction(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('取消'),
        ),
      ),
    );
    if (ok == true && mounted) {
      context.read<SessionController>().signOut();
    }
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return CupertinoPageScaffold(
      backgroundColor: palette.mist,
      navigationBar: CupertinoNavigationBar(
        middle: Text('设置', style: AppTextStyle.navTitle(context)),
        border: null,
        backgroundColor: palette.mist,
      ),
      child: PrimaryScrollController(
        controller: _scroll,
        child: ListView(
          controller: _scroll,
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          padding: const EdgeInsets.all(AppSpace.space4),
          children: [
            IosCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('关于', style: AppTextStyle.heading3(context)),
                  const SizedBox(height: AppSpace.space2),
                  Text(
                    '115REX · iOS 优先 Flutter 客户端骨架',
                    style: AppTextStyle.caption(context),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpace.space6),
            IosButton(
              onPressed: _confirmSignOut,
              destructive: true,
              child: const Text('退出登录'),
            ),
          ],
        ),
      ),
    );
  }
}
