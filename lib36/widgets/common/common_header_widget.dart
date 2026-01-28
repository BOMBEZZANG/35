import 'package:flutter/material.dart';

class CommonHeaderWidget extends StatelessWidget {
  final String title;
  final String? subtitle;
  final VoidCallback? onBackPressed;
  final VoidCallback? onHomePressed;
  final bool showHomeButton;
  final bool showBackButton;

  const CommonHeaderWidget({
    Key? key,
    required this.title,
    this.subtitle,
    this.onBackPressed,
    this.onHomePressed,
    this.showHomeButton = true,
    this.showBackButton = true,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        children: [
          if (showBackButton)
            GestureDetector(
              onTap: onBackPressed ?? () => Navigator.pop(context),
              child: Container(
                padding: EdgeInsets.all(5),
                decoration: BoxDecoration(
                  color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.white.withOpacity(0.7),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1)),
                ),
                child: Icon(
                  Icons.arrow_back_ios_rounded,
                  color: isDarkMode ? Colors.white : Colors.black87,
                  size: 16,
                ),
              ),
            ),
          if (showBackButton) SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    color: isDarkMode ? Colors.white : Colors.black87,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.3,
                  ),
                ),
                if (subtitle != null)
                  Text(
                    subtitle!,
                    style: TextStyle(
                      color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54,
                      fontSize: 11,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
              ],
            ),
          ),
          if (showHomeButton)
            GestureDetector(
              onTap: onHomePressed ?? () => Navigator.pushNamedAndRemoveUntil(context, '/', (route) => false),
              child: Container(
                padding: EdgeInsets.all(5),
                decoration: BoxDecoration(
                  color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.white.withOpacity(0.7),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1)),
                ),
                child: Icon(
                  Icons.home_rounded,
                  color: isDarkMode ? Colors.white : Colors.black87,
                  size: 18,
                ),
              ),
            ),
        ],
      ),
    );
  }
}