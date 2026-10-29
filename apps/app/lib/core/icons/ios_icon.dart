import 'package:flutter/cupertino.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

/// SF Symbols 名称常量表。页面只写 IosSf.xxx，不直接碰 Phosphor。
abstract final class IosSf {
  static const chevronBackward = 'chevron.backward';
  static const chevronRight = 'chevron.right';
  static const house = 'house';
  static const houseFill = 'house.fill';
  static const filmStack = 'film.stack';
  static const magnifyingGlass = 'magnifyingglass';
  static const gearshape = 'gearshape';
  static const playCircleFill = 'play.circle.fill';
  static const personCircle = 'person.circle';
  static const eye = 'eye';
  static const eyeSlash = 'eye.slash';
  static const arrowClockwise = 'arrow.clockwise';
  static const xmark = 'xmark';
  static const gobackward10 = 'gobackward.10';
  static const goforward10 = 'goforward.10';
  static const checkmarkCircleFill = 'checkmark.circle.fill';
  static const circle = 'circle';
}

/// SF 名称 → Phosphor 字形。换库时只改这张表。
const Map<String, PhosphorIconData> _phosphorBySfName = {
  IosSf.chevronBackward: PhosphorIconsRegular.caretLeft,
  IosSf.chevronRight: PhosphorIconsRegular.caretRight,
  IosSf.house: PhosphorIconsRegular.house,
  IosSf.houseFill: PhosphorIconsFill.house,
  IosSf.filmStack: PhosphorIconsRegular.filmStrip,
  IosSf.magnifyingGlass: PhosphorIconsRegular.magnifyingGlass,
  IosSf.gearshape: PhosphorIconsRegular.gearSix,
  IosSf.playCircleFill: PhosphorIconsFill.playCircle,
  IosSf.personCircle: PhosphorIconsRegular.userCircle,
  IosSf.eye: PhosphorIconsRegular.eye,
  IosSf.eyeSlash: PhosphorIconsRegular.eyeSlash,
  IosSf.arrowClockwise: PhosphorIconsRegular.arrowClockwise,
  IosSf.xmark: PhosphorIconsRegular.x,
  IosSf.gobackward10: PhosphorIconsRegular.arrowCounterClockwise,
  IosSf.goforward10: PhosphorIconsRegular.arrowClockwise,
  IosSf.checkmarkCircleFill: PhosphorIconsFill.checkCircle,
  IosSf.circle: PhosphorIconsRegular.circle,
};

class IosIcon extends StatelessWidget {
  const IosIcon(
    this.sfName, {
    super.key,
    this.size = 22,
    this.color,
  });

  final String sfName;
  final double size;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final data = _phosphorBySfName[sfName];
    if (data == null) {
      assert(false, 'IosSf 缺少映射：$sfName，请在 _phosphorBySfName 中补齐');
      return SizedBox.square(dimension: size);
    }
    return PhosphorIcon(data, size: size, color: color);
  }
}

/// 触控热区 ≥ 44×44 的图标按钮容器。
class IosIconHitTarget extends StatelessWidget {
  const IosIconHitTarget({
    super.key,
    required this.child,
    this.size = 44,
  });

  final Widget child;
  final double size;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: Center(child: child),
    );
  }
}
