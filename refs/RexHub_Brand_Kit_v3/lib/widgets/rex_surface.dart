import 'package:flutter/material.dart';
import '../design_system/rex_design_tokens.dart';

class RexSurface extends StatelessWidget {
  const RexSurface({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(RexSpacing.x5),
    this.radius = RexRadius.xl,
    this.color = RexColors.surface,
    this.border,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final double radius;
  final Color color;
  final BorderSide? border;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(radius),
        border: border == null ? null : Border.fromBorderSide(border!),
      ),
      child: child,
    );
  }
}
