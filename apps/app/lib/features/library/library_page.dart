import 'package:flutter/cupertino.dart';
import 'package:rex_app/core/icons/ios_icon.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/widgets/ios_states.dart';

/// 影视库空壳：大标题列表骨架（01 §9.1）。
class LibraryPage extends StatefulWidget {
  const LibraryPage({super.key});

  @override
  State<LibraryPage> createState() => _LibraryPageState();
}

class _LibraryPageState extends State<LibraryPage> {
  final _scroll = ScrollController();

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    await Future<void>.delayed(const Duration(milliseconds: 600));
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return CupertinoPageScaffold(
      backgroundColor: palette.mist,
      child: PrimaryScrollController(
        controller: _scroll,
        child: CustomScrollView(
          controller: _scroll,
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          slivers: [
            CupertinoSliverNavigationBar(
              largeTitle: const Text('媒体库'),
              backgroundColor: palette.mist,
              border: null,
            ),
            CupertinoSliverRefreshControl(onRefresh: _refresh),
            SliverSafeArea(
              top: false,
              sliver: SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpace.space4,
                  ),
                  child: IosEmptyState(
                    icon: IosSf.filmStack,
                    title: '还没有影片',
                    message: '绑定网盘目录并入库后，条目会出现在这里',
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
