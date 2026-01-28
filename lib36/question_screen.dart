import 'package:flutter/material.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:typed_data';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'ad_state.dart';
import 'home.dart';
import 'bookmark.dart';
import 'wrong_answer.dart';
import 'database_helper.dart';
import 'ad_helper.dart';
import 'ad_config.dart';
import 'constants.dart'; // reverseRoundMapping 등 정의
import 'statistics.dart'; // recordYearlyLearningSession import
import 'widgets/common/index.dart';
import 'package:flutter_html/flutter_html.dart';



class QuestionScreenPage extends StatefulWidget {
  final String round;       // 예: "2022년 4월"
  final String dbPath;      // 예: 'assets/question1.db'

  QuestionScreenPage({
    required this.round,
    required this.dbPath,
  });

  @override
  _QuestionScreenPageState createState() => _QuestionScreenPageState();
}

class _QuestionScreenPageState extends State<QuestionScreenPage> with TickerProviderStateMixin {
  late Future<List<Map<String, dynamic>>> futureQuestions;
  late DatabaseHelper dbHelper;

  Map<int, String> selectedOptions = {};
  Map<int, bool> isCorrectOptions = {};
  Map<int, bool> showAnswerDescription = {};
  Map<int, bool> savedQuestions = {};

  List<String> correctAnswers = [];
  List<String> wrongAnswers = [];

  int _currentIndex = 0;
  InterstitialAd? _interstitialAd;
  bool _isAdLoaded = false;
  bool _isStatsExpanded = false;

  late AnimationController _fadeController;
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    dbHelper = DatabaseHelper.getInstance(widget.dbPath);

    loadCorrectWrongAnswers();
    futureQuestions = fetchQuestions(widget.round);
    loadSavedQuestions();
    loadSelectedStatesFromPrefs();

    if (!adsRemovedGlobal) {
      _loadInterstitialAd();
    }

    _fadeController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    _slideController = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );
    
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _fadeController, curve: Curves.easeInOut),
    );
    _slideAnimation = Tween<Offset>(begin: Offset(0, 0.2), end: Offset.zero).animate(
      CurvedAnimation(parent: _slideController, curve: Curves.easeOutCubic),
    );

    _fadeController.forward();
    _slideController.forward();
  }

  @override
  void dispose() {
  if (selectedOptions.isNotEmpty) {
    recordYearlyLearningSession(widget.round, selectedOptions, isCorrectOptions);
  }
  
  _interstitialAd?.dispose();
  _fadeController.dispose();
  _slideController.dispose();
  super.dispose();
}

  Future<void> loadCorrectWrongAnswers() async {
    final prefs = await SharedPreferences.getInstance();
    correctAnswers = prefs.getStringList('correctAnswers_${widget.round}') ?? [];
    wrongAnswers = prefs.getStringList('wrongAnswers_${widget.round}') ?? [];
    // print('Loaded correctAnswers for ${widget.round}: $correctAnswers');
    // print('Loaded wrongAnswers for ${widget.round}: $wrongAnswers');
  }

  Future<void> saveAnswersToPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('correctAnswers_${widget.round}', correctAnswers);
    await prefs.setStringList('wrongAnswers_${widget.round}', wrongAnswers);
    // print('Saved correctAnswers for ${widget.round}: $correctAnswers');
    // print('Saved wrongAnswers for ${widget.round}: $wrongAnswers');
  }

  Future<List<Map<String, dynamic>>> fetchQuestions(String roundStr) async {
    final roundValue = reverseRoundMapping.entries
        .firstWhere((e) => e.value == roundStr, orElse: () => MapEntry(-1, '기타'))
        .key;
    if (roundValue == -1) {
      throw Exception('해당 라운드를 찾을 수 없습니다: $roundStr');
    }
    return await dbHelper.getQuestions(roundValue);
  }

  Future<void> loadSavedQuestions() async {
    final prefs = await SharedPreferences.getInstance();
    final savedList = prefs.getStringList('savedQuestions_${widget.round}') ?? [];
    setState(() {
      for (String item in savedList) {
        final parts = item.split('|');
        if (parts.length == 2) {
          String rName = parts[0];
          int qId = int.parse(parts[1]);
          if (rName == widget.round) {
            savedQuestions[qId] = true;
          }
        }
      }
    });
  }

  Future<void> saveBookmarkStatus(int qId, bool bookmarked) async {
    final prefs = await SharedPreferences.getInstance();
    List<String> savedList = prefs.getStringList('savedQuestions_${widget.round}') ?? [];

    final itemKey = '${widget.round}|$qId';
    if (bookmarked) {
      if (!savedList.contains(itemKey)) {
        savedList.add(itemKey);
      }
    } else {
      savedList.remove(itemKey);
    }
    await prefs.setStringList('savedQuestions_${widget.round}', savedList);
  }

  Future<void> loadSelectedStatesFromPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    for (String key in prefs.getKeys()) {
      if (key.startsWith('selected_${widget.round}|')) {
        final questionPart = key.substring('selected_'.length);
        final parts = questionPart.split('|');
        if (parts.length == 2) {
          String roundName = parts[0];
          int? qId = int.tryParse(parts[1]);
          if (roundName == widget.round && qId != null) {
            final val = prefs.getString(key);
            if (val != null) {
              setState(() {
                selectedOptions[qId] = val;
              });
            }
          }
        }
      }

      if (key.startsWith('showDescription_${widget.round}|')) {
        final questionPart = key.substring('showDescription_'.length);
        final parts = questionPart.split('|');
        if (parts.length == 2) {
          String roundName = parts[0];
          int? qId = int.tryParse(parts[1]);
          if (roundName == widget.round && qId != null) {
            final val = prefs.getString(key);
            if (val != null) {
              setState(() {
                showAnswerDescription[qId] = (val == 'true');
              });
            }
          }
        }
      }
    }
  }

  Future<void> saveSelectedStateToPrefs(int qId, String chosenOpt) async {
    final prefs = await SharedPreferences.getInstance();
    final key = 'selected_${widget.round}|$qId';
    await prefs.setString(key, chosenOpt);
  }

  Future<void> saveShowDescriptionToPrefs(int qId, bool show) async {
    final prefs = await SharedPreferences.getInstance();
    final key = 'showDescription_${widget.round}|$qId';
    await prefs.setString(key, show.toString());
  }

  Future<void> resetProgress() async {
    final prefs = await SharedPreferences.getInstance();
    final prefix = '${widget.round}|';

    wrongAnswers.removeWhere((item) => item.startsWith(prefix));
    correctAnswers.removeWhere((item) => item.startsWith(prefix));
    await prefs.setStringList('wrongAnswers_${widget.round}', wrongAnswers);
    await prefs.setStringList('correctAnswers_${widget.round}', correctAnswers);

    final keysToRemove = prefs.getKeys().where((k) =>
        k.startsWith('selected_${widget.round}|') ||
        k.startsWith('showDescription_${widget.round}|')).toList();
    for (var k in keysToRemove) {
      await prefs.remove(k);
    }

    setState(() {
      selectedOptions.clear();
      isCorrectOptions.clear();
      showAnswerDescription.clear();
    });
  }

  void _loadInterstitialAd() {
    InterstitialAd.load(
      adUnitId: AdHelper.interstitialAdUnitId,
      request: const AdRequest(),
      adLoadCallback: InterstitialAdLoadCallback(
        onAdLoaded: (InterstitialAd ad) {
          _interstitialAd = ad;
          _isAdLoaded = true;
          _interstitialAd?.fullScreenContentCallback = FullScreenContentCallback(
            onAdDismissedFullScreenContent: (ad) {
              ad.dispose();
              setState(() => _isAdLoaded = false);
              if (!adsRemovedGlobal) _loadInterstitialAd();
            },
            onAdFailedToShowFullScreenContent: (ad, error) {
              ad.dispose();
              setState(() => _isAdLoaded = false);
              if (!adsRemovedGlobal) _loadInterstitialAd();
            },
          );
        },
        onAdFailedToLoad: (LoadAdError error) {
          print('InterstitialAd failed to load: $error');
          _isAdLoaded = false;
        },
      ),
    );
  }

  void handleOptionTap(int qId, String chosen, dynamic correctOpt, Map<String, dynamic> question) async {
    final correctStr = correctOpt?.toString() ?? '';
    final prefixKey = '${widget.round}|$qId';

    setState(() {
      selectedOptions[qId] = chosen;
      bool correct = (chosen == correctStr);
      isCorrectOptions[qId] = correct;
      showAnswerDescription[qId] = true;
    });

    await saveSelectedStateToPrefs(qId, chosen);
    await saveShowDescriptionToPrefs(qId, true);

    if (chosen == correctStr) {
      if (!correctAnswers.contains(prefixKey)) correctAnswers.add(prefixKey);
      wrongAnswers.remove(prefixKey);
    } else {
      if (!wrongAnswers.contains(prefixKey)) wrongAnswers.add(prefixKey);
      correctAnswers.remove(prefixKey);
    }
    await saveAnswersToPrefs();

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          chosen == correctStr ? '정답입니다!' : '오답입니다.',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 16,
          ),
        ),
        backgroundColor: chosen == correctStr ? Color(0xFF4CAF50) : Color(0xFFF44336),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        duration: Duration(milliseconds: 1500),
      ),
    );
  }

  void handleBookmarkTap(int qId) async {
    bool newVal = !(savedQuestions[qId] ?? false);
    setState(() {
      savedQuestions[qId] = newVal;
    });

    await saveBookmarkStatus(qId, newVal);

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          newVal ? '문제가 북마크에 저장되었습니다.' : '문제가 북마크에서 제거되었습니다.',
          style: TextStyle(fontWeight: FontWeight.w500),
        ),
        backgroundColor: Color(0xFF2196F3),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        duration: Duration(seconds: 1),
      ),
    );
  }

  Widget _buildModernHeader(bool isDarkMode) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        children: [
          GestureDetector(
            onTap: () => Navigator.pop(context),
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
          SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '문제풀이',
                  style: TextStyle(
                    color: isDarkMode ? Colors.white : Colors.black87,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.3,
                  ),
                ),
                Text(
                  widget.round,
                  style: TextStyle(
                    color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54,
                    fontSize: 11,
                    fontWeight: FontWeight.w400,
                  ),
                ),
              ],
            ),
          ),
          GestureDetector(
            onTap: () => Navigator.pushAndRemoveUntil(
      context, MaterialPageRoute(builder: (_) => HomePage()), (route) => false), // <<< 이렇게 수정
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

  Widget _buildCompactProgressCard(List<Map<String, dynamic>> questions, bool isDarkMode) {
    final totalCount = questions.length;
    final answeredCount = selectedOptions.length;
    final corrCount = isCorrectOptions.values.where((b) => b).length;
    final wrongCount = answeredCount - corrCount;
    final progress = (totalCount == 0) ? 0.0 : (answeredCount / totalCount);

    return Container(
      margin: EdgeInsets.symmetric(horizontal: 16, vertical: 3),
      decoration: BoxDecoration(
        color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.white.withOpacity(0.9),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            blurRadius: 4,
            offset: Offset(0, 1),
          ),
        ],
      ),
      child: Column(
        children: [
          Padding(
            padding: EdgeInsets.all(10),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '학습 진행률',
                      style: TextStyle(
                        color: isDarkMode ? Colors.white : Colors.black87,
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    GestureDetector(
                      onTap: () async {
                        bool? confirm = await showDialog(
                          context: context,
                          builder: (ctx) => AlertDialog(
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
                            title: Row(
                              children: [
                                Container(
                                  padding: EdgeInsets.all(8),
                                  decoration: BoxDecoration(
                                    color: Colors.orange.withOpacity(0.2),
                                    borderRadius: BorderRadius.circular(8),
                                  ),
                                  child: Icon(Icons.refresh_rounded, color: Colors.orange),
                                ),
                                SizedBox(width: 12),
                                Text("풀이 상태 초기화"),
                              ],
                            ),
                            content: Text("지금까지 풀었던 문제를 모두 초기화하시겠습니까?"),
                            actions: [
                              TextButton(
                                child: Text("취소", style: TextStyle(color: Colors.grey[600])),
                                onPressed: () => Navigator.pop(ctx, false),
                              ),
                              ElevatedButton(
                                style: ElevatedButton.styleFrom(
                                  backgroundColor: Colors.orange,
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                ),
                                child: Text("초기화", style: TextStyle(color: Colors.white)),
                                onPressed: () => Navigator.pop(ctx, true),
                              ),
                            ],
                          ),
                        );
                        if (confirm == true) {
                          await resetProgress();
                          ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(
                              content: Text("풀이 상태가 초기화되었습니다."),
                              backgroundColor: Colors.orange,
                              behavior: SnackBarBehavior.floating,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            ),
                          );
                        }
                      },
                      child: Container(
                        padding: EdgeInsets.all(3),
                        decoration: BoxDecoration(
                          color: Colors.orange.withOpacity(0.2),
                          borderRadius: BorderRadius.circular(5),
                        ),
                        child: Icon(
                          Icons.refresh_rounded,
                          color: Colors.orange,
                          size: 14,
                        ),
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 6),
                Row(
                  children: [
                    Expanded(
                      child: Container(
                        height: 2.5,
                        decoration: BoxDecoration(
                          color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade300,
                          borderRadius: BorderRadius.circular(1.25),
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(1.25),
                          child: LinearProgressIndicator(
                            value: progress,
                            backgroundColor: Colors.transparent,
                            valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF8E9AAF)),
                            minHeight: 2.5,
                          ),
                        ),
                      ),
                    ),
                    SizedBox(width: 8),
                    Text(
                      '$answeredCount/$totalCount',
                      style: TextStyle(
                        color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54,
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    SizedBox(width: 4),
                    GestureDetector(
                      onTap: () {
                        setState(() {
                          _isStatsExpanded = !_isStatsExpanded;
                        });
                      },
                      child: Container(
                        padding: EdgeInsets.all(2),
                        child: AnimatedRotation(
                          turns: _isStatsExpanded ? 0.5 : 0,
                          duration: Duration(milliseconds: 200),
                          child: Icon(
                            Icons.keyboard_arrow_down_rounded,
                            color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54,
                            size: 16,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          AnimatedContainer(
            duration: Duration(milliseconds: 300),
            curve: Curves.easeInOut,
            height: _isStatsExpanded ? null : 0,
            child: _isStatsExpanded
                ? Container(
                    padding: EdgeInsets.fromLTRB(10, 0, 10, 10),
                    child: Column(
                      children: [
                        Divider(
                          color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade300,
                          height: 1,
                        ),
                        SizedBox(height: 8),
                        Row(
                          children: [
                            Expanded(
                              child: _buildCompactStatContainer(
                                icon: Icons.assignment_turned_in_rounded,
                                label: '완료',
                                value: '$answeredCount',
                                color: Color(0xFF8E9AAF),
                                isDarkMode: isDarkMode,
                              ),
                            ),
                            SizedBox(width: 4),
                            Expanded(
                              child: _buildCompactStatContainer(
                                icon: Icons.check_circle_rounded,
                                label: '정답',
                                value: '$corrCount',
                                color: Color(0xFF4CAF50),
                                isDarkMode: isDarkMode,
                              ),
                            ),
                            SizedBox(width: 4),
                            Expanded(
                              child: _buildCompactStatContainer(
                                icon: Icons.cancel_rounded,
                                label: '오답',
                                value: '$wrongCount',
                                color: Color(0xFFF44336),
                                isDarkMode: isDarkMode,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  )
                : SizedBox.shrink(),
          ),
        ],
      ),
    );
  }

  Widget _buildCompactStatContainer({
    required IconData icon,
    required String label,
    required String value,
    required Color color,
    required bool isDarkMode,
  }) {
    return Container(
      padding: EdgeInsets.symmetric(vertical: 6, horizontal: 8),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withOpacity(0.3)),
      ),
      child: Column(
        children: [
          Icon(icon, color: color, size: 14),
          SizedBox(height: 2),
          Text(
            value,
            style: TextStyle(
              color: isDarkMode ? Colors.white : Colors.black87,
              fontSize: 12,
              fontWeight: FontWeight.bold,
            ),
          ),
          Text(
            label,
            style: TextStyle(
              color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54,
              fontSize: 9,
            ),
          ),
        ],
      ),
    );
  }

  void onTabTapped(int index) {
    if (_currentIndex == index) return; // 이미 현재 탭이면 아무것도 안함

    _showInterstitialAdAndNavigate(index);
     // 광고 후 또는 광고 없을 시 실제 네비게이션은 _navigateToPage에서 처리하고, 거기서 _currentIndex를 업데이트
  }

  void _showInterstitialAdAndNavigate(int pageIndex) {
    final adState = Provider.of<AdState>(context, listen: false);
    if (adState.adsRemoved || !_isAdLoaded || _interstitialAd == null) {
      _navigateToPage(pageIndex);
      return;
    }

    _interstitialAd!.fullScreenContentCallback = FullScreenContentCallback(
      onAdDismissedFullScreenContent: (ad) {
        ad.dispose();
        setState(() => _isAdLoaded = false);
        _navigateToPage(pageIndex);
        if (!adState.adsRemoved) _loadInterstitialAd();
      },
      onAdFailedToShowFullScreenContent: (ad, error) {
        ad.dispose();
        setState(() => _isAdLoaded = false);
        _navigateToPage(pageIndex);
        if (!adState.adsRemoved) _loadInterstitialAd();
      },
    );
    _interstitialAd!.show();
  }

 void _navigateToPage(int index) {
    // 현재 화면과 같은 탭을 눌렀을 때 중복 이동 방지 (onTabTapped에서 이미 처리하지만 안전장치)
    if (_currentIndex == index && ModalRoute.of(context)?.settings.name == _getRouteNameForIndex(index)) {
        return;
    }
    
    setState(() {
      _currentIndex = index; // 여기서 currentIndex 업데이트
    });

    Widget page;
    String routeName;

    switch (index) {
      case 0: // 문제풀이 (현재 화면이므로, 새로고침 또는 특정 동작을 원할 수 있음)
        // 현재 화면이 QuestionScreenPage 이므로, 다시 push 하는 대신,
        // 상태를 초기화하거나 특정 동작을 수행할 수 있습니다.
        // 여기서는 의도적으로 같은 화면을 다시 push하여 새로고침 효과를 주도록 유지합니다.
        // (만약 다른 동작을 원한다면 이 부분을 수정)
        page = QuestionScreenPage(
          round: widget.round,
          dbPath: widget.dbPath,
        );
        routeName = '/questionScreen';
        break;
      case 1:
        page = WrongAnswerPage(
          round: widget.round,
          dbPath: widget.dbPath,
        );
        routeName = '/wrongAnswer';
        break;
      case 2:
        page = BookmarkPage(
          round: widget.round,
          dbPath: widget.dbPath,
        );
        routeName = '/bookmark';
        break;
      default:
        return;
    }

    // 현재 라우트와 목표 라우트가 다를 경우에만 pushReplacement
    // HomePage로 가는 케이스가 아니므로 pushReplacement대신 push를 사용하거나,
    // 스택 관리를 더 명확히 할 필요가 있습니다.
    // 여기서는 단순 push를 사용하여 뒤로가기 시 이전 문제풀이 화면으로 돌아올 수 있게 합니다.
    // 만약 탭 이동 시 이전 화면을 스택에서 제거하고 싶다면 Navigator.pushReplacement를 사용합니다.
     Navigator.push(
        context,
        MaterialPageRoute(
            builder: (context) => page,
            settings: RouteSettings(name: routeName),
        ),
    );
  }

  String _getRouteNameForIndex(int index) {
    switch (index) {
      case 0: return '/questionScreen';
      case 1: return '/wrongAnswer';
      case 2: return '/bookmark';
      default: return '';
    }
  }
  
  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: ThemedBackgroundWidget(
        isDarkMode: isDarkMode,
        child: SafeArea(
          child: FadeTransition(
            opacity: _fadeAnimation,
            child: SlideTransition(
              position: _slideAnimation,
              child: Column(
                children: [
                CommonHeaderWidget(
                  title: '문제풀이',
                  subtitle: widget.round,
                  // ▼▼▼▼▼ 이 줄을 추가해 주세요! ▼▼▼▼▼
                  onHomePressed: () => Navigator.pushAndRemoveUntil(
                    context,
                    MaterialPageRoute(builder: (_) => HomePage()),
                    (route) => false,
                  ),
                ),
                  Expanded(
                    child: FutureBuilder<List<Map<String, dynamic>>>(
                      future: futureQuestions,
                      builder: (ctx, snapshot) {
                        if (snapshot.connectionState == ConnectionState.waiting) {
                          return Center( child: CircularProgressIndicator() );
                        }
                        if (snapshot.hasError) {
                          return Center( child: Text('오류가 발생했습니다: ${snapshot.error}') );
                        }
                        if (!snapshot.hasData || snapshot.data!.isEmpty) {
                          return Center( child: Text('해당 회차의 문제가 없습니다.') );
                        }
                        final questions = snapshot.data!;

                        return Column(
                          children: [
                            _buildCompactProgressCard(questions, isDarkMode),
                            Expanded(
                              child: ListView.builder(
                                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                                itemCount: questions.length,
                                itemBuilder: (ctx, index) {
                                  final question = questions[index];
                                  final qId = question['Question_id'];
                                  final userSelected = selectedOptions[qId];
                                  final isSaved = savedQuestions[qId] ?? false;
                                  final showDesc = showAnswerDescription[qId] ?? false;
                                  final catStr = question['Category'] ?? '';

                                  return Container(
                                    margin: EdgeInsets.only(bottom: 12), 
                                    decoration: BoxDecoration(
                                      color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.white.withOpacity(0.9),
                                      borderRadius: BorderRadius.circular(16),
                                      border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.black.withOpacity(0.08)),
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.black.withOpacity(0.05),
                                          blurRadius: 8,
                                          offset: Offset(0, 3),
                                        ),
                                      ],
                                    ),
                                    child: Padding(
                                      padding: const EdgeInsets.all(14.0), 
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Expanded(
                                                child: Row(
                                                  crossAxisAlignment: CrossAxisAlignment.center,
                                                  children: [
                                                    Text(
                                                      '문제 ${qId}',
                                                      style: TextStyle(
                                                        fontSize: 16,
                                                        fontWeight: FontWeight.bold,
                                                        color: isDarkMode ? Colors.white : Colors.black87,
                                                      ),
                                                    ),
                                                    SizedBox(width: 8), 
                                                    if (catStr.isNotEmpty)
                                                      Container(
                                                        padding: EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                                        decoration: BoxDecoration(
                                                          color: Color(0xFF8E9AAF).withOpacity(0.15),
                                                          borderRadius: BorderRadius.circular(8),
                                                        ),
                                                        child: Text(
                                                          catStr,
                                                          style: TextStyle(
                                                            fontSize: 12,
                                                            fontWeight: FontWeight.w500,
                                                            color: Color(0xFF8E9AAF),
                                                          ),
                                                        ),
                                                      ),
                                                  ],
                                                ),
                                              ),
                                              GestureDetector(
                                                onTap: () => handleBookmarkTap(qId),
                                                child: Container(
                                                  padding: EdgeInsets.all(7),
                                                  decoration: BoxDecoration(
                                                    color: isSaved ? Color(0xFF2196F3).withOpacity(0.15) : (isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.withOpacity(0.1)),
                                                    borderRadius: BorderRadius.circular(8),
                                                  ),
                                                  child: Icon(
                                                    isSaved ? Icons.bookmark_rounded : Icons.bookmark_border_rounded,
                                                    color: isSaved ? Color(0xFF2196F3) : Colors.grey.shade600,
                                                    size: 18,
                                                  ),
                                                ),
                                              ),
                                            ],
                                          ),
                                          SizedBox(height: 10), 

                                          _buildBigQuestionWidget(question, isDarkMode),
                                          if (question['Big_Question'] != null && question['Big_Question'].isNotEmpty)
                                            const SizedBox(height: 8), 

                                          // =================================================
                                          // NEW WIDGET ADDED HERE
                                          // 'Big_Question_Special'을 표시하기 위한 위젯
                                          _buildBigQuestionSpecialWidget(question, isDarkMode),
                                          // =================================================

                                          _buildModernQuestionWidget(question['Question'], isDarkMode),
                                          if (question['Question'] != null)
                                             const SizedBox(height: 14), 

                                          _buildUnifiedOptionsWidget(qId, question, userSelected, isDarkMode),

                                          if (showDesc)
                                            _buildModernDescWidget(question['Answer_description'], isDarkMode),
                                        ],
                                      ),
                                    ),
                                  );
                                },
                              ),
                            ),
                          ],
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
      bottomNavigationBar: Container(
        decoration: BoxDecoration(
          color: isDarkMode ? Color(0xFF2C2C2C) : Colors.white,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 10,
              offset: Offset(0, -5),
            ),
          ],
        ),
        child: BottomNavigationBar(
          currentIndex: _currentIndex,
          onTap: onTabTapped,
          backgroundColor: Colors.transparent,
          elevation: 0,
          selectedItemColor: Color(0xFF8E9AAF),
          unselectedItemColor: isDarkMode ? Colors.white.withOpacity(0.6) : Colors.black54,
          selectedLabelStyle: TextStyle(fontWeight: FontWeight.bold, fontSize: 11),
          unselectedLabelStyle: TextStyle(fontSize: 11),
          type: BottomNavigationBarType.fixed,
          items: const [
            BottomNavigationBarItem(
              icon: Icon(Icons.edit_document, size: 22),
              label: '문제풀이',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.quiz_rounded, size: 22),
              label: '오답노트',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.bookmark_rounded, size: 22),
              label: '즐겨찾기',
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBigQuestionWidget(Map<String, dynamic> question, bool isDarkMode) {
  final bigQ = question['Big_Question'];

  if (bigQ is String && bigQ.isNotEmpty) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isDarkMode ? Colors.white.withOpacity(0.05) : Colors.grey.shade50,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200),
      ),
      child: Html(
        data: bigQ,
        style: {
          "body": Style(
            fontSize: FontSize(15),
            fontWeight: FontWeight.w500,
            lineHeight: LineHeight(1.4),
            color: isDarkMode ? Colors.white.withOpacity(0.9) : Colors.black.withOpacity(0.85),
            margin: Margins.zero,
            padding: HtmlPaddings.zero,
          ),
        },
      ),
    );
  }
  return const SizedBox.shrink();
}

// =================================================
// NEW WIDGET FUNCTION
// 'Big_Question_Special' 이미지를 렌더링하는 함수
// =================================================
Widget _buildBigQuestionSpecialWidget(Map<String, dynamic> question, bool isDarkMode) {
  final bigQSpecial = question['Big_Question_Special'];

  if (bigQSpecial is Uint8List && bigQSpecial.isNotEmpty) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 8), // 위젯 아래에 간격 추가
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(10.0),
        child: Image.memory(
          bigQSpecial,
          fit: BoxFit.contain, // 이미지가 잘리지 않고 모두 보이도록 설정
        ),
      ),
    );
  }
  return const SizedBox.shrink(); // 데이터가 없으면 아무것도 표시하지 않음
}


Widget _buildModernQuestionWidget(dynamic data, bool isDarkMode) {
  if (data == null) return SizedBox.shrink();

  if (data is String && data.isNotEmpty) {
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isDarkMode ? Colors.white.withOpacity(0.05) : Colors.grey.shade50,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200),
      ),
      child: Html(
        data: data,
        style: {
          "body": Style(
            fontSize: FontSize(16),
            fontWeight: FontWeight.w500,
            color: isDarkMode ? Colors.white : Colors.black87,
            lineHeight: LineHeight(1.5),
            margin: Margins.zero,
            padding: HtmlPaddings.zero,
          ),
        },
      ),
    );
  } else if (data is Uint8List && data.isNotEmpty) {
    // 이미지 데이터(BLOB)를 표시하는 코드
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(10.0),
        child: Image.memory(
          data,
          fit: BoxFit.contain,
        ),
      ),
    );
  }
  return SizedBox.shrink();
}
  Widget _buildUnifiedOptionsWidget(
    int qId,
    Map<String, dynamic> question,
    String? selectedOpt,
    bool isDarkMode,
  ) {
    final correctStr = question['Correct_Option']?.toString() ?? '';
    
    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.grey.shade300, width: 1),
      ),
      child: Column(
        children: [
          _buildOptionRow(qId, question['Option1'], '1', correctStr, selectedOpt, question, isDarkMode, isFirst: true),
          _buildDividerLine(isDarkMode),
          _buildOptionRow(qId, question['Option2'], '2', correctStr, selectedOpt, question, isDarkMode),
          _buildDividerLine(isDarkMode),
          _buildOptionRow(qId, question['Option3'], '3', correctStr, selectedOpt, question, isDarkMode),
          _buildDividerLine(isDarkMode),
          _buildOptionRow(qId, question['Option4'], '4', correctStr, selectedOpt, question, isDarkMode, isLast: true),
        ],
      ),
    );
  }

  Widget _buildDividerLine(bool isDarkMode) {
    return Container(
      height: 1,
      color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200,
    );
  }

Widget _buildOptionRow(
  int qId,
  dynamic optData,
  String letter,
  String correctStr,
  String? selectedOpt,
  Map<String, dynamic> question,
  bool isDarkMode, {
  bool isFirst = false,
  bool isLast = false,
}) {
  if (optData == null || (optData is String && optData.isEmpty)) return SizedBox.shrink();

  final isSelected = (selectedOpt == letter);
  final isAnswered = selectedOpt != null;
  final isCorrectChoice = (letter == correctStr);

  Color backgroundColor = Colors.transparent;
  Color textColor = isDarkMode ? Colors.white.withOpacity(0.85) : Colors.black.withOpacity(0.75);
  FontWeight fontWeight = FontWeight.normal;
  IconData radioIcon = Icons.radio_button_unchecked_rounded;
  Color radioColor = Colors.grey.shade500;

  if (isAnswered) {
    if (isSelected) {
      if (isCorrectChoice) {
        backgroundColor = Color(0xFF4CAF50).withOpacity(0.1);
        textColor = isDarkMode ? Color(0xFF81C784) : Color(0xFF388E3C);
        fontWeight = FontWeight.w600;
        radioIcon = Icons.check_circle_rounded;
        radioColor = Color(0xFF4CAF50);
      } else {
        backgroundColor = Color(0xFFF44336).withOpacity(0.1);
        textColor = isDarkMode ? Color(0xFFE57373) : Color(0xFFD32F2F);
        fontWeight = FontWeight.w600;
        radioIcon = Icons.cancel_rounded;
        radioColor = Color(0xFFF44336);
      }
    } else if (isCorrectChoice) {
      backgroundColor = Color(0xFF4CAF50).withOpacity(0.05);
      textColor = isDarkMode ? Color(0xFF81C784).withOpacity(0.8) : Color(0xFF388E3C).withOpacity(0.8);
      radioIcon = Icons.check_circle_outline_rounded;
      radioColor = Color(0xFF4CAF50).withOpacity(0.7);
    }
  }

  Widget childWidget;
  if (optData is String) {
    // Text 위젯을 Html 위젯으로 교체
    childWidget = Html(
      data: optData,
      style: {
        "body": Style(
          fontSize: FontSize(15),
          color: textColor,
          fontWeight: fontWeight,
          lineHeight: LineHeight(1.4),
          margin: Margins.zero,
          padding: HtmlPaddings.zero,
        ),
      },
    );
  } else if (optData is Uint8List && optData.isNotEmpty) {
    childWidget = ClipRRect(
        borderRadius: BorderRadius.circular(8.0),
        child: Image.memory(optData, fit: BoxFit.contain),
    );
  } else {
    return SizedBox.shrink();
  }

  return GestureDetector(
    onTap: (selectedOpt == null)
        ? () => handleOptionTap(qId, letter, correctStr, question)
        : null,
    child: Container(
      padding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.only(
          topLeft: isFirst ? Radius.circular(10) : Radius.zero,
          topRight: isFirst ? Radius.circular(10) : Radius.zero,
          bottomLeft: isLast ? Radius.circular(10) : Radius.zero,
          bottomRight: isLast ? Radius.circular(10) : Radius.zero,
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: radioColor.withOpacity(isAnswered && isCorrectChoice && !isSelected ? 0.05 : 0.1),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              radioIcon,
              color: radioColor,
              size: 18,
            ),
          ),
          SizedBox(width: 12),
          Expanded(child: childWidget),
        ],
      ),
    ),
  );
}

  Widget _buildModernDescWidget(dynamic descData, bool isDarkMode) {
    if (descData == null) return SizedBox.shrink();
    
    Widget content;
    if (descData is String && descData.isNotEmpty) {
      content = Text(
        descData,
        style: TextStyle(
          fontSize: 15,
          height: 1.5,
          color: isDarkMode ? Color(0xFF90CAF9) : Color(0xFF1E88E5),
        ),
      );
    } else if (descData is Uint8List && descData.isNotEmpty) {
       content = ClipRRect(
         borderRadius: BorderRadius.circular(8.0),
         child: Image.memory(descData, fit: BoxFit.contain),
       );
    } else {
      return SizedBox.shrink();
    }

    return Container(
      margin: const EdgeInsets.only(top: 14), 
      padding: const EdgeInsets.all(12), 
      decoration: BoxDecoration(
        color: Color(0xFF2196F3).withOpacity(0.08),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Color(0xFF2196F3).withOpacity(0.25), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: EdgeInsets.all(5),
                decoration: BoxDecoration(
                  color: Color(0xFF2196F3),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Icon(
                  Icons.lightbulb_outline_rounded,
                  color: Colors.white,
                  size: 14,
                ),
              ),
              SizedBox(width: 8),
              Text(
                '정답 해설',
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF2196F3),
                ),
              ),
            ],
          ),
          SizedBox(height: 10), 
          content,
        ],
      ),
    );
  }
}