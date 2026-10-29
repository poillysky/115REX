import 'package:flutter/cupertino.dart';

/// 全局 iOS 滚动手感：回弹、无滚动条、无安卓 overscroll 辉光。
class IosScrollBehavior extends CupertinoScrollBehavior {
  const IosScrollBehavior();

  @override
  Widget buildScrollbar(
    BuildContext context,
    Widget child,
    ScrollableDetails details,
  ) =>
      child;

  @override
  Widget buildOverscrollIndicator(
    BuildContext context,
    Widget child,
    ScrollableDetails details,
  ) =>
      child;
}
