library phosphor_flutter;

import 'package:flutter/widgets.dart';
import 'package:phosphor_flutter/phosphor_flutter.dart';

/// Renders a [PhosphorIconData] glyph. Uses [widgets.Icon], not Material.
class PhosphorIcon extends StatelessWidget {
  const PhosphorIcon(
    this.data, {
    super.key,
    this.size,
    this.color,
    this.shadows,
    this.semanticLabel,
    this.textDirection,
    this.duotoneSecondaryOpacity = 0.20,
    this.duotoneSecondaryColor,
  });

  final PhosphorIconData data;
  final double? size;
  final Color? color;
  final List<Shadow>? shadows;
  final String? semanticLabel;
  final TextDirection? textDirection;
  final double duotoneSecondaryOpacity;
  final Color? duotoneSecondaryColor;

  @override
  Widget build(BuildContext context) {
    if (data is PhosphorDuotoneIconData) {
      final duotoneIcon = data as PhosphorDuotoneIconData;
      return Stack(
        alignment: Alignment.center,
        children: [
          Opacity(
            opacity: duotoneSecondaryOpacity,
            child: Icon(
              duotoneIcon.secondary.iconData,
              size: size,
              color: duotoneSecondaryColor ?? color,
              shadows: shadows,
              semanticLabel: semanticLabel,
              textDirection: textDirection,
            ),
          ),
          Icon(
            data.iconData,
            size: size,
            color: color,
            shadows: shadows,
            semanticLabel: semanticLabel,
            textDirection: textDirection,
          ),
        ],
      );
    }
    return Icon(
      data.iconData,
      size: size,
      color: color,
      shadows: shadows,
      semanticLabel: semanticLabel,
      textDirection: textDirection,
    );
  }
}
