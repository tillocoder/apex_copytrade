import 'package:flutter/material.dart';
import '../../core/theme/apex_colors.dart';
import '../../core/theme/apex_typography.dart';

class MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final String? subtitle;
  final IconData? icon;
  final Color? accentColor;
  final bool isProfit;

  const MetricCard({
    super.key,
    required this.title,
    required this.value,
    this.subtitle,
    this.icon,
    this.accentColor,
    this.isProfit = true,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveAccent = accentColor ?? (isProfit ? ApexColors.success : ApexColors.danger);

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: ApexColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: ApexColors.border, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                title.toUpperCase(),
                style: ApexTypography.monoMicro.copyWith(letterSpacing: 0.8),
              ),
              if (icon != null)
                Icon(icon, size: 16, color: effectiveAccent),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: ApexTypography.monoLarge.copyWith(
              color: accentColor ?? (isProfit ? ApexColors.textPrimary : ApexColors.danger),
            ),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: 4),
            Text(
              subtitle!,
              style: ApexTypography.monoMicro.copyWith(
                color: isProfit ? ApexColors.success : ApexColors.danger,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ],
      ),
    );
  }
}