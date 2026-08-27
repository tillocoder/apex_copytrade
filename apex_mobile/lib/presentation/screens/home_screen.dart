import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/apex_colors.dart';
import '../../core/theme/apex_typography.dart';
import '../../core/utils/formatters.dart';
import '../../state/terminal_provider.dart';
import '../../state/signals_provider.dart';
import '../../state/trades_provider.dart';
import '../widgets/metric_card.dart';
import '../widgets/signal_card.dart';
import '../widgets/position_card.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final terminal = context.watch<TerminalProvider>();
    final signals = context.watch<SignalsProvider>();
    final trades = context.watch<TradesProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.flash_on, color: ApexColors.accent, size: 20),
            const SizedBox(width: 6),
            Text("APEX TERMINAL", style: ApexTypography.headingMedium),
          ],
        ),
        actions: [
          Container(
            margin: const EdgeInsets.only(right: 12),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: terminal.health.isHealthy ? ApexColors.success.withValues(alpha: 0.15) : ApexColors.danger.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: terminal.health.isHealthy ? ApexColors.success.withValues(alpha: 0.4) : ApexColors.danger.withValues(alpha: 0.4),
              ),
            ),
            child: Row(
              children: [
                Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: terminal.health.isHealthy ? ApexColors.success : ApexColors.danger,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 5),
                Text(
                  "\${terminal.health.vpsLatency}ms",
                  style: ApexTypography.monoMicro.copyWith(
                    color: terminal.health.isHealthy ? ApexColors.success : ApexColors.danger,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          await terminal.refreshAll();
          await signals.loadSignals();
          await trades.loadPositions();
        },
        color: ApexColors.accent,
        backgroundColor: ApexColors.surface,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Equity Hero Card
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                gradient: ApexColors.cardGradient,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: ApexColors.border, width: 1.2),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text("PORTFOLIO EQUITY", style: ApexTypography.monoMicro.copyWith(letterSpacing: 1.0)),
                      Text(
                        terminal.portfolio.pnlPercent >= 0 ? "BULLISH ENGINE" : "DEFENSIVE",
                        style: ApexTypography.monoMicro.copyWith(
                          color: terminal.portfolio.pnlPercent >= 0 ? ApexColors.success : ApexColors.warning,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    Formatters.currency(terminal.portfolio.currentEquity),
                    style: ApexTypography.monoLarge.copyWith(fontSize: 28, color: ApexColors.textPrimary),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      Icon(
                        terminal.portfolio.totalRealizedPnl >= 0 ? Icons.trending_up : Icons.trending_down,
                        size: 16,
                        color: terminal.portfolio.totalRealizedPnl >= 0 ? ApexColors.success : ApexColors.danger,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        "\${Formatters.currency(terminal.portfolio.totalRealizedPnl)} (\${Formatters.percent(terminal.portfolio.pnlPercent)})",
                        style: ApexTypography.monoSmall.copyWith(
                          color: terminal.portfolio.totalRealizedPnl >= 0 ? ApexColors.success : ApexColors.danger,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // 4 Stats Grid: Win Rate, Profit Factor, Active Trades, Open Signals
            GridView.count(
              crossAxisCount: 2,
              crossAxisSpacing: 12,
              mainAxisSpacing: 12,
              childAspectRatio: 1.6,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              children: [
                MetricCard(
                  title: "Win Rate",
                  value: "\${terminal.portfolio.winRate.toStringAsFixed(1)}%",
                  subtitle: "\${terminal.portfolio.winningTrades}W / \${terminal.portfolio.losingTrades}L",
                  icon: Icons.emoji_events,
                  accentColor: ApexColors.accent,
                ),
                MetricCard(
                  title: "Profit Factor",
                  value: "\${terminal.portfolio.profitFactor.toStringAsFixed(2)}x",
                  subtitle: "Max DD: \${terminal.portfolio.maxDrawdown.toStringAsFixed(1)}%",
                  icon: Icons.balance,
                  accentColor: ApexColors.warning,
                ),
                MetricCard(
                  title: "Open Positions",
                  value: "\${trades.openPositions.length}",
                  subtitle: "Prop 10K Engine",
                  icon: Icons.layers,
                  accentColor: ApexColors.success,
                ),
                MetricCard(
                  title: "Live AI Signals",
                  value: "\${signals.activeSignals.length}",
                  subtitle: "Gemini 2.5 Flash",
                  icon: Icons.auto_awesome,
                  accentColor: ApexColors.aiPurple,
                ),
              ],
            ),
            const SizedBox(height: 20),

            // Live Positions Section
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text("ACTIVE POSITIONS", style: ApexTypography.monoMicro.copyWith(letterSpacing: 1.0)),
                Text("\${trades.openPositions.length} Open", style: ApexTypography.monoMicro.copyWith(color: ApexColors.accent)),
              ],
            ),
            const SizedBox(height: 10),
            if (trades.openPositions.isEmpty)
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: ApexColors.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: ApexColors.border),
                ),
                child: Center(
                  child: Text("No open positions. Engine scanning market...", style: ApexTypography.bodyMedium),
                ),
              )
            else
              ...trades.openPositions.map((pos) => PositionCard(
                position: pos,
                onPanicClose: () => trades.panicCloseAll(),
              )),
            const SizedBox(height: 20),

            // Live Signals Section
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text("LATEST AI SIGNALS", style: ApexTypography.monoMicro.copyWith(letterSpacing: 1.0)),
                Text("\${signals.activeSignals.length} Active", style: ApexTypography.monoMicro.copyWith(color: ApexColors.aiPurple)),
              ],
            ),
            const SizedBox(height: 10),
            if (signals.activeSignals.isEmpty)
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: ApexColors.surface,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: ApexColors.border),
                ),
                child: Center(
                  child: Text("No active signals right now. Next scan in 5 min.", style: ApexTypography.bodyMedium),
                ),
              )
            else
              ...signals.activeSignals.map((sig) => SignalCard(signal: sig)),
          ],
        ),
      ),
    );
  }
}