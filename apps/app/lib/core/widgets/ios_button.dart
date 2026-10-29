import 'package:flutter/cupertino.dart';
import 'package:flutter/services.dart';
import 'package:rex_app/core/theme/app_palette.dart';
import 'package:rex_app/core/theme/design_tokens.dart';
import 'package:rex_app/core/theme/text_styles.dart';

const double kMinTapTarget = 44;

/// iOS 按压反馈：缩放 0.96 + 透明度 0.9，120ms（01 §7.1）。
class IosButton extends StatefulWidget {
  const IosButton({
    super.key,
    required this.onPressed,
    required this.child,
    this.filled = false,
    this.destructive = false,
    this.expanded = true,
    this.haptic = true,
  });

  final VoidCallback? onPressed;
  final Widget child;
  final bool filled;
  final bool destructive;
  final bool expanded;
  final bool haptic;

  @override
  State<IosButton> createState() => _IosButtonState();
}

class _IosButtonState extends State<IosButton> {
  bool _pressed = false;

  bool get _enabled => widget.onPressed != null;

  void _setPressed(bool value) {
    if (!_enabled) return;
    if (_pressed == value) return;
    setState(() => _pressed = value);
  }

  void _handleTap() {
    if (!_enabled) return;
    if (widget.haptic) {
      HapticFeedback.lightImpact();
    }
    widget.onPressed!();
  }

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    final bg = !_enabled
        ? palette.surfaceSecondary
        : widget.destructive
            ? palette.danger
            : widget.filled
                ? palette.primary
                : palette.surfaceSecondary;
    final fg = widget.filled || widget.destructive
        ? palette.onPrimary
        : palette.textPrimary;

    final label = DefaultTextStyle(
      style: AppTextStyle.label(context).copyWith(color: fg),
      child: IconTheme(
        data: IconThemeData(color: fg, size: 20),
        child: widget.child,
      ),
    );

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTapDown: (_) => _setPressed(true),
      onTapUp: (_) => _setPressed(false),
      onTapCancel: () => _setPressed(false),
      onTap: _handleTap,
      child: AnimatedScale(
        scale: _pressed ? 0.96 : 1,
        duration: Duration(milliseconds: AppDuration.micro),
        curve: Curves.easeOut,
        child: AnimatedOpacity(
          opacity: _pressed ? 0.9 : 1,
          duration: Duration(milliseconds: AppDuration.micro),
          curve: Curves.easeOut,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: kMinTapTarget),
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: bg,
                borderRadius: BorderRadius.circular(AppRadius.radiusFull),
              ),
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpace.space5,
                  vertical: AppSpace.space3,
                ),
                child: widget.expanded
                    ? SizedBox(
                        width: double.infinity,
                        child: Center(child: label),
                      )
                    : label,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
