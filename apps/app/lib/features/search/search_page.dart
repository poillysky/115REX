import 'package:flutter/cupertino.dart';
import 'package:rex_app/core/icons/ios_icon.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/theme/text_styles.dart';
import 'package:rex_app/core/widgets/ios_states.dart';

/// 搜索空壳：带输入的滚动页必须 onDrag 收键盘。
class SearchPage extends StatefulWidget {
  const SearchPage({super.key, this.initialQuery});

  final String? initialQuery;

  @override
  State<SearchPage> createState() => _SearchPageState();
}

class _SearchPageState extends State<SearchPage> {
  final _scroll = ScrollController();
  late final TextEditingController _query;

  @override
  void initState() {
    super.initState();
    _query = TextEditingController(text: widget.initialQuery ?? '');
  }

  @override
  void dispose() {
    _scroll.dispose();
    _query.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return CupertinoPageScaffold(
      backgroundColor: palette.mist,
      navigationBar: CupertinoNavigationBar(
        middle: Text('搜索', style: AppTextStyle.navTitle(context)),
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
            CupertinoSearchTextField(
              controller: _query,
              placeholder: '片名、演员、资源…',
            ),
            const SizedBox(height: AppSpace.space6),
            IosEmptyState(
              icon: IosSf.magnifyingGlass,
              title: '输入关键词开始搜索',
              message: '跨源结果会按「作品 → 候选」两层展示',
            ),
          ],
        ),
      ),
    );
  }
}
