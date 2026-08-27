import 'package:flutter/material.dart';
import 'apex_colors.dart';
import 'apex_typography.dart';

class ApexTheme {
  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: ApexColors.background,
      primaryColor: ApexColors.accent,
      cardColor: ApexColors.surface,
      dividerColor: ApexColors.border,
      
      appBarTheme: AppBarTheme(
        backgroundColor: ApexColors.bgSecondary,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: ApexTypography.headingMedium,
        iconTheme: const IconThemeData(color: ApexColors.textPrimary),
        shape: const Border(
          bottom: BorderSide(color: ApexColors.border, width: 1),
        ),
      ),

      bottomNavigationBarTheme: const BottomNavigationBarThemeData(
        backgroundColor: ApexColors.bgSecondary,
        selectedItemColor: ApexColors.accent,
        unselectedItemColor: ApexColors.textMuted,
        type: BottomNavigationBarType.fixed,
        elevation: 10,
      ),

      cardTheme: CardThemeData(
        color: ApexColors.surface,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: ApexColors.border, width: 1),
        ),
      ),

      snackBarTheme: SnackBarThemeData(
        backgroundColor: ApexColors.surface,
        contentTextStyle: ApexTypography.bodyMedium.copyWith(color: ApexColors.textPrimary),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: ApexColors.border, width: 1),
        ),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}