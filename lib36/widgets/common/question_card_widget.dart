import 'package:flutter/material.dart';

class QuestionCardWidget extends StatelessWidget {
  final String questionText;
  final int? questionNumber;
  final Widget? child;
  final EdgeInsetsGeometry? margin;
  final EdgeInsetsGeometry? padding;
  final Color? backgroundColor;
  final Color? borderColor;
  final bool showQuestionNumber;
  final VoidCallback? onTap;

  const QuestionCardWidget({
    Key? key,
    required this.questionText,
    this.questionNumber,
    this.child,
    this.margin,
    this.padding,
    this.backgroundColor,
    this.borderColor,
    this.showQuestionNumber = true,
    this.onTap,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: margin ?? EdgeInsets.only(bottom: 12),
        decoration: BoxDecoration(
          color: backgroundColor ?? (isDarkMode 
              ? Colors.white.withOpacity(0.1) 
              : Colors.white.withOpacity(0.9)),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: borderColor ?? (isDarkMode 
                ? Colors.white.withOpacity(0.15) 
                : Colors.black.withOpacity(0.08)),
          ),
          boxShadow: [
            BoxShadow(
              color: isDarkMode 
                  ? Colors.black.withOpacity(0.3) 
                  : Colors.black.withOpacity(0.08),
              blurRadius: 8,
              offset: Offset(0, 2),
            ),
          ],
        ),
        child: Padding(
          padding: padding ?? EdgeInsets.all(14.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (showQuestionNumber && questionNumber != null)
                _buildQuestionHeader(isDarkMode),
              _buildQuestionText(isDarkMode),
              if (child != null) ...[
                SizedBox(height: 12),
                child!,
              ],
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildQuestionHeader(bool isDarkMode) {
    return Container(
      margin: EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Container(
            padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Color(0xFF8E9AAF).withOpacity(0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              '문제 $questionNumber',
              style: TextStyle(
                color: Color(0xFF8E9AAF),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildQuestionText(bool isDarkMode) {
    return Text(
      questionText,
      style: TextStyle(
        color: isDarkMode ? Colors.white.withOpacity(0.9) : Colors.black87,
        fontSize: 15,
        fontWeight: FontWeight.w500,
        height: 1.4,
        letterSpacing: 0.2,
      ),
    );
  }
}

class OptionSelectionWidget extends StatelessWidget {
  final List<String> options;
  final String? selectedOption;
  final Function(String)? onOptionSelected;
  final bool showCorrectAnswer;
  final String? correctAnswer;
  final bool isDarkMode;

  const OptionSelectionWidget({
    Key? key,
    required this.options,
    this.selectedOption,
    this.onOptionSelected,
    this.showCorrectAnswer = false,
    this.correctAnswer,
    required this.isDarkMode,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isDarkMode 
              ? Colors.white.withOpacity(0.1) 
              : Colors.black.withOpacity(0.08),
        ),
      ),
      child: Column(
        children: options.asMap().entries.map((entry) {
          final index = entry.key;
          final option = entry.value;
          final isSelected = selectedOption == option;
          final isCorrect = showCorrectAnswer && correctAnswer == option;
          final isWrong = showCorrectAnswer && isSelected && correctAnswer != option;
          
          return Column(
            children: [
              _buildOptionRow(option, isSelected, isCorrect, isWrong),
              if (index < options.length - 1) _buildDividerLine(),
            ],
          );
        }).toList(),
      ),
    );
  }

  Widget _buildOptionRow(String option, bool isSelected, bool isCorrect, bool isWrong) {
    Color? backgroundColor;
    Color? textColor;
    Color? borderColor;

    if (showCorrectAnswer) {
      if (isCorrect) {
        backgroundColor = Colors.green.withOpacity(0.1);
        textColor = Colors.green;
        borderColor = Colors.green.withOpacity(0.3);
      } else if (isWrong) {
        backgroundColor = Colors.red.withOpacity(0.1);
        textColor = Colors.red;
        borderColor = Colors.red.withOpacity(0.3);
      }
    } else if (isSelected) {
      backgroundColor = Color(0xFF8E9AAF).withOpacity(0.1);
      textColor = Color(0xFF8E9AAF);
      borderColor = Color(0xFF8E9AAF).withOpacity(0.3);
    }

    return GestureDetector(
      onTap: onOptionSelected != null ? () => onOptionSelected!(option) : null,
      child: Container(
        width: double.infinity,
        padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        decoration: BoxDecoration(
          color: backgroundColor,
          border: borderColor != null ? Border.all(color: borderColor, width: 1) : null,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          option,
          style: TextStyle(
            color: textColor ?? (isDarkMode ? Colors.white.withOpacity(0.9) : Colors.black87),
            fontSize: 14,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }

  Widget _buildDividerLine() {
    return Container(
      height: 1,
      color: isDarkMode 
          ? Colors.white.withOpacity(0.05) 
          : Colors.black.withOpacity(0.05),
    );
  }
}