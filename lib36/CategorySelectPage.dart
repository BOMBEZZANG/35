import 'package:flutter/material.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'ad_helper.dart';
import 'question_list_page.dart'; // 실제 문제풀이 페이지
import 'ad_config.dart'; // adsRemovedGlobal
import 'constants.dart'; // constants.dart 파일 임포트
import 'widgets/common/index.dart';

// 카테고리 통계 모델
class CategoryStat {
  final String categoryName;
  final int totalCount;
  final int answeredCount;
  final int correctCount;
  final int wrongCount;
  final double correctRate;
  final List<RoundStat> roundStats;

  CategoryStat({
    required this.categoryName,
    required this.totalCount,
    required this.answeredCount,
    required this.correctCount,
    required this.wrongCount,
    required this.correctRate,
    required this.roundStats,
  });
}

// 라운드 통계 모델
class RoundStat {
  final String roundName;
  final int totalQuestions;
  final int answeredCount;
  final int correctCount;
  final int wrongCount;
  final double correctRate;

  RoundStat({
    required this.roundName,
    required this.totalQuestions,
    required this.answeredCount,
    required this.correctCount,
    required this.wrongCount,
    required this.correctRate,
  });
}

class CategorySelectPage extends StatefulWidget {
  @override
  _CategorySelectPageState createState() => _CategorySelectPageState();
}

class _CategorySelectPageState extends State<CategorySelectPage> with TickerProviderStateMixin {
  InterstitialAd? _interstitialAd; // 전면 광고
  bool _isInterstitialAdLoaded = false;

  List<String> correctAnswers = [];
  List<String> wrongAnswers = [];
  late Future<List<CategoryStat>> _categoryStatsFuture;

  // 애니메이션 컨트롤러들
  late AnimationController _fadeController;
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    if (!adsRemovedGlobal) {
      _loadInterstitialAd(); // 전면 광고 로드
    }
    _categoryStatsFuture = _loadAllCategoryStats();

    // 애니메이션 컨트롤러 초기화
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

    // 애니메이션 시작
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

  /// 전면 광고 로드
  void _loadInterstitialAd() {
    InterstitialAd.load(
      adUnitId: AdHelper.interstitialAdUnitId,
      request: AdRequest(),
      adLoadCallback: InterstitialAdLoadCallback(
        onAdLoaded: (InterstitialAd ad) {
          _interstitialAd = ad;
          _isInterstitialAdLoaded = true;

          // 전면 광고 콜백
          _interstitialAd?.fullScreenContentCallback = FullScreenContentCallback(
            onAdDismissedFullScreenContent: (ad) {
              ad.dispose();
              _isInterstitialAdLoaded = false;
              // 광고가 닫혔을 때 다시 로드 필요하면 아래 실행
              if (!adsRemovedGlobal) {
                _loadInterstitialAd();
              }
            },
            onAdFailedToShowFullScreenContent: (ad, error) {
              ad.dispose();
              _isInterstitialAdLoaded = false;
              if (!adsRemovedGlobal) {
                _loadInterstitialAd();
              }
            },
          );
        },
        onAdFailedToLoad: (LoadAdError error) {
          _interstitialAd = null;
          _isInterstitialAdLoaded = false;
        },
      ),
    );
  }

  /// 전면 광고 보여주고 문제 페이지로 이동
  void _showInterstitialAdAndNavigate(String category, String round) {
    if (adsRemovedGlobal) {
      // 광고 제거 상태
      _navigateToQuestionList(category, round);
      return;
    }
    if (_interstitialAd != null && _isInterstitialAdLoaded) {
      // 광고 준비됨
      _interstitialAd!.fullScreenContentCallback = FullScreenContentCallback(
        onAdDismissedFullScreenContent: (ad) {
          // 광고 닫힌 후
          ad.dispose();
          _isInterstitialAdLoaded = false;
          // 다시 광고 로드
          if (!adsRemovedGlobal) {
            _loadInterstitialAd();
          }
          // 문제 페이지로 이동
          _navigateToQuestionList(category, round);
        },
        onAdFailedToShowFullScreenContent: (ad, error) {
          ad.dispose();
          _isInterstitialAdLoaded = false;
          if (!adsRemovedGlobal) {
            _loadInterstitialAd();
          }
          // 광고 실패 시 바로 페이지 이동
          _navigateToQuestionList(category, round);
        },
      );
      _interstitialAd!.show();
    } else {
      // 광고가 없으면 바로 이동
      _navigateToQuestionList(category, round);
    }
  }

  // 문제 페이지로 이동
  void _navigateToQuestionList(String cat, String round) {
    // reverseRoundMapping을 사용해 라운드 값을 찾음
    final roundValue = reverseRoundMapping.entries
        .firstWhere((entry) => entry.value == round, orElse: () => MapEntry(-1, '기타'))
        .key;
    if (roundValue == -1) {
      Fluttertoast.showToast(msg: '라운드 매핑 실패');
      return;
    }
    String dbId = roundValue.toString();
    String dbPath = 'assets/question$dbId.db';

    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => QuestionListPage(
          category: cat,
          databaseId: dbId,
          round: round,
          dbPath: dbPath,
        ),
      ),
    ).then((_) {
      // 돌아올 때 다시 통계 로드
      setState(() {
        _categoryStatsFuture = _loadAllCategoryStats();
      });
    });
  }

  /// 카테고리 전체 통계 계산
  Future<List<CategoryStat>> _loadAllCategoryStats() async {
    final prefs = await SharedPreferences.getInstance();
    correctAnswers = prefs.getStringList('correctAnswers') ?? [];
    wrongAnswers = prefs.getStringList('wrongAnswers') ?? [];

    List<CategoryStat> catList = [];

    // constants.dart의 categories 사용
    for (String cat in categories) {
      int catTotal = 120; // 예시
      int catAnswered = 0;
      int catCorrect = 0;
      int catWrong = 0;

      List<RoundStat> roundStatList = [];

      // constants.dart의 reverseRoundMapping 값을 사용해 라운드 이름 리스트 생성
      final rounds = reverseRoundMapping.values.toList();
      for (String round in rounds) {
        int? rv = reverseRoundMapping.entries
            .firstWhere((entry) => entry.value == round, orElse: () => MapEntry(-1, '기타'))
            .key;
        if (rv == -1) continue;

        // dbId|cat|문제ID
        String dbId = rv.toString();
        String prefix = '$dbId|$cat|'; 

        // 실제 DB에서 해당 라운드+카테고리 문제 수
        int totalQ = await _getQuestionsCountForCategoryRound(cat, round);

        int cCount = correctAnswers.where((s) => s.startsWith(prefix)).length;
        int wCount = wrongAnswers.where((s) => s.startsWith(prefix)).length;
        int aCount = cCount + wCount;

        double rr = 0.0;
        if (aCount > 0) {
          rr = (cCount / aCount) * 100.0;
        }

        roundStatList.add(
          RoundStat(
            roundName: round,
            totalQuestions: totalQ,
            answeredCount: aCount,
            correctCount: cCount,
            wrongCount: wCount,
            correctRate: rr,
          ),
        );

        catAnswered += aCount;
        catCorrect += cCount;
        catWrong += wCount;
      }

      double catRate = 0.0;
      if (catAnswered > 0) {
        catRate = (catCorrect / catAnswered) * 100.0;
      }

      catList.add(CategoryStat(
        categoryName: cat,
        totalCount: catTotal,
        answeredCount: catAnswered,
        correctCount: catCorrect,
        wrongCount: catWrong,
        correctRate: catRate,
        roundStats: roundStatList,
      ));
    }

    return catList;
  }

  Future<int> _getQuestionsCountForCategoryRound(String cat, String round) async {
    // 실제 DB 조회 로직
    // 여기선 예시로 20문제
    return 20;
  }


  // 진행 바(ProgressIndicator)용 헬퍼
  Widget _buildProgressBar(double value) {
    return Container(
      height: 4,
      decoration: BoxDecoration(
        color: Colors.grey.shade300,
        borderRadius: BorderRadius.circular(2),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(2),
        child: LinearProgressIndicator(
          value: value,
          backgroundColor: Colors.transparent,
          valueColor: AlwaysStoppedAnimation<Color>(Color(0xFFB4A7D6)),
          minHeight: 4,
        ),
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
          child: FadeTransition(
            opacity: _fadeAnimation,
            child: SlideTransition(
              position: _slideAnimation,
              child: Column(
                children: [
                  // 모던 헤더
                  CommonHeaderWidget(
                    title: '과목별 문제풀기',
                    subtitle: '원하는 과목을 선택하세요',
                    onHomePressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
                  ),
                  
                  // 메인 콘텐츠
                  Expanded(
                    child: FutureBuilder<List<CategoryStat>>(
                      future: _categoryStatsFuture,
                      builder: (context, snapshot) {
                        if (snapshot.connectionState == ConnectionState.waiting) {
                          return Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                CircularProgressIndicator(
                                  color: isDarkMode ? Colors.white : Color(0xFF8E9AAF),
                                ),
                                SizedBox(height: 16),
                                Text(
                                  '카테고리 정보를 불러오는 중...',
                                  style: TextStyle(
                                    color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54,
                                    fontSize: 16,
                                  ),
                                ),
                              ],
                            ),
                          );
                        }
                        if (snapshot.hasError) {
                          return Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.error_outline_rounded,
                                  size: 48,
                                  color: Colors.red[400],
                                ),
                                SizedBox(height: 16),
                                Text(
                                  '데이터를 불러오는 중 오류가 발생했습니다',
                                  style: TextStyle(
                                    color: isDarkMode ? Colors.white : Colors.black87,
                                    fontSize: 16,
                                  ),
                                ),
                                SizedBox(height: 8),
                                Text(
                                  '${snapshot.error}',
                                  style: TextStyle(
                                    color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54,
                                    fontSize: 14,
                                  ),
                                  textAlign: TextAlign.center,
                                ),
                              ],
                            ),
                          );
                        }
                        if (!snapshot.hasData || snapshot.data!.isEmpty) {
                          return Center(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.library_books_rounded,
                                  size: 48,
                                  color: isDarkMode ? Colors.white.withOpacity(0.5) : Colors.black54,
                                ),
                                SizedBox(height: 16),
                                Text(
                                  '카테고리 정보가 없습니다',
                                  style: TextStyle(
                                    color: isDarkMode ? Colors.white : Colors.black87,
                                    fontSize: 16,
                                  ),
                                ),
                              ],
                            ),
                          );
                        }

                        final catList = snapshot.data!;
                        return SingleChildScrollView(
                          padding: EdgeInsets.symmetric(horizontal: 16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              SizedBox(height: 8),
                              Text(
                                '과목별 학습 현황',
                                style: TextStyle(
                                  color: isDarkMode ? Colors.white : Colors.black87,
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                ),
                              ),
                              SizedBox(height: 16),
                              
                              // 카테고리 목록
                              ...catList.map((catStat) {
                                final catAnswered = catStat.answeredCount;
                                final catTotal = catStat.totalCount;
                                final catCorrect = catStat.correctCount;
                                final catWrong = catStat.wrongCount;
                                final catRate = catStat.correctRate.toStringAsFixed(0);
                                double catProgress = (catTotal == 0) ? 0 : (catAnswered / catTotal);

                                return Container(
                                  margin: EdgeInsets.only(bottom: 16),
                                  decoration: BoxDecoration(
                                    color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.white.withOpacity(0.9),
                                    borderRadius: BorderRadius.circular(20),
                                    border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1)),
                                    boxShadow: [
                                      BoxShadow(
                                        color: Colors.black.withOpacity(0.1),
                                        blurRadius: 10,
                                        offset: Offset(0, 5),
                                      ),
                                    ],
                                  ),
                                  child: Theme(
                                    data: Theme.of(context).copyWith(
                                      dividerColor: Colors.transparent,
                                      splashColor: Colors.transparent,
                                      highlightColor: Colors.transparent,
                                    ),
                                    child: ExpansionTile(
                                      tilePadding: EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                                      childrenPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 8),
                                      title: Text(
                                        catStat.categoryName,
                                        style: TextStyle(
                                          fontSize: 18,
                                          fontWeight: FontWeight.bold,
                                          color: isDarkMode ? Colors.white : Colors.black87,
                                        ),
                                      ),
                                      subtitle: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          SizedBox(height: 8),
                                          Text(
                                            '풀이 $catAnswered/$catTotal | 정답 $catCorrect, 오답 $catWrong | 정답률 ${catRate}%',
                                            style: TextStyle(
                                              fontSize: 14,
                                              color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54,
                                            ),
                                          ),
                                          SizedBox(height: 8),
                                          _buildProgressBar(catProgress),
                                        ],
                                      ),
                                      children: catStat.roundStats.map((rs) {
                                        final answered = rs.answeredCount;
                                        final correct = rs.correctCount;
                                        final wrong = rs.wrongCount;
                                        final rTotal = rs.totalQuestions;
                                        final rateStr = rs.correctRate.toStringAsFixed(0);
                                        double roundProgress = (rTotal == 0) ? 0 : (answered / rTotal);

                                        return Container(
                                          margin: EdgeInsets.symmetric(vertical: 6),
                                          padding: EdgeInsets.all(16),
                                          decoration: BoxDecoration(
                                            color: isDarkMode ? Colors.white.withOpacity(0.05) : Colors.grey.shade50,
                                            borderRadius: BorderRadius.circular(12),
                                            border: Border.all(
                                              color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade300,
                                            ),
                                          ),
                                          child: Column(
                                            crossAxisAlignment: CrossAxisAlignment.start,
                                            children: [
                                              Row(
                                                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                                children: [
                                                  Text(
                                                    rs.roundName,
                                                    style: TextStyle(
                                                      fontSize: 16,
                                                      fontWeight: FontWeight.w600,
                                                      color: isDarkMode ? Colors.white : Colors.black87,
                                                    ),
                                                  ),
                                                  Container(
                                                    padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                                    decoration: BoxDecoration(
                                                      color: Color(0xFFB4A7D6).withOpacity(0.2),
                                                      borderRadius: BorderRadius.circular(8),
                                                    ),
                                                    child: Text(
                                                      '$rateStr%',
                                                      style: TextStyle(
                                                        fontSize: 12,
                                                        fontWeight: FontWeight.bold,
                                                        color: Color(0xFFB4A7D6),
                                                      ),
                                                    ),
                                                  ),
                                                ],
                                              ),
                                              SizedBox(height: 8),
                                              Text(
                                                '풀이 $answered/$rTotal | 정답 $correct, 오답 $wrong',
                                                style: TextStyle(
                                                  fontSize: 13,
                                                  color: isDarkMode ? Colors.white.withOpacity(0.7) : Colors.black54,
                                                ),
                                              ),
                                              SizedBox(height: 8),
                                              _buildProgressBar(roundProgress),
                                              SizedBox(height: 12),

                                              // 문제 풀기 버튼
                                              Align(
                                                alignment: Alignment.centerRight,
                                                child: GestureDetector(
                                                  onTap: () => _showInterstitialAdAndNavigate(catStat.categoryName, rs.roundName),
                                                  child: Container(
                                                    padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                                    decoration: BoxDecoration(
                                                      gradient: LinearGradient(
                                                        colors: [
                                                          Color(0xFFB4A7D6),
                                                          Color(0xFFB4A7D6).withOpacity(0.8),
                                                        ],
                                                      ),
                                                      borderRadius: BorderRadius.circular(8),
                                                      boxShadow: [
                                                        BoxShadow(
                                                          color: Color(0xFFB4A7D6).withOpacity(0.3),
                                                          blurRadius: 4,
                                                          offset: Offset(0, 2),
                                                        ),
                                                      ],
                                                    ),
                                                    child: Row(
                                                      mainAxisSize: MainAxisSize.min,
                                                      children: [
                                                        Text(
                                                          '문제 풀기',
                                                          style: TextStyle(
                                                            color: Colors.white,
                                                            fontSize: 14,
                                                            fontWeight: FontWeight.bold,
                                                          ),
                                                        ),
                                                        SizedBox(width: 4),
                                                        Icon(
                                                          Icons.arrow_forward_ios_rounded,
                                                          color: Colors.white,
                                                          size: 14,
                                                        ),
                                                      ],
                                                    ),
                                                  ),
                                                ),
                                              ),
                                            ],
                                          ),
                                        );
                                      }).toList(),
                                    ),
                                  ),
                                );
                              }).toList(),
                              
                              SizedBox(height: 20),
                            ],
                          ),
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
    );
  }
}