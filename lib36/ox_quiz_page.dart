import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

import 'database_helper.dart';
import 'home.dart';
import 'ox_bookmark.dart';
import 'ox_wronganswer.dart';
import 'ad_helper.dart';
import 'ad_config.dart';
import 'constants.dart';
import 'statistics.dart'; // recordOXLearningSession import


class OXQuizPage extends StatefulWidget {
  final String category; // "전체문제" 또는 특정 과목

  const OXQuizPage({Key? key, required this.category}) : super(key: key);

  @override
  _OXQuizPageState createState() => _OXQuizPageState();
}

class _OXQuizPageState extends State<OXQuizPage> {
  // OX 문제용 카테고리 목록 - constants.dart에서 가져오기
  late final List<String> oxCategories;

  // 라디오/정답/해설/북마크 상태
  Map<String, String> selectedOptions = {}; // 키를 고유 식별자로 변경
  Map<String, bool> isCorrectOptions = {};
  Map<String, bool> showAnswerDescription = {};
  Map<String, bool> savedQuestions = {};

  // 정답/오답 목록
  List<String> correctAnswers = [];
  List<String> wrongAnswers = [];

  // 문제 목록 Future
  late Future<List<Map<String, dynamic>>> futureQuestions;
  bool isLoading = false;
  String errorMessage = '';

  InterstitialAd? _interstitialAd;
  bool _isAdLoaded = false;
  int _currentIndex = 0;

  // 현재 선택된 카테고리
  String _selectedCategory = '전체문제';

  @override
  void initState() {
    super.initState();
    
    // constants.dart의 categories를 사용하여 카테고리 목록 구성
    oxCategories = ['전체문제'] + categories;
    
    _selectedCategory = widget.category == "ALL" ? '전체문제' : widget.category;
    loadCorrectWrongAnswers();
    futureQuestions = fetchOXQuestions();
    loadSavedQuestions();
    loadSelectedStatesFromPrefs();

    if (!adsRemovedGlobal) {
      _loadInterstitialAd();
    }
  }

  /// (A) 정답/오답 로드
  Future<void> loadCorrectWrongAnswers() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      correctAnswers = prefs.getStringList('ox_correctAnswers') ?? [];
      wrongAnswers = prefs.getStringList('ox_wrongAnswers') ?? [];
    } catch (e) {
      print('Error loading OX correct/wrong answers: $e');
      correctAnswers = [];
      wrongAnswers = [];
    }
  }

  /// (B) 정답/오답 저장
  Future<void> saveAnswersToPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList('ox_correctAnswers', correctAnswers);
      await prefs.setStringList('ox_wrongAnswers', wrongAnswers);
    } catch (e) {
      print('Error saving OX answers: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('답변 저장 중 오류가 발생했습니다.')),
        );
      }
    }
  }

  /// (C) OX 문제 로드
  Future<List<Map<String, dynamic>>> fetchOXQuestions() async {
    setState(() {
      isLoading = true;
      errorMessage = '';
    });

    try {
      DatabaseHelper? dbHelper;
      List<Map<String, dynamic>> allQuestions = [];
      
      try {
        dbHelper = DatabaseHelper.getInstance('assets/quiz.db');
        final questions = await dbHelper.getAllQuestions();
        print('Loaded ${questions.length} OX questions from quiz.db');
        
        if (questions.isNotEmpty) {
          allQuestions.addAll(questions);
        }
      } catch (e) {
        print('Error loading OX questions from quiz.db: $e');
        setState(() {
          isLoading = false;
          errorMessage = 'OX 문제 데이터베이스를 불러오지 못했습니다.';
        });
        return [];
      }

      if (allQuestions.isEmpty) {
        setState(() {
          isLoading = false;
          errorMessage = 'OX 문제를 불러오지 못했습니다.';
        });
        return [];
      }

      // 카테고리 필터 (전체문제가 아닌 경우)
      if (_selectedCategory != '전체문제') {
        allQuestions = allQuestions.where((q) => q['Category'] == _selectedCategory).toList();
        
        if (allQuestions.isEmpty) {
          setState(() {
            isLoading = false;
            errorMessage = '선택한 카테고리($_selectedCategory)에 해당하는 문제가 없습니다.';
          });
          return [];
        }
      }

      // 셔플
      var random = Random();
      allQuestions.shuffle(random);
      
      // 가져올 문제 수 제한
      int takeCount = (allQuestions.length < 50) ? allQuestions.length : 50;
      
      // 각 문제에 대해 고유 식별자 생성
      List<Map<String, dynamic>> result = [];
      for (var i = 0; i < takeCount; i++) {
        var q = Map<String, dynamic>.from(allQuestions[i]); // 복사본 생성
        int questionId = q['Question_id'] ?? 0;
        
        // 고유 키 생성: "OX|QuestionId|RandomIndex"
        String uniqueKey = "OX|$questionId|$i";
        q['uniqueKey'] = uniqueKey;
        print('Loading OX question: $uniqueKey');
        print('Question content: ${q['Big_Question']}');
        print('Correct answer: ${q['Correct_Option']}');
        print('Answer description: ${q['Answer_description']}');
        
        result.add(q);
      }
      
      setState(() {
        isLoading = false;
      });
      
      return result;
    } catch (e) {
      print('Error in fetchOXQuestions: $e');
      setState(() {
        isLoading = false;
        errorMessage = 'OX 문제를 불러오는 중 오류가 발생했습니다: $e';
      });
      return [];
    }
  }

  /// (D) 북마크 로드
  Future<void> loadSavedQuestions() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedList = prefs.getStringList('ox_savedQuestions') ?? [];
      setState(() {
        for (String item in savedList) {
          if (item.startsWith('OX|')) {
            savedQuestions[item] = true;
          }
        }
      });
    } catch (e) {
      print('Error loading OX saved questions: $e');
    }
  }

  /// (E) 라디오/해설 상태 로드
  Future<void> loadSelectedStatesFromPrefs() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      for (String key in prefs.getKeys()) {
        // selected_OX|xxx
        if (key.startsWith('selected_OX|')) {
          final optionValue = prefs.getString(key);
          if (optionValue != null) {
            final stateKey = key.substring('selected_'.length);
            setState(() {
              selectedOptions[stateKey] = optionValue;
            });
          }
        }
        // showDescription_OX|xxx
        if (key.startsWith('showDescription_OX|')) {
          final showDescValue = prefs.getString(key);
          if (showDescValue != null) {
            final stateKey = key.substring('showDescription_'.length);
            setState(() {
              showAnswerDescription[stateKey] = (showDescValue == 'true');
            });
          }
        }
      }
    } catch (e) {
      print('Error loading OX selected states: $e');
    }
  }

  /// (F) "풀이 상태"만 초기화
  Future<void> resetProgress() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      // 정/오답 목록에서 "OX|..." 제거
      wrongAnswers.removeWhere((item) => item.startsWith('OX|'));
      correctAnswers.removeWhere((item) => item.startsWith('OX|'));
      await prefs.setStringList('ox_wrongAnswers', wrongAnswers);
      await prefs.setStringList('ox_correctAnswers', correctAnswers);

      // 라디오/해설
      final keysToRemove = prefs.getKeys().where((k) =>
          k.startsWith('selected_OX|') ||
          k.startsWith('showDescription_OX|')).toList();
      for (var k in keysToRemove) {
        await prefs.remove(k);
      }

      setState(() {
        selectedOptions.clear();
        isCorrectOptions.clear();
        showAnswerDescription.clear();
      });
    } catch (e) {
      print('Error resetting OX progress: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('상태 초기화 중 오류가 발생했습니다.')),
        );
      }
    }
  }

  /// (G) 광고 로드
  void _loadInterstitialAd() {
    InterstitialAd.load(
      adUnitId: AdHelper.interstitialAdUnitId,
      request: const AdRequest(),
      adLoadCallback: InterstitialAdLoadCallback(
        onAdLoaded: (InterstitialAd ad) {
          _interstitialAd = ad;
          _isAdLoaded = true;
        },
        onAdFailedToLoad: (LoadAdError error) {
          _interstitialAd = null;
          _isAdLoaded = false;
        },
      ),
    );
  }

  /// (H) 보기 탭 => 정/오답
  void handleOptionTap({
    required String uniqueKey,
    required String chosenOpt,
    required dynamic correctOpt,
    required Map<String, dynamic> questionData,
  }) async {
    final correctStr = correctOpt?.toString() ?? '';

    setState(() {
      selectedOptions[uniqueKey] = chosenOpt;
      bool isCorr = (chosenOpt == correctStr);
      isCorrectOptions[uniqueKey] = isCorr;
      showAnswerDescription[uniqueKey] = true;
    });

    try {
      // 라디오/해설 저장
      await saveSelectedStateToPrefs(uniqueKey, chosenOpt);
      await saveShowDescriptionToPrefs(uniqueKey, true);

      // 정/오답 목록
      final prefixKey = 'OX|$uniqueKey';
      if (chosenOpt == correctStr) {
        if (!correctAnswers.contains(prefixKey)) correctAnswers.add(prefixKey);
        wrongAnswers.remove(prefixKey);
      } else {
        if (!wrongAnswers.contains(prefixKey)) wrongAnswers.add(prefixKey);
        correctAnswers.remove(prefixKey);

        dynamic _encodeImageData(dynamic data) {
          if (data is Uint8List) {
            return base64Encode(data);
          }
          return data;
        }

        // 오답노트 JSON
        final prefs = await SharedPreferences.getInstance();
        final qMap = {
          'uniqueId': uniqueKey,
          'Category': questionData['Category'],
          'Big_Question': _encodeImageData(questionData['Big_Question']),
          'Option1': _encodeImageData(questionData['Option1']),
          'Option2': _encodeImageData(questionData['Option2']),
          'Correct_Option': questionData['Correct_Option'],
          'Answer_description': _encodeImageData(questionData['Answer_description']),
        };
        if (qMap['Big_Question'] != null && qMap['Answer_description'] == null) {
          print('Warning: OX question has no description: $uniqueKey');
        }

        final jsonString = jsonEncode(qMap);
        await prefs.setString('ox_wrong_data_$uniqueKey', jsonString);
      }
      await saveAnswersToPrefs();

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(isCorrectOptions[uniqueKey]! ? '정답' : '오답'),
            backgroundColor: isCorrectOptions[uniqueKey]! ? Colors.blue : Colors.red,
            duration: const Duration(seconds: 1),
          ),
        );
      }
    } catch (e) {
      print('Error in OX handleOptionTap: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('처리 중 오류가 발생했습니다.')),
        );
      }
    }
  }

  /// (I) 북마크
  void handleBookmarkTap(String uniqueKey, Map<String, dynamic> question) async {
    try {
      String bookmarkKey = 'OX|$uniqueKey';
      bool newVal = !(savedQuestions[bookmarkKey] ?? false);
      
      setState(() {
        savedQuestions[bookmarkKey] = newVal;
      });

      dynamic _encodeImageData(dynamic data) {
        if (data is Uint8List) {
          return base64Encode(data);
        }
        return data;
      }

      final prefs = await SharedPreferences.getInstance();
      final savedList = prefs.getStringList('ox_savedQuestions') ?? [];

      if (newVal) {
        if (!savedList.contains(bookmarkKey)) {
          savedList.add(bookmarkKey);
        }
        // 북마크 JSON 저장
        final qMap = {
          'uniqueId': uniqueKey,
          'Category': question['Category'],
          'Big_Question': _encodeImageData(question['Big_Question']),
          'Option1': _encodeImageData(question['Option1']),
          'Option2': _encodeImageData(question['Option2']),
          'Correct_Option': question['Correct_Option'],
          'Answer_description': _encodeImageData(question['Answer_description']),
        };
        final jsonString = jsonEncode(qMap);
        await prefs.setString('ox_bookmark_data_$uniqueKey', jsonString);
      } else {
        savedList.remove(bookmarkKey);
        await prefs.remove('ox_bookmark_data_$uniqueKey');
      }

      await prefs.setStringList('ox_savedQuestions', savedList);

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              newVal ? '문제가 북마크에 저장되었습니다' : '문제가 북마크에서 제거되었습니다',
            ),
            duration: const Duration(seconds: 1),
          ),
        );
      }
    } catch (e) {
      print('Error in OX handleBookmarkTap: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('북마크 처리 중 오류가 발생했습니다.')),
        );
      }
    }
  }

  /// (J) 라디오/해설
  Future<void> saveSelectedStateToPrefs(String uniqueKey, String opt) async {
    final prefs = await SharedPreferences.getInstance();
    final key = 'selected_OX|$uniqueKey';
    await prefs.setString(key, opt);
  }

  Future<void> saveShowDescriptionToPrefs(String uniqueKey, bool show) async {
    final prefs = await SharedPreferences.getInstance();
    final key = 'showDescription_OX|$uniqueKey';
    await prefs.setString(key, show.toString());
  }

  /// (K) 진행현황 바
  Widget _buildProgressBar(List<Map<String, dynamic>> questions) {
    final total = questions.length;
    final answered = selectedOptions.length;
    final corrCount = isCorrectOptions.values.where((b) => b).length;
    final wrongCount = answered - corrCount;
    final progressVal = (total == 0) ? 0.0 : (answered / total);
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;

    return Container(
      color: Colors.white,
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      child: Row(
        children: [
          // 왼쪽
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  'OX 풀이 현황: $answered/$total (맞음 $corrCount, 틀림 $wrongCount)',
                  style: TextStyle(
                    color: isDarkMode ? Colors.black.withOpacity(0.8) : Colors.black,
                    fontSize: 14,
                  ),
                ),
                const SizedBox(height: 6),
                LinearProgressIndicator(
                  value: progressVal,
                  backgroundColor: Colors.grey.shade300,
                  color: Colors.blueAccent,
                  minHeight: 6,
                ),
              ],
            ),
          ),
          // 오른쪽 (상태 초기화)
          IconButton(
            icon: const Icon(Icons.refresh, color: Colors.grey),
            onPressed: () async {
              bool? confirm = await showDialog(
                context: context,
                builder: (ctx) => AlertDialog(
                  title: const Text("OX 풀이 상태 초기화"),
                  content: const Text("이미 불러온 OX 문제 세트를 그대로 두고,\n정답/해설 상태만 초기화 하시겠습니까?"),
                  actions: [
                    TextButton(child: Text("아니오"), onPressed: () => Navigator.pop(ctx, false)),
                    TextButton(child: Text("확인"), onPressed: () => Navigator.pop(ctx, true)),
                  ],
                ),
              );
              if (confirm == true) {
                await resetProgress();
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text("OX 풀이 상태가 초기화되었습니다.")),
                  );
                }
              }
            },
          ),
        ],
      ),
    );
  }

  /// (L) 하단 탭
  void onTabTapped(int index) {
    setState(() => _currentIndex = index);
    switch (index) {
      case 0:
        _navigateToPage(0);
        break;
      case 1:
        _showInterstitialAdAndNavigate(1);
        break;
      case 2:
        _showInterstitialAdAndNavigate(2);
        break;
    }
  }

  void _showInterstitialAdAndNavigate(int index) {
    if (adsRemovedGlobal || !_isAdLoaded || _interstitialAd == null) {
      _navigateToPage(index);
      return;
    }
    _interstitialAd!.fullScreenContentCallback = FullScreenContentCallback(
      onAdDismissedFullScreenContent: (ad) {
        ad.dispose();
        setState(() => _isAdLoaded = false);
        _navigateToPage(index);
        if (!adsRemovedGlobal) _loadInterstitialAd();
      },
      onAdFailedToShowFullScreenContent: (ad, error) {
        ad.dispose();
        setState(() => _isAdLoaded = false);
        _navigateToPage(index);
        if (!adsRemovedGlobal) _loadInterstitialAd();
      },
    );
    _interstitialAd!.show();
  }

  void _navigateToPage(int index) {
    switch (index) {
      case 0:
        Navigator.pushAndRemoveUntil(
          context, 
          MaterialPageRoute(builder: (_) => HomePage()), 
          (route) => false
        );
        break;
      case 1:
        Navigator.push(context, MaterialPageRoute(builder: (_) => OXWrongAnswerPage()));
        break;
      case 2:
        Navigator.push(context, MaterialPageRoute(builder: (_) => OXBookmarkPage()));
        break;
    }
  }

  // 새로운 문제 세트 불러오기
  void _loadNewQuestionSet() {
    setState(() {
      futureQuestions = fetchOXQuestions();
      selectedOptions.clear();
      isCorrectOptions.clear();
      showAnswerDescription.clear();
    });
  }

  // 카테고리 변경
  void _onCategoryChanged(String? newCategory) {
    if (newCategory != null && newCategory != _selectedCategory) {
      setState(() {
        _selectedCategory = newCategory;
        // 상태 초기화
        selectedOptions.clear();
        isCorrectOptions.clear();
        showAnswerDescription.clear();
        // 새로운 문제 로드
        futureQuestions = fetchOXQuestions();
      });
    }
  }

  @override
void dispose() {
  // 페이지를 떠날 때 학습 세션 기록
  if (selectedOptions.isNotEmpty) {
    recordOXLearningSession(_selectedCategory, selectedOptions, isCorrectOptions);
  }
  
  _interstitialAd?.dispose();
  super.dispose();
}

  /// 빌드
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
                title: 'OX 문제 풀이',
                subtitle: _selectedCategory == '전체문제' ? '모든 과목 OX 문제' : '$_selectedCategory OX 문제',
                  // ▼▼▼▼▼ 이 줄을 추가해 주세요! ▼▼▼▼▼
                  onHomePressed: () => Navigator.pushAndRemoveUntil(
                    context,
                    MaterialPageRoute(builder: (_) => HomePage()),
                    (route) => false,
                  ),
                ),              Expanded(
                child: isLoading 
                  ? Center(child: CircularProgressIndicator())
                  : FutureBuilder<List<Map<String, dynamic>>>(
          future: futureQuestions,
          builder: (ctx, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            
            if (snapshot.hasError) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.error_outline, size: 48, color: Colors.red),
                    SizedBox(height: 16),
                    Text(
                      'OX 문제 로드 중 오류가 발생했습니다:\n${snapshot.error}',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 16,
                        color: isDarkMode ? Colors.white : Colors.black87,
                      ),
                    ),
                    SizedBox(height: 24),
                    ElevatedButton(
                      onPressed: () => Navigator.pop(context),
                      child: Text('돌아가기'),
                    ),
                  ],
                ),
              );
            }
            
            if (!snapshot.hasData || snapshot.data!.isEmpty || errorMessage.isNotEmpty) {
              return Center(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.warning_amber_rounded, size: 48, color: Colors.amber),
                    SizedBox(height: 16),
                    Text(
                      errorMessage.isNotEmpty 
                        ? errorMessage 
                        : 'OX 문제를 불러올 수 없습니다.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 16,
                        color: isDarkMode ? Colors.white : Colors.black87,
                      ),
                    ),
                    SizedBox(height: 24),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        ElevatedButton(
                          onPressed: _loadNewQuestionSet,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.blue,
                          ),
                          child: Text('다시 시도'),
                        ),
                        SizedBox(width: 16),
                        ElevatedButton(
                          onPressed: () => Navigator.pop(context),
                          child: Text('돌아가기'),
                        ),
                      ],
                    ),
                  ],
                ),
              );
            }

            final questions = snapshot.data!;
            return Column(
              children: [
                _buildProgressBar(questions),

                // 카테고리 선택 드롭다운
                Container(
                  color: Colors.blue.shade50,
                  padding: const EdgeInsets.all(16.0),
                  margin: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 1.0),
                  child: Row(
                    children: [
                      Text(
                        '카테고리: ',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Colors.deepPurple.shade700,
                        ),
                      ),
                      SizedBox(width: 8),
                      Expanded(
                        child: DropdownButton<String>(
                          value: _selectedCategory,
                          isExpanded: true,
                          items: oxCategories.map((String category) {
                            return DropdownMenuItem<String>(
                              value: category,
                              child: Text(
                                category,
                                style: TextStyle(
                                  fontSize: 15,
                                  color: Colors.deepPurple.shade700,
                                ),
                              ),
                            );
                          }).toList(),
                          onChanged: _onCategoryChanged,
                          underline: Container(
                            height: 1,
                            color: Colors.deepPurple.shade300,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                // "새로운 OX문제 풀기" 배너
                Container(
                  color: Colors.amber.shade100,
                  padding: const EdgeInsets.all(16.0),
                  margin: const EdgeInsets.symmetric(horizontal: 12.0, vertical: 1.0),
                  child: InkWell(
                    onTap: _loadNewQuestionSet,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.refresh, color: Colors.deepPurple),
                        const SizedBox(width: 8),
                        Text(
                          '새로운 OX문제 풀기',
                          style: TextStyle(
                            fontSize: 16,
                            color: Colors.deepPurple.shade700,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                // 문제 리스트
                Expanded(
                  child: ListView.builder(
                    itemCount: questions.length,
                    itemBuilder: (ctx, index) {
                      final q = questions[index];
                      final uniqueKey = q['uniqueKey'] as String;
                      final catStr = q['Category'] as String? ?? '';
                      final bigQString = q['Big_Question'] as String?;
                      final userSelected = selectedOptions[uniqueKey];
                      final correctOpt = q['Correct_Option'];
                      final showDesc = showAnswerDescription[uniqueKey] ?? false;
                      final isBookmarked = savedQuestions['OX|$uniqueKey'] ?? false;

                      // 문제 순서 번호 (index + 1)
                      final questionNumber = index + 1;

                      return Padding(
                        padding: const EdgeInsets.all(8.0),
                        child: Card(
                          child: Padding(
                            padding: const EdgeInsets.all(12.0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // 상단 - 카테고리와 문제 번호
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Expanded(
                                      child: Text(
                                        'OX 문제 - $catStr $questionNumber',
                                        style: TextStyle(
                                          fontSize: 16,
                                          fontWeight: FontWeight.bold,
                                          color: isDarkMode ? Colors.grey : Colors.black,
                                        ),
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                    IconButton(
                                      icon: Icon(
                                        isBookmarked ? Icons.bookmark : Icons.bookmark_border,
                                        color: isBookmarked ? Colors.blue : Colors.grey,
                                      ),
                                      onPressed: () => handleBookmarkTap(uniqueKey, q),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),

                                // 문제 텍스트 (Big_Question에서 "문제 XX:" 부분 제거)
                                if (bigQString != null && bigQString.isNotEmpty) ...[
                                  Container(
                                    margin: const EdgeInsets.only(top: 8),
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      border: Border.all(color: Colors.grey),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(
                                      // "문제 XX:" 패턴 제거
                                      bigQString.replaceFirst(RegExp(r'^문제\s*\d+:\s*'), ''),
                                      style: TextStyle(
                                        fontSize: 18,
                                        color: isDarkMode ? Colors.white : Colors.black,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 16),
                                ],

                                // O/X 옵션을 한 줄에 배치 (라디오 버튼 제거)
                                _buildOXOptionsRow(
                                  questionData: q,
                                  uniqueKey: uniqueKey,
                                  correctOpt: correctOpt,
                                  selectedOpt: userSelected,
                                  isDarkMode: isDarkMode,
                                ),

                                // 해설
                                if (showDesc) _buildDescWidget(q['Answer_description']),
                              ],
                            ),
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
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: onTabTapped,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.edit_document), label: 'OX 문제풀이'),
          BottomNavigationBarItem(icon: Icon(Icons.check_box_sharp), label: 'OX 오답노트'),
          BottomNavigationBarItem(icon: Icon(Icons.bookmark), label: 'OX 즐겨찾기'),
        ],
      ),
    );
  }

  /// O/X 옵션을 한 줄에 배치 (라디오 버튼 제거)
  Widget _buildOXOptionsRow({
    required Map<String, dynamic> questionData,
    required String uniqueKey,
    required dynamic correctOpt,
    required String? selectedOpt,
    required bool isDarkMode,
  }) {
    final correctStr = correctOpt?.toString() ?? '';
    final option1 = questionData['Option1'] as String? ?? 'O';
    final option2 = questionData['Option2'] as String? ?? 'X';

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // O 옵션
        Expanded(
          child: _buildOXButton(
            text: option1,
            optionLetter: '1',
            uniqueKey: uniqueKey,
            questionData: questionData,
            correctStr: correctStr,
            selectedOpt: selectedOpt,
            isDarkMode: isDarkMode,
          ),
        ),
        SizedBox(width: 20),
        // X 옵션
        Expanded(
          child: _buildOXButton(
            text: option2,
            optionLetter: '2',
            uniqueKey: uniqueKey,
            questionData: questionData,
            correctStr: correctStr,
            selectedOpt: selectedOpt,
            isDarkMode: isDarkMode,
          ),
        ),
      ],
    );
  }

  /// 개별 O/X 버튼
  Widget _buildOXButton({
    required String text,
    required String optionLetter,
    required String uniqueKey,
    required Map<String, dynamic> questionData,
    required String correctStr,
    required String? selectedOpt,
    required bool isDarkMode,
  }) {
    // 색상 로직
    Color backgroundColor = Colors.grey.shade200;
    Color textColor = isDarkMode ? Colors.black : Colors.black;
    Color borderColor = Colors.grey.shade400;

    if (selectedOpt != null) {
      final isSelected = (selectedOpt == optionLetter);
      final isCorrect = (optionLetter == correctStr);
      
      if (isSelected) {
        if (isCorrect) {
          backgroundColor = Colors.blue.shade100;
          textColor = Colors.blue.shade700;
          borderColor = Colors.blue;
        } else {
          backgroundColor = Colors.red.shade100;
          textColor = Colors.red.shade700;
          borderColor = Colors.red;
        }
      } else if (isCorrect) {
        backgroundColor = Colors.blue.shade100;
        textColor = Colors.blue.shade700;
        borderColor = Colors.blue;
      }
    }

    return InkWell(
      onTap: (selectedOpt == null)
          ? () => handleOptionTap(
                uniqueKey: uniqueKey,
                chosenOpt: optionLetter,
                correctOpt: correctStr,
                questionData: questionData,
              )
          : null,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
        decoration: BoxDecoration(
          color: backgroundColor,
          border: Border.all(color: borderColor, width: 2),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Center(
          child: Text(
            text,
            style: TextStyle(
              fontSize: 32,
              fontWeight: FontWeight.bold,
              color: textColor,
            ),
          ),
        ),
      ),
    );
  }

  /// 해설
  Widget _buildDescWidget(dynamic descData) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;

    if (descData == null) return const SizedBox.shrink();
    if (descData is String && descData.isNotEmpty) {
      return Container(
        margin: const EdgeInsets.only(top: 16),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.blue),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(
          descData,
          style: TextStyle(
            fontSize: 16,
            color: isDarkMode ? Colors.blue[300] : Colors.blue,
          ),
        ),
      );
    } else if (descData is Uint8List && descData.isNotEmpty) {
      return Container(
        margin: const EdgeInsets.only(top: 16),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.blue),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Image.memory(descData),
      );
    }
    return const SizedBox.shrink();
  }
}