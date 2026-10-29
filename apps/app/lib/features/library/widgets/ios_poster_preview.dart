import 'package:flutter/cupertino.dart';

/// 海报长按预览统一入口（01 §7.6）。阶段 3 接真实海报图。
class IosPosterPreview extends StatelessWidget {
  const IosPosterPreview({
    super.key,
    required this.child,
    required this.onPlay,
    required this.onOpenDetail,
  });

  final Widget child;
  final VoidCallback onPlay;
  final VoidCallback onOpenDetail;

  @override
  Widget build(BuildContext context) {
    return CupertinoContextMenu(
      actions: [
        CupertinoContextMenuAction(
          onPressed: () {
            Navigator.of(context, rootNavigator: true).pop();
            onPlay();
          },
          isDefaultAction: true,
          child: const Text('播放'),
        ),
        CupertinoContextMenuAction(
          onPressed: () {
            Navigator.of(context, rootNavigator: true).pop();
            onOpenDetail();
          },
          child: const Text('详情'),
        ),
      ],
      child: child,
    );
  }
}
