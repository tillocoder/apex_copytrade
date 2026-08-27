import 'package:flutter/material.dart';
import '../../core/theme/apex_colors.dart';
import '../../core/theme/apex_typography.dart';
import '../../core/utils/formatters.dart';
import '../../data/models/position_model.dart';

class PositionCard extends StatelessWidget {
  final PositionModel position;
  final VoidCallback? onPanicClose;

  const PositionCard({
    super.key,
    required this.position,
    this.onPanicClose,
  });

  @override
  Widget build(BuildContext context) {
    final isBuy = position.isBuy;
    final isProfit = position.isProfit;
    final pnlColor = isProfit ? ApexColors.success : ApexColors.danger;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: ApexColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: ApexColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header: Symbol, Leverage, PnL
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Text(position.symbol, style: ApexTypography.monoMedium),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: (isBuy ? ApexColors.success : ApexColors.danger).withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      "${position.side} ${position.leverage}X",
                      style: ApexTypography.monoMicro.copyWith(
                        color: isBuy ? ApexColors.success : ApexColors.danger,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    Formatters.currency(position.unrealizedPnl),
                    style: ApexTypography.monoMedium.copyWith(
                      color: pnlColor,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    Formatters.percent(position.unrealizedPnlPercent),
                    style: ApexTypography.monoMicro.copyWith(color: pnlColor),
                  ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Price Metrics Grid
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: ApexColors.background,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _metric("Entry", Formatters.price(position.entryPrice)),
                _metric("Current", Formatters.price(position.currentPrice)),
                _metric("Stop Loss", Formatters.price(position.sl), ApexColors.danger),
                _metric("TP1", Formatters.price(position.tp1), ApexColors.success),
              ],
            ),
          ),
          const SizedBox(height: 10),

          // Footer info + Quick Actions
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                "Margin: \${Formatters.currency(position.marginUsed)} | \${position.duration}",
                style: ApexTypography.monoMicro,
              ),
              if (onPanicClose != null)
                TextButton(
                  onPressed: onPanicClose,
                  style: TextButton.styleFrom(
                    backgroundColor: ApexColors.danger.withValues(alpha: 0.15),
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    minimumSize: Size.zero,
                  ),
                  child: Text(
                    "Close Trade",
                    style: ApexTypography.monoMicro.copyWith(
                      color: ApexColors.danger,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _metric(String label, String val, [Color? color]) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: ApexTypography.monoMicro.copyWith(fontSize: 8)),
        const SizedBox(height: 2),
        Text(r'$' + val, style: ApexTypography.monoSmall.copyWith(color: color ?? ApexColors.textPrimary)),
      ],
    );
  }
}