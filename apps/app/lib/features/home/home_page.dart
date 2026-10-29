import 'package:flutter/cupertino.dart';
import 'package:go_router/go_router.dart';
import 'package:rex_app/core/icons/ios_icon.dart';
import 'package:rex_app/core/theme/app_gradients.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/theme/text_styles.dart';
import 'package:rex_app/core/widgets/ios_app_icon.dart';
import 'package:rex_app/core/widgets/ios_button.dart';
import 'package:rex_app/core/widgets/ios_card.dart';

/// 首页：海报气质（浅冷底 + 白卡片 + 品牌氛围），影视库入口用线性列表（02 §11），
/// 顶部快捷宫格用功能图标轨（渐变底板）。
class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
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
      child: PrimaryScrollController(
        controller: _scroll,
        child: CustomScrollView(
          controller: _scroll,
          physics: const BouncingScrollPhysics(
            parent: AlwaysScrollableScrollPhysics(),
          ),
          keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
          slivers: [
            SliverToBoxAdapter(
              child: DecoratedBox(
                decoration: BoxDecoration(
                  gradient: LinearGradient(
                    begin: Alignment.topCenter,
                    end: Alignment.bottomCenter,
                    colors: [
                      palette.primarySubtle,
                      palette.mist,
                    ],
                  ),
                ),
                child: SafeArea(
                  bottom: false,
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(
                      AppSpace.space4,
                      AppSpace.space3,
                      AppSpace.space4,
                      AppSpace.space4,
                    ),
                    child: Row(
                      children: [
                        Text(
                          '115REX',
                          style: AppTextStyle.heading2(context).copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const Spacer(),
                        CupertinoButton(
                          padding: EdgeInsets.zero,
                          minimumSize:
                              const Size(kMinTapTarget, kMinTapTarget),
                          onPressed: () => context.push('/settings'),
                          child: IosIconHitTarget(
                            child: IosIcon(
                              IosSf.personCircle,
                              color: palette.textPrimary,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            SliverPadding(
              padding: const EdgeInsets.fromLTRB(
                AppSpace.space4,
                0,
                AppSpace.space4,
                AppSpace.space8,
              ),
              sliver: SliverList.list(
                children: [
                  Text('快捷入口', style: AppTextStyle.heading3(context)),
                  const SizedBox(height: AppSpace.space3),
                  IosCard(
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        IosAppIconLabel(
                          sfName: IosSf.filmStack,
                          label: '影视库',
                          onTap: () => context.push('/library'),
                        ),
                        IosAppIconLabel(
                          sfName: IosSf.magnifyingGlass,
                          label: '搜索',
                          onTap: () => context.push('/search'),
                        ),
                        IosAppIconLabel(
                          sfName: IosSf.playCircleFill,
                          label: '播放',
                          onTap: () => context.push('/player/demo'),
                        ),
                        IosAppIconLabel(
                          sfName: IosSf.gearshape,
                          label: '设置',
                          onTap: () => context.push('/settings'),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppSpace.space6),
                  Text('继续观看', style: AppTextStyle.heading3(context)),
                  const SizedBox(height: AppSpace.space3),
                  IosCard(
                    child: Row(
                      children: [
                        DecoratedBox(
                          decoration: BoxDecoration(
                            gradient: AppGradients.brand(context),
                            borderRadius:
                                BorderRadius.circular(AppRadius.radiusMd),
                          ),
                          child: SizedBox(
                            width: 64,
                            height: 88,
                            child: Center(
                              child: IosIcon(
                                IosSf.playCircleFill,
                                size: 28,
                                color: palette.onPrimary,
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(width: AppSpace.space4),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '示例条目',
                                style: AppTextStyle.body(context).copyWith(
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: AppSpace.space1),
                              Text(
                                '入库后在此续播 · 阶段 3 接入',
                                style: AppTextStyle.caption(context),
                              ),
                              const SizedBox(height: AppSpace.space3),
                              ClipRRect(
                                borderRadius: BorderRadius.circular(
                                  AppRadius.radiusFull,
                                ),
                                child: SizedBox(
                                  height: 4,
                                  child: Stack(
                                    fit: StackFit.expand,
                                    children: [
                                      ColoredBox(color: palette.separator),
                                      FractionallySizedBox(
                                        alignment: Alignment.centerLeft,
                                        widthFactor: 0.37,
                                        child: ColoredBox(color: palette.primary),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: AppSpace.space6),
                  Text('更多', style: AppTextStyle.heading3(context)),
                  const SizedBox(height: AppSpace.space3),
                  IosCard(
                    padding: EdgeInsets.zero,
                    child: Column(
                      children: [
                        _HomeLink(
                          icon: IosSf.filmStack,
                          title: '全部影视库',
                          subtitle: '浏览已入库条目',
                          onTap: () => context.push('/library'),
                        ),
                        _divider(palette),
                        _HomeLink(
                          icon: IosSf.magnifyingGlass,
                          title: '资源搜索',
                          subtitle: '跨源整合 · 作品 → 候选',
                          onTap: () => context.push('/search'),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _divider(AppPalette palette) => Container(
        height: 0.5,
        margin: const EdgeInsets.only(left: AppSpace.space4 + 28),
        color: palette.separator,
      );
}

class _HomeLink extends StatelessWidget {
  const _HomeLink({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  final String icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return CupertinoButton(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.space4,
        vertical: AppSpace.space3,
      ),
      onPressed: onTap,
      child: Row(
        children: [
          IosIcon(icon, color: palette.primary),
          const SizedBox(width: AppSpace.space3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: AppTextStyle.body(context)),
                Text(subtitle, style: AppTextStyle.caption(context)),
              ],
            ),
          ),
          IosIcon(
            IosSf.chevronRight,
            size: 18,
            color: palette.textTertiary,
          ),
        ],
      ),
    );
  }
}
