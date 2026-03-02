import 'package:flutter/material.dart';

class SaveTuneTheme {
  static const Color primaryColor = Color(0xFF1DB954);
  static const Color accentColor = Color(0xFF1ED760);
  static const Color surfaceColor = Color(0xFF282828);
  static const Color backgroundColor = Color(0xFF121212);
  static const Color cardColor = Color(0xFF181818);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFFB3B3B3);

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      primaryColor: primaryColor,
      scaffoldBackgroundColor: backgroundColor,
      appBarTheme: const AppBarTheme(
        backgroundColor: backgroundColor,
        elevation: 0,
      ),
      colorScheme: const ColorScheme.dark(
        primary: primaryColor,
        secondary: accentColor,
        surface: surfaceColor,
      ),
    );
  }
}
