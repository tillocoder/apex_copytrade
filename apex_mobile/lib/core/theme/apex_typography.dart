import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'apex_colors.dart';

class ApexTypography {
  // General UI Sans Typography (Inter)
  static TextStyle headingLarge = GoogleFonts.inter(
    fontSize: 22,
    fontWeight: FontWeight.w700,
    color: ApexColors.textPrimary,
    letterSpacing: -0.5,
  );

  static TextStyle headingMedium = GoogleFonts.inter(
    fontSize: 18,
    fontWeight: FontWeight.w600,
    color: ApexColors.textPrimary,
    letterSpacing: -0.3,
  );

  static TextStyle headingSmall = GoogleFonts.inter(
    fontSize: 15,
    fontWeight: FontWeight.w600,
    color: ApexColors.textPrimary,
  );

  static TextStyle bodyLarge = GoogleFonts.inter(
    fontSize: 14,
    fontWeight: FontWeight.w400,
    color: ApexColors.textPrimary,
  );

  static TextStyle bodyMedium = GoogleFonts.inter(
    fontSize: 13,
    fontWeight: FontWeight.w400,
    color: ApexColors.textSecondary,
  );

  static TextStyle bodySmall = GoogleFonts.inter(
    fontSize: 11,
    fontWeight: FontWeight.w400,
    color: ApexColors.textMuted,
  );

  // Financial & Terminal Monospace Typography (JetBrains Mono)
  static TextStyle monoLarge = GoogleFonts.jetBrainsMono(
    fontSize: 20,
    fontWeight: FontWeight.w700,
    color: ApexColors.textPrimary,
  );

  static TextStyle monoMedium = GoogleFonts.jetBrainsMono(
    fontSize: 14,
    fontWeight: FontWeight.w600,
    color: ApexColors.textPrimary,
  );

  static TextStyle monoSmall = GoogleFonts.jetBrainsMono(
    fontSize: 12,
    fontWeight: FontWeight.w500,
    color: ApexColors.textSecondary,
  );

  static TextStyle monoMicro = GoogleFonts.jetBrainsMono(
    fontSize: 10,
    fontWeight: FontWeight.w500,
    color: ApexColors.textMuted,
  );
}