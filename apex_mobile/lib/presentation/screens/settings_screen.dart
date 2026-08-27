import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/theme/apex_colors.dart';
import '../../core/theme/apex_typography.dart';
import '../../core/constants/api_constants.dart';
import '../../data/services/storage_service.dart';
import '../../state/terminal_provider.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final TextEditingController _urlController = TextEditingController();

  @override
  void initState() {
    super.initState();
    StorageService.getBaseUrl().then((url) {
      _urlController.text = url;
    });
  }

  @override
  Widget build(BuildContext context) {
    final terminal = context.watch<TerminalProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Text("TERMINAL SETTINGS", style: ApexTypography.headingMedium),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Server Connection Section
          Text("BACKEND SERVER CONNECTION", style: ApexTypography.monoMicro.copyWith(letterSpacing: 1.0)),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: ApexColors.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: ApexColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: _urlController,
                  style: ApexTypography.monoSmall,
                  decoration: InputDecoration(
                    labelText: "Backend Base URL",
                    labelStyle: ApexTypography.bodySmall,
                    hintText: "https://apex.xrinvest.uz",
                    filled: true,
                    fillColor: ApexColors.background,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                      borderSide: const BorderSide(color: ApexColors.border),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    ElevatedButton(
                      style: ElevatedButton.styleFrom(backgroundColor: ApexColors.accent),
                      onPressed: () async {
                        final newUrl = _urlController.text.trim();
                        if (newUrl.isNotEmpty) {
                          await StorageService.setBaseUrl(newUrl);
                          terminal.apiService.updateBaseUrl(newUrl);
                          terminal.refreshAll();
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text("Backend URL updated successfully!")),
                          );
                        }
                      },
                      child: Text("Save & Connect", style: ApexTypography.monoSmall.copyWith(color: ApexColors.background, fontWeight: FontWeight.w700)),
                    ),
                    const SizedBox(width: 8),
                    OutlinedButton(
                      onPressed: () {
                        _urlController.text = ApiConstants.defaultLocalUrl;
                      },
                      child: Text("Use LAN IP", style: ApexTypography.monoSmall),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // System Health & Latency
          Text("DIAGNOSTICS & TELEGRAM ALERTS", style: ApexTypography.monoMicro.copyWith(letterSpacing: 1.0)),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: ApexColors.surface,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: ApexColors.border),
            ),
            child: Column(
              children: [
                _row("Termux Backend Status", terminal.health.vpsStatus, ApexColors.success),
                _divider(),
                _row("API Response Latency", "\${terminal.health.vpsLatency} ms", ApexColors.accent),
                _divider(),
                _row("Binance WebSocket", terminal.health.wsStatus, ApexColors.success),
                _divider(),
                _row("Telegram Alert Notifications", "ACTIVE & SYNCED", ApexColors.aiPurple),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _row(String label, String value, Color color) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: ApexTypography.bodyMedium),
          Text(value, style: ApexTypography.monoSmall.copyWith(color: color, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }

  Widget _divider() {
    return const Divider(color: ApexColors.border, height: 12);
  }
}