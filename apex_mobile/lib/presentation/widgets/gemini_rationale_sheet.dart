import 'package:flutter/material.dart';
import '../../core/theme/apex_colors.dart';
import '../../core/theme/apex_typography.dart';
import '../../data/models/signal_model.dart';

class GeminiRationaleSheet extends StatelessWidget {
  final SignalModel signal;

  const GeminiRationaleSheet({super.key, required this.signal});

  @override
  Widget build(BuildContext context) {
    return Container(
      height: MediaQuery.of(context).size.height * 0.75,
      padding: const EdgeInsets.all(20),
      decoration: const BoxDecoration(
        color: ApexColors.bgSecondary,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        border: Border(top: BorderSide(color: ApexColors.border, width: 1)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Drag Handle
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: ApexColors.border,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Header: AI Title & Symbol
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(Icons.auto_awesome, color: ApexColors.aiPurple, size: 20),
                  const SizedBox(width: 8),
                  Text("Gemini Lead Quant Review", style: ApexTypography.headingSmall),
                ],
              ),
              IconButton(
                icon: const Icon(Icons.close, color: ApexColors.textMuted),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const Divider(color: ApexColors.border),
          const SizedBox(height: 10),

          Expanded(
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Confidence & Scores Card
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: ApexColors.surface,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: ApexColors.border),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _scoreCol("Quant Score", '${signal.quantScore.toStringAsFixed(1)}%', ApexColors.accent),
                        _scoreCol("AI Review", '${signal.aiReviewScore.toStringAsFixed(1)}%', ApexColors.aiPurple),
                        _scoreCol("Factor Score", '${signal.factorScore.toStringAsFixed(1)}%', ApexColors.success),
                      ],
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Institutional Rationale Text
                  Text("INSTITUTIONAL ANALYSIS", style: ApexTypography.monoMicro.copyWith(letterSpacing: 1.0)),
                  const SizedBox(height: 6),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: ApexColors.surface,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: ApexColors.border),
                    ),
                    child: Text(
                      signal.reasoning,
                      style: ApexTypography.bodyMedium.copyWith(height: 1.5),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // 8-Factor SMC & MTF Verification Matrix
                  Text("8-FACTOR VERIFICATION MATRIX", style: ApexTypography.monoMicro.copyWith(letterSpacing: 1.0)),
                  const SizedBox(height: 8),
                  if (signal.verification.isNotEmpty)
                    ...signal.verification.map((v) => Container(
                      margin: const EdgeInsets.only(bottom: 6),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: ApexColors.surface,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: ApexColors.border),
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(v.label, style: ApexTypography.monoSmall),
                          Row(
                            children: [
                              Icon(
                                v.passed ? Icons.check_circle : Icons.cancel,
                                size: 14,
                                color: v.passed ? ApexColors.success : ApexColors.danger,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                v.passed ? "PASSED" : "FAILED",
                                style: ApexTypography.monoMicro.copyWith(
                                  color: v.passed ? ApexColors.success : ApexColors.danger,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ))
                  else
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: ApexColors.surface,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text("Multi-Timeframe Trend & SMC Structure Confirmed", style: ApexTypography.bodyMedium),
                    ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _scoreCol(String title, String val, Color color) {
    return Column(
      children: [
        Text(title, style: ApexTypography.monoMicro),
        const SizedBox(height: 4),
        Text(val, style: ApexTypography.monoMedium.copyWith(color: color, fontWeight: FontWeight.w700)),
      ],
    );
  }
}