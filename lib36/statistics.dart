import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:table_calendar/table_calendar.dart';
// import 'database_helper.dart'; // 직접적인 DB 호출은 없으므로 주석 처리 (데이터는 다른 곳에서 이미 저장됨)
import 'widgets/common/index.dart';
import 'constants.dart';
import 'home.dart'; // reverseRoundMapping, categories 등

// 학습 기록 데이터 모델
class LearningSession {
  final DateTime date;
  final String type; // "Yearly", "Category", "OX", "Random"
  final String identifier; // 예: "2020년 8월", "일반화학", "OX 전체", "랜덤 일반화학"
  final int attempted;
  final int correct;

  LearningSession({
    required this.date,
    required this.type,
    required this.identifier,
    required this.attempted,
    required this.correct,
  });

  factory LearningSession.fromJson(Map<String, dynamic> json) {
    return LearningSession(
      date: DateTime.parse(json['date']),
      type: json['type'],
      identifier: json['identifier'],
      attempted: json['attempted'],
      correct: json['correct'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'date': date.toIso8601String(),
      'type': type,
      'identifier': identifier,
      'attempted': attempted,
      'correct': correct,
    };
  }
}

  // 통계 데이터 통합 모델
class UnifiedStatsData {
  // 종합 현황
  int totalAnswered = 0;
  int totalCorrect = 0;
  double overallAccuracy = 0.0;
  List<DateTime> accessLog = [];
  List<LearningSession> learningRecords = []; // learningSessions → learningRecords
  int consecutiveAccessDays = 0;

  // 유형별 통계
  Map<String, Map<String, int>> yearlyStats = {};
  Map<String, Map<String, int>> categoryStats = {};
  Map<String, int> oxStats = {'attempted': 0, 'correct': 0};
  Map<String, int> randomStats = {'attempted': 0, 'correct': 0};
  Map<String, Map<String, int>> randomCategoryStats = {};

  UnifiedStatsData();
}

class StatisticsPage extends StatefulWidget {
  @override
  _StatisticsPageState createState() => _StatisticsPageState();
}

class _StatisticsPageState extends State<StatisticsPage> with TickerProviderStateMixin {
  late TabController _tabController;
  late Future<UnifiedStatsData> _unifiedStatsFuture;

  CalendarFormat _calendarFormat = CalendarFormat.month;
  DateTime _focusedDay = DateTime.now();
  DateTime? _selectedDay;

  int _currentPageYearly = 0;
  final int _itemsPerPageYearly = 5;

  int _currentPageLearningLog = 0;
  final int _itemsPerPageLearningLog = 10;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    _selectedDay = _focusedDay;
    _loadStats();
  }

