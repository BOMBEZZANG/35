import 'package:flutter/material.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:provider/provider.dart';
import 'home.dart';
import 'widgets/common/index.dart';
import 'ad_helper.dart';
import 'question_screen.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'database_helper.dart';
import 'constants.dart';
import 'ad_state.dart';

class QuestionSelectPage extends StatefulWidget {
  @override
  _QuestionSelectPageState createState() => _QuestionSelectPageState();
}

// 라운드별 통계 정보
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

class _QuestionSelectPageState extends State<QuestionSelectPage> with TickerProviderStateMixin {
  RewardedAd? _rewardedAd;
  bool _isRewardedAdLoaded = false;

  // 정오답 기록 (라운드별로 관리하지 않음 - 통계용)
  List<String> correctAnswers = [];
  List<String> wrongAnswers = [];

  // 라운드별 통계를 담을 Future
  late Future<List<RoundStat>> _roundStatsFuture;
  bool _isAdStateInitialized = false;

  // 애니메이션 컨트롤러들
  late AnimationController _fadeController;
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    print('QuestionSelectPage initState called');
    _roundStatsFuture = _loadRoundStats();
    _initializeAdState();

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
    _rewardedAd?.dispose();
    _fadeController.dispose();
    _slideController.dispose();
    super.dispose();
  }

Future<void> _initializeAdState() async {
  // 빌드가 완료된 후 실행되도록 수정
  WidgetsBinding.instance.addPostFrameCallback((_) async {
    print('Initializing AdState...');
    final adState = Provider.of<AdState>(context, listen: false);
    await adState.isInitialized;
    print('AdState initialization complete: adsRemoved = ${adState.adsRemoved}');
    
    if (mounted) {
      setState(() {
        _isAdStateInitialized = true;
      });
      
      if (!adState.adsRemoved) {
        print('AdState indicates ads should load');
        _loadRewardedAd();
      } else {
        print('AdState indicates ads are removed, skipping load');
      }
    }
  });
}

  void _loadRewardedAd() {
    RewardedAd.load(
      adUnitId: AdHelper.rewardedAdUnitId,
      request: AdRequest(),
      rewardedAdLoadCallback: RewardedAdLoadCallback(
        onAdLoaded: (RewardedAd ad) {
          _rewardedAd = ad;
          _isRewardedAdLoaded = true;
          _rewardedAd?.fullScreenContentCallback = FullScreenContentCallback(
            onAdDismissedFullScreenContent: (RewardedAd ad) {
              ad.dispose();
              final adState = Provider.of<AdState>(context, listen: false);
              if (!adState.adsRemoved) {
                _loadRewardedAd();
              }
            },
            onAdFailedToShowFullScreenContent: (RewardedAd ad, AdError error) {
              ad.dispose();
              final adState = Provider.of<AdState>(context, listen: false);
              if (!adState.adsRemoved) {
                _loadRewardedAd();
              }
            },
          );
        },
        onAdFailedToLoad: (LoadAdError error) {
          _rewardedAd = null;
          _isRewardedAdLoaded = false;
        },
      ),
    );
  }

  Future<List<RoundStat>> _loadRoundStats() async {
    final prefs = await SharedPreferences.getInstance();

    List<RoundStat> list = [];
    final rounds = reverseRoundMapping.values.toList();
    for (String roundName in rounds) {
      int totalQuestions = await _getTotalQuestionsForRound(roundName);
      List<String> roundCorrectAnswers = prefs.getStringList('correctAnswers_${roundName}') ?? [];
      List<String> roundWrongAnswers = prefs.getStringList('wrongAnswers_${roundName}') ?? [];

      final prefix = '${roundName}|';
      int correctCount = roundCorrectAnswers.where((s) => s.startsWith(prefix)).length;
      int wrongCount = roundWrongAnswers.where((s) => s.startsWith(prefix)).length;
      int answeredCount = correctCount + wrongCount;

      double rate = 0.0;
      if (answeredCount > 0) {
        rate = (correctCount / answeredCount) * 100.0;
      }

      list.add(RoundStat(
        roundName: roundName,
        totalQuestions: totalQuestions,
        answeredCount: answeredCount,
        correctCount: correctCount,
        wrongCount: wrongCount,
        correctRate: rate,
      ));
    }
    return list;
  }

  Future<int> _getTotalQuestionsForRound(String roundName) async {
    int? roundValue = reverseRoundMapping.entries
        .firstWhere((entry) => entry.value == roundName, orElse: () => MapEntry(-1, '기타'))
        .key;
    if (roundValue == -1) return 0;
    final dbPath = getDbPath(roundName);
    final dbHelper = DatabaseHelper.getInstance(dbPath);
    int cnt = await dbHelper.getQuestionsCount(roundValue);
    return cnt;
  }

  String getDbPath(String round) {
    int? roundValue = reverseRoundMapping.entries
        .firstWhere((entry) => entry.value == round, orElse: () => MapEntry(-1, '기타'))
        .key;
    if (roundValue != -1) {
      return 'assets/question${roundValue}.db';
    } else {
      return 'assets/question_default.db';
    }
  }

  void onRoundSelected(String round) {
    final adState = Provider.of<AdState>(context, listen: false);

    if (adState.adsRemoved) {
        _navigateToNextPage(round);
        return;
    }

    if (!_isRewardedAdLoaded) {
        _loadRewardedAd();
    }

    showDialog(
        context: context,
        builder: (context) => AlertDialog(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
            title: Row(
              children: [
                Container(
                  padding: EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Color(0xFF8E9AAF).withOpacity(0.2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(Icons.play_circle_outline, color: Color(0xFF8E9AAF)),
                ),
                SizedBox(width: 12),
                Text("광고 시청"),
              ],
            ),
            content: Text("문제를 풀기 위해 광고를 시청하시겠습니까?"),
            actions: [
                TextButton(
                    child: Text("아니요", style: TextStyle(color: Colors.grey[600])),
                    onPressed: () => Navigator.pop(context),
                ),
                ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: Color(0xFF8E9AAF),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    child: Text("예: 시청하기", style: TextStyle(color: Colors.white)),
                    onPressed: () {
                        Navigator.pop(context);
                        _showRewardedAdAndNavigate(round);
                    },
                ),
            ],
        ),
    );
  }

  void _showRewardedAdAndNavigate(String round) {
    if (_rewardedAd != null && _isRewardedAdLoaded) {
      _rewardedAd!.show(
        onUserEarnedReward: (AdWithoutView ad, RewardItem rewardItem) {
          _navigateToNextPage(round);
        },
      );
    } else {
      Fluttertoast.showToast(
        msg: '광고가 아직 준비되지 않았습니다.',
        toastLength: Toast.LENGTH_SHORT,
        gravity: ToastGravity.BOTTOM,
      );
      _navigateToNextPage(round);
    }
  }

  void _navigateToNextPage(String round) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => QuestionScreenPage(
          round: round,
          dbPath: getDbPath(round),
        ),
      ),
    ).then((_) {
      setState(() {
        _roundStatsFuture = _loadRoundStats();
      });
    });
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
                  // 공통 헤더
                  CommonHeaderWidget(
                    title: '연도별 문제풀기',
                    subtitle: '원하는 회차를 선택하세요',
                  // ▼▼▼▼▼ 이 줄을 추가해 주세요! ▼▼▼▼▼
                  onHomePressed: () => Navigator.pushAndRemoveUntil(
                    context,
                    MaterialPageRoute(builder: (_) => HomePage()),
                    (route) => false,
                  ),
                ),
                  // 메인 콘텐츠
                  Expanded(
                    child: _buildMainContent(isDarkMode),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }


  // 메인 콘텐츠
  Widget _buildMainContent(bool isDarkMode) {
    return FutureBuilder<List<RoundStat>>(
      future: _roundStatsFuture,
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
                  '문제 데이터를 불러오는 중...',
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
                  Icons.inbox_rounded,
                  size: 48,
                  color: isDarkMode ? Colors.white.withOpacity(0.5) : Colors.black54,
                ),
                SizedBox(height: 16),
                Text(
                  '회차 정보가 없습니다',
                  style: TextStyle(
                    color: isDarkMode ? Colors.white : Colors.black87,
                    fontSize: 16,
                  ),
                ),
              ],
            ),
          );
        }

        final statsList = snapshot.data!;

        return SingleChildScrollView(
          padding: EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(height: 8),
              Text(
                '회차별 학습 현황',
                style: TextStyle(
                  color: isDarkMode ? Colors.white : Colors.black87,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 16),
              GridView.builder(
                shrinkWrap: true,
                physics: NeverScrollableScrollPhysics(),
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: 2,
                  childAspectRatio: 0.8,
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                ),
                itemCount: reverseRoundMapping.length,
                itemBuilder: (context, index) {
                  final roundName = reverseRoundMapping.values.toList()[index];
                  final stat = statsList.firstWhere(
                    (s) => s.roundName == roundName,
                    orElse: () => RoundStat(
                      roundName: roundName,
                      totalQuestions: 0,
                      answeredCount: 0,
                      correctCount: 0,
                      wrongCount: 0,
                      correctRate: 0.0,
                    ),
                  );

                  return _buildRoundCard(stat, isDarkMode);
                },
              ),
              SizedBox(height: 20),
            ],
          ),
        );
      },
    );
  }

  // 개별 회차 카드
  Widget _buildRoundCard(RoundStat stat, bool isDarkMode) {
    final progressValue = (stat.totalQuestions == 0) ? 0.0 : (stat.answeredCount / stat.totalQuestions);
    final rateStr = stat.correctRate.toStringAsFixed(0);

    return GestureDetector(
        key: Key('round_card_${stat.roundName}'),

      onTap: () => onRoundSelected(stat.roundName),
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Color(0xFF8E9AAF),
              Color(0xFF8E9AAF).withOpacity(0.8),
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: Color(0xFF8E9AAF).withOpacity(0.3),
              blurRadius: 12,
              offset: Offset(0, 6),
            ),
          ],
        ),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: Colors.white.withOpacity(0.2),
              width: 1,
            ),
          ),
          child: Stack(
            children: [
              // 배경 패턴
              Positioned(
                top: -10,
                right: -10,
                child: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                ),
              ),
              // 메인 콘텐츠
              Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // 회차명
                    Text(
                      stat.roundName,
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        height: 1.2,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    SizedBox(height: 12),
                    
                    // 진행률 바
                    Container(
                      height: 6,
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(3),
                      ),
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(3),
                        child: LinearProgressIndicator(
                          value: progressValue,
                          backgroundColor: Colors.transparent,
                          valueColor: AlwaysStoppedAnimation<Color>(Colors.white.withOpacity(0.8)),
                          minHeight: 6,
                        ),
                      ),
                    ),
                    SizedBox(height: 12),
                    
                    // 통계 정보
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                        children: [
                          _buildStatRow(
                            icon: Icons.task_alt_rounded,
                            label: '${stat.answeredCount}/${stat.totalQuestions}',
                            subtitle: '완료',
                          ),
                          _buildStatRow(
                            icon: Icons.check_circle_rounded,
                            label: '${stat.correctCount}',
                            subtitle: '정답',
                          ),
                          _buildStatRow(
                            icon: Icons.star_rounded,
                            label: '$rateStr%',
                            subtitle: '정답률',
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  // 통계 행
  Widget _buildStatRow({
    required IconData icon,
    required String label,
    required String subtitle,
  }) {
    return Row(
      children: [
        Container(
          padding: EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.2),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Icon(
            icon,
            color: Colors.white,
            size: 14,
          ),
        ),
        SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                subtitle,
                style: TextStyle(
                  color: Colors.white.withOpacity(0.8),
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}