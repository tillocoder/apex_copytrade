import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/apex_colors.dart';
import '../../core/theme/apex_typography.dart';
import '../../state/signals_provider.dart';
import '../widgets/signal_card.dart';

class SignalsScreen extends StatefulWidget {
  const SignalsScreen({super.key});

  @override
  State<SignalsScreen> createState() => _SignalsScreenState();
}

class _SignalsScreenState extends State<SignalsScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  Widget build(BuildContext context) {
    final signals = context.watch<SignalsProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Text("AI SIGNAL CENTER", style: ApexTypography.headingMedium),
        actions: [
          IconButton(
            icon: signals.isScanning
                ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: ApexColors.accent))
                : const Icon(Icons.refresh, color: ApexColors.accent),
            onPressed: signals.isScanning ? null : () => signals.triggerScanNow(),
          ),
        ],
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: ApexColors.accent,
          labelColor: ApexColors.textPrimary,
          unselectedLabelColor: ApexColors.textMuted,
          labelStyle: ApexTypography.monoSmall.copyWith(fontWeight: FontWeight.w700),
          tabs: [
            Tab(text: "Active (\${signals.activeSignals.length})"),
            Tab(text: "History (\${signals.historySignals.length})"),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          // Active Signals
          RefreshIndicator(
            onRefresh: () => signals.loadSignals(),
            color: ApexColors.accent,
            backgroundColor: ApexColors.surface,
            child: signals.activeSignals.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.auto_awesome, size: 36, color: ApexColors.aiPurple),
                        const SizedBox(height: 12),
                        Text("No Active Signals", style: ApexTypography.headingSmall),
                        const SizedBox(height: 6),
                        Text("Gemini AI scans every 5 min. Pull down to refresh.", style: ApexTypography.bodySmall),
                      ],
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: signals.activeSignals.length,
                    itemBuilder: (_, i) => SignalCard(signal: signals.activeSignals[i]),
                  ),
          ),

          // History Signals
          RefreshIndicator(
            onRefresh: () => signals.loadSignals(),
            color: ApexColors.accent,
            backgroundColor: ApexColors.surface,
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: signals.historySignals.length,
              itemBuilder: (_, i) => SignalCard(signal: signals.historySignals[i]),
            ),
          ),
        ],
      ),
    );
  }
}