  void _loadStats() {
    _unifiedStatsFuture = _loadUnifiedStats();
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  Future<UnifiedStatsData> _loadUnifiedStats() async {
    final prefs = await SharedPreferences.getInstance();
    UnifiedStatsData statsData = UnifiedStatsData();

    // 1. 접속 기록 로드 및 연속 접속일 계산
    final accessLogStrings = prefs.getStringList('access_log') ?? [];
    statsData.accessLog = accessLogStrings.map((dateString) => DateTime.parse(dateString)).toList();
    statsData.consecutiveAccessDays = _calculateConsecutiveDays(statsData.accessLog);

    // 2. 학습 기록 로드
    final learningSessionsStrings = prefs.getStringList('learning_sessions') ?? [];
    statsData.learningRecords = learningSessionsStrings
        .map((jsonString) {
          try {
            return LearningSession.fromJson(jsonDecode(jsonString));
          } catch (e) {
            print("Error decoding learning session: $jsonString, error: $e");
            return null; // 오류 발생 시 null 반환
          }
        })
        .where((session) => session != null) // null이 아닌 세션만 필터링
        .cast<LearningSession>() // LearningSession으로 캐스팅
        .toList();
    statsData.learningRecords.sort((a, b) => b.date.compareTo(a.date));

    // 3. 전체 문제풀이 통계
    const String keyCorrectAnswers = 'correctAnswers';
    const String keyWrongAnswers = 'wrongAnswers';
    const String keyOxCorrectAnswers = 'ox_correctAnswers';
    const String keyOxWrongAnswers = 'ox_wrongAnswers';

    List<String> allCorrect = prefs.getStringList(keyCorrectAnswers) ?? [];
    List<String> allWrong = prefs.getStringList(keyWrongAnswers) ?? [];
    List<String> oxCorrect = prefs.getStringList(keyOxCorrectAnswers) ?? [];
    List<String> oxWrong = prefs.getStringList(keyOxWrongAnswers) ?? [];

    int tempTotalCorrect = 0;
    int tempTotalAttempted = 0;

    // 연도별
    for (String roundName in reverseRoundMapping.values) {
      List<String> roundCorrect = prefs.getStringList('correctAnswers_$roundName') ?? [];
      List<String> roundWrong = prefs.getStringList('wrongAnswers_$roundName') ?? [];
      int correctCount = roundCorrect.length;
      int wrongCount = roundWrong.length;
      statsData.yearlyStats[roundName] = {'correct': correctCount, 'wrong': wrongCount, 'attempted': correctCount + wrongCount};
      tempTotalCorrect += correctCount;
      tempTotalAttempted += correctCount + wrongCount;
    }
    
    // 과목별
    for (String cat in categories) { // `constants.dart`의 `categories` 사용
      statsData.categoryStats[cat] = {'correct': 0, 'wrong': 0, 'attempted': 0};
    }

    // 랜덤 문제의 카테고리별 통계 집계를 위한 준비
    Map<String, String> randomQuestionCategoryMap = {};
    final allPrefsKeys = prefs.getKeys(); 

    for (String key in allPrefsKeys) {
        if (key.startsWith('random_wrong_data_') || key.startsWith('random_bookmark_data_')) {
            final jsonString = prefs.getString(key);
            if (jsonString != null) {
                try {
                    final Map<String, dynamic> qData = jsonDecode(jsonString);
                    final String? uniqueId = qData['uniqueId']?.toString();
                    final String? category = qData['Category'] as String?;
                    if (uniqueId != null && category != null) {
                        randomQuestionCategoryMap[uniqueId] = category;
                    }
                } catch (e) {
                    print("Error parsing random question JSON for key $key: $e");
                }
            }
        }
    }
    
    // 전역 정오답 리스트 처리 (과목별 & 랜덤 문제 일반)
    for (String entry in allCorrect) {
        final parts = entry.split('|');
        if (parts.length == 3) { // "dbId|category|questionId"
            final category = parts[1];
            if (statsData.categoryStats.containsKey(category)) {
                statsData.categoryStats[category]!['correct'] = (statsData.categoryStats[category]!['correct'] ?? 0) + 1;
                statsData.categoryStats[category]!['attempted'] = (statsData.categoryStats[category]!['attempted'] ?? 0) + 1;
            }
        } else if (parts.first == "RANDOM" && parts.length > 1) {
            final uniqueKey = parts.sublist(1).join('|');
            statsData.randomStats['correct'] = (statsData.randomStats['correct'] ?? 0) + 1;
            statsData.randomStats['attempted'] = (statsData.randomStats['attempted'] ?? 0) + 1;

            final String? category = randomQuestionCategoryMap[uniqueKey];
            if (category != null && categories.contains(category)) {
                if (!statsData.randomCategoryStats.containsKey(category)) {
                    statsData.randomCategoryStats[category] = {'attempted': 0, 'correct': 0};
                }
                statsData.randomCategoryStats[category]!['attempted'] = (statsData.randomCategoryStats[category]!['attempted'] ?? 0) + 1;
                statsData.randomCategoryStats[category]!['correct'] = (statsData.randomCategoryStats[category]!['correct'] ?? 0) + 1;
            }
        }
    }
    for (String entry in allWrong) {
        final parts = entry.split('|');
        if (parts.length == 3) { // "dbId|category|questionId"
            final category = parts[1];
            if (statsData.categoryStats.containsKey(category)) {
                statsData.categoryStats[category]!['wrong'] = (statsData.categoryStats[category]!['wrong'] ?? 0) + 1;
                statsData.categoryStats[category]!['attempted'] = (statsData.categoryStats[category]!['attempted'] ?? 0) + 1;
            }
        } else if (parts.first == "RANDOM" && parts.length > 1) {
            final uniqueKey = parts.sublist(1).join('|');
            statsData.randomStats['attempted'] = (statsData.randomStats['attempted'] ?? 0) + 1;

            final String? category = randomQuestionCategoryMap[uniqueKey];
             if (category != null && categories.contains(category)) {
                if (!statsData.randomCategoryStats.containsKey(category)) {
                    statsData.randomCategoryStats[category] = {'attempted': 0, 'correct': 0};
                }
                statsData.randomCategoryStats[category]!['attempted'] = (statsData.randomCategoryStats[category]!['attempted'] ?? 0) + 1;
                // 오답이므로 correct는 증가시키지 않음
            }
        }
    }
    tempTotalCorrect += (statsData.randomStats['correct'] ?? 0); // This seems to double count random correct answers if they are also in allCorrect.
                                                               // However, the logic for allCorrect for RANDOM type already increments randomStats['correct'].
                                                               // For now, I will assume the original logic is intended unless specified otherwise.
                                                               // A more robust way might be to process `allCorrect` and `allWrong` once for all types.

    // OX 퀴즈
    statsData.oxStats['correct'] = oxCorrect.length;
    statsData.oxStats['attempted'] = oxCorrect.length + oxWrong.length;
    tempTotalCorrect += oxCorrect.length;
    tempTotalAttempted += oxCorrect.length + oxWrong.length;

    // Recalculate totalCorrect and totalAttempted from the specific stats to avoid double counting
    // and ensure accuracy with the new structure.
    int finalTotalCorrect = 0;
    int finalTotalAttempted = 0;

    // Yearly
    statsData.yearlyStats.values.forEach((stat) {
      // Assuming yearly stats correctly capture their own correct/attempted,
      // and these are not meant to be part of category/random/ox at this stage of summation.
      // The original code adds yearly to tempTotalCorrect/Attempted.
      // Let's keep this part of the summation logic as it was.
    });
    finalTotalCorrect += tempTotalCorrect; // This already includes yearly, ox, and random (from allCorrect)
    finalTotalAttempted += tempTotalAttempted; // This already includes yearly, ox, and random (from allCorrect/allWrong)

    // It looks like category stats were meant to be summed from allCorrect/allWrong,
    // and random/ox were separate. The original code summed up yearly, then added random (from allCorrect), then ox.
    // The `tempTotalCorrect` and `tempTotalAttempted` track these.

    // Let's refine the totals based on the processed data:
    // `tempTotalAttempted` already has yearly, ox, and random (from allCorrect/allWrong iteration).
    // `tempTotalCorrect` already has yearly, ox, and random (from allCorrect iteration).

    statsData.totalCorrect = tempTotalCorrect;
    statsData.totalAnswered = tempTotalAttempted;

    // Ensure category attempts are also part of the grand total if they weren't implicitly
    // covered by the `allCorrect`/`allWrong` processing for yearly/random.
    // The current structure implies `allCorrect` and `allWrong` are the primary source for category stats.
    // If questions can be *only* category and not yearly/random, this needs adjustment.
    // For now, assuming `allCorrect`/`allWrong` cover all non-OX questions.

    // The current `tempTotalAttempted` sums:
    // 1. Yearly (correct + wrong)
    // 2. Random (from `allCorrect` and `allWrong` where parts.first == "RANDOM")
    // 3. OX (correct + wrong)
    // Category attempts are derived from `allCorrect` and `allWrong` where `parts.length == 3`.
    // It seems `tempTotalAttempted` does *not* explicitly sum up category stats *again*.
    // It sums the sources. If `allCorrect`/`allWrong` are comprehensive, this is fine.

    if (statsData.totalAnswered > 0) {
      statsData.overallAccuracy = (statsData.totalCorrect / statsData.totalAnswered) * 100;
    }

    return statsData;
  }

  int _calculateConsecutiveDays(List<DateTime> dates) {
    if (dates.isEmpty) return 0;
    Set<String> uniqueAccessDays = dates.map((date) => "${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}").toSet();
    List<DateTime> sortedUniqueDates = uniqueAccessDays.map((s) => DateTime.parse(s)).toList();
    sortedUniqueDates.sort((a, b) => b.compareTo(a));

    int consecutiveDays = 0;
    DateTime today = DateTime.now();
    DateTime currentDate = DateTime(today.year, today.month, today.day);

    if (sortedUniqueDates.isNotEmpty && _isSameDayCustom(sortedUniqueDates.first, currentDate)) {
      consecutiveDays = 1;
      currentDate = currentDate.subtract(Duration(days: 1));

      for (int i = 1; i < sortedUniqueDates.length; i++) {
        if (_isSameDayCustom(sortedUniqueDates[i], currentDate)) {
          consecutiveDays++;
          currentDate = currentDate.subtract(Duration(days: 1));
        } else if (sortedUniqueDates[i].isBefore(currentDate)) {
          break;
        }
      }
    }
    return consecutiveDays;
  }

  List<DateTime> _getEventsForDay(DateTime day, List<DateTime> accessLog, List<LearningSession> learningRecords) {
    List<DateTime> events = [];
    events.addAll(accessLog.where((logDate) => _isSameDayCustom(logDate, day)));
    events.addAll(learningRecords.where((record) => _isSameDayCustom(record.date, day)).map((e) => e.date));
    return events.toSet().toList();
  }

  bool _isSameDayCustom(DateTime date1, DateTime date2) {
    return date1.year == date2.year &&
           date1.month == date2.month &&
           date1.day == date2.day;
  }
  
  Color _getIntensityColor(int problemCount, bool isDarkMode) {
    if (problemCount == 0) return isDarkMode ? Colors.grey[700]! : Colors.grey[300]!;
    if (problemCount < 10) return primaryColor.withOpacity(0.3);
    if (problemCount < 20) return primaryColor.withOpacity(0.6);
    if (problemCount < 30) return primaryColor.withOpacity(0.8);
    return primaryColor;
  }

  int _getDayProblemCount(DateTime day, UnifiedStatsData stats) {
    return stats.learningRecords // Corrected: learningSessions -> learningRecords
        .where((session) => _isSameDayCustom(session.date, day))
        .fold(0, (sum, session) => sum + session.attempted);
  }

  double _getDayAccuracy(DateTime day, UnifiedStatsData stats) {
    final daySessions = stats.learningRecords // Corrected: learningSessions -> learningRecords
        .where((session) => _isSameDayCustom(session.date, day)).toList();
    if (daySessions.isEmpty) return 0.0;
    
    int totalCorrect = daySessions.fold(0, (sum, session) => sum + session.correct);
    int totalAttempted = daySessions.fold(0, (sum, session) => sum + session.attempted);
    
    return totalAttempted > 0 ? (totalCorrect / totalAttempted * 100) : 0.0;
  }

  bool _isInCurrentStreak(DateTime day, List<DateTime> accessLog) {
    final today = DateTime.now();
    final daysDiff = today.difference(day).inDays;
    
    if (daysDiff < 0 || daysDiff > 30) return false; 
    
    return accessLog.any((logDate) => _isSameDayCustom(logDate, day));
  }

  IconData _getTypeIcon(String type) {
    switch(type) {
      case "Yearly": return Icons.calendar_month_outlined;
      case "Category": return Icons.class_outlined;
      case "OX": return Icons.quiz_outlined;
      case "Random": return Icons.shuffle_on_outlined;
      default: return Icons.help_outline;
    }
  }

  Color _getTypeColor(String type) {
    switch(type) {
      case "Yearly": return Colors.blueAccent;
      case "Category": return Colors.green;
      case "OX": return Colors.orange;
      case "Random": return Colors.purple;
      default: return primaryColor;
    }
  }

  Map<String, dynamic> _getMonthlyStats(UnifiedStatsData stats, DateTime month) {
    final monthRecords = stats.learningRecords.where((record) => 
      record.date.year == month.year && record.date.month == month.month
    ).toList();
    
    if (monthRecords.isEmpty) {
      return {
        'count': 0,
        'problems': 0,
        'accuracy': 0.0,
      };
    }
    
    return {
      'count': monthRecords.length,
      'problems': monthRecords.fold(0, (sum, record) => sum + record.attempted),
      'accuracy': (monthRecords.fold(0, (sum, record) => sum + record.correct) / 
                   monthRecords.fold(0, (sum, record) => sum + record.attempted)) * 100,
    };
  }

  void _showDayDetailsBottomSheet(DateTime selectedDay, UnifiedStatsData stats) {
    final daySessions = stats.learningRecords.where((session) => // Corrected: dayRecords -> daySessions (consistent naming)
      _isSameDayCustom(session.date, selectedDay)
    ).toList();
    
    final dayProblemCount = _getDayProblemCount(selectedDay, stats);
    final dayAccuracy = _getDayAccuracy(selectedDay, stats);
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        decoration: BoxDecoration(
          color: isDarkMode ? Color(0xFF2C2C2C) : Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        padding: EdgeInsets.all(20),
        constraints: BoxConstraints(
          maxHeight: MediaQuery.of(context).size.height * 0.7,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: isDarkMode ? Colors.white38 : Colors.grey[400],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            SizedBox(height: 16),
            
            Row(
              children: [
                Icon(Icons.calendar_today, color: primaryColor, size: 24),
                SizedBox(width: 12),
                Text(
                  '${selectedDay.year}년 ${selectedDay.month}월 ${selectedDay.day}일',
                  style: TextStyle(
                    fontSize: 20, 
                    fontWeight: FontWeight.bold,
                    color: isDarkMode ? Colors.white : Colors.black,
                  ),
                ),
                Spacer(),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: Icon(Icons.close, color: isDarkMode ? Colors.white : Colors.black),
                ),
              ],
            ),
            SizedBox(height: 20),
            
            if (dayProblemCount > 0) ...[
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  _buildDayStatChip("총 ${dayProblemCount}문제", Icons.quiz, Colors.blue, isDarkMode),
                  _buildDayStatChip("${dayAccuracy.toStringAsFixed(1)}% 정답률", Icons.check_circle, Colors.green, isDarkMode),
                  _buildDayStatChip("${daySessions.length}번 공부", Icons.schedule, Colors.orange, isDarkMode), // Corrected: dayRecords -> daySessions
                ],
              ),
              SizedBox(height: 20),
            ],
            
            Text(
              daySessions.isNotEmpty ? '📚 오늘의 학습 기록' : '학습 기록 없음', // Corrected: dayRecords -> daySessions
              style: TextStyle(
                fontSize: 16, 
                fontWeight: FontWeight.w600,
                color: isDarkMode ? Colors.white : Colors.black,
              ),
            ),
            SizedBox(height: 12),
            
            if (daySessions.isNotEmpty) ...[ // Corrected: dayRecords -> daySessions
              Expanded(
                child: ListView.builder(
                  itemCount: daySessions.length, // Corrected: dayRecords -> daySessions
                  itemBuilder: (context, index) {
                    final record = daySessions[index]; // Corrected: dayRecords -> daySessions
                    final accuracy = record.attempted > 0 ? (record.correct / record.attempted * 100) : 0;
                    
                    return Card(
                      margin: EdgeInsets.symmetric(vertical: 4),
                      elevation: 1,
                      color: isDarkMode ? Color(0xFF424242) : Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      child: ListTile(
                        contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                        leading: CircleAvatar(
                          backgroundColor: _getTypeColor(record.type).withOpacity(0.2),
                          child: Icon(
                            _getTypeIcon(record.type), 
                            color: _getTypeColor(record.type), 
                            size: 20
                          ),
                        ),
                        title: Text(
                          record.identifier, 
                          style: TextStyle(
                            fontWeight: FontWeight.w500,
                            color: isDarkMode ? Colors.white : Colors.black87,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                        subtitle: Text(
                          '${record.correct}/${record.attempted}문제 (${accuracy.toStringAsFixed(1)}% 정답률)',
                          style: TextStyle(
                            color: isDarkMode ? Colors.white70 : Colors.grey[600],
                          ),
                        ),
                        trailing: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.end,
                          children: [
                            Text(
                              '${record.date.hour}:${record.date.minute.toString().padLeft(2, '0')}',
                              style: TextStyle(
                                color: isDarkMode ? Colors.white60 : Colors.grey[600], 
                                fontSize: 12
                              ),
                            ),
                            SizedBox(height: 2),
                            Container(
                              padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: _getTypeColor(record.type).withOpacity(0.1),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: Text(
                                record.type,
                                style: TextStyle(
                                  fontSize: 10,
                                  color: _getTypeColor(record.type),
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ] else ...[
              Expanded(
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        Icons.book_outlined, 
                        size: 64, 
                        color: isDarkMode ? Colors.white38 : Colors.grey[400]
                      ),
                      SizedBox(height: 16),
                      Text(
                        '아직 공부 기록이 없어요',
                        style: TextStyle(
                          fontSize: 16,
                          color: isDarkMode ? Colors.white60 : Colors.grey[600]
                        ),
                      ),
                      SizedBox(height: 8),
                      Text(
                        '문제를 풀고 학습 기록을 만들어보세요! 📚',
                        style: TextStyle(
                          fontSize: 14,
                          color: isDarkMode ? Colors.white38 : Colors.grey[500]
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildDayStatChip(String text, IconData icon, Color color, bool isDarkMode) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: color),
          SizedBox(width: 6),
          Text(
            text, 
            style: TextStyle(
              fontSize: 12, 
              color: color, 
              fontWeight: FontWeight.w500
            )
          ),
        ],
      ),
    );
  }

  Widget _buildCalendarStat(String label, String value, IconData icon, Color color, bool isDarkMode) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, color: color, size: 18),
        SizedBox(height: 6),
        Text(
          value, 
          style: TextStyle(
            fontSize: 14, 
            fontWeight: FontWeight.bold, 
            color: isDarkMode ? Colors.white : Colors.black87
          )
        ),
        Text(
          label, 
          style: TextStyle(
            fontSize: 11, 
            color: isDarkMode ? Colors.white60 : Colors.grey[600]
          )
        ),
      ],
    );
  }

  // 달력 도움말 대화상자 표시
  void _showCalendarHelpDialog(bool isDarkMode) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            Icon(Icons.info_outline_rounded, color: primaryColor),
            SizedBox(width: 10),
            Text('달력 표시 방법', style: TextStyle(fontSize: 18)),
          ],
        ),
        backgroundColor: isDarkMode ? Color(0xFF303030) : Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        content: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              _buildHelpSectionTitle('공부량 표시', isDarkMode),
              SizedBox(height: 8),
              _buildHelpItemWithVisual(
                '문제 없음',
                '문제를 풀지 않은 날',
                isDarkMode ? Colors.grey[700]! : Colors.grey[300]!,
                isDarkMode,
              ),
              _buildHelpItemWithVisual(
                '조금 (~9문제)',
                '1-9개의 문제를 푼 날',
                primaryColor.withOpacity(0.3),
                isDarkMode,
              ),
              _buildHelpItemWithVisual(
                '보통 (10~19문제)',
                '10-19개의 문제를 푼 날',
                primaryColor.withOpacity(0.6),
                isDarkMode,
              ),
              _buildHelpItemWithVisual(
                '많이 (20~29문제)',
                '20-29개의 문제를 푼 날',
                primaryColor.withOpacity(0.8),
                isDarkMode,
              ),
              _buildHelpItemWithVisual(
                '매우 많이 (30+문제)',
                '30개 이상의 문제를 푼 날',
                primaryColor,
                isDarkMode,
              ),
              
              Divider(height: 24),
              _buildHelpSectionTitle('특별 표시', isDarkMode),
              SizedBox(height: 8),
              
              _buildSpecialHelpItem(
                '연속 공부',
                '앱에 접속하여 연속으로 공부한 날',
                Icons.calendar_today,
                Colors.blue.withOpacity(0.3),
                isDarkMode,
                isBackgroundHighlight: true,
              ),
              _buildSpecialHelpItem(
                '우수 (80%+)',
                '정답률이 80% 이상인 날',
                Icons.star_border,
                Colors.amber,
                isDarkMode,
                isBorder: true,
              ),
              _buildSpecialHelpItem(
                '집중 (50+문제)',
                '하루에 50문제 이상 푼 날',
                Icons.star,
                primaryColor,
                isDarkMode,
                hasStar: true,
              ),
              
              Divider(height: 24),
              _buildHelpSectionTitle('조합 표시 예시', isDarkMode),
              SizedBox(height: 8),
              
              _buildCombinedHelpItem(
                '우수한 연속 공부',
                '연속 접속 + 80% 이상 정답률',
                primaryColor.withOpacity(0.6),
                Colors.amber,
                isDarkMode,
                isBackgroundHighlight: true,
                isBorder: true,
              ),
              _buildCombinedHelpItem(
                '집중 연속 공부',
                '연속 접속 + 50문제 이상',
                primaryColor,
                Colors.white,
                isDarkMode,
                isBackgroundHighlight: true,
                hasStar: true,
              ),
              _buildCombinedHelpItem(
                '모든 요소 조합',
                '연속 공부 + 많은 문제 + 우수 + 집중',
                primaryColor,
                Colors.amber,
                isDarkMode,
                isBackgroundHighlight: true,
                isBorder: true,
                hasStar: true,
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text('확인', style: TextStyle(color: primaryColor, fontWeight: FontWeight.bold)),
          ),
        ],
      ),
    );
  }

  // 도움말 섹션 제목
  Widget _buildHelpSectionTitle(String title, bool isDarkMode) {
    return Text(
      title,
      style: TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.bold,
        color: isDarkMode ? Colors.white : Colors.black87,
      ),
    );
  }

  // 공부량 표시 도움말 항목
  Widget _buildHelpItemWithVisual(String title, String description, Color color, bool isDarkMode) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: EdgeInsets.only(top: 3),
            width: 12,
            height: 12,
            decoration: BoxDecoration(
              color: color,
              shape: BoxShape.circle,
            ),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: isDarkMode ? Colors.white : Colors.black87,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  description,
                  style: TextStyle(
                    fontSize: 12,
                    color: isDarkMode ? Colors.white70 : Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // 특별 표시 도움말 항목
  Widget _buildSpecialHelpItem(
    String title,
    String description,
    IconData icon,
    Color color,
    bool isDarkMode, {
    bool isBackgroundHighlight = false,
    bool isBorder = false,
    bool hasStar = false,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: EdgeInsets.only(top: 3),
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: isBackgroundHighlight ? Colors.blue.withOpacity(0.08) : Colors.transparent,
              borderRadius: BorderRadius.circular(6),
              border: isBackgroundHighlight ? Border.all(color: Colors.blue.withOpacity(0.2)) : null,
            ),
            child: Center(
              child: Container(
                width: 16,
                height: 16,
                decoration: BoxDecoration(
                  color: hasStar ? primaryColor : color.withOpacity(0.3),
                  shape: BoxShape.circle,
                  border: isBorder ? Border.all(color: Colors.amber, width: 1.5) : null,
                ),
                child: hasStar
                    ? Icon(Icons.star, color: Colors.white, size: 10)
                    : null,
              ),
            ),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: isDarkMode ? Colors.white : Colors.black87,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  description,
                  style: TextStyle(
                    fontSize: 12,
                    color: isDarkMode ? Colors.white70 : Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // 조합된 표시 도움말 항목
  Widget _buildCombinedHelpItem(
    String title,
    String description,
    Color dotColor,
    Color starColor,
    bool isDarkMode, {
    bool isBackgroundHighlight = false,
    bool isBorder = false,
    bool hasStar = false,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            margin: EdgeInsets.only(top: 3),
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: isBackgroundHighlight ? Colors.blue.withOpacity(0.08) : Colors.transparent,
              borderRadius: BorderRadius.circular(6),
              border: isBackgroundHighlight ? Border.all(color: Colors.blue.withOpacity(0.2)) : null,
            ),
            child: Center(
              child: Container(
                width: 16,
                height: 16,
                decoration: BoxDecoration(
                  color: dotColor,
                  shape: BoxShape.circle,
                  border: isBorder ? Border.all(color: Colors.amber, width: 1.5) : null,
                ),
                child: hasStar
                    ? Icon(Icons.star, color: starColor, size: 10)
                    : null,
              ),
            ),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: isDarkMode ? Colors.white : Colors.black87,
                  ),
                ),
                SizedBox(height: 2),
                Text(
                  description,
                  style: TextStyle(
                    fontSize: 12,
                    color: isDarkMode ? Colors.white70 : Colors.grey[600],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: ThemedBackgroundWidget(
        isDarkMode: isDarkMode,
        child: SafeArea(
          child: Column(
            children: [
              CommonHeaderWidget(
                title: '공부 현황',
                subtitle: '학습 진도와 통계를 확인하세요',
                onHomePressed: () => Navigator.pushAndRemoveUntil(
                  context, 
                  MaterialPageRoute(builder: (_) => HomePage()), 
                  (route) => false
                ),
              ),
              Container(
                color: isDarkMode ? Color(0xFF2C2C2C) : Colors.white,
                child: TabBar(
                  controller: _tabController,
                  labelColor: isDarkMode ? Colors.white : primaryColor,
                  unselectedLabelColor: Colors.grey,
                  indicatorColor: isDarkMode ? primaryColor : Color(0xFF2d2d41),
                  tabs: [
                    Tab(text: '공부 현황'),
                    Tab(text: '유형별 통계'),
                    Tab(text: '공부 기록'),
                  ],
                ),
              ),
              Container(
                padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                color: isDarkMode ? Color(0xFF2C2C2C) : Colors.white,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    ElevatedButton.icon(
                      onPressed: () {
                        setState(() {
                          _loadStats();
                        });
                      },
                      icon: Icon(Icons.refresh, size: 16),
                      label: Text('새로고침'),
                      style: ElevatedButton.styleFrom(
                        padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: FutureBuilder<UnifiedStatsData>(
        future: _unifiedStatsFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Center(child: Text('통계 로딩 중 오류 발생: ${snapshot.error}\n${snapshot.stackTrace}'));
          }
          if (!snapshot.hasData) {
            return Center(child: Text('표시할 통계 데이터가 없습니다.'));
          }

          final stats = snapshot.data!;

          return TabBarView(
            controller: _tabController,
            children: [
              _buildOverallDashboardTab(stats, isDarkMode),
              _buildByTypeStatsTab(stats, isDarkMode),
              _buildLearningLogTab(stats, isDarkMode),
            ],
          );
        },
        ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildOverallDashboardTab(UnifiedStatsData stats, bool isDarkMode) {
    final monthlyStats = _getMonthlyStats(stats, _focusedDay);
    
    return SingleChildScrollView(
      padding: EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 공부 달력 제목 부분 수정 (도움말 아이콘 추가)
          Row(
            children: [
              Expanded(child: _buildSectionTitle('공부 달력', Icons.calendar_today, isDarkMode)),
              IconButton(
                icon: Icon(
                  Icons.help_outline_rounded,
                  color: isDarkMode ? Colors.white60 : Colors.grey[600],
                  size: 20,
                ),
                onPressed: () => _showCalendarHelpDialog(isDarkMode),
                tooltip: '달력 표시 방법 설명',
                padding: EdgeInsets.zero,
                constraints: BoxConstraints(minWidth: 32, minHeight: 32),
              ),
            ],
          ),
          
          Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            color: isDarkMode ? Color(0xFF3A3A3A) : Colors.white,
            child: Padding(
              padding: const EdgeInsets.all(12.0),
              child: Column(
                children: [
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: isDarkMode ? Color(0xFF424242) : Colors.grey[50],
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildCalendarStat(
                          "이번 달", 
                          "${monthlyStats['count']}회", 
                          Icons.calendar_month, 
                          Colors.blue, 
                          isDarkMode
                        ),
                        _buildCalendarStat(
                          "연속일", 
                          "${stats.consecutiveAccessDays}일", 
                          Icons.local_fire_department, 
                          Colors.orange, 
                          isDarkMode
                        ),
                        _buildCalendarStat(
                          "월 평균", 
                          "${(monthlyStats['accuracy'] as double).toStringAsFixed(0)}%", 
                          Icons.trending_up, 
                          Colors.green, 
                          isDarkMode
                        ),
                      ],
                    ),
                  ),
                  SizedBox(height: 16),
                  
                  TableCalendar(
                    locale: 'ko_KR',
                    firstDay: DateTime.utc(DateTime.now().year - 1, DateTime.now().month, 1), // Ensure firstDay is valid
                    lastDay: DateTime.now().add(Duration(days:1)), // Ensure lastDay is not before firstDay or focusedDay
                    focusedDay: _focusedDay,
                    calendarFormat: _calendarFormat,
                    selectedDayPredicate: (day) => _selectedDay != null && _isSameDayCustom(_selectedDay!, day),
                    onDaySelected: (selectedDay, focusedDay) {
                      _showDayDetailsBottomSheet(selectedDay, stats);
                      if (_selectedDay == null || !_isSameDayCustom(_selectedDay!, selectedDay)) {
                        setState(() {
                          _selectedDay = selectedDay;
                          _focusedDay = focusedDay; 
                        });
                      }
                    },
                    onFormatChanged: (format) {
                      if (_calendarFormat != format) {
                        setState(() {
                          _calendarFormat = format;
                        });
                      }
                    },
                    onPageChanged: (focusedDay) {
                       // Make sure focusedDay is within the valid range if you have strict first/last days
                        final now = DateTime.now();
                        DateTime validFocusedDay = focusedDay;
                        if (focusedDay.isAfter(now)) {
                           validFocusedDay = now;
                        } else if (focusedDay.isBefore(DateTime.utc(now.year -1, now.month, 1))) {
                           validFocusedDay = DateTime.utc(now.year -1, now.month, 1);
                        }
                      setState(() {
                        _focusedDay = validFocusedDay;
                      });
                    },
                    eventLoader: (day) => _getEventsForDay(day, stats.accessLog, stats.learningRecords),
                    
                    calendarBuilders: CalendarBuilders(
                      markerBuilder: (context, date, events) {
                        if (events.isNotEmpty) {
                          final int problemCount = _getDayProblemCount(date, stats);
                          final double accuracy = _getDayAccuracy(date, stats);
                          final Color intensity = _getIntensityColor(problemCount, isDarkMode);
                          
                          return Positioned(
                            right: 2,
                            bottom: 2,
                            child: Container(
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: intensity,
                                border: accuracy >= 80 ? Border.all(color: Colors.amber, width: 1.5) : null,
                              ),
                              width: problemCount > 30 ? 12.0 : (problemCount > 15 ? 10.0 : 8.0),
                              height: problemCount > 30 ? 12.0 : (problemCount > 15 ? 10.0 : 8.0),
                              child: problemCount > 50 ? 
                                Icon(Icons.star, color: Colors.white, size: (problemCount > 30 ? 8 : (problemCount > 15 ? 6 : 4))) : null, // Adjusted star size
                            ),
                          );
                        }
                        return null;
                      },
                      
                      defaultBuilder: (context, day, focusedDay) {
                        if (_isInCurrentStreak(day, stats.accessLog)) {
                          return Container(
                            margin: const EdgeInsets.all(4.0),
                            decoration: BoxDecoration(
                              color: Colors.blue.withOpacity(0.08),
                              borderRadius: BorderRadius.circular(8.0),
                              border: Border.all(color: Colors.blue.withOpacity(0.2)),
                            ),
                            child: Center(
                              child: Text(
                                '${day.day}',
                                style: TextStyle(
                                  color: isDarkMode ? Colors.white : Colors.black87,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ),
                          );
                        }
                        return null;
                      },
                    ),
                    
                    headerStyle: HeaderStyle(
                      titleCentered: true,
                      formatButtonVisible: false,
                      titleTextStyle: TextStyle(fontSize: 18, color: isDarkMode ? Colors.white : Colors.black),
                      leftChevronIcon: Icon(Icons.chevron_left, color: isDarkMode ? Colors.white : Colors.black),
                      rightChevronIcon: Icon(Icons.chevron_right, color: isDarkMode ? Colors.white : Colors.black),
                    ),
                    calendarStyle: CalendarStyle(
                      todayDecoration: BoxDecoration(
                        color: Colors.orangeAccent.withOpacity(0.7), 
                        shape: BoxShape.circle
                      ),
                      selectedDecoration: BoxDecoration(
                        color: primaryColor, 
                        shape: BoxShape.circle
                      ),
                      weekendTextStyle: TextStyle(color: isDarkMode ? Colors.red[300]! : Colors.red),
                      defaultTextStyle: TextStyle(color: isDarkMode ? Colors.white70: Colors.black87),
                      outsideTextStyle: TextStyle(color: isDarkMode ? Colors.white38 : Colors.grey[400]!),
                    ),
                  ),
                  
                  SizedBox(height: 12),
                  
                  Container(
                    padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(
                      color: isDarkMode ? Color(0xFF424242) : Colors.grey[50],
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Column(
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [
                            Text('공부량:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: isDarkMode ? Colors.white70 : Colors.grey[600])),
                            _buildLegendItem("조금 (~9)", primaryColor.withOpacity(0.3), isDarkMode),
                            _buildLegendItem("보통 (10~19)", primaryColor.withOpacity(0.6), isDarkMode),
                            _buildLegendItem("많이 (20+)", primaryColor, isDarkMode),
                          ],
                        ),
                        SizedBox(height: 6),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceAround,
                          children: [
                            Text('특별표시:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: isDarkMode ? Colors.white70 : Colors.grey[600])),
                             // For "연속공부", the visual cue is defaultBuilder in TableCalendar
                            _buildLegendItem("연속공부", Colors.blue.withOpacity(0.3), isDarkMode, showBackgroundHighlight: true),
                            _buildLegendItem("우수 (80%+)", Colors.amber, isDarkMode, showBorder: true),
                            _buildLegendItem("집중 (50+)", primaryColor, isDarkMode, showStar: true),
                          ],
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          SizedBox(height: 24),

          _buildSectionTitle('종합 공부 현황', Icons.assessment, isDarkMode),
          Card(
            elevation: 2,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
             color: isDarkMode ? Color(0xFF3A3A3A) : Colors.white,
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                       _buildStatItem("총 푼 문제", "${stats.totalAnswered}개", Icons.quiz_outlined, Colors.blueAccent, isDarkMode),
                       _buildStatItem("평균 정답률", "${stats.overallAccuracy.toStringAsFixed(1)}%", Icons.check_circle_outline, Colors.green, isDarkMode),
                    ],
                  ),
                  SizedBox(height: 20),
                  Row(
                     mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                       _buildStatItem("연속 공부일", "${stats.consecutiveAccessDays}일", Icons.event_available_outlined, Colors.orangeAccent, isDarkMode),
                       _buildStatItem("공부 횟수", "${stats.learningRecords.length}회", Icons.history_toggle_off_outlined, Colors.purpleAccent, isDarkMode),
                    ],
                  )
                ],
              ),
            ),
          ),
          SizedBox(height: 24),

          _buildSectionTitle('최근 공부 기록', Icons.history_edu_outlined, isDarkMode),
          stats.learningRecords.isEmpty
              ? Card(
                elevation: 2,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                color: isDarkMode ? Color(0xFF3A3A3A) : Colors.white,
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Center(child: Text("아직 학습 기록이 없어요. 문제를 풀어보세요! 📚", style: TextStyle(color: isDarkMode ? Colors.white70 : Colors.grey[600]))),
                )
              )
              : ListView.builder(
                  shrinkWrap: true,
                  physics: NeverScrollableScrollPhysics(),
                  itemCount: stats.learningRecords.length > 5 ? 5 : stats.learningRecords.length,
                  itemBuilder: (context, index) {
                    final record = stats.learningRecords[index];
                    IconData typeIcon = _getTypeIcon(record.type);
                    return Card(
                      elevation: 1,
                       color: isDarkMode ? Color(0xFF424242) : Colors.white,
                      margin: EdgeInsets.symmetric(vertical: 4),
                       shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                      child: ListTile(
                        leading: Icon(typeIcon, color: primaryColor),
                        title: Text("${record.identifier}", style: TextStyle(fontWeight: FontWeight.w500, color: isDarkMode ? Colors.white : Colors.black87)),
                        subtitle: Text(
                            "${record.date.year}-${record.date.month}-${record.date.day}, ${record.attempted}문제 풀이 (정답률: ${record.attempted > 0 ? (record.correct / record.attempted * 100).toStringAsFixed(0) : '0'}%)",
                             style: TextStyle(color: isDarkMode ? Colors.white70 : Colors.grey[700])
                        ),
                      ),
                    );
                  },
                ),
        ],
      ),
    );
  }

  // Updated _buildLegendItem to handle showStar and showBackgroundHighlight
  Widget _buildLegendItem(String label, Color color, bool isDarkMode, {bool showBorder = false, bool showStar = false, bool showBackgroundHighlight = false}) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            // If showBackgroundHighlight, it implies the circle itself IS the highlight.
            // If it means a background behind the circle, this needs more complex layering.
            // Assuming `color` is the primary visual element of the legend item.
            color: showBackgroundHighlight ? color.withOpacity(0.3) : (showStar ? color : color), // Star will be inside
            shape: BoxShape.circle,
            border: showBorder ? Border.all(color: Colors.amber, width: 1.5) : (showBackgroundHighlight ? Border.all(color: color, width: 1.0) : null),
          ),
          child: showStar ? Icon(Icons.star, color: Colors.white, size: 8) : null,
        ),
        SizedBox(width: 4),
        Text(
          label,
          style: TextStyle(
            fontSize: 10,
            color: isDarkMode ? Colors.white60 : Colors.grey[600]
          )
        ),
      ],
    );
  }


  Widget _buildByTypeStatsTab(UnifiedStatsData stats, bool isDarkMode) {
    List<String> sortedYearlyKeys = stats.yearlyStats.keys.toList()
      ..sort((a, b) {
        int? aId = reverseRoundMapping.entries.firstWhere((e) => e.value == a, orElse: () => MapEntry(-1, '')).key;
        int? bId = reverseRoundMapping.entries.firstWhere((e) => e.value == b, orElse: () => MapEntry(-1, '')).key;
        return aId.compareTo(bId);
      });
    
    int yearlyTotalPages = sortedYearlyKeys.isEmpty ? 1 : (sortedYearlyKeys.length / _itemsPerPageYearly).ceil();
    int yearlyStartIndex = _currentPageYearly * _itemsPerPageYearly;
    int yearlyEndIndex = (yearlyStartIndex + _itemsPerPageYearly < sortedYearlyKeys.length)
                        ? (yearlyStartIndex + _itemsPerPageYearly)
                        : sortedYearlyKeys.length;
    List<String> currentDisplayYears = sortedYearlyKeys.isNotEmpty ? sortedYearlyKeys.sublist(yearlyStartIndex, yearlyEndIndex) : [];

    List<FlSpot> yearlySpots = [];
    if (currentDisplayYears.isNotEmpty) {
      for (int i = 0; i < currentDisplayYears.length; i++) {
          String yearKey = currentDisplayYears[i];
          int correct = stats.yearlyStats[yearKey]?['correct'] ?? 0;
          int attempted = stats.yearlyStats[yearKey]?['attempted'] ?? 0;
          double accuracy = attempted > 0 ? (correct / attempted) * 100 : 0;
          yearlySpots.add(FlSpot(i.toDouble(), accuracy));
      }
    }

    return ListView(
      padding: EdgeInsets.all(16.0),
      children: [
        _buildSectionTitle('연도별 문제 통계', Icons.bar_chart_outlined, isDarkMode),
        Card(
           elevation: 2,
           shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
           color: isDarkMode ? Color(0xFF3A3A3A) : Colors.white,
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
GestureDetector(
  onHorizontalDragEnd: (details) {
    if (yearlyTotalPages > 1) {
      // 스와이프 속도가 충분한지 확인 (기본 스와이프 감지 임계값)
      if (details.primaryVelocity != null) {
        // 왼쪽으로 스와이프: 다음 페이지
        if (details.primaryVelocity! < -300 && _currentPageYearly < yearlyTotalPages - 1) {
          setState(() {
            _currentPageYearly++;
          });
        }
        // 오른쪽으로 스와이프: 이전 페이지
        else if (details.primaryVelocity! > 300 && _currentPageYearly > 0) {
          setState(() {
            _currentPageYearly--;
          });
        }
      }
    }
  },
  // 이벤트 버블링 방지 - 그래프 내에서 발생한 스와이프는 여기서 처리하고 상위로 전파하지 않음
  behavior: HitTestBehavior.opaque,
  child: Container(
    height: 250,
    child: yearlySpots.isNotEmpty 
      ? Stack(
          children: [
            LineChart(
              LineChartData(
                gridData: FlGridData(show: true, drawVerticalLine: false, horizontalInterval: 25, getDrawingHorizontalLine: (value) => FlLine(color: (isDarkMode? Colors.white24 : Colors.grey[300])!, strokeWidth: 0.5)),
                titlesData: FlTitlesData(
                  bottomTitles: AxisTitles(
                    sideTitles: SideTitles(
                      showTitles: true,
                      reservedSize: 30,
                      interval: 1,
                      getTitlesWidget: (value, meta) {
                          final index = value.toInt();
                          if (index >= 0 && index < currentDisplayYears.length) {
                              // Attempt to extract year part, e.g., "2020" from "2020년 1회"
                              String yearLabel = currentDisplayYears[index].split('년').first;
                              if (yearLabel.length > 4) yearLabel = yearLabel.substring(yearLabel.length - 4); // Heuristic for "YYYY"
                              return Padding(
                                  padding: const EdgeInsets.only(top: 8.0),
                                  child: Text(yearLabel, style: TextStyle(fontSize: 10, color: isDarkMode? Colors.white70 : Colors.black54)),
                              );
                          }
                          return Text('');
                      },
                    ),
                  ),
                  leftTitles: AxisTitles(sideTitles: SideTitles(showTitles: true, reservedSize: 35, interval: 25, getTitlesWidget: (value, meta) => Text('${value.toInt()}%', style: TextStyle(fontSize: 10, color: isDarkMode? Colors.white70 : Colors.black54)))),
                  topTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  rightTitles: AxisTitles(sideTitles: SideTitles(showTitles: false)),
                ),
                borderData: FlBorderData(show: true, border: Border.all(color: isDarkMode ? Colors.white30: Colors.grey[300]!, width: 0.5)),
                minY: 0, maxY: 100,
                lineBarsData: [
                  LineChartBarData(
                      spots: yearlySpots,
                      isCurved: true,
                      color: primaryColor,
                      barWidth: 2.5,
                      dotData: FlDotData(show: true, getDotPainter: (spot, percent, barData, index) => FlDotCirclePainter(radius: 4, color: primaryColor, strokeWidth: 1.5, strokeColor: isDarkMode? Colors.grey[800]! : Colors.white)),
                      belowBarData: BarAreaData(show: true, color: primaryColor.withOpacity(0.2))
                  ),
                ],
                lineTouchData: LineTouchData(
                  touchTooltipData: LineTouchTooltipData(
                    getTooltipItems: (List<LineBarSpot> touchedBarSpots) {
                      return touchedBarSpots.map((barSpot) {
                        final flSpot = barSpot;
                        if (flSpot.x.toInt() >= 0 && flSpot.x.toInt() < currentDisplayYears.length) {
                          String yearKey = currentDisplayYears[flSpot.x.toInt()];
                          int correct = stats.yearlyStats[yearKey]?['correct'] ?? 0;
                          int attempted = stats.yearlyStats[yearKey]?['attempted'] ?? 0;
                          return LineTooltipItem(
                            '$yearKey\n',
                            TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
                            children: [
                              TextSpan(
                                text: '${flSpot.y.toStringAsFixed(1)}% ($correct/$attempted)',
                                style: TextStyle(
                                  color: Colors.white.withOpacity(0.8),
                                  fontWeight: FontWeight.normal,
                                ),
                              ),
                            ],
                          );
                        }
                        return null;
                      }).where((item) => item != null).toList().cast<LineTooltipItem>();
                    },
                  ),
                ),
              ),
            ),
            if (yearlyTotalPages > 1) ...[
              Positioned(
                left: 0,
                top: 0,
                bottom: 0,
                child: _currentPageYearly > 0 
                  ? Container(
                      width: 30,
                      color: Colors.transparent,
                      alignment: Alignment.center,
                      child: Icon(
                        Icons.chevron_left,
                        color: isDarkMode ? Colors.white30 : Colors.black26,
                      ),
                    )
                  : SizedBox.shrink(),
              ),
              Positioned(
                right: 0,
                top: 0,
                bottom: 0,
                child: _currentPageYearly < yearlyTotalPages - 1
                  ? Container(
                      width: 30,
                      color: Colors.transparent,
                      alignment: Alignment.center,
                      child: Icon(
                        Icons.chevron_right,
                        color: isDarkMode ? Colors.white30 : Colors.black26,
                      ),
                    )
                  : SizedBox.shrink(),
              ),
            ],
          ],
        )
      : Center(child: Text("데이터 없음", style: TextStyle(color: isDarkMode ? Colors.white70: Colors.grey[600]))),
  ),
),
                if(yearlyTotalPages > 1)
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: List.generate(yearlyTotalPages, (index) {
                    return InkWell(
                      onTap: () => setState(() => _currentPageYearly = index),
                      child: Container(
                        margin: EdgeInsets.symmetric(horizontal: 4, vertical: 8),
                        width: 8, height: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _currentPageYearly == index ? primaryColor : (isDarkMode? Colors.grey[600] : Colors.grey[400]),
                        ),
                      ),
                    );
                  }),
                )
              ],
            ),
          ),
        ),
        SizedBox(height: 24),

        _buildSectionTitle('과목별 문제 통계', Icons.pie_chart_outline_outlined, isDarkMode),
        ...stats.categoryStats.entries.map((entry) {
          String category = entry.key;
          int correct = entry.value['correct'] ?? 0;
          int attempted = entry.value['attempted'] ?? 0;
          double accuracy = attempted > 0 ? (correct / attempted * 100) : 0;
          if (attempted == 0) return SizedBox.shrink(); // Hide if no attempts
          return Card(
            elevation: 2,
            margin: EdgeInsets.symmetric(vertical: 6),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            color: isDarkMode ? Color(0xFF3A3A3A) : Colors.white,
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(category, style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: isDarkMode ? Colors.white : Colors.black)),
                  SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('푼 문제: $attempted', style: TextStyle(color: isDarkMode ? Colors.white70: Colors.grey[700])),
                            Text('정답률: ${accuracy.toStringAsFixed(1)}%', style: TextStyle(color: isDarkMode ? Colors.white70: Colors.grey[700])),
                          ],
                        ),
                      ),
                      SizedBox(
                        height: 60, width: 60,
                        child: attempted > 0 ? PieChart(
                           PieChartData(
                             sectionsSpace: 2,
                             centerSpaceRadius: 15,
                             startDegreeOffset: -90,
                             sections: [
                               PieChartSectionData(color: Colors.greenAccent[400], value: correct.toDouble(), title: '${(correct/attempted*100).toStringAsFixed(0)}%', titleStyle: TextStyle(fontSize: 10, color: Colors.black87, fontWeight: FontWeight.bold), radius: 18),
                               PieChartSectionData(color: Colors.redAccent[100], value: (attempted - correct).toDouble(), title: '', radius: 15),
                             ]
                           )
                        ) : Container(alignment: Alignment.center, child: Text("N/A", style: TextStyle(color: isDarkMode ? Colors.white38 : Colors.grey[400]))),
                      )
                    ],
                  )
                ],
              ),
            ),
          );
        }).toList(),
        SizedBox(height: 24),

        _buildSectionTitle('OX 퀴즈 통계', Icons.check_circle_outline, isDarkMode),
        _buildQuizTypeStatCard("OX 퀴즈 전체", stats.oxStats, Icons.check_circle_outline, Colors.teal, isDarkMode),
        SizedBox(height: 24),
        
        _buildSectionTitle('랜덤 문제 통계', Icons.casino_outlined, isDarkMode),
         _buildQuizTypeStatCard("랜덤 전체", stats.randomStats, Icons.casino_outlined, Colors.deepPurpleAccent, isDarkMode),
        if(stats.randomCategoryStats.isNotEmpty) ...[
            SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.only(left: 16.0, bottom: 4.0, top: 8.0),
              child: Text("랜덤 (과목별)", style: TextStyle(fontSize: 14, fontWeight: FontWeight.w500, color: isDarkMode? Colors.white60 : Colors.grey[700])),
            ),
        ],
        ...stats.randomCategoryStats.entries.map((entry) {
            if((entry.value['attempted'] ?? 0) == 0) return SizedBox.shrink();
            return _buildQuizTypeStatCard(entry.key, entry.value, Icons.label_important_outline, Colors.indigoAccent, isDarkMode, isSubStat: true);
        }).toList(),
      ],
    );
  }

 Widget _buildLearningLogTab(UnifiedStatsData stats, bool isDarkMode) {
    if (stats.learningRecords.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.menu_book_outlined, size: 64, color: isDarkMode ? Colors.white38 : Colors.grey[400]),
            SizedBox(height: 16),
            Text("아직 학습 기록이 없어요", style: TextStyle(fontSize: 18, color: isDarkMode ? Colors.white70 : Colors.grey[600])),
            SizedBox(height: 8),
            Text("문제를 풀고 학습 기록을 만들어보세요! 📚", style: TextStyle(fontSize: 14, color: isDarkMode ? Colors.white60 : Colors.grey[500])),
          ],
        ),
      );
    }
    
    int logTotalPages = (stats.learningRecords.length / _itemsPerPageLearningLog).ceil();
    int logStartIndex = _currentPageLearningLog * _itemsPerPageLearningLog;
    int logEndIndex = (logStartIndex + _itemsPerPageLearningLog < stats.learningRecords.length)
                        ? (logStartIndex + _itemsPerPageLearningLog)
                        : stats.learningRecords.length;
    List<LearningSession> currentDisplayLogs = stats.learningRecords.isNotEmpty ? stats.learningRecords.sublist(logStartIndex, logEndIndex) : [];

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16.0, 16.0, 16.0, 8.0), // Adjusted padding
          child: _buildSectionTitle('📚 나의 학습 기록', Icons.list_alt_outlined, isDarkMode),
        ),
        Expanded(
          child: ListView.builder(
            padding: EdgeInsets.symmetric(horizontal: 16.0),
            itemCount: currentDisplayLogs.length,
            itemBuilder: (context, index) {
              final record = currentDisplayLogs[index];
              final accuracy = record.attempted > 0 ? (record.correct / record.attempted * 100) : 0;
               IconData typeIcon = _getTypeIcon(record.type);
                Color iconColor = _getTypeColor(record.type);
              return Card(
                elevation: 1.5,
                margin: EdgeInsets.symmetric(vertical: 5),
                color: isDarkMode ? Color(0xFF424242) : Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                child: ListTile(
                  contentPadding: EdgeInsets.symmetric(vertical: 10, horizontal: 16),
                  leading: CircleAvatar(
                    backgroundColor: iconColor.withOpacity(0.15),
                    child: Icon(typeIcon, color: iconColor, size: 22),
                  ),
                  title: Text(
                    "${record.identifier}",
                    style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14.5, color: isDarkMode ? Colors.white : Colors.black87),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  subtitle: Text(
                    "${record.date.year}.${record.date.month.toString().padLeft(2,'0')}.${record.date.day.toString().padLeft(2,'0')} - ${record.attempted}문제 (정답률: ${accuracy.toStringAsFixed(0)}%)", // Removed 풀이
                    style: TextStyle(fontSize: 12.5, color: isDarkMode ? Colors.white70 : Colors.grey[600]),
                  ),
                   trailing: Text(
                    '${record.date.hour}:${record.date.minute.toString().padLeft(2,'0')}',
                     style: TextStyle(fontSize: 12, color: isDarkMode ? Colors.white60 : Colors.grey[500]),
                  ),
                  onTap: () {
                    _showDayDetailsBottomSheet(record.date, stats);
                  },
                ),
              );
            },
          ),
        ),
        if (logTotalPages > 1)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 12.0), // Increased padding
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: List.generate(logTotalPages, (index) {
                 return InkWell(
                      onTap: () => setState(() => _currentPageLearningLog = index),
                      child: Container(
                        margin: EdgeInsets.symmetric(horizontal: 4),
                        padding: EdgeInsets.symmetric(horizontal: 10, vertical: 6), // Adjusted padding for better touch
                        decoration: BoxDecoration(
                          color: _currentPageLearningLog == index ? primaryColor : (isDarkMode? Colors.grey[700] : Colors.grey[300]),
                          borderRadius: BorderRadius.circular(6) // Slightly more rounded
                        ),
                        child: Text(
                          '${index + 1}',
                          style: TextStyle(color: _currentPageLearningLog == index ? Colors.white : (isDarkMode ? Colors.white70 : Colors.black54), fontWeight: FontWeight.w500),
                        ),
                      ),
                    );
              })
            ),
          )
      ],
    );
  }
  
  Widget _buildQuizTypeStatCard(String title, Map<String, int> quizStats, IconData icon, Color color, bool isDarkMode, {bool isSubStat = false}) {
    int attempted = quizStats['attempted'] ?? 0;
    int correct = quizStats['correct'] ?? 0;
    double accuracy = attempted > 0 ? (correct / attempted * 100) : 0;

    if (attempted == 0 && isSubStat) return SizedBox.shrink(); // Don't show sub-stats if no attempts

    return Card(
        elevation: isSubStat ? 1.5 : 2,
        margin: EdgeInsets.symmetric(vertical: isSubStat ? 4: 8, horizontal: isSubStat ? 8 : 0),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        color: isDarkMode ? (isSubStat ? Color(0xFF424242) : Color(0xFF3A3A3A)) : Colors.white,
        child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Row(
            children: [
            CircleAvatar(backgroundColor: color.withOpacity(0.15), child: Icon(icon, color: color, size: 20)),
            SizedBox(width: 16),
            Expanded(
                child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                    Text(title, style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600, color: isDarkMode ? Colors.white : Colors.black87)),
                    SizedBox(height: 4),
                    Text('푼 문제: $attempted', style: TextStyle(fontSize: 12.5, color: isDarkMode ? Colors.white70: Colors.grey[600])),
                    if (attempted > 0) Text('정답률: ${accuracy.toStringAsFixed(1)}%', style: TextStyle(fontSize: 12.5, color: isDarkMode ? Colors.white70: Colors.grey[600])),
                ],
                ),
            ),
            if(attempted > 0)
            SizedBox(height: 50, width: 50,
                child: PieChart(
                  PieChartData(
                    sectionsSpace: 1, centerSpaceRadius: 12, startDegreeOffset: -90,
                    sections: [
                      PieChartSectionData(color: color, value: correct.toDouble(), title: '${accuracy.toStringAsFixed(0)}%', titleStyle: TextStyle(fontSize:9, fontWeight: FontWeight.bold, color: Colors.white.withOpacity(0.9)), radius: 10),
                      PieChartSectionData(color: (isDarkMode? Colors.grey[700] : Colors.grey[300])!, value: (attempted - correct).toDouble(), title: '', radius: 8),
                    ]
                  )
                )
            )
            else Container(width:50, height:50, alignment:Alignment.center, child: Text("없음", style: TextStyle(fontSize: 12, color: isDarkMode ? Colors.white38 : Colors.grey[400]))),
            ],
        ),
        ),
    );
}

  Widget _buildStatItem(String title, String value, IconData icon, Color color, bool isDarkMode) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        CircleAvatar(
          radius: 22,
          backgroundColor: color.withOpacity(0.15),
          child: Icon(icon, size: 22, color: color),
        ),
        SizedBox(height: 8),
        Text(value, style: TextStyle(fontSize: 17, fontWeight: FontWeight.bold, color: isDarkMode ? Colors.white : Colors.black87)),
        SizedBox(height: 2),
        Text(title, style: TextStyle(fontSize: 12.5, color: isDarkMode ? Colors.white70 : Colors.grey[700])),
      ],
    );
  }
  
  Widget _buildSectionTitle(String title, IconData icon, bool isDarkMode){
    return Padding(
      padding: const EdgeInsets.only(bottom: 12.0, top: 8.0),
      child: Row(
        children: [
          Icon(icon, color: isDarkMode ? Colors.white70 : Colors.grey[700], size: 18),
          SizedBox(width: 8),
          Text(
            title,
            style: TextStyle(fontSize: 17, fontWeight: FontWeight.w600, color: isDarkMode ? Colors.white : Colors.black87),
          ),
        ],
      ),
    );
  }
}

// --- Helper functions to be called from other parts of the app ---

Future<void> recordAppAccess() async {
    final prefs = await SharedPreferences.getInstance();
    List<String> accessLog = prefs.getStringList('access_log') ?? [];
    // Store full DateTime string for potential future use, but comparison logic uses date part only
    String todayIsoDateString = DateTime.now().toIso8601String(); 

    // Check if today's date (ignoring time) is already in the log
    bool alreadyLoggedToday = accessLog.any((loggedIsoDateString) {
        try {
            DateTime loggedDate = DateTime.parse(loggedIsoDateString);
            DateTime today = DateTime.now();
            return loggedDate.year == today.year &&
                   loggedDate.month == today.month &&
                   loggedDate.day == today.day;
        } catch (e) {
            // If parsing fails, it's a malformed entry, treat as not logged for this entry
            print("Error parsing access log entry: $loggedIsoDateString");
            return false;
        }
    });

    if (!alreadyLoggedToday) {
        accessLog.add(todayIsoDateString); // Add the full ISO string
        if (accessLog.length > 365) { 
            accessLog = accessLog.sublist(accessLog.length - 365);
        }
        await prefs.setStringList('access_log', accessLog);
        print("App access recorded for today: ${todayIsoDateString.substring(0,10)}");
    } else {
        print("App access already recorded for today.");
    }
}

Future<void> recordLearningSession({
  required String type,
  required String identifier,
  required int attempted,
  required int correct,
}) async {
  if (attempted < 1) { // Changed minimum to 1, as some might want to record even a single question attempt.
    print("Learning session not recorded: too few problems ($attempted)");
    return;
  }

  final prefs = await SharedPreferences.getInstance();
  List<String> sessions = prefs.getStringList('learning_sessions') ?? [];
  LearningSession newSession = LearningSession(
    date: DateTime.now(),
    type: type,
    identifier: identifier,
    attempted: attempted,
    correct: correct,
  );
  sessions.add(jsonEncode(newSession.toJson()));
   if (sessions.length > 200) { 
      sessions = sessions.sublist(sessions.length - 200);
  }
  await prefs.setStringList('learning_sessions', sessions);
  print("🎉 학습 완료! $type - $identifier ($correct/$attempted)");
}

Future<void> recordYearlyLearningSession(String round, Map<int, String> selectedOptions, Map<int, bool> isCorrectOptions) async {
  if (selectedOptions.isEmpty) return;
  
  int attempted = selectedOptions.length;
  int correct = isCorrectOptions.values.where((isCorrect) => isCorrect).length;
  
  await recordLearningSession(
    type: "Yearly",
    identifier: round,
    attempted: attempted,
    correct: correct,
  );
}

Future<void> recordCategoryLearningSession(String category, Map<int, String> selectedOptions, Map<int, bool> isCorrectOptions) async {
  if (selectedOptions.isEmpty) return;
  
  int attempted = selectedOptions.length;
  int correct = isCorrectOptions.values.where((isCorrect) => isCorrect).length;
  
  await recordLearningSession(
    type: "Category",
    identifier: category,
    attempted: attempted,
    correct: correct,
  );
}

Future<void> recordOXLearningSession(String category, Map<String, String> selectedOptions, Map<String, bool> isCorrectOptions) async {
  if (selectedOptions.isEmpty) return;
  
  int attempted = selectedOptions.length;
  int correct = isCorrectOptions.values.where((isCorrect) => isCorrect).length;
  
  String identifier = category == "전체문제" ? "OX 전체" : "OX $category";
  
  await recordLearningSession(
    type: "OX",
    identifier: identifier,
    attempted: attempted,
    correct: correct,
  );
}

Future<void> recordRandomLearningSession(String category, Map<String, String> selectedOptions, Map<String, bool> isCorrectOptions) async {
  if (selectedOptions.isEmpty) return;
  
  final validOptions = selectedOptions.entries.where((entry) => entry.key.startsWith("RANDOM|"));
  final validCorrectOptions = isCorrectOptions.entries.where((entry) => entry.key.startsWith("RANDOM|"));
  
  int attempted = validOptions.length;
  int correct = validCorrectOptions.where((entry) => entry.value).length;

  if (attempted == 0) return; // Don't record if no valid random questions were answered
  
  String identifier = category == "ALL" ? "랜덤 전체" : "랜덤 $category";
  
  await recordLearningSession(
    type: "Random",
    identifier: identifier,
    attempted: attempted,
    correct: correct,
  );
}

// Dummy constants.dart content if not provided by user
// Make sure these are defined in your actual constants.dart
// const primaryColor = Colors.teal;
// final Map<int, String> reverseRoundMapping = {1: "2020년 1회", 2: "2020년 2회", 3: "2021년 1회"};
// final List<String> categories = ["일반화학", "유기화학", "물리화학"];