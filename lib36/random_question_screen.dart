import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:flutter_html/flutter_html.dart';

import 'widgets/common/index.dart';
import 'database_helper.dart';
import 'home.dart';
import 'random_bookmark.dart';
import 'random_wronganswer.dart';
import 'ad_helper.dart';
import 'ad_config.dart';
import 'constants.dart';
import 'package:provider/provider.dart'; // AdState 사용을 위해 추가
import 'ad_state.dart'; // AdState 사용을 위해 추가
import 'statistics.dart'; // recordRandomLearningSession import


class RandomQuestionPage extends StatefulWidget {
  final String category; 

  const RandomQuestionPage({Key? key, required this.category}) : super(key: key);

  @override
  _RandomQuestionPageState createState() => _RandomQuestionPageState();
}

class _RandomQuestionPageState extends State<RandomQuestionPage> with TickerProviderStateMixin {
  Map<String, String> selectedOptions = {}; 
  Map<String, bool> isCorrectOptions = {};
  Map<String, bool> showAnswerDescription = {};
  Map<String, bool> savedQuestionsState = {}; // 북마크 UI 즉시 반영

  List<String> correctAnswers = [];
  List<String> wrongAnswers = [];

  // 질문 목록을 캐시로 저장
  List<Map<String, dynamic>> _cachedQuestions = [];
  late Future<List<Map<String, dynamic>>> futureQuestions;
  bool isLoading = false;
  String errorMessage = '';

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
    loadCorrectWrongAnswers();
    futureQuestions = fetchAllRandomQuestions();
    loadSavedQuestions();
    loadSelectedStatesFromPrefs();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      final adState = Provider.of<AdState>(context, listen: false);
      if (!adState.adsRemoved) {
        _loadInterstitialAd();
      }
    });
    
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
      recordRandomLearningSession(widget.category, selectedOptions, isCorrectOptions);
    }
    
    _interstitialAd?.dispose();
    _fadeController.dispose();
    _slideController.dispose();
    super.dispose();
  }

  Future<void> loadCorrectWrongAnswers() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      correctAnswers = prefs.getStringList('correctAnswers') ?? [];
      wrongAnswers = prefs.getStringList('wrongAnswers') ?? [];
    } catch (e) { correctAnswers = []; wrongAnswers = []; }
  }

  Future<void> saveAnswersToPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('correctAnswers', correctAnswers);
      await prefs.setStringList('wrongAnswers', wrongAnswers);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('답변 저장 중 오류가 발생했습니다.')));
    }
  }

  Future<List<Map<String, dynamic>>> fetchAllRandomQuestions() async {
    setState(() { isLoading = true; errorMessage = ''; });
    try {
      // 이미 질문이 캐시되어 있으면 반환
      if (_cachedQuestions.isNotEmpty) {
        setState(() { isLoading = false; });
        return _cachedQuestions;
      }

      List<String> dbFiles = ['assets/question1.db', 'assets/question2.db', 'assets/question3.db', 'assets/question5.db', 'assets/question6.db'];
      List<Map<String, dynamic>> allQuestions = [];
      for (String dbPath in dbFiles) {
        DatabaseHelper? dbHelper;
        try {
          dbHelper = DatabaseHelper.getInstance(dbPath);
          final questions = await dbHelper.getAllQuestions();
          if (questions.isNotEmpty) allQuestions.addAll(questions);
        } catch (e) { continue; }
      }
      if (allQuestions.isEmpty) {
        setState(() { isLoading = false; errorMessage = '데이터베이스에서 문제를 불러오지 못했습니다.'; });
        return [];
      }
      if (widget.category != "ALL") {
        allQuestions = allQuestions.where((q) => q['Category'] == widget.category).toList();
        if (allQuestions.isEmpty) {
          setState(() { isLoading = false; errorMessage = '선택한 카테고리(${widget.category})에 해당하는 문제가 없습니다.'; });
          return [];
        }
      }
      allQuestions.shuffle(Random());
      int takeCount = (allQuestions.length < 100) ? allQuestions.length : 100;
      List<Map<String, dynamic>> result = [];
      for (var i = 0; i < takeCount; i++) {
        var q = Map<String, dynamic>.from(allQuestions[i]);
        int? examSession = q['ExamSession'] is int ? q['ExamSession'] : (q['ExamSession'] is String ? int.tryParse(q['ExamSession']) : null);
        int questionId = q['Question_id'] ?? 0;
        String uniqueKey = "${examSession ?? 0}|$questionId|$i"; // 중복 방지를 위해 인덱스 추가
        q['uniqueKey'] = uniqueKey;

        // 데이터 변환
        q['Big_Question'] = _processFieldData(q['Big_Question']);
        q['Question'] = _processFieldData(q['Question']);
        q['Option1'] = _processFieldData(q['Option1']);
        q['Option2'] = _processFieldData(q['Option2']);
        q['Option3'] = _processFieldData(q['Option3']);
        q['Option4'] = _processFieldData(q['Option4']);
        q['Answer_description'] = _processFieldData(q['Answer_description']);
        if (q.containsKey('Image') && q['Image'] != null) {
          q['Image'] = _processFieldData(q['Image']);
        }
        result.add(q);
      }
      
      // 결과 캐시에 저장
      _cachedQuestions = result;
      
      setState(() { isLoading = false; });
      return result;
    } catch (e) {
      setState(() { isLoading = false; errorMessage = '문제를 불러오는 중 오류가 발생했습니다: $e'; });
      return [];
    }
  }
  
  dynamic _processFieldData(dynamic fieldData) {
    if (fieldData != null) {
      if (fieldData is List<int>) return Uint8List.fromList(fieldData);
      if (fieldData is String && fieldData.isNotEmpty) {
        // Base64 디코딩 시도 (선택적)
        try {
          if (fieldData.length > 100 && (fieldData.contains('+') || fieldData.contains('/') || fieldData.endsWith('='))) {
            return base64Decode(fieldData);
          }
        } catch (_){} // 디코딩 실패시 문자열 그대로 사용
        return fieldData;
      }
    }
    return '';
  }


  Future<void> loadSavedQuestions() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedList = prefs.getStringList('savedQuestions') ?? [];
      Map<String, bool> currentSavedStatus = {};
      for (String item in savedList) {
        currentSavedStatus[item] = true; // 키 자체를 저장
      }
      if (mounted) {
        setState(() {
          savedQuestionsState = currentSavedStatus;
        });
      }
    } catch (e) { /* Error handling */ }
  }

  Future<void> loadSelectedStatesFromPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      Map<String, String> tempSelectedOptions = {};
      Map<String, bool> tempIsCorrectOptions = {};
      Map<String, bool> tempShowAnswerDescription = {};
      
      for (String key in prefs.getKeys()) {
        if (key.startsWith('selected_RANDOM|')) {
          final optionValue = prefs.getString(key);
          if (optionValue != null) {
            final stateKey = key.substring('selected_'.length); // "RANDOM|..."
            tempSelectedOptions[stateKey] = optionValue;
          }
        }
        if (key.startsWith('isCorrect_RANDOM|')) {
          final isCorrectValue = prefs.getBool(key);
          if (isCorrectValue != null) {
            final stateKey = key.substring('isCorrect_'.length); // "RANDOM|..."
            tempIsCorrectOptions[stateKey] = isCorrectValue;
          }
        }
        if (key.startsWith('showDescription_RANDOM|')) {
          final showDescValue = prefs.getBool(key) ?? prefs.getString(key) == 'true';
          final stateKey = key.substring('showDescription_'.length); // "RANDOM|..."
          tempShowAnswerDescription[stateKey] = showDescValue;
        }
      }
      
      if(mounted) {
        setState(() { 
          selectedOptions = tempSelectedOptions;
          isCorrectOptions = tempIsCorrectOptions;
          showAnswerDescription = tempShowAnswerDescription;
        });
      }
    } catch (e) { 
      print("선택 상태 로드 오류: $e");
    }
  }

  Future<void> resetProgress() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      wrongAnswers.removeWhere((item) => item.startsWith('RANDOM|'));
      correctAnswers.removeWhere((item) => item.startsWith('RANDOM|'));
      await prefs.setStringList('wrongAnswers', wrongAnswers);
      await prefs.setStringList('correctAnswers', correctAnswers);
      final keysToRemove = prefs.getKeys().where((k) => 
        k.startsWith('selected_RANDOM|') || 
        k.startsWith('showDescription_RANDOM|') || 
        k.startsWith('isCorrect_RANDOM|')
      ).toList();
      for (var k in keysToRemove) { await prefs.remove(k); }
      if(mounted) {
        setState(() {
          selectedOptions.clear();
          isCorrectOptions.clear();
          showAnswerDescription.clear();
        });
      }
       Fluttertoast.showToast(msg: "풀이 상태가 초기화되었습니다.");
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('상태 초기화 중 오류가 발생했습니다.')));
    }
  }

  void _loadInterstitialAd() {
    InterstitialAd.load(
      adUnitId: AdHelper.interstitialAdUnitId,
      request: const AdRequest(),
      adLoadCallback: InterstitialAdLoadCallback(
        onAdLoaded: (InterstitialAd ad) { _interstitialAd = ad; _isAdLoaded = true; },
        onAdFailedToLoad: (LoadAdError error) { _interstitialAd = null; _isAdLoaded = false; },
      ),
    );
  }

  Future<void> handleOptionTap({required String uniqueKey, required String chosenOpt, required dynamic correctOpt, required Map<String, dynamic> questionData}) async {
    final correctStr = correctOpt?.toString() ?? '';
    final prefixKey = 'RANDOM|$uniqueKey'; // 정오답 목록용 키
    final bool isCorr = (chosenOpt == correctStr);
    
    // 먼저 메모리 상태 업데이트
    setState(() {
      selectedOptions[prefixKey] = chosenOpt;
      isCorrectOptions[prefixKey] = isCorr;
      showAnswerDescription[prefixKey] = true;
    });
    
    try {
      // SharedPreferences에 상태 저장 
      final prefs = await SharedPreferences.getInstance();
      
      // 선택된 옵션 저장
      await prefs.setString('selected_$prefixKey', chosenOpt);
      
      // 정답 여부 저장 (Boolean으로 저장)
      await prefs.setBool('isCorrect_$prefixKey', isCorr);
      
      // 설명 표시 여부 저장 (Boolean으로 저장)
      await prefs.setBool('showDescription_$prefixKey', true);
      
      // 정답/오답 목록 업데이트
      if (isCorr) {
        if (!correctAnswers.contains(prefixKey)) {
          correctAnswers.add(prefixKey);
        }
        wrongAnswers.remove(prefixKey);
      } else {
        if (!wrongAnswers.contains(prefixKey)) {
          wrongAnswers.add(prefixKey);
        }
        correctAnswers.remove(prefixKey);
        
        // 오답 데이터 저장
        dynamic _encodeImageData(dynamic data) { 
          if (data is Uint8List) return base64Encode(data); 
          return data; 
        }
        
        final qMap = {
          'uniqueId': uniqueKey, 
          'ExamSession': questionData['ExamSession'], 
          'Category': questionData['Category'],
          'Big_Question': _encodeImageData(questionData['Big_Question']), 
          'Big_Question_Special': _encodeImageData(questionData['Big_Question_Special']),

          'Question': _encodeImageData(questionData['Question']),
          'Option1': _encodeImageData(questionData['Option1']), 
          'Option2': _encodeImageData(questionData['Option2']),
          'Option3': _encodeImageData(questionData['Option3']), 
          'Option4': _encodeImageData(questionData['Option4']),
          'Correct_Option': questionData['Correct_Option'], 
          'Answer_description': _encodeImageData(questionData['Answer_description']),
          if (questionData.containsKey('Image')) 'Image': _encodeImageData(questionData['Image']),
        };
        
        final jsonString = jsonEncode(qMap);
        await prefs.setString('random_wrong_data_$uniqueKey', jsonString);
      }
      
      // 정답/오답 목록 저장
      await saveAnswersToPrefs();
      
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(isCorr ? '정답입니다!' : '오답입니다!', 
                       style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
          backgroundColor: isCorr ? Color(0xFF4CAF50) : Color(0xFFF44336),
          behavior: SnackBarBehavior.floating, 
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)), 
          duration: Duration(milliseconds: 1500),
        ));
      }
    } catch (e) {
      print("옵션 처리 오류: $e");
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('처리 중 오류가 발생했습니다: $e'))
        );
      }
    }
  }

  Future<void> handleBookmarkTap(String uniqueKey, Map<String, dynamic> question) async {
    try {
      String bookmarkKey = 'RANDOM|$uniqueKey'; // 북마크 저장용 키 (항상 "RANDOM|" 접두사)
      bool newSaveStatus = !(savedQuestionsState[bookmarkKey] ?? false);
      setState(() { savedQuestionsState[bookmarkKey] = newSaveStatus; });
      dynamic _encodeImageData(dynamic data) { if (data is Uint8List) return base64Encode(data); return data; }
      final prefs = await SharedPreferences.getInstance();
      final savedList = prefs.getStringList('savedQuestions') ?? [];
      if (newSaveStatus) {
        if (!savedList.contains(bookmarkKey)) savedList.add(bookmarkKey);
        final qMap = {
          'uniqueId': uniqueKey, 'ExamSession': question['ExamSession'], 'Category': question['Category'],
          'Big_Question': _encodeImageData(question['Big_Question']), 
                  'Big_Question_Special': _encodeImageData(question['Big_Question_Special']),

          'Question': _encodeImageData(question['Question']),
          'Option1': _encodeImageData(question['Option1']), 'Option2': _encodeImageData(question['Option2']),
          'Option3': _encodeImageData(question['Option3']), 'Option4': _encodeImageData(question['Option4']),
          'Correct_Option': question['Correct_Option'], 'Answer_description': _encodeImageData(question['Answer_description']),
          if (question.containsKey('Image')) 'Image': _encodeImageData(question['Image']),
        };
        final jsonString = jsonEncode(qMap);
        await prefs.setString('random_bookmark_data_$uniqueKey', jsonString); // 데이터 저장시 uniqueKey만 사용
      } else {
        savedList.remove(bookmarkKey);
        await prefs.remove('random_bookmark_data_$uniqueKey'); // 데이터 삭제시 uniqueKey만 사용
      }
      await prefs.setStringList('savedQuestions', savedList);
      if (mounted) {
        Fluttertoast.showToast(msg: newSaveStatus ? '북마크에 추가되었습니다.' : '북마크에서 삭제되었습니다.');
      }
    } catch (e) {
      print("북마크 처리 오류: $e");
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('북마크 처리 중 오류가 발생했습니다.')));
    }
  }

  void _loadNewQuestionSet() {
    setState(() {
      _cachedQuestions = []; // 캐시 비우기
      futureQuestions = fetchAllRandomQuestions();
      // 사용자의 풀이 상태는 초기화하지 않음
    });
  }


  Widget _buildCompactProgressCard(List<Map<String, dynamic>> questions, bool isDarkMode) {
    final totalCount = questions.length;
    // selectedOptions의 키는 "RANDOM|uniqueKey" 형태이므로, 이를 기준으로 카운트
    final answeredCount = selectedOptions.keys.where((k) => k.startsWith("RANDOM|")).length;
    final corrCount = isCorrectOptions.entries.where((entry) => entry.key.startsWith("RANDOM|") && entry.value).length;

    final wrongCount = answeredCount - corrCount;
    final progress = (totalCount == 0) ? 0.0 : (answeredCount / totalCount);

    return Container(
      margin: EdgeInsets.symmetric(horizontal: 12, vertical: 3), // MODIFIED
      decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.white.withOpacity(0.9), borderRadius: BorderRadius.circular(10), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.black.withOpacity(0.08)), boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.03), blurRadius: 4,offset: Offset(0, 1))]), // MODIFIED
      child: Column(children: [
        Padding(padding: EdgeInsets.all(10), child: Column(children: [
          Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
            Text('학습 진행률', style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 13, fontWeight: FontWeight.bold)),
            Row(children: [
              GestureDetector(onTap: _loadNewQuestionSet, child: Container(padding: EdgeInsets.all(3), margin: EdgeInsets.only(right: 8), decoration: BoxDecoration(color: Colors.deepPurple.withOpacity(0.2), borderRadius: BorderRadius.circular(5)), child: Icon(Icons.shuffle_rounded, color: Colors.deepPurple, size: 14))),
              GestureDetector(
                onTap: () async {
                  bool? confirm = await showDialog(context: context, builder: (ctx) => AlertDialog(shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)), title: Row(children: [Container(padding: EdgeInsets.all(8), decoration: BoxDecoration(color: Colors.orange.withOpacity(0.2), borderRadius: BorderRadius.circular(8)), child: Icon(Icons.refresh_rounded, color: Colors.orange)), SizedBox(width: 12), Text("풀이 상태 초기화")]), content: Text("지금까지 풀었던 문제를 모두 초기화하시겠습니까?"), actions: [TextButton(child: Text("취소", style: TextStyle(color: Colors.grey[600])), onPressed: () => Navigator.pop(ctx, false)), ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: Colors.orange, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))), child: Text("초기화", style: TextStyle(color: Colors.white)), onPressed: () => Navigator.pop(ctx, true))]));
                  if (confirm == true) { await resetProgress(); }
                },
                child: Container(padding: EdgeInsets.all(3), decoration: BoxDecoration(color: Colors.orange.withOpacity(0.2), borderRadius: BorderRadius.circular(5)), child: Icon(Icons.refresh_rounded, color: Colors.orange, size: 14)),
              ),
            ]),
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
            Expanded(child: _buildCompactStatContainer(icon: Icons.check_circle_rounded, label: '정답', value: '$corrCount', color: Color(0xFF4CAF50), isDarkMode: isDarkMode)), SizedBox(width: 4),
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
          ad.dispose(); _isAdLoaded = false;
          if (!adState.adsRemoved) _loadInterstitialAd();
          _navigateToPage(pageIndex);
        },
        onAdFailedToShowFullScreenContent: (ad, error) {
          ad.dispose(); _isAdLoaded = false;
          if (!adState.adsRemoved) _loadInterstitialAd();
          _navigateToPage(pageIndex);
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
      case 0: // 현재 페이지 (랜덤 문제풀이)
        return; // 또는 _loadNewQuestionSet(); 으로 새로고침
      case 1:
        page = RandomWrongAnswerPage();
        routeName = '/randomWrongAnswer';
        break;
      case 2:
        page = RandomBookmarkPage();
        routeName = '/randomBookmark';
        break;
      default:
        return;
    }
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (context) => page, settings: RouteSettings(name: routeName)));
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

  Widget _buildUnifiedOptionsWidget({required String uniqueKey, required Map<String, dynamic> questionData, required dynamic option1, required dynamic option2, required dynamic option3, required dynamic option4, required dynamic correctOpt, required String? userSelected, required bool isDarkMode}) {
    final correctStr = correctOpt?.toString() ?? '';
    return Container(decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.grey.shade300, width: 1)),
      child: Column(children: [
        _buildOptionRow(uniqueKey, questionData, option1, '1', correctStr, userSelected, isDarkMode, isFirst: true),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(uniqueKey, questionData, option2, '2', correctStr, userSelected, isDarkMode),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(uniqueKey, questionData, option3, '3', correctStr, userSelected, isDarkMode),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(uniqueKey, questionData, option4, '4', correctStr, userSelected, isDarkMode, isLast: true),
      ]),
    );
  }

  Widget _buildDividerLine(bool isDarkMode) {
    return Container(height: 1, color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200);
  }

  Widget _buildOptionRow(String uniqueKey, Map<String, dynamic> questionData, dynamic optData, String letter, String correctStr, String? selectedOpt, bool isDarkMode, {bool isFirst = false, bool isLast = false}) {
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
      onTap: (selectedOpt == null) ? () => handleOptionTap(uniqueKey: uniqueKey, chosenOpt: letter, correctOpt: correctStr, questionData: questionData) : null,
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
      body: ThemedBackgroundWidget(
        isDarkMode: isDarkMode,
        child: SafeArea(child: FadeTransition(opacity: _fadeAnimation, child: SlideTransition(position: _slideAnimation, child: Column(
          children: [
            CommonHeaderWidget(
              title: widget.category == "ALL" ? '랜덤 문제 - 전체' : '랜덤 문제 - ${widget.category}',
              subtitle: '랜덤 문제풀이',
                  // ▼▼▼▼▼ 이 줄을 추가해 주세요! ▼▼▼▼▼
                  onHomePressed: () => Navigator.pushAndRemoveUntil(
                    context,
                    MaterialPageRoute(builder: (_) => HomePage()),
                    (route) => false,
                  ),
                ),            Expanded(child: isLoading 
              ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [CircularProgressIndicator(color: isDarkMode ? Colors.white : Color(0xFF8E9AAF)), SizedBox(height: 16), Text('문제를 불러오는 중...', style: TextStyle(color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54, fontSize: 16))]))
              : FutureBuilder<List<Map<String, dynamic>>>(
                  future: futureQuestions,
                  builder: (ctx, snapshot) {
                    if (snapshot.connectionState == ConnectionState.waiting && isLoading) { // isLoading도 함께 체크
                      return Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [CircularProgressIndicator(color: isDarkMode ? Colors.white : Color(0xFF8E9AAF)), SizedBox(height: 16), Text('문제를 불러오는 중...', style: TextStyle(color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54, fontSize: 16))]));
                    }
                    if (snapshot.hasError || errorMessage.isNotEmpty) {
                      return Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(Icons.error_outline_rounded, size: 48, color: Colors.red[400]), SizedBox(height: 16), Text(errorMessage.isNotEmpty ? errorMessage : '문제를 불러오는 중 오류가 발생했습니다:\n${snapshot.error}', textAlign: TextAlign.center, style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 16)), SizedBox(height: 24), ElevatedButton(onPressed: _loadNewQuestionSet, style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF8E9AAF), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))), child: Text('새 문제 받기'))]));
                    }
                    if (!snapshot.hasData || snapshot.data!.isEmpty) {
                       return Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(Icons.warning_amber_rounded, size: 48, color: isDarkMode ? Colors.white.withOpacity(0.5) : Colors.black54), SizedBox(height: 16), Text('문제를 불러올 수 없습니다.', textAlign: TextAlign.center, style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 16)), SizedBox(height: 24), Row(mainAxisAlignment: MainAxisAlignment.center, children: [ElevatedButton(onPressed: _loadNewQuestionSet, style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF8E9AAF), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))), child: Text('새 문제 받기')), SizedBox(width: 16), ElevatedButton(onPressed: () => Navigator.pop(context), style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF8E9AAF), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))), child: Text('돌아가기'))])]));
                    }
                    final questions = snapshot.data!;
                    return Column(children: [
                      _buildCompactProgressCard(questions, isDarkMode),
                      Expanded(child: ListView.builder(
                        padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8), // MODIFIED
                        itemCount: questions.length,
                        itemBuilder: (ctx, index) {
                          final q = questions[index];
                          final uniqueKey = q['uniqueKey'] as String;
                          // selectedOptions, showAnswerDescription은 "RANDOM|" 접두사 포함된 키 사용
                          final userSelected = selectedOptions['RANDOM|$uniqueKey'];
                          final showDesc = showAnswerDescription['RANDOM|$uniqueKey'] ?? false;
                          final isBookmarked = savedQuestionsState['RANDOM|$uniqueKey'] ?? false;

                          final examVal = q['ExamSession'];
                          final roundName = examSessionToRoundName(examVal);
                          final catStr = q['Category'] as String? ?? '기타';
                          final realId = q['Question_id'] as int?;

                          return Container(
                            margin: EdgeInsets.only(bottom: 12), // MODIFIED
                            decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.white.withOpacity(0.9), borderRadius: BorderRadius.circular(16), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.black.withOpacity(0.08)), boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 8, offset: Offset(0, 3))]), // MODIFIED
                            child: Padding(
                              padding: const EdgeInsets.all(14.0), // MODIFIED
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, crossAxisAlignment: CrossAxisAlignment.start, children: [ // MODIFIED
                                  Expanded(child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [ // MODIFIED
                                    Text('문제 ${realId ?? (index + 1)}', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: isDarkMode ? Colors.white : Colors.black87)), // MODIFIED
                                    SizedBox(width: 8), // MODIFIED
                                    Container(
                                      padding: EdgeInsets.symmetric(horizontal: 8, vertical: 3), // MODIFIED
                                      decoration: BoxDecoration(color: Color(0xFF8E9AAF).withOpacity(0.15), borderRadius: BorderRadius.circular(8)), // MODIFIED
                                      child: Text('$roundName - $catStr', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: Color(0xFF8E9AAF))), // MODIFIED
                                    ),
                                  ])),
                                  GestureDetector(onTap: () => handleBookmarkTap(uniqueKey, q), child: Container(padding: EdgeInsets.all(7), decoration: BoxDecoration(color: isBookmarked ? Color(0xFF2196F3).withOpacity(0.15) : (isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.withOpacity(0.1)), borderRadius: BorderRadius.circular(8)), child: Icon(isBookmarked ? Icons.bookmark_rounded : Icons.bookmark_border_rounded, color: isBookmarked ? Color(0xFF2196F3) : Colors.grey.shade600, size: 18))), // MODIFIED
                                ]),
                                SizedBox(height: 10), // MODIFIED
                                if (q['Big_Question'] != null && q['Big_Question'] != '') _buildBigQuestionWidget(q['Big_Question'], isDarkMode),
                                if (q['Big_Question'] != null && q['Big_Question'] != '') const SizedBox(height: 8), // MODIFIED
                                _buildBigQuestionSpecialWidget(q, isDarkMode),
                                _buildModernQuestionWidget(q['Question'], isDarkMode),
                                const SizedBox(height: 14), // MODIFIED
                                _buildUnifiedOptionsWidget(uniqueKey: uniqueKey, questionData: q, option1: q['Option1'], option2: q['Option2'], option3: q['Option3'], option4: q['Option4'], correctOpt: q['Correct_Option'], userSelected: userSelected, isDarkMode: isDarkMode),
                                if (showDesc) _buildModernDescWidget(q['Answer_description'], isDarkMode),
                              ]),
                            ),
                          );
                        },
                      )),
                    ]);
                  },
                ),
            ),
          ],
        )))),
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