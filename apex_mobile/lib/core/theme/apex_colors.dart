import 'package:flutter/material.dart';

class ApexColors {
  // Deep Institutional Dark Palette
  static const Color background = Color(0xFF0E1116);
  static const Color bgSecondary = Color(0xFF151A21);
  static const Color surface = Color(0xFF1B222C);
  static const Color surfaceHover = Color(0xFF242D39);
  static const Color border = Color(0xFF2C3643);
  static const Color divider = Color(0xFF3A4655);

  // Typography Colors
  static const Color textPrimary = Color(0xFFF5F7FA);
  static const Color textSecondary = Color(0xFFB5BDC8);
  static const Color textMuted = Color(0xFF7C8796);
  static const Color textDisabled = Color(0xFF596272);

  // Brand & Trading Accents
  static const Color accent = Color(0xFF5EA8FF); // Apex Cyan/Blue
  static const Color success = Color(0xFF22C55E); // Bullish Green
  static const Color danger = Color(0xFFEF4444); // Bearish Red
  static const Color warning = Color(0xFFF59E0B); // Amber
  static const Color info = Color(0xFF38BDF8); // Sky Blue
  static const Color aiPurple = Color(0xFF8B5CF6); // Gemini AI Purple

  // Gradients
  static const LinearGradient cardGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF1E2631), Color(0xFF151A21)],
  );

  static const LinearGradient aiGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF8B5CF6), Color(0xFF5EA8FF)],
  );

  static const LinearGradient successGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFF22C55E), Color(0xFF10B981)],
  );

  static const LinearGradient dangerGradient = LinearGradient(
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
    colors: [Color(0xFFEF4444), Color(0xFFDC2626)],
  );
}