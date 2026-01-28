import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'dart:typed_data';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:flutter_html/flutter_html.dart';
import 'database_helper.dart';
import 'home.dart';
import 'category_wronganswer.dart';
import 'category_bookmark.dart';
import 'ad_helper.dart';
import 'ad_config.dart';
import 'package:provider/provider.dart'; // AdState 사용을 위해 추가
import 'ad_state.dart'; // AdState 사용을 위해 추가
import 'constants.dart'; // 필요시 추가 (getCategory 등)
import 'statistics.dart'; // recordCategoryLearningSession import


class QuestionListPage extends StatefulWidget {
  final String category;
  final String databaseId;
  final String round;
  final String dbPath;

  QuestionListPage({
    required this.category,
    required this.databaseId,
    required this.round,
    required this.dbPath,
  });

  @override
  _QuestionListPageState createState() => _QuestionListPageState();
}

class _QuestionListPageState extends State<QuestionListPage> with TickerProviderStateMixin {
  late Future<List<Map<String, dynamic>>> futureQuestions;
  late DatabaseHelper dbHelper;

  Map<int, String> selectedOptions = {};
  Map<int, bool> isCorrectOptions = {};
  Map<int, bool> showAnswerDescription = {};
  Map<String, bool> savedQuestionsState = {}; // 북마크 UI 즉시 반영
  List<String> correctAnswers = []; // 전체 앱 기준
  List<String> wrongAnswers = []; // 전체 앱 기준

  InterstitialAd? _interstitialAd;
  bool _isAdLoaded = false;
  int _currentIndex = 0;
  bool _isStatsExpanded = false;

  late AnimationController _fadeController;
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    dbHelper = DatabaseHelper.getInstance(widget.dbPath);
    loadCorrectWrongAnswers(); // 전체 정오답 로드
    futureQuestions = fetchQuestionsByCategory(widget.category);
    loadSavedQuestions(); // 북마크 상태 로드
    loadSelectedStatesFromPrefs(); // 이 화면의 선택 상태 로드
    
    final adState = Provider.of<AdState>(context, listen: false);
    if (!adState.adsRemoved) {
      _loadInterstitialAd();
    }
    
    _fadeController = AnimationController(duration: const Duration(milliseconds: 1200), vsync: this);
    _slideController = AnimationController(duration: const Duration(milliseconds: 1000), vsync: this);
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(parent: _fadeController, curve: Curves.easeInOut));
    _slideAnimation = Tween<Offset>(begin: Offset(0, 0.2), end: Offset.zero).animate(CurvedAnimation(parent: _slideController, curve: Curves.easeOutCubic));
    _fadeController.forward();
    _slideController.forward();
  }

  @override
void dispose() {
  // 페이지를 떠날 때 학습 세션 기록
  if (selectedOptions.isNotEmpty) {
    recordCategoryLearningSession(widget.category, selectedOptions, isCorrectOptions);
  }
  
  _interstitialAd?.dispose();
  _fadeController.dispose();
  _slideController.dispose();
  super.dispose();
}

  // 전체 앱 기준 정오답 목록 로드/저장 (키: "dbId|category|questionId")
  Future<void> loadCorrectWrongAnswers() async {
    final prefs = await SharedPreferences.getInstance();
    correctAnswers = prefs.getStringList('correctAnswers') ?? [];
    wrongAnswers = prefs.getStringList('wrongAnswers') ?? [];
  }

  Future<void> saveAnswersToPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('correctAnswers', correctAnswers);
    await prefs.setStringList('wrongAnswers', wrongAnswers);
  }

  Future<List<Map<String, dynamic>>> fetchQuestionsByCategory(String category) async {
    List<Map<String, dynamic>> rawQuestions = await dbHelper.getQuestionsByCategory(category);
    return rawQuestions.map((q) => _convertFieldsToImageOrText(q)).toList();
  }
  
  Map<String, dynamic> _convertFieldsToImageOrText(Map<String, dynamic> question) {
    final Map<String, dynamic> modifiedQuestion = Map<String, dynamic>.from(question);
    modifiedQuestion['Big_Question'] = _processFieldData(modifiedQuestion['Big_Question']);
    modifiedQuestion['Big_Question_Special'] = _processFieldData(modifiedQuestion['Big_Question_Special']);
    modifiedQuestion['Question'] = _processFieldData(modifiedQuestion['Question']);
    for (var optionField in ['Option1', 'Option2', 'Option3', 'Option4']) {
      modifiedQuestion[optionField] = _processFieldData(modifiedQuestion[optionField]);
    }
    modifiedQuestion['Answer_description'] = _processFieldData(modifiedQuestion['Answer_description']);
    return modifiedQuestion;
  }

  dynamic _processFieldData(dynamic fieldData) {
    if (fieldData != null) {
      if (fieldData is List<int>) return Uint8List.fromList(fieldData);
      if (fieldData is String && fieldData.isNotEmpty) return fieldData;
    }
    return '';
  }


  Future<void> loadSavedQuestions() async {
    final prefs = await SharedPreferences.getInstance();
    List<String> savedList = prefs.getStringList('savedQuestions') ?? [];
    Map<String, bool> currentSavedStatus = {};
    for (String item in savedList) {
       currentSavedStatus[item] = true;
    }
     if (mounted) {
      setState(() {
        savedQuestionsState = currentSavedStatus;
      });
    }
  }

  Future<void> loadSelectedStatesFromPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    // 이 화면(카테고리별 문제풀이)의 선택 상태만 로드
    // 키 형식: "selected_DBID|카테고리|문제ID"
    // 키 형식: "showDescription_DBID|카테고리|문제ID"
    String basePrefix = '${widget.databaseId}|${widget.category}|';

    for (String key in prefs.getKeys()) {
      if (key.startsWith('selected_$basePrefix')) {
        final qIdStr = key.substring('selected_$basePrefix'.length);
        int? qId = int.tryParse(qIdStr);
        if (qId != null) {
          final selectedValue = prefs.getString(key);
          if (selectedValue != null) {
            if(mounted) setState(() { selectedOptions[qId] = selectedValue; });
          }
        }
      }
      if (key.startsWith('showDescription_$basePrefix')) {
         final qIdStr = key.substring('showDescription_$basePrefix'.length);
        int? qId = int.tryParse(qIdStr);
        if (qId != null) {
          final showDescStr = prefs.getString(key);
          if (showDescStr != null) {
             if(mounted) setState(() { showAnswerDescription[qId] = (showDescStr == 'true'); });
          }
        }
      }
    }
  }

  Future<void> saveSelectedStateToPrefs(int questionId, String optionLetter) async {
    final prefs = await SharedPreferences.getInstance();
    final key = 'selected_${widget.databaseId}|${widget.category}|$questionId';
    await prefs.setString(key, optionLetter);
  }

  Future<void> saveShowDescriptionToPrefs(int questionId, bool show) async {
    final prefs = await SharedPreferences.getInstance();
    final key = 'showDescription_${widget.databaseId}|${widget.category}|$questionId';
    await prefs.setString(key, show.toString());
  }

  Future<void> resetCategoryProgress() async {
    final prefs = await SharedPreferences.getInstance();
    final prefix = '${widget.databaseId}|${widget.category}|';
    
    // 전체 오답 목록에서 현재 카테고리 문제들 제거
    List<String> globalWrongAnswers = prefs.getStringList('wrongAnswers') ?? [];
    globalWrongAnswers.removeWhere((item) => item.startsWith(prefix));
    await prefs.setStringList('wrongAnswers', globalWrongAnswers);
    
    // 전체 정답 목록에서 현재 카테고리 문제들 제거
    List<String> globalCorrectAnswers = prefs.getStringList('correctAnswers') ?? [];
    globalCorrectAnswers.removeWhere((item) => item.startsWith(prefix));
    await prefs.setStringList('correctAnswers', globalCorrectAnswers);


    final keysToRemove = prefs.getKeys().where((key) =>
            key.startsWith('selected_$prefix') ||
            key.startsWith('showDescription_$prefix')).toList();
    for (var key in keysToRemove) {
      await prefs.remove(key);
    }

    if(mounted) {
      setState(() {
        selectedOptions.clear();
        isCorrectOptions.clear(); // isCorrectOptions는 handleOptionTap에서 관리되므로, selectedOptions 클리어로 충분할 수 있음
        showAnswerDescription.clear();
        // UI용 정오답 상태도 초기화
        correctAnswers.removeWhere((item) => item.startsWith(prefix));
        wrongAnswers.removeWhere((item) => item.startsWith(prefix));

      });
    }
    Fluttertoast.showToast(msg: "${widget.category} 풀이 상태가 초기화되었습니다.");
  }

  void _loadInterstitialAd() {
    InterstitialAd.load(
      adUnitId: AdHelper.interstitialAdUnitId,
      request: AdRequest(),
      adLoadCallback: InterstitialAdLoadCallback(
        onAdLoaded: (ad) { _interstitialAd = ad; _isAdLoaded = true; },
        onAdFailedToLoad: (error) { _isAdLoaded = false; },
      ),
    );
  }

  void _showInterstitialAdAndNavigateWrapper(int pageIndex) {
    final adState = Provider.of<AdState>(context, listen: false);
     if (adState.adsRemoved || pageIndex == _currentIndex) { // 현재 탭과 같으면 광고 없이 네비게이션 (또는 아무것도 안함)
      _navigateToPage(pageIndex);
      return;
    }
    if (_isAdLoaded && _interstitialAd != null) {
      _interstitialAd!.fullScreenContentCallback = FullScreenContentCallback(
        onAdDismissedFullScreenContent: (ad) {
          ad.dispose(); _isAdLoaded = false;
          _navigateToPage(pageIndex);
          if (!adState.adsRemoved) _loadInterstitialAd();
        },
        onAdFailedToShowFullScreenContent: (ad, error) {
          ad.dispose(); _isAdLoaded = false;
          _navigateToPage(pageIndex);
          if (!adState.adsRemoved) _loadInterstitialAd();
        },
      );
      _interstitialAd!.show();
    } else {
      _navigateToPage(pageIndex);
    }
  }

  void _navigateToPage(int index) {
    setState(() => _currentIndex = index);
    Widget page;
    String routeName;
    switch (index) {
      case 0: // 현재 페이지 (문제풀이)
        // 필요시 새로고침 로직 추가
        return;
      case 1:
        page = CategoryWrongAnswerPage(category: widget.category, databaseId: widget.databaseId, round: widget.round, dbPath: widget.dbPath);
        routeName = '/categoryWrongAnswer';
        break;
      case 2:
        page = CategoryBookmarkPage(category: widget.category, databaseId: widget.databaseId, round: widget.round, dbPath: widget.dbPath);
        routeName = '/categoryBookmark';
        break;
      default:
        return;
    }
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (context) => page, settings: RouteSettings(name: routeName)));
  }

  void handleOptionTap(int questionId, String selectedOpt, dynamic correctOption) async {
    final correctOptStr = correctOption.toString();
    final saveKey = '${widget.databaseId}|${widget.category}|$questionId';

    setState(() {
      selectedOptions[questionId] = selectedOpt;
      isCorrectOptions[questionId] = (selectedOpt == correctOptStr);
      showAnswerDescription[questionId] = true;
    });

    await saveSelectedStateToPrefs(questionId, selectedOpt);
    await saveShowDescriptionToPrefs(questionId, true);

    if (selectedOpt == correctOptStr) {
      if (!correctAnswers.contains(saveKey)) correctAnswers.add(saveKey);
      wrongAnswers.remove(saveKey);
    } else {
      if (!wrongAnswers.contains(saveKey)) wrongAnswers.add(saveKey);
      correctAnswers.remove(saveKey);
    }
    await saveAnswersToPrefs(); // 변경된 전체 정오답 목록 저장

    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(selectedOpt == correctOptStr ? '정답입니다!' : '오답입니다!', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
      backgroundColor: selectedOpt == correctOptStr ? Color(0xFF4CAF50) : Color(0xFFF44336),
      behavior: SnackBarBehavior.floating, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)), duration: Duration(milliseconds: 1500),
    ));
  }

  Future<void> handleSaveTap(int questionId) async {
    String saveKey = '${widget.databaseId}|${widget.category}|$questionId';
    bool isCurrentlySaved = savedQuestionsState[saveKey] ?? false;
    bool newSaveStatus = !isCurrentlySaved;

    setState(() {
      savedQuestionsState[saveKey] = newSaveStatus;
    });

    final prefs = await SharedPreferences.getInstance();
    List<String> savedList = prefs.getStringList('savedQuestions') ?? [];
    if (newSaveStatus) {
      if (!savedList.contains(saveKey)) savedList.add(saveKey);
    } else {
      savedList.remove(saveKey);
    }
    await prefs.setStringList('savedQuestions', savedList);
    Fluttertoast.showToast(msg: newSaveStatus ? '북마크에 추가되었습니다.' : '북마크에서 삭제되었습니다.');
  }

  void onTabTapped(int index) {
    if (_currentIndex == index) return;
    _showInterstitialAdAndNavigateWrapper(index);
  }

  Widget _buildModernHeader(bool isDarkMode) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        children: [
          GestureDetector(onTap: () => Navigator.pop(context), child: Container(padding: EdgeInsets.all(5), decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.white.withOpacity(0.7), borderRadius: BorderRadius.circular(8), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1))), child: Icon(Icons.arrow_back_ios_rounded, color: isDarkMode ? Colors.white : Colors.black87, size: 16))),
          SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${widget.category}', style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 0.3)),
            Text('${widget.round}', style: TextStyle(color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54, fontSize: 11, fontWeight: FontWeight.w400)),
          ])),
          GestureDetector(onTap: () => Navigator.pushAndRemoveUntil(context, MaterialPageRoute(builder: (_) => HomePage()), (route)=>false), child: Container(padding: EdgeInsets.all(5), decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.white.withOpacity(0.7), borderRadius: BorderRadius.circular(8), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1))), child: Icon(Icons.home_rounded, color: isDarkMode ? Colors.white : Colors.black87, size: 18))),
        ],
      ),
    );
  }

  Widget _buildCompactProgressCard(List<Map<String, dynamic>> questions, bool isDarkMode) {
    final totalCount = questions.length;
    int answeredCount = 0;
    int correctCount = 0;

    // 현재 카테고리, 현재 라운드(databaseId)에 해당하는 문제들의 진행 상태만 계산
    String currentProgressPrefix = '${widget.databaseId}|${widget.category}|';
    
    // selectedOptions는 Question_id를 키로 사용하므로, 현재 로드된 questions 리스트 기준으로 계산
     for (var q in questions) {
        int qId = q['Question_id'];
        if (selectedOptions.containsKey(qId)) {
            answeredCount++;
            if (isCorrectOptions[qId] == true) {
                correctCount++;
            }
        }
    }

    final wrongCount = answeredCount - correctCount;
    final progress = (totalCount == 0) ? 0.0 : (answeredCount / totalCount);


    return Container(
      margin: EdgeInsets.symmetric(horizontal: 12, vertical: 3), // MODIFIED
      decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.white.withOpacity(0.9), borderRadius: BorderRadius.circular(10), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.black.withOpacity(0.08)), boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 4,offset: Offset(0, 1))]), // MODIFIED
      child: Column(children: [
        Padding(padding: EdgeInsets.all(10), child: Column(children: [
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text('학습 진행률', style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 13, fontWeight: FontWeight.bold)),
            GestureDetector(
              onTap: () async {
                bool? confirm = await showDialog(context: context, builder: (ctx) => AlertDialog(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)), title: Row(children: [Container(padding: EdgeInsets.all(8), decoration: BoxDecoration(color: Colors.orange.withOpacity(0.2), borderRadius: BorderRadius.circular(8)), child: Icon(Icons.refresh_rounded, color: Colors.orange)), SizedBox(width: 12), Text("풀이 상태 초기화")]), content: Text("지금까지 풀었던 문제를 모두 초기화하시겠습니까?"), actions: [TextButton(child: Text("취소", style: TextStyle(color: Colors.grey[600])), onPressed: () => Navigator.pop(ctx, false)), ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: Colors.orange, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))), child: Text("초기화", style: TextStyle(color: Colors.white)), onPressed: () => Navigator.pop(ctx, true))]));
                if (confirm == true) { await resetCategoryProgress(); }
              },
              child: Container(padding: EdgeInsets.all(3), decoration: BoxDecoration(color: Colors.orange.withOpacity(0.2), borderRadius: BorderRadius.circular(5)), child: Icon(Icons.refresh_rounded, color: Colors.orange, size: 14)),
            ),
          ]),
          SizedBox(height: 6),
          Row(children: [
            Expanded(child: Container(height: 2.5, decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade300, borderRadius: BorderRadius.circular(1.25)), child: ClipRRect(borderRadius: BorderRadius.circular(1.25), child: LinearProgressIndicator(value: progress, backgroundColor: Colors.transparent, valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF8E9AAF)), minHeight: 2.5)))),
            SizedBox(width: 8), Text('$answeredCount/$totalCount', style: TextStyle(color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54, fontSize: 11, fontWeight: FontWeight.w500)), SizedBox(width: 4),
            GestureDetector(onTap: () { setState(() { _isStatsExpanded = !_isStatsExpanded; }); }, child: Container(padding: EdgeInsets.all(2), child: AnimatedRotation(turns: _isStatsExpanded ? 0.5 : 0, duration: Duration(milliseconds: 200), child: Icon(Icons.keyboard_arrow_down_rounded, color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54, size: 16)))),
          ]),
        ])),
        AnimatedContainer(duration: Duration(milliseconds: 300), curve: Curves.easeInOut, height: _isStatsExpanded ? null : 0, child: _isStatsExpanded ? Container(padding: EdgeInsets.fromLTRB(10, 0, 10, 10), child: Column(children: [
          Divider(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade300, height: 1), SizedBox(height: 8),
          Row(children: [
            Expanded(child: _buildCompactStatContainer(icon: Icons.assignment_turned_in_rounded, label: '완료', value: '$answeredCount', color: Color(0xFF8E9AAF), isDarkMode: isDarkMode)), SizedBox(width: 4),
            Expanded(child: _buildCompactStatContainer(icon: Icons.check_circle_rounded, label: '정답', value: '$correctCount', color: Color(0xFF4CAF50), isDarkMode: isDarkMode)), SizedBox(width: 4),
            Expanded(child: _buildCompactStatContainer(icon: Icons.cancel_rounded, label: '오답', value: '$wrongCount', color: Color(0xFFF44336), isDarkMode: isDarkMode)),
          ]),
        ])) : SizedBox.shrink()),
      ]),
    );
  }

  Widget _buildCompactStatContainer({required IconData icon, required String label, required String value, required Color color, required bool isDarkMode}) {
    return Container(padding: EdgeInsets.symmetric(vertical: 6, horizontal: 8), decoration: BoxDecoration(color: color.withOpacity(0.1), borderRadius: BorderRadius.circular(6), border: Border.all(color: color.withOpacity(0.3))),
      child: Column(children: [
        Icon(icon, color: color, size: 14), SizedBox(height: 2),
        Text(value, style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 12, fontWeight: FontWeight.bold)),
        Text(label, style: TextStyle(color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54, fontSize: 9)),
      ]),
    );
  }

  Widget _buildBigQuestionSpecialWidget(Map<String, dynamic> question, bool isDarkMode) {
    final bigQSpecial = question['Big_Question_Special'];

    if (bigQSpecial is Uint8List && bigQSpecial.isNotEmpty) {
      return Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(10.0),
          child: Image.memory(
            bigQSpecial,
            fit: BoxFit.contain,
          ),
        ),
      );
    }
    return const SizedBox.shrink();
  }

  Widget _buildBigQuestionWidget(dynamic bigQuestionData, bool isDarkMode) {
    if (bigQuestionData is String && bigQuestionData.isNotEmpty) {
      return Container(width: double.infinity, padding: EdgeInsets.all(12), decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.05) : Colors.grey.shade50, borderRadius: BorderRadius.circular(10), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200)), child: Html(data: bigQuestionData, style: {"body": Style(fontSize: FontSize(15), fontWeight: FontWeight.w500, lineHeight: LineHeight(1.4), color: isDarkMode ? Colors.white.withOpacity(0.9) : Colors.black.withOpacity(0.85), margin: Margins.zero, padding: HtmlPaddings.zero)}));
    } else if (bigQuestionData is Uint8List && bigQuestionData.isNotEmpty) {
      return Container(width: double.infinity, padding: EdgeInsets.all(12), decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.05) : Colors.grey.shade50, borderRadius: BorderRadius.circular(10), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200)), child: ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.memory(bigQuestionData)));
    }
    return const SizedBox.shrink();
  }

  Widget _buildModernQuestionWidget(dynamic questionData, bool isDarkMode) {
    if (questionData == null) return SizedBox.shrink();
    if (questionData is String && questionData.isNotEmpty) {
      return Container(width: double.infinity, padding: EdgeInsets.all(12), decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.05) : Colors.grey.shade50, borderRadius: BorderRadius.circular(10), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200)), child: Html(data: questionData, style: {"body": Style(fontSize: FontSize(16), lineHeight: LineHeight(1.5), fontWeight: FontWeight.w500, color: isDarkMode ? Colors.white : Colors.black87, margin: Margins.zero, padding: HtmlPaddings.zero)}));
    } else if (questionData is Uint8List && questionData.isNotEmpty) {
       return Container(width: double.infinity, padding: EdgeInsets.all(12), decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.05) : Colors.grey.shade50, borderRadius: BorderRadius.circular(10), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200)), child: ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.memory(questionData)));
    }
    return SizedBox.shrink();
  }

  Widget _buildUnifiedOptionsWidget(int qId, Map<String, dynamic> question, String? selectedOpt, bool isDarkMode) {
    final correctStr = question['Correct_Option']?.toString() ?? '';
    return Container(decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.grey.shade300, width: 1)),
      child: Column(children: [
        _buildOptionRow(qId, question['Option1'], '1', correctStr, selectedOpt, question, isDarkMode, isFirst: true),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(qId, question['Option2'], '2', correctStr, selectedOpt, question, isDarkMode),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(qId, question['Option3'], '3', correctStr, selectedOpt, question, isDarkMode),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(qId, question['Option4'], '4', correctStr, selectedOpt, question, isDarkMode, isLast: true),
      ]),
    );
  }

  Widget _buildDividerLine(bool isDarkMode) {
    return Container(height: 1, color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200);
  }

  Widget _buildOptionRow(int qId, dynamic optData, String letter, String correctStr, String? selectedOpt, Map<String, dynamic> question, bool isDarkMode, {bool isFirst = false, bool isLast = false}) {
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
        if (isCorrectChoice) { backgroundColor = Color(0xFF4CAF50).withOpacity(0.1); textColor = isDarkMode ? Color(0xFF81C784) : Color(0xFF388E3C); fontWeight = FontWeight.w600; radioIcon = Icons.check_circle_rounded; radioColor = Color(0xFF4CAF50); }
        else { backgroundColor = Color(0xFFF44336).withOpacity(0.1); textColor = isDarkMode ? Color(0xFFE57373) : Color(0xFFD32F2F); fontWeight = FontWeight.w600; radioIcon = Icons.cancel_rounded; radioColor = Color(0xFFF44336); }
      } else if (isCorrectChoice) { backgroundColor = Color(0xFF4CAF50).withOpacity(0.05); textColor = isDarkMode ? Color(0xFF81C784).withOpacity(0.8) : Color(0xFF388E3C).withOpacity(0.8); radioIcon = Icons.check_circle_outline_rounded; radioColor = Color(0xFF4CAF50).withOpacity(0.7); }
    }
    Widget childWidget;
    if (optData is String) { childWidget = Html(data: optData, style: {"body": Style(fontSize: FontSize(15), color: textColor, fontWeight: fontWeight, lineHeight: LineHeight(1.4), margin: Margins.zero, padding: HtmlPaddings.zero)}); }
    else if (optData is Uint8List && optData.isNotEmpty) { childWidget = ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.memory(optData, height: 80, fit: BoxFit.contain, alignment: Alignment.centerLeft)); }
    else { return SizedBox.shrink(); }

    return GestureDetector(
      onTap: (selectedOpt == null) ? () => handleOptionTap(qId, letter, correctStr) : null,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(color: backgroundColor, borderRadius: BorderRadius.only(topLeft: isFirst ? Radius.circular(10) : Radius.zero, topRight: isFirst ? Radius.circular(10) : Radius.zero, bottomLeft: isLast ? Radius.circular(10) : Radius.zero, bottomRight: isLast ? Radius.circular(10) : Radius.zero)),
        child: Row(children: [
          Container(width: 28, height: 28, decoration: BoxDecoration(color: radioColor.withOpacity(isAnswered && isCorrectChoice && !isSelected ? 0.05 : 0.1), borderRadius: BorderRadius.circular(14)), child: Icon(radioIcon, color: radioColor, size: 18)),
          SizedBox(width: 12),
          Expanded(child: childWidget),
        ]),
      ),
    );
  }

  Widget _buildModernDescWidget(dynamic descData, bool isDarkMode) {
    if (descData == null) return SizedBox.shrink();
    Widget content;
    if (descData is String && descData.isNotEmpty) { content = Html(data: descData, style: {"body": Style(fontSize: FontSize(15), lineHeight: LineHeight(1.5), color: isDarkMode ? Color(0xFF90CAF9) : Color(0xFF1E88E5), margin: Margins.zero, padding: HtmlPaddings.zero)}); }
    else if (descData is Uint8List && descData.isNotEmpty) { content = ClipRRect(borderRadius: BorderRadius.circular(8), child: Image.memory(descData)); }
    else { return SizedBox.shrink(); }
    return Container(
      margin: const EdgeInsets.only(top: 14), padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Color(0xFF2196F3).withOpacity(0.08), borderRadius: BorderRadius.circular(10), border: Border.all(color: Color(0xFF2196F3).withOpacity(0.25), width: 1)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(padding: EdgeInsets.all(5), decoration: BoxDecoration(color: Color(0xFF2196F3), borderRadius: BorderRadius.circular(6)), child: Icon(Icons.lightbulb_outline_rounded, color: Colors.white, size: 14)),
          SizedBox(width: 8),
          Text('정답 해설', style: TextStyle(fontSize: 15, fontWeight: FontWeight.bold, color: Color(0xFF2196F3))),
        ]),
        SizedBox(height: 10),
        content,
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(gradient: LinearGradient(colors: isDarkMode ? [Color(0xFF2C2C2C), Color(0xFF3E3E3E), Color(0xFF4A4A4A)] : [Color(0xFFF5F7FA), Color(0xFFE8ECF0), Color(0xFFDDE4EA)], begin: Alignment.topLeft, end: Alignment.bottomRight)),
        child: SafeArea(
          child: FadeTransition(
            opacity: _fadeAnimation,
            child: SlideTransition(
              position: _slideAnimation,
              child: Column(
                children: [
                  _buildModernHeader(isDarkMode),
                  Expanded(
                    child: FutureBuilder<List<Map<String, dynamic>>>(
                      future: futureQuestions,
                      builder: (ctx, snapshot) {
                        if (snapshot.connectionState == ConnectionState.waiting) {
                          return Center(child: CircularProgressIndicator(color: isDarkMode ? Colors.white : Color(0xFF8E9AAF)));
                        }
                        if (snapshot.hasError) {
                          return Center(child: Text('오류: ${snapshot.error}', style: TextStyle(color: isDarkMode ? Colors.white70 : Colors.black54)));
                        }
                        if (!snapshot.hasData || snapshot.data!.isEmpty) {
                           return Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                            Icon(Icons.search_off_rounded, size: 48, color: isDarkMode ? Colors.white.withOpacity(0.5) : Colors.black54),
                            SizedBox(height: 16),
                            Text('해당 과목 문제를 찾을 수 없습니다', style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 16)),
                          ]));
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
                                  final saveKey = '${widget.databaseId}|${widget.category}|$qId';
                                  final isBookmarked = savedQuestionsState[saveKey] ?? false;
                                  final showDesc = showAnswerDescription[qId] ?? false;

                                  return Container(
                                    margin: EdgeInsets.only(bottom: 12),
                                    decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.white.withOpacity(0.9), borderRadius: BorderRadius.circular(16), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.black.withOpacity(0.08)), boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 8, offset: Offset(0, 3))]),
                                    child: Padding(
                                      padding: const EdgeInsets.all(14.0),
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, crossAxisAlignment: CrossAxisAlignment.start, children: [
                                            Expanded(child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
                                              Text('문제 ${qId}', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: isDarkMode ? Colors.white : Colors.black87)),
                                              SizedBox(width: 8),
                                              // 카테고리 페이지에서는 widget.category를 태그로 사용
                                              Container(
                                                padding: EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                                decoration: BoxDecoration(color: Color(0xFF8E9AAF).withOpacity(0.15), borderRadius: BorderRadius.circular(8)),
                                                child: Text(widget.category, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: Color(0xFF8E9AAF))),
                                              ),
                                            ])),
                                            GestureDetector(onTap: () => handleSaveTap(qId), child: Container(padding: EdgeInsets.all(7), decoration: BoxDecoration(color: isBookmarked ? Color(0xFF2196F3).withOpacity(0.15) : (isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.withOpacity(0.1)), borderRadius: BorderRadius.circular(8)), child: Icon(isBookmarked ? Icons.bookmark_rounded : Icons.bookmark_border_rounded, color: isBookmarked ? Color(0xFF2196F3) : Colors.grey.shade600, size: 18))),
                                          ]),
                                          SizedBox(height: 10),
                                          if (question['Big_Question'] != null && question['Big_Question'].isNotEmpty) _buildBigQuestionWidget(question['Big_Question'], isDarkMode),
                                          if (question['Big_Question'] != null && question['Big_Question'].isNotEmpty) const SizedBox(height: 8),
                                          _buildBigQuestionSpecialWidget(question, isDarkMode),
                                          _buildModernQuestionWidget(question['Question'], isDarkMode),
                                          const SizedBox(height: 14),
                                          _buildUnifiedOptionsWidget(qId, question, userSelected, isDarkMode),
                                          if (showDesc) _buildModernDescWidget(question['Answer_description'], isDarkMode),
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
        decoration: BoxDecoration(color: isDarkMode ? Color(0xFF2C2C2C) : Colors.white, boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 10, offset: Offset(0, -5))]),
        child: BottomNavigationBar(
          currentIndex: _currentIndex, onTap: onTabTapped, backgroundColor: Colors.transparent, elevation: 0, selectedItemColor: Color(0xFF8E9AAF), unselectedItemColor: isDarkMode ? Colors.white.withOpacity(0.6) : Colors.black54,
          selectedLabelStyle: TextStyle(fontWeight: FontWeight.bold, fontSize: 11), unselectedLabelStyle: TextStyle(fontSize: 11), type: BottomNavigationBarType.fixed,
          items: const [
            BottomNavigationBarItem(icon: Icon(Icons.edit_document, size: 22), label: '문제풀이'),
            BottomNavigationBarItem(icon: Icon(Icons.quiz_rounded, size: 22), label: '오답노트'),
            BottomNavigationBarItem(icon: Icon(Icons.bookmark_rounded, size: 22), label: '즐겨찾기'),
          ],
        ),
      ),
    );
  }
}