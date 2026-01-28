import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'database_helper.dart';
import 'dart:typed_data';
import 'home.dart';
import 'category_bookmark.dart';
import 'constants.dart';
import 'ad_helper.dart';
import 'ad_config.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'question_list_page.dart';
// import 'random_bookmark.dart'; // 현재 사용되지 않으므로 주석 처리 또는 필요시 확인
import 'package:provider/provider.dart'; // AdState 사용을 위해 추가
import 'ad_state.dart'; // AdState 사용을 위해 추가
import 'package:flutter_html/flutter_html.dart';

class CategoryWrongAnswerPage extends StatefulWidget {
  final String category;
  final String databaseId;
  final String round;
  final String dbPath;

  CategoryWrongAnswerPage({
    required this.category,
    required this.databaseId,
    required this.round,
    required this.dbPath,
  });

  @override
  _CategoryWrongAnswerPageState createState() => _CategoryWrongAnswerPageState();
}

class _CategoryWrongAnswerPageState extends State<CategoryWrongAnswerPage> with TickerProviderStateMixin {
  late Future<List<Map<String, dynamic>>> futureQuestions;
  late Map<String, DatabaseHelper> dbHelpers;

  Map<String, String> selectedOptions = {};
  Map<String, bool> isCorrectOptions = {};
  Map<String, bool> showAnswerDescription = {};
  Map<String, bool> savedQuestionsState = {}; // 북마크 UI 반영용

  int _currentIndex = 1;
  bool _isAdLoaded = false;
  InterstitialAd? _interstitialAd;

  late AnimationController _fadeController;
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    dbHelpers = {};
    futureQuestions = fetchCategoryWrongAnswers();
    loadSavedQuestionStatus(); // 북마크 상태 로드 추가

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
    _interstitialAd?.dispose();
    _fadeController.dispose();
    _slideController.dispose();
    super.dispose();
  }

  Future<void> loadSavedQuestionStatus() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
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

  Future<void> _initializeDbHelpers() async {
    reverseRoundMapping.forEach((dbId, roundName) {
      if (!dbHelpers.containsKey(dbId.toString())) { // 이미 초기화된 경우 건너뜀
        String dbPath = 'assets/question$dbId.db';
        dbHelpers[dbId.toString()] = DatabaseHelper.getInstance(dbPath);
      }
    });
  }

  Future<List<Map<String, dynamic>>> fetchCategoryWrongAnswers() async {
    try {
      await _initializeDbHelpers();
      SharedPreferences prefs = await SharedPreferences.getInstance();
      List<String> wrongAnswerList = List<String>.from(prefs.getStringList('wrongAnswers') ?? []);
      List<Map<String, dynamic>> questions = [];

      for (String item in wrongAnswerList) {
        List<String> parts = item.split('|');
        if (parts.length == 3) {
          String dbId = parts[0].trim();
          String categoryFromFile = parts[1].trim();
          int questionId = int.parse(parts[2].trim());

          if (categoryFromFile.toLowerCase() != widget.category.toLowerCase()) {
            continue;
          }
          if (!dbHelpers.containsKey(dbId)) {
            continue;
          }

          DatabaseHelper dbHelper = dbHelpers[dbId]!;
          var questionData = await dbHelper.getQuestionByCategoryAndId(categoryFromFile, questionId);

          if (questionData != null) {
            Map<String, dynamic> question = Map<String, dynamic>.from(questionData);
            question['CategoryFromFile'] = categoryFromFile; // 실제 파일에서 읽어온 카테고리
            question['databaseId'] = dbId;
            String saveKey = '$dbId|$categoryFromFile|$questionId';
            question['saveKey'] = saveKey;
            int? roundValue = int.tryParse(dbId);
            question['roundName'] = reverseRoundMapping[roundValue] ?? '기타';
            question = _convertFieldsToImageOrText(question);
            questions.add(question);
          }
        }
      }
      return questions;
    } catch (e) {
      return [];
    }
  }

  Map<String, dynamic> _convertFieldsToImageOrText(Map<String, dynamic> question) {
    final Map<String, dynamic> modifiedQuestion = Map<String, dynamic>.from(question);
    modifiedQuestion['Big_Question'] = _processFieldData(modifiedQuestion['Big_Question']);
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

  void handleOptionTap(String saveKey, String selectedOption, dynamic correctOption) async {
    setState(() {
      selectedOptions[saveKey] = selectedOption;
      isCorrectOptions[saveKey] = (selectedOption == correctOption.toString());
      showAnswerDescription[saveKey] = true;
    });

    SharedPreferences prefs = await SharedPreferences.getInstance();
    List<String> wrongAnswerList = List<String>.from(prefs.getStringList('wrongAnswers') ?? []);

    if (selectedOption == correctOption.toString()) { // 정답을 맞췄다면
      wrongAnswerList.remove(saveKey); // 오답 목록에서 제거
      await prefs.setStringList('wrongAnswers', wrongAnswerList);
      Fluttertoast.showToast(msg: "정답! 오답노트에서 삭제됩니다.");
      setState(() { // UI 갱신
        futureQuestions = fetchCategoryWrongAnswers();
      });
    } else { // 여전히 오답이라면
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('오답입니다!', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        backgroundColor: Color(0xFFF44336),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        duration: Duration(milliseconds: 1500),
      ));
    }
  }
  
  Future<void> handleSaveTap(String saveKey) async {
    bool isCurrentlySaved = savedQuestionsState[saveKey] ?? false;
    bool newSaveStatus = !isCurrentlySaved;

    setState(() {
      savedQuestionsState[saveKey] = newSaveStatus;
    });

    SharedPreferences prefs = await SharedPreferences.getInstance();
    List<String> savedList = List<String>.from(prefs.getStringList('savedQuestions') ?? []);

    if (newSaveStatus) {
      if (!savedList.contains(saveKey)) savedList.add(saveKey);
    } else {
      savedList.remove(saveKey);
    }
    await prefs.setStringList('savedQuestions', savedList);
    Fluttertoast.showToast(msg: newSaveStatus ? '북마크에 추가되었습니다.' : '북마크에서 삭제되었습니다.');
  }

  Widget _buildModernHeader(bool isDarkMode) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        children: [
          GestureDetector(onTap: () => Navigator.pop(context), child: Container(padding: EdgeInsets.all(5), decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.white.withOpacity(0.7), borderRadius: BorderRadius.circular(8), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1))), child: Icon(Icons.arrow_back_ios_rounded, color: isDarkMode ? Colors.white : Colors.black87, size: 16))),
          SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${widget.category} 오답노트', style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 0.3)),
            Text('틀린 문제 모음', style: TextStyle(color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54, fontSize: 11, fontWeight: FontWeight.w400)),
          ])),
          GestureDetector(onTap: () => Navigator.pushAndRemoveUntil(context, MaterialPageRoute(builder: (_) => HomePage()), (route)=>false), child: Container(padding: EdgeInsets.all(5), decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.white.withOpacity(0.7), borderRadius: BorderRadius.circular(8), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1))), child: Icon(Icons.home_rounded, color: isDarkMode ? Colors.white : Colors.black87, size: 18))),
        ],
      ),
    );
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

  Widget _buildUnifiedOptionsWidget(String saveKey, Map<String, dynamic> question, String? selectedOpt, bool isDarkMode) {
    final correctStr = question['Correct_Option']?.toString() ?? '';
    return Container(decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.grey.shade300, width: 1)),
      child: Column(children: [
        _buildOptionRow(saveKey, question['Option1'], '1', correctStr, selectedOpt, question, isDarkMode, isFirst: true),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(saveKey, question['Option2'], '2', correctStr, selectedOpt, question, isDarkMode),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(saveKey, question['Option3'], '3', correctStr, selectedOpt, question, isDarkMode),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(saveKey, question['Option4'], '4', correctStr, selectedOpt, question, isDarkMode, isLast: true),
      ]),
    );
  }

  Widget _buildDividerLine(bool isDarkMode) {
    return Container(height: 1, color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200);
  }

  Widget _buildOptionRow(String saveKey, dynamic optData, String letter, String correctStr, String? selectedOpt, Map<String, dynamic> question, bool isDarkMode, {bool isFirst = false, bool isLast = false}) {
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
      onTap: (selectedOpt == null) ? () => handleOptionTap(saveKey, letter, correctStr) : null,
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

  /// Renders the 'Big_Question_Special' image if it exists.
  Widget _buildBigQuestionSpecialWidget(Map<String, dynamic> question, bool isDarkMode) {
    final bigQSpecial = question['Big_Question_Special'];

    if (bigQSpecial is Uint8List && bigQSpecial.isNotEmpty) {
      return Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 8), // Adds spacing below the widget
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(10.0),
          child: Image.memory(
            bigQSpecial,
            fit: BoxFit.contain, // Ensures the entire image is visible without cropping
          ),
        ),
      );
    }
    return const SizedBox.shrink(); // Returns an empty box if data is absent
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

  void onTabTapped(int index) {
    if (_currentIndex == index) return;
    _showInterstitialAdAndNavigateWrapper(index);
  }

  void _showInterstitialAdAndNavigateWrapper(int pageIndex) {
    final adState = Provider.of<AdState>(context, listen: false);
    if (adState.adsRemoved || pageIndex == _currentIndex) {
      _navigateToPage(pageIndex);
      return;
    }

    if (_isAdLoaded && _interstitialAd != null) {
      _interstitialAd!.fullScreenContentCallback = FullScreenContentCallback(
        onAdDismissedFullScreenContent: (ad) {
          ad.dispose();
          _isAdLoaded = false;
          _navigateToPage(pageIndex);
          if (!adState.adsRemoved) _loadInterstitialAd();
        },
        onAdFailedToShowFullScreenContent: (ad, error) {
          ad.dispose();
          _isAdLoaded = false;
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
    setState(() {
      _currentIndex = index;
    });
    Widget page;
    String routeName;
    switch (index) {
      case 0:
        page = QuestionListPage(category: widget.category, databaseId: widget.databaseId, round: widget.round, dbPath: widget.dbPath);
        routeName = '/categoryQuestionList';
        break;
      case 1: // 현재 오답노트 페이지
        futureQuestions = fetchCategoryWrongAnswers(); // 목록 새로고침
        return;
      case 2:
        page = CategoryBookmarkPage(category: widget.category, databaseId: widget.databaseId, round: widget.round, dbPath: widget.dbPath);
        routeName = '/categoryBookmark';
        break;
      default:
        return;
    }
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (context) => page, settings: RouteSettings(name: routeName)));
  }

  void _loadInterstitialAd() {
    InterstitialAd.load(
      adUnitId: AdHelper.interstitialAdUnitId,
      request: AdRequest(),
      adLoadCallback: InterstitialAdLoadCallback(
        onAdLoaded: (InterstitialAd ad) {
          _interstitialAd = ad;
          _isAdLoaded = true;
        },
        onAdFailedToLoad: (LoadAdError error) {
          _isAdLoaded = false;
        },
      ),
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
                      builder: (context, snapshot) {
                        if (snapshot.connectionState == ConnectionState.waiting) {
                          return Center(child: CircularProgressIndicator(color: isDarkMode ? Colors.white : Color(0xFF8E9AAF)));
                        } else if (snapshot.hasError) {
                          return Center(child: Text('오류: ${snapshot.error}', style: TextStyle(color: isDarkMode ? Colors.white70 : Colors.black54)));
                        } else if (!snapshot.hasData || snapshot.data!.isEmpty) {
                          return Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                            Icon(Icons.check_circle_outline_rounded, size: 48, color: isDarkMode ? Colors.white.withOpacity(0.5) : Colors.black54),
                            SizedBox(height: 16),
                            Text('해당 과목에 대한 오답 문제가 없습니다', style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 16)),
                            SizedBox(height: 8),
                            Text('문제를 풀고 틀린 문제들이 여기에 모입니다', style: TextStyle(color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54, fontSize: 14)),
                          ]));
                        } else {
                          final questions = snapshot.data!;
                          return ListView.builder(
                            padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                            itemCount: questions.length,
                            itemBuilder: (context, index) {
                              final question = questions[index];
                              final questionId = question['Question_id'];
                              final saveKey = question['saveKey'];
                              final selectedOption = selectedOptions[saveKey];
                              final showDescription = showAnswerDescription[saveKey] ?? false;
                              final isBookmarked = savedQuestionsState[saveKey] ?? false;
                              final roundName = question['roundName'] ?? widget.round; // 오답노트에서는 개별 문제의 roundName 사용

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
                                          Text('문제 ${questionId}', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: isDarkMode ? Colors.white : Colors.black87)),
                                          SizedBox(width: 8),
                                          Container(
                                            padding: EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                            decoration: BoxDecoration(color: Color(0xFFF44336).withOpacity(0.15), borderRadius: BorderRadius.circular(8)), // 오답노트는 빨간색 태그
                                            child: Text(roundName, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: Color(0xFFF44336))),
                                          ),
                                        ])),
                                        GestureDetector(onTap: () => handleSaveTap(saveKey), child: Container(padding: EdgeInsets.all(7), decoration: BoxDecoration(color: isBookmarked ? Color(0xFF2196F3).withOpacity(0.15) : (isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.withOpacity(0.1)), borderRadius: BorderRadius.circular(8)), child: Icon(isBookmarked ? Icons.bookmark_rounded : Icons.bookmark_border_rounded, color: isBookmarked ? Color(0xFF2196F3) : Colors.grey.shade600, size: 18))),
                                      ]),
                                      SizedBox(height: 10),
                                      if (question['Big_Question'] != null && question['Big_Question'].isNotEmpty) _buildBigQuestionWidget(question['Big_Question'], isDarkMode),
                                      if (question['Big_Question'] != null && question['Big_Question'].isNotEmpty) const SizedBox(height: 8),
                                      
                                      // <<< INSERT THE NEW WIDGET CALL HERE, IN THIS EXACT POSITION
                                      _buildBigQuestionSpecialWidget(question, isDarkMode),
                                      
                                      _buildModernQuestionWidget(question['Question'], isDarkMode),
                                      const SizedBox(height: 14),
                                      _buildUnifiedOptionsWidget(saveKey, question, selectedOption, isDarkMode),
                                      if (showDescription) _buildModernDescWidget(question['Answer_description'], isDarkMode),
                                    ],
                                  ),
                                ),
                              );
                            },
                          );
                        }
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