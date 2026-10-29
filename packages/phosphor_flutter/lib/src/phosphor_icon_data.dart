library phosphor_flutter;

import 'package:flutter/widgets.dart';

/// Composition wrapper around [IconData].
///
/// Flutter 3.47+ / Dart 3.13 made [IconData] a `final class`, so the upstream
/// `extends IconData` pattern no longer compiles. Call sites that need a raw
/// [IconData] use [iconData].
class PhosphorIconData {
  const PhosphorIconData(this.codePoint, this.style);

  final int codePoint;
  final String style;

  IconData get iconData => IconData(
        codePoint,
        fontFamily: 'Phosphor$style',
        fontPackage: 'phosphor_flutter',
        matchTextDirection: true,
      );
}

class PhosphorFlatIconData extends PhosphorIconData {
  const PhosphorFlatIconData(int codePoint, String style)
      : super(codePoint, style);
}

class PhosphorDuotoneIconData extends PhosphorIconData {
  const PhosphorDuotoneIconData(int codePoint, this.secondary)
      : super(codePoint, 'Duotone');

  final PhosphorIconData secondary;
}
