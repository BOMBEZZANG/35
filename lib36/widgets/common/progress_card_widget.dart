import 'package:flutter/material.dart';

class ProgressCardWidget extends StatelessWidget {
  final int totalCount;
  final int answeredCount;
  final int correctCount;
  final int wrongCount;
  final bool isExpanded;
  final VoidCallback? onToggleExpanded;
  final EdgeInsetsGeometry? margin;
  final EdgeInsetsGeometry? padding;
  final bool showDetails;

  const ProgressCardWidget({
    Key? key,
    required this.totalCount,
    required this.answeredCount,
    required this.correctCount,
    required this.wrongCount,
    this.isExpanded = false,
    this.onToggleExpanded,
    this.margin,
    this.padding,
    this.showDetails = true,
  }) : super(key: key);

  double get progress => totalCount == 0 ? 0.0 : (answeredCount / totalCount);

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    
    return Container(
      margin: margin ?? EdgeInsets.symmetric(horizontal: 16, vertical: 3),
      decoration: BoxDecoration(
        color: isDarkMode 
            ? Colors.white.withOpacity(0.05) 
            : Colors.white.withOpacity(0.8),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: isDarkMode 
              ? Colors.white.withOpacity(0.1) 
              : Colors.black.withOpacity(0.05),
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
        padding: padding ?? EdgeInsets.all(16),
        child: Column(
          children: [
            _buildProgressHeader(isDarkMode),
            SizedBox(height: 12),
            _buildProgressBar(isDarkMode),
            if (showDetails && isExpanded) ...[
              SizedBox(height: 12),
              _buildExpandedStats(isDarkMode),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildProgressHeader(bool isDarkMode) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          '진행률',
          style: TextStyle(
            color: isDarkMode ? Colors.white.withOpacity(0.9) : Colors.black87,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        Row(
          children: [
            Text(
              '$answeredCount/$totalCount',
              style: TextStyle(
                color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
            if (onToggleExpanded != null) ...[
              SizedBox(width: 8),
              GestureDetector(
                onTap: onToggleExpanded,
                child: Container(
                  padding: EdgeInsets.all(4),
                  decoration: BoxDecoration(
                    color: Colors.transparent,
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Icon(
                    isExpanded ? Icons.expand_less : Icons.expand_more,
                    color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54,
                    size: 16,
                  ),
                ),
              ),
            ],
          ],
        ),
      ],
    );
  }

  Widget _buildProgressBar(bool isDarkMode) {
    return Column(
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
            value: progress,
            backgroundColor: isDarkMode 
                ? Colors.white.withOpacity(0.1) 
                : Colors.grey.withOpacity(0.2),
            valueColor: AlwaysStoppedAnimation<Color>(
              Color(0xFF8E9AAF),
            ),
            minHeight: 8,
          ),
        ),
        SizedBox(height: 4),
        Text(
          '${(progress * 100).toInt()}% 완료',
          style: TextStyle(
            color: isDarkMode ? Colors.white.withOpacity(0.6) : Colors.black45,
            fontSize: 11,
            fontWeight: FontWeight.w400,
          ),
        ),
      ],
    );
  }

  Widget _buildExpandedStats(bool isDarkMode) {
    return Container(
      padding: EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isDarkMode 
            ? Colors.white.withOpacity(0.05) 
            : Colors.grey.withOpacity(0.05),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildStatItem(
            '정답',
            correctCount.toString(),
            Colors.green,
            isDarkMode,
          ),
          _buildStatItem(
            '오답',
            wrongCount.toString(),
            Colors.red,
            isDarkMode,
          ),
          _buildStatItem(
            '미응답',
            (totalCount - answeredCount).toString(),
            Colors.orange,
            isDarkMode,
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, String value, Color color, bool isDarkMode) {
    return Column(
      children: [
        Container(
          padding: EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: color.withOpacity(0.15),
            shape: BoxShape.circle,
          ),
          child: Text(
            value,
            style: TextStyle(
              color: color,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
        SizedBox(height: 4),
        Text(
          label,
          style: TextStyle(
            color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54,
            fontSize: 10,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }
}