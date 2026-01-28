import 'package:flutter/material.dart';

class ThemedBackgroundWidget extends StatelessWidget {
  final Widget child;
  final bool isDarkMode;
  final List<Color>? customLightColors;
  final List<Color>? customDarkColors;
  final AlignmentGeometry? begin;
  final AlignmentGeometry? end;

  const ThemedBackgroundWidget({
    Key? key,
    required this.child,
    bool? isDarkMode,
    this.customLightColors,
    this.customDarkColors,
    this.begin,
    this.end,
  }) : isDarkMode = isDarkMode ?? false, super(key: key);

  static const List<Color> defaultLightColors = [
    Color(0xFFF5F7FA),
    Color(0xFFE8ECF0),
    Color(0xFFDDE4EA),
  ];

  static const List<Color> defaultDarkColors = [
    Color(0xFF2C2C2C),
    Color(0xFF3E3E3E),
    Color(0xFF4A4A4A),
  ];

  @override
  Widget build(BuildContext context) {
    final actualIsDarkMode = isDarkMode || Theme.of(context).brightness == Brightness.dark;
    
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: actualIsDarkMode
              ? (customDarkColors ?? defaultDarkColors)
              : (customLightColors ?? defaultLightColors),
          begin: begin ?? Alignment.topLeft,
          end: end ?? Alignment.bottomRight,
        ),
      ),
      child: child,
    );
  }
}