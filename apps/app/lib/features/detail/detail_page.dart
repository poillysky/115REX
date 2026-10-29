import 'package:flutter/cupertino.dart';
import 'package:go_router/go_router.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/theme/text_styles.dart';
import 'package:rex_app/core/widgets/ios_button.dart';
import 'package:rex_app/core/widgets/ios_card.dart';

/// 详情空壳：普通导航栏 + PrimaryScrollController。
class DetailPage extends StatefulWidget {
  const DetailPage({super.key, required this.mediaId});

  final String mediaId;

  @override
  State<DetailPage> createState() => _DetailPageState();
}

class _DetailPageState extends State<DetailPage> {
  final _scroll = ScrollController();

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return CupertinoPageScaffold(
      backgroundColor: palette.mist,
      navigationBar: CupertinoNavigationBar(
        middle: Text('详情', style: AppTextStyle.navTitle(context)),
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
                  Text('条目 ${widget.mediaId}', style: AppTextStyle.heading2(context)),
                  const SizedBox(height: AppSpace.space2),
                  Text(
                    '详情与元数据将在阶段 3 接入',
                    style: AppTextStyle.caption(context),
                  ),
                ],
              ),
            ),
            const SizedBox(height: AppSpace.space6),
            IosButton(
              onPressed: () => context.push('/player/${widget.mediaId}'),
              filled: true,
              child: const Text('播放'),
            ),
          ],
        ),
      ),
    );
  }
}
