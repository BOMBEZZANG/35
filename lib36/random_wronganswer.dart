import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:fluttertoast/fluttertoast.dart'; // Fluttertoast 추가
import 'package:flutter_html/flutter_html.dart';

// 광고 관련 import
import 'ad_helper.dart';
import 'ad_config.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:provider/provider.dart'; // AdState 사용을 위해 추가
import 'ad_state.dart'; // AdState 사용을 위해 추가

import 'home.dart';
import 'random_bookmark.dart';
import 'random_question_screen.dart'; 
import 'constants.dart'; 

class RandomWrongAnswerPage extends StatefulWidget {
  @override
  _RandomWrongAnswerPageState createState() => _RandomWrongAnswerPageState();
}

class _RandomWrongAnswerPageState extends State<RandomWrongAnswerPage> with TickerProviderStateMixin {
  List<Map<String, dynamic>> wrongQuestions = [];
  Map<String, String> localSelectedOptions = {}; 
  Map<String, bool> localShowDescription = {}; 
  Map<String, bool> savedQuestionsState = {}; // 북마크 UI 반영용
  bool isLoading = true;
  String errorMessage = '';
  
  int _currentIndex = 1; 

  InterstitialAd? _interstitialAd;
  bool _isAdLoaded = false;

  late AnimationController _fadeController;
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    fetchRandomWrongAnswers();
    loadSavedQuestionStatus(); // 북마크 상태 로드 추가

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

  void _showInterstitialAdAndNavigate(int pageIndex) {
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
    if (_currentIndex == index && index == 1) return; // 현재 페이지가 이미 오답노트 탭

    setState(() { _currentIndex = index; });
    Widget page;
    String routeName;
    switch (index) {
      case 0:
        page = RandomQuestionPage(category: "ALL");
        routeName = '/randomQuestionAll';
        break;
      case 1: // 현재 오답노트 페이지
        fetchRandomWrongAnswers(); // 새로고침
        return;
      case 2:
        page = RandomBookmarkPage();
        routeName = '/randomBookmark';
        break;
      default:
        return;
    }
    Navigator.pushReplacement(context, MaterialPageRoute(builder: (context) => page, settings: RouteSettings(name: routeName)));
  }

  void onTabTapped(int index) {
    _showInterstitialAdAndNavigate(index);
  }

  dynamic _decodeImageData(dynamic data) {
    if (data is String) {
      try {
        if (data.length > 100 && (data.contains('+') || data.contains('/') || data.endsWith('='))) {
          return base64Decode(data);
        }
        return data;
      } catch (e) { return data; }
    }
    return data;
  }

  Future<void> fetchRandomWrongAnswers() async {
    setState(() { isLoading = true; errorMessage = ''; });
    try {
      final prefs = await SharedPreferences.getInstance();
      final allWrongList = prefs.getStringList('wrongAnswers') ?? [];
      final randomWrongs = allWrongList.where((item) => item.startsWith('RANDOM|')).toList();
      if (randomWrongs.isEmpty) {
        setState(() { isLoading = false; wrongQuestions = []; });
        return;
      }
      final tempList = <Map<String, dynamic>>[];
      for (String item in randomWrongs) {
        try {
          final parts = item.split('|');
          if (parts.length >= 2) {
            final uniqueKey = parts.sublist(1).join('|');
            final jsonString = prefs.getString('random_wrong_data_$uniqueKey');
            if (jsonString != null) {
              Map<String, dynamic> qData = jsonDecode(jsonString) as Map<String, dynamic>;
              qData['uniqueId'] = qData['uniqueId'] ?? uniqueKey;
              qData['Big_Question'] = _decodeImageData(qData['Big_Question']);
                qData['Big_Question_Special'] = _decodeImageData(qData['Big_Question_Special']);

              qData['Question'] = _decodeImageData(qData['Question']);
              qData['Option1'] = _decodeImageData(qData['Option1']);
              qData['Option2'] = _decodeImageData(qData['Option2']);
              qData['Option3'] = _decodeImageData(qData['Option3']);
              qData['Option4'] = _decodeImageData(qData['Option4']);
              qData['Answer_description'] = _decodeImageData(qData['Answer_description']);
              if (qData.containsKey('Image') && qData['Image'] != null) {
                 qData['Image'] = _decodeImageData(qData['Image']);
              }
              tempList.add(qData);
            }
          }
        } catch (e) { /* Error processing item */ }
      }
      setState(() { wrongQuestions = tempList; isLoading = false; });
    } catch (e) {
      setState(() { isLoading = false; errorMessage = '오답 노트를 불러오는 중 오류가 발생했습니다.'; });
    }
  }

  Future<void> handleSaveTap(String uniqueKey, Map<String, dynamic> question) async {
    try {
      String bookmarkKey = 'RANDOM|$uniqueKey';
      bool newSaveStatus = !(savedQuestionsState[bookmarkKey] ?? false);
      setState(() { savedQuestionsState[bookmarkKey] = newSaveStatus; });
      dynamic _encodeImageData(dynamic data) { if (data is Uint8List) return base64Encode(data); return data; }
      final prefs = await SharedPreferences.getInstance();
      final savedList = prefs.getStringList('savedQuestions') ?? [];
      if (newSaveStatus) {
        if (!savedList.contains(bookmarkKey)) savedList.add(bookmarkKey);
        final qMap = {
          'uniqueId': uniqueKey, 'ExamSession': question['ExamSession'], 'Category': question['Category'],
          'Big_Question': _encodeImageData(question['Big_Question']), 'Question': _encodeImageData(question['Question']),
          'Option1': _encodeImageData(question['Option1']), 'Option2': _encodeImageData(question['Option2']),
          'Option3': _encodeImageData(question['Option3']), 'Option4': _encodeImageData(question['Option4']),
          'Correct_Option': question['Correct_Option'], 'Answer_description': _encodeImageData(question['Answer_description']),
          if (question.containsKey('Image')) 'Image': _encodeImageData(question['Image']),
        };
        final jsonString = jsonEncode(qMap);
        await prefs.setString('random_bookmark_data_$uniqueKey', jsonString);
      } else {
        savedList.remove(bookmarkKey);
        await prefs.remove('random_bookmark_data_$uniqueKey');
      }
      await prefs.setStringList('savedQuestions', savedList);
      if (mounted) {
        Fluttertoast.showToast(msg: newSaveStatus ? '북마크에 추가되었습니다.' : '북마크에서 삭제되었습니다.');
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('북마크 처리 중 오류가 발생했습니다.')));
    }
  }


  void handleOptionTapInWrongPage({ required String uniqueId, required String chosenOpt, required dynamic correctOpt }) async {
    setState(() {
      localSelectedOptions[uniqueId] = chosenOpt;
      localShowDescription[uniqueId] = true;
    });
    final isCorrect = chosenOpt == correctOpt.toString();
    if (isCorrect) {
      final prefs = await SharedPreferences.getInstance();
      List<String> wrongAnswerKeys = prefs.getStringList('wrongAnswers') ?? [];
      String fullWrongKey = 'RANDOM|$uniqueId'; // "RANDOM|" 접두사 포함된 키
      wrongAnswerKeys.remove(fullWrongKey); // 키로 직접 제거
      await prefs.setStringList('wrongAnswers', wrongAnswerKeys);
      await prefs.remove('random_wrong_data_$uniqueId'); // JSON 데이터도 삭제
      
      Fluttertoast.showToast(msg: "정답! 오답노트에서 삭제됩니다.");
      setState(() { // UI 갱신
        wrongQuestions.removeWhere((q) => q['uniqueId'] == uniqueId);
      });
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('오답입니다.', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
        backgroundColor: Color(0xFFF44336),
        behavior: SnackBarBehavior.floating, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)), duration: Duration(milliseconds: 1500),
      ));
    }
  }

  Widget _buildModernHeader(bool isDarkMode) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(children: [
        GestureDetector(onTap: () => Navigator.pop(context), child: Container(padding: EdgeInsets.all(5), decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.white.withOpacity(0.7), borderRadius: BorderRadius.circular(8), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1))), child: Icon(Icons.arrow_back_ios_rounded, color: isDarkMode ? Colors.white : Colors.black87, size: 16))),
        SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('랜덤 오답노트', style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 16, fontWeight: FontWeight.bold, letterSpacing: 0.3)),
          Text('틀린 문제 다시 풀기', style: TextStyle(color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54, fontSize: 11, fontWeight: FontWeight.w400)),
        ])),
        GestureDetector(onTap: () => Navigator.pushAndRemoveUntil(context, MaterialPageRoute(builder: (_) => HomePage()), (route)=>false), child: Container(padding: EdgeInsets.all(5), decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.white.withOpacity(0.7), borderRadius: BorderRadius.circular(8), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1))), child: Icon(Icons.home_rounded, color: isDarkMode ? Colors.white : Colors.black87, size: 18))),
      ]),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(gradient: LinearGradient(colors: isDarkMode ? [Color(0xFF2C2C2C), Color(0xFF3E3E3E), Color(0xFF4A4A4A)] : [Color(0xFFF5F7FA), Color(0xFFE8ECF0), Color(0xFFDDE4EA)], begin: Alignment.topLeft, end: Alignment.bottomRight)),
        child: SafeArea(child: FadeTransition(opacity: _fadeAnimation, child: SlideTransition(position: _slideAnimation, child: Column(
          children: [
            _buildModernHeader(isDarkMode),
            Expanded(child: isLoading 
              ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [CircularProgressIndicator(color: isDarkMode ? Colors.white : Color(0xFF8E9AAF)), SizedBox(height: 16), Text('오답 문제를 불러오는 중...', style: TextStyle(color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54, fontSize: 16))]))
              : errorMessage.isNotEmpty
                ? Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [Icon(Icons.error_outline_rounded, size: 48, color: Colors.red[400]), SizedBox(height: 16), Text(errorMessage, style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 16)), SizedBox(height: 8), ElevatedButton(onPressed: fetchRandomWrongAnswers, style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF8E9AAF), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))), child: Text('다시 시도'))]))
                : wrongQuestions.isEmpty
                  ? _buildEmptyWrongAnswerView(isDarkMode)
                  : _buildWrongAnswerList(isDarkMode),
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

  Widget _buildEmptyWrongAnswerView(bool isDarkMode) {
    return Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
      Icon(Icons.check_circle_outline_rounded, size: 48, color: isDarkMode ? Colors.white.withOpacity(0.5) : Colors.black54), SizedBox(height: 16), // 아이콘 변경
      Text('저장된 랜덤 오답 문제가 없습니다', style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 16)), SizedBox(height: 8),
      Text('문제를 풀고 틀린 문제들이 여기에 모입니다', style: TextStyle(color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54, fontSize: 14)),
    ]));
  }

 Widget _buildWrongAnswerList(bool isDarkMode) {
    return RefreshIndicator(
      onRefresh: fetchRandomWrongAnswers,
      child: ListView.builder(
        padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8), // MODIFIED
        itemCount: wrongQuestions.length,
        itemBuilder: (ctx, index) {
          final q = wrongQuestions[index];
          final uniqueId = q['uniqueId'].toString();
          final examVal  = q['ExamSession'];
          final roundName = examSessionToRoundName(examVal);
          final catName  = q['Category'] as String? ?? '';
          final questionId = q['Question_id'] as int? ?? (index +1); // uniqueId가 없을 경우 대비
          final bigQ     = q['Big_Question'];
          final question = q['Question'];
          final option1  = q['Option1'];
          final option2  = q['Option2'];
          final option3  = q['Option3'];
          final option4  = q['Option4'];
          final correctOpt = q['Correct_Option'];
          final desc     = q['Answer_description'];
          final userSelected = localSelectedOptions[uniqueId];
          final showDesc     = localShowDescription[uniqueId] ?? false;
          final isBookmarked = savedQuestionsState['RANDOM|$uniqueId'] ?? false; // 북마크 상태 확인

          return Container(
            margin: EdgeInsets.only(bottom: 12), // MODIFIED
            decoration: BoxDecoration(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.white.withOpacity(0.9), borderRadius: BorderRadius.circular(16), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.black.withOpacity(0.08)), boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 8, offset: Offset(0, 3))]), // MODIFIED
            child: Padding(
              padding: const EdgeInsets.all(14.0), // MODIFIED
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, crossAxisAlignment: CrossAxisAlignment.start, children: [ // MODIFIED
                    Expanded(child: Row(crossAxisAlignment: CrossAxisAlignment.center, children: [ // MODIFIED
                      Text('문제 ${questionId}', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: isDarkMode ? Colors.white : Colors.black87)), // MODIFIED
                      SizedBox(width: 8), // MODIFIED
                      Container(
                        padding: EdgeInsets.symmetric(horizontal: 8, vertical: 3), // MODIFIED
                        decoration: BoxDecoration(color: Color(0xFFF44336).withOpacity(0.15), borderRadius: BorderRadius.circular(8)), // MODIFIED: 오답노트 빨간색 태그
                        child: Text('$roundName - $catName', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: Color(0xFFF44336))), // MODIFIED
                      ),
                    ])),
                     GestureDetector(onTap: () => handleSaveTap(uniqueId, q), child: Container(padding: EdgeInsets.all(7), decoration: BoxDecoration(color: isBookmarked ? Color(0xFF2196F3).withOpacity(0.15) : (isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.withOpacity(0.1)), borderRadius: BorderRadius.circular(8)), child: Icon(isBookmarked ? Icons.bookmark_rounded : Icons.bookmark_border_rounded, color: isBookmarked ? Color(0xFF2196F3) : Colors.grey.shade600, size: 18))), // MODIFIED
                  ]),
                  SizedBox(height: 10), // MODIFIED
                  if (bigQ != null && ((bigQ is String && bigQ.isNotEmpty) || bigQ is Uint8List))
                    _buildBigQuestionWidget(bigQ, isDarkMode),
                  if (bigQ != null && ((bigQ is String && bigQ.isNotEmpty) || bigQ is Uint8List))
                    const SizedBox(height: 8), // MODIFIED
                  _buildBigQuestionSpecialWidget(q, isDarkMode),
                  _buildModernQuestionWidget(question, isDarkMode),
                  const SizedBox(height: 14), // MODIFIED
                  _buildUnifiedOptionsWidget(uniqueId, q, userSelected, isDarkMode),
                  if (showDesc) _buildModernDescWidget(desc, isDarkMode),
                ],
              ),
            ),
          );
        },
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

  Widget _buildUnifiedOptionsWidget(String uniqueId, Map<String, dynamic> question, String? selectedOpt, bool isDarkMode) {
    final correctStr = question['Correct_Option']?.toString() ?? '';
    return Container(decoration: BoxDecoration(borderRadius: BorderRadius.circular(10), border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.grey.shade300, width: 1)),
      child: Column(children: [
        _buildOptionRow(uniqueId, question['Option1'], '1', correctStr, selectedOpt, isDarkMode, isFirst: true),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(uniqueId, question['Option2'], '2', correctStr, selectedOpt, isDarkMode),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(uniqueId, question['Option3'], '3', correctStr, selectedOpt, isDarkMode),
        _buildDividerLine(isDarkMode),
        _buildOptionRow(uniqueId, question['Option4'], '4', correctStr, selectedOpt, isDarkMode, isLast: true),
      ]),
    );
  }

  Widget _buildDividerLine(bool isDarkMode) {
    return Container(height: 1, color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200);
  }

  Widget _buildOptionRow(String uniqueId, dynamic optData, String letter, String correctStr, String? selectedOpt, bool isDarkMode, {bool isFirst = false, bool isLast = false}) {
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
      onTap: (selectedOpt == null) ? () => handleOptionTapInWrongPage(uniqueId: uniqueId, chosenOpt: letter, correctOpt: correctStr) : null,
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
}