import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

// 광고 관련 import
import 'ad_helper.dart';
import 'ad_config.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';

import 'home.dart';
import 'ox_bookmark.dart';
import 'ox_quiz_page.dart';

class OXWrongAnswerPage extends StatefulWidget {
  @override
  _OXWrongAnswerPageState createState() => _OXWrongAnswerPageState();
}

class _OXWrongAnswerPageState extends State<OXWrongAnswerPage> {
  List<Map<String, dynamic>> wrongQuestions = [];
  Map<String, String> localSelectedOptions = {}; // 고유 키 사용
  Map<String, bool> localShowDescription = {}; // 고유 키 사용
  bool isLoading = true;
  String errorMessage = '';
  
  int _currentIndex = 1; // 하단 탭(오답노트)이 기본 인덱스

  // 전면 광고 관련 필드
  InterstitialAd? _interstitialAd;
  bool _isAdLoaded = false;

  @override
  void initState() {
    super.initState();
    fetchOXWrongAnswers();

    // 광고 구매 사용자가 아니라면 광고 로드
    if (!adsRemovedGlobal) {
      _loadInterstitialAd();
    }
  }

  /// 전면 광고 로드 함수
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
          print('InterstitialAd failed to load: $error');
          _interstitialAd = null;
          _isAdLoaded = false;
        },
      ),
    );
  }

  /// 전면 광고 표시 -> 페이지 이동
  void _showInterstitialAdAndNavigate(int index) {
    // 광고 구매 사용자는 광고 없이 바로 이동
    if (adsRemovedGlobal) {
      _navigateToPage(index);
      return;
    }
    // 광고가 로드되어 있으면 표시
    if (_isAdLoaded && _interstitialAd != null) {
      _interstitialAd!.fullScreenContentCallback = FullScreenContentCallback(
        onAdDismissedFullScreenContent: (ad) {
          ad.dispose();
          setState(() => _isAdLoaded = false);
          _loadInterstitialAd(); // 광고 다시 로드 시도
          _navigateToPage(index);
        },
        onAdFailedToShowFullScreenContent: (ad, error) {
          ad.dispose();
          setState(() => _isAdLoaded = false);
          _loadInterstitialAd();
          _navigateToPage(index);
        },
      );
      _interstitialAd!.show();
    } else {
      // 광고가 없으면 즉시 이동
      _navigateToPage(index);
    }
  }

  /// 하단 탭에서 이동할 페이지 결정
  void _navigateToPage(int index) {
    switch (index) {
      case 0:
        // OX 문제풀이 아이콘 클릭 시 → 전면광고 후 OXQuizPage 이동
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => OXQuizPage(category: "전체문제")),
        );
        break;
      case 1:
        // 현재 오답노트 페이지이므로 아무 것도 안 함
        break;
      case 2:
        // 북마크 아이콘 클릭 시 → 전면광고 후 OXBookmarkPage 이동
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => OXBookmarkPage()),
        );
        break;
    }
  }

  /// 바텀 탭 선택 시 전면광고 로직
  void onTabTapped(int index) {
    setState(() => _currentIndex = index);
    _showInterstitialAdAndNavigate(index);
  }

  /// wrongQuestions 로드
  Future<void> fetchOXWrongAnswers() async {
    setState(() {
      isLoading = true;
      errorMessage = '';
    });
    
    try {
      final prefs = await SharedPreferences.getInstance();
      final allWrongList = prefs.getStringList('ox_wrongAnswers') ?? [];
      
      // "OX|NN" 형태만 추출
      final oxWrongs = allWrongList.where((item) => item.startsWith('OX|')).toList();
      
      if (oxWrongs.isEmpty) {
        setState(() {
          isLoading = false;
          wrongQuestions = [];
        });
        return;
      }

      final tempList = <Map<String, dynamic>>[];
      for (String item in oxWrongs) {
        try {
          final parts = item.split('|');
          if (parts.length >= 2) {
            final uniqueKey = parts.sublist(1).join('|');
            final jsonString = prefs.getString('ox_wrong_data_$uniqueKey');
            if (jsonString != null) {
              Map<String, dynamic> qData = jsonDecode(jsonString) as Map<String, dynamic>;

              // Base64 디코딩을 위한 헬퍼 함수
              dynamic _decodeImageData(dynamic data) {
                if (data is String) {
                  try {
                    return base64Decode(data);
                  } catch (e) {
                    return data;
                  }
                }
                return data;
              }

              // 이미지일 가능성이 있는 필드들에 _decodeImageData 적용
              qData['Big_Question'] = _decodeImageData(qData['Big_Question']);
              qData['Option1'] = _decodeImageData(qData['Option1']);
              qData['Option2'] = _decodeImageData(qData['Option2']);
              qData['Answer_description'] = _decodeImageData(qData['Answer_description']);

              if (!qData.containsKey('uniqueId')) {
                qData['uniqueId'] = uniqueKey;
              }
              tempList.add(qData);
            }
          }
        } catch (e) {
          print('Error processing OX wrong answer item $item: $e');
        }
      }

      setState(() {
        wrongQuestions = tempList;
        isLoading = false;
      });
    } catch (e) {
      print('Error in fetchOXWrongAnswers: $e');
      setState(() {
        isLoading = false;
        errorMessage = 'OX 오답 노트를 불러오는 중 오류가 발생했습니다.';
      });
    }
  }

  /// 옵션 탭
  void handleOptionTapInWrongPage({
    required String uniqueId,
    required String chosenOpt,
    required dynamic correctOpt,
  }) {
    setState(() {
      localSelectedOptions[uniqueId] = chosenOpt;
      localShowDescription[uniqueId] = true;
    });
  }

  @override
  void dispose() {
    // 전면 광고 dispose
    _interstitialAd?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    bool isDarkMode = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'OX 오답노트',
          style: TextStyle(
            color: isDarkMode ? Colors.white : Colors.black,
          ),
        ),
        backgroundColor: isDarkMode ? Colors.blueGrey[800] : Colors.blueGrey,
        actions: [
          IconButton(
            icon: Icon(Icons.home),
            onPressed: () {
              // 홈 아이콘 클릭 시 전면광고 없이 바로 HomePage로 이동
              Navigator.pushAndRemoveUntil(
                context, 
                MaterialPageRoute(builder: (_) => HomePage()), 
                (route) => false
              );
            },
          ),
        ],
      ),
      body: isLoading 
          ? Center(child: CircularProgressIndicator())
          : errorMessage.isNotEmpty
              ? Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.error_outline, size: 48, color: Colors.red),
                      SizedBox(height: 16),
                      Text(
                        errorMessage,
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 16,
                          color: isDarkMode ? Colors.white : Colors.black87,
                        ),
                      ),
                      SizedBox(height: 24),
                      ElevatedButton(
                        onPressed: () => fetchOXWrongAnswers(),
                        child: Text('다시 시도'),
                      ),
                    ],
                  ),
                )
              : wrongQuestions.isEmpty
                  ? _buildEmptyWrongAnswerView(isDarkMode)
                  : _buildWrongAnswerList(isDarkMode),

      // 바텀 네비게이션 바
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: onTabTapped,
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.edit_document),
            label: 'OX 문제풀이',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.check_box_sharp),
            label: 'OX 오답노트',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.bookmark),
            label: 'OX 즐겨찾기',
          ),
        ],
        selectedItemColor: isDarkMode ? Colors.white : Colors.blue,
        unselectedItemColor: isDarkMode ? Colors.grey[400] : Colors.grey,
        backgroundColor: isDarkMode ? Colors.grey[900] : Colors.white,
      ),
    );
  }

  Widget _buildEmptyWrongAnswerView(bool isDarkMode) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.notes, size: 64, color: isDarkMode ? Colors.grey : Colors.grey[400]),
          SizedBox(height: 16),
          Text(
            '저장된 OX 오답 문제가 없습니다.',
            style: TextStyle(
              fontSize: 16,
              color: isDarkMode ? Colors.white : Colors.black,
            ),
          ),
          SizedBox(height: 20),
          ElevatedButton(
            onPressed: () => Navigator.pushReplacement(
              context,
              MaterialPageRoute(builder: (_) => HomePage()),
            ),
            style: ElevatedButton.styleFrom(
              foregroundColor: isDarkMode ? Colors.white : Colors.black,
              backgroundColor: Colors.blueGrey,
            ),
            child: Text(
              '홈으로 돌아가기',
              style: TextStyle(color: isDarkMode ? Colors.white : Colors.white),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildWrongAnswerList(bool isDarkMode) {
    return RefreshIndicator(
      onRefresh: fetchOXWrongAnswers,
      child: ListView.builder(
        itemCount: wrongQuestions.length,
        itemBuilder: (ctx, index) {
          final q = wrongQuestions[index];
  
          final uniqueId = q['uniqueId'].toString();
          final catName = q['Category'] as String? ?? '';
          final bigQ = q['Big_Question'];
          final option1 = q['Option1'];
          final option2 = q['Option2'];
          final correctOpt = q['Correct_Option'];
          final desc = q['Answer_description'];
  
          final userSelected = localSelectedOptions[uniqueId];
          final showDesc = localShowDescription[uniqueId] ?? false;

          // 문제 순서 번호 (index + 1)
          final questionNumber = index + 1;
  
          return Padding(
            padding: const EdgeInsets.all(8.0),
            child: Card(
              color: isDarkMode ? Colors.grey[900] : Colors.white,
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 상단: 카테고리와 문제 번호
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            'OX 문제 - $catName $questionNumber',
                            style: TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                              color: isDarkMode ? Colors.white : Colors.black,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      ],
                    ),
                    SizedBox(height: 12),
                    
                    // 문제 박스 (Big_Question에서 "문제 XX:" 부분 제거)
                    _buildQuestionBox(bigQ, isDarkMode),
                    SizedBox(height: 16),
                    
                    // O/X 옵션을 한 줄에 배치 (라디오 버튼 제거)
                    _buildOXOptionsRow(
                      uniqueId: uniqueId,
                      option1: option1,
                      option2: option2,
                      correctOpt: correctOpt,
                      userSelected: userSelected,
                      isDarkMode: isDarkMode,
                    ),
  
                    // 해설
                    if (userSelected != null && showDesc)
                      _buildDescWidget(desc, isDarkMode),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  /// 질문 박스
  Widget _buildQuestionBox(dynamic data, bool isDarkMode) {
    if (data == null) return SizedBox.shrink();
    
    String questionText = '';
    if (data is String && data.isNotEmpty) {
      // "문제 XX:" 패턴 제거
      questionText = data.replaceFirst(RegExp(r'^문제\s*\d+:\s*'), '');
    } else if (data is Uint8List && data.isNotEmpty) {
      return Container(
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey),
          borderRadius: BorderRadius.circular(4.0),
        ),
        padding: const EdgeInsets.all(12.0),
        child: Image.memory(data),
      );
    } else {
      return SizedBox.shrink();
    }

    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey),
        borderRadius: BorderRadius.circular(4.0),
      ),
      padding: const EdgeInsets.all(12.0),
      child: Text(
        questionText,
        style: TextStyle(
          fontSize: 18,
          color: isDarkMode ? Colors.white : Colors.black,
        ),
      ),
    );
  }

  /// O/X 옵션을 한 줄에 배치 (라디오 버튼 제거)
  Widget _buildOXOptionsRow({
    required String uniqueId,
    required dynamic option1,
    required dynamic option2,
    required dynamic correctOpt,
    required String? userSelected,
    required bool isDarkMode,
  }) {
    final correctStr = correctOpt?.toString() ?? '';
    final opt1Text = (option1 is String) ? option1 : 'O';
    final opt2Text = (option2 is String) ? option2 : 'X';

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        // O 옵션
        Expanded(
          child: _buildOXButton(
            text: opt1Text,
            optionLetter: '1',
            uniqueId: uniqueId,
            correctStr: correctStr,
            userSelected: userSelected,
            isDarkMode: isDarkMode,
          ),
        ),
        SizedBox(width: 20),
        // X 옵션
        Expanded(
          child: _buildOXButton(
            text: opt2Text,
            optionLetter: '2',
            uniqueId: uniqueId,
            correctStr: correctStr,
            userSelected: userSelected,
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
    required String uniqueId,
    required String correctStr,
    required String? userSelected,
    required bool isDarkMode,
  }) {
    // 색상 로직
    Color backgroundColor = Colors.grey.shade200;
    Color textColor = isDarkMode ? Colors.black : Colors.black;
    Color borderColor = Colors.grey.shade400;

    if (userSelected != null) {
      final isSelected = (userSelected == optionLetter);
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
      onTap: (userSelected == null)
          ? () => handleOptionTapInWrongPage(
                uniqueId: uniqueId,
                chosenOpt: optionLetter,
                correctOpt: correctStr,
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
  Widget _buildDescWidget(dynamic descData, bool isDarkMode) {
    if (descData == null) return SizedBox.shrink();
    
    return Container(
      margin: const EdgeInsets.only(top: 16),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.blue),
        borderRadius: BorderRadius.circular(8),
      ),
      child: (descData is String && descData.isNotEmpty)
          ? Text(
              descData,
              style: TextStyle(fontSize: 16, color: isDarkMode ? Colors.blue[300] : Colors.blue),
            )
          : (descData is Uint8List && descData.isNotEmpty)
              ? Image.memory(descData)
              : SizedBox.shrink(),
    );
  }
}