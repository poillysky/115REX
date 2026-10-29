import 'package:flutter/material.dart';
import '../design_system/rex_design_tokens.dart';

class RexPrimaryButton extends StatelessWidget {
  const RexPrimaryButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.isLoading = false,
    this.icon,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool isLoading;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 54,
      child: FilledButton(
        onPressed: isLoading ? null : onPressed,
        style: FilledButton.styleFrom(
          backgroundColor: RexColors.brand,
          foregroundColor: Colors.white,
          disabledBackgroundColor: RexColors.brand.withValues(alpha: .45),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(RexRadius.lg),
          ),
          textStyle: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
        ),
        child: isLoading
            ? const SizedBox(
                width: 21, height: 21,
                child: CircularProgressIndicator(
                  strokeWidth: 2.2, color: Colors.white,
                ),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  if (icon != null) ...[
                    Icon(icon, size: 20),
                    const SizedBox(width: RexSpacing.x2),
                  ],
                  Text(label),
                ],
              ),
      ),
    );
  }
}
