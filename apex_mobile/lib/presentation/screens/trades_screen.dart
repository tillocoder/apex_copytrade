import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/apex_colors.dart';
import '../../core/theme/apex_typography.dart';
import '../../state/trades_provider.dart';
import '../widgets/position_card.dart';

class TradesScreen extends StatelessWidget {
  const TradesScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final trades = context.watch<TradesProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Text("POSITION COMMAND", style: ApexTypography.headingMedium),
        actions: [
          if (trades.openPositions.isNotEmpty)
            TextButton.icon(
              onPressed: () {
                showDialog(
                  context: context,
                  builder: (_) => AlertDialog(
                    backgroundColor: ApexColors.bgSecondary,
                    title: Text("Panic Close All Trades?", style: ApexTypography.headingSmall.copyWith(color: ApexColors.danger)),
                    content: Text("This will immediately execute market exits on all open Binance positions.", style: ApexTypography.bodyMedium),
                    actions: [
                      TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(backgroundColor: ApexColors.danger),
                        onPressed: () {
                          Navigator.pop(context);
                          trades.panicCloseAll();
                        },
                        child: const Text("Confirm Close All"),
                      ),
                    ],
                  ),
                );
              },
              icon: const Icon(Icons.warning, color: ApexColors.danger, size: 16),
              label: Text("Panic Close", style: ApexTypography.monoMicro.copyWith(color: ApexColors.danger, fontWeight: FontWeight.w700)),
            ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => trades.loadPositions(),
        color: ApexColors.accent,
        backgroundColor: ApexColors.surface,
        child: trades.openPositions.isEmpty
            ? Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(Icons.layers_clear, size: 36, color: ApexColors.textMuted),
                    const SizedBox(height: 12),
                    Text("No Live Open Positions", style: ApexTypography.headingSmall),
                    const SizedBox(height: 6),
                    Text("Engine is waiting for high-probability confluence.", style: ApexTypography.bodySmall),
                  ],
                ),
              )
            : ListView.builder(
                padding: const EdgeInsets.all(16),
                itemCount: trades.openPositions.length,
                itemBuilder: (_, i) => PositionCard(
                  position: trades.openPositions[i],
                  onPanicClose: () => trades.panicCloseAll(),
                ),
              ),
      ),
    );
  }
}