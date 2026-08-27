import 'package:flutter/material.dart';
import '../../core/theme/apex_colors.dart';
import '../../core/theme/apex_typography.dart';
import '../../core/utils/formatters.dart';
import '../../data/models/signal_model.dart';
import 'gemini_rationale_sheet.dart';

class SignalCard extends StatelessWidget {
  final SignalModel signal;
  final bool isSelected;
  final VoidCallback? onTap;

  const SignalCard({
    super.key,
    required this.signal,
    this.isSelected = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isBuy = signal.isBuy;
    final sideColor = isBuy ? ApexColors.success : ApexColors.danger;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: isSelected ? ApexColors.surfaceHover : ApexColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? ApexColors.accent : ApexColors.border,
            width: isSelected ? 1.5 : 1.0,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Top Row: Symbol, Side badge, Timeframe, AI Score
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Text(signal.symbol, style: ApexTypography.monoMedium),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: sideColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: sideColor.withValues(alpha: 0.3)),
                      ),
                      child: Text(
                        signal.side,
                        style: ApexTypography.monoMicro.copyWith(
                          color: sideColor,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(signal.timeframe, style: ApexTypography.monoMicro),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(
                    color: ApexColors.aiPurple.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: ApexColors.aiPurple.withValues(alpha: 0.3)),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.auto_awesome, size: 10, color: ApexColors.aiPurple),
                      const SizedBox(width: 4),
                      Text(
                        '${signal.quantScore.toStringAsFixed(0)}% AI',
                        style: ApexTypography.monoMicro.copyWith(
                          color: ApexColors.aiPurple,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Middle: Entry, Dynamic SL, Multi-Targets TP1/TP2/TP3
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: ApexColors.background,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: ApexColors.border.withValues(alpha: 0.6)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _priceCol("ENTRY", Formatters.price(signal.entry), ApexColors.textPrimary),
                  _divider(),
                  _priceCol("STOP LOSS", Formatters.price(signal.sl), ApexColors.danger),
                  _divider(),
                  _priceCol("TP1 (1:1.5)", Formatters.price(signal.tp1), ApexColors.success),
                  if (signal.tp2 > 0) ...[
                    _divider(),
                    _priceCol("TP2 (Main)", Formatters.price(signal.tp2), ApexColors.accent),
                  ],
                ],
              ),
            ),
            const SizedBox(height: 10),

            // Bottom Action Row: Setup Type & Gemini Breakdown Sheet trigger
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Row(
                  children: [
                    Text("Setup: ", style: ApexTypography.bodySmall),
                    Text(signal.setupType, style: ApexTypography.monoMicro.copyWith(color: ApexColors.textPrimary)),
                  ],
                ),
                TextButton.icon(
                  onPressed: () {
                    showModalBottomSheet(
                      context: context,
                      backgroundColor: Colors.transparent,
                      isScrollControlled: true,
                      builder: (_) => GeminiRationaleSheet(signal: signal),
                    );
                  },
                  icon: const Icon(Icons.insights, size: 13, color: ApexColors.accent),
                  label: Text("Gemini Rationale", style: ApexTypography.monoMicro.copyWith(color: ApexColors.accent)),
                  style: TextButton.styleFrom(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _priceCol(String label, String val, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: ApexTypography.monoMicro.copyWith(fontSize: 8, color: ApexColors.textMuted)),
        const SizedBox(height: 2),
        Text(r'$' + val, style: ApexTypography.monoSmall.copyWith(color: color, fontWeight: FontWeight.w700)),
      ],
    );
  }

  Widget _divider() {
    return Container(height: 24, width: 1, color: ApexColors.border.withValues(alpha: 0.5));
  }
}