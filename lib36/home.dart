import 'dart:io';

import 'package:flutter/material.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:provider/provider.dart';
import 'package:in_app_review/in_app_review.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'ad_state.dart';
import 'question_select.dart';
import 'CategorySelectPage.dart';
import 'ad_remove.dart';
import 'ad_config.dart';
import 'random_select.dart';
import 'statistics.dart';
import 'package:url_launcher/url_launcher.dart';
import 'setting.dart';
import 'ad_helper.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:async';
import 'dart:math';
import 'audio_select.dart';
import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'config.dart';
import 'ox_quiz_page.dart';
import 'widgets/common/index.dart';


class HomePage extends StatefulWidget {
  final Function(ThemeMode)? onThemeChanged;

  HomePage({this.onThemeChanged});

  @override
  _HomePageState createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> with TickerProviderStateMixin {
  InterstitialAd? _interstitialAd;
  RewardedAd? _rewardedAd;
  bool _isAdLoaded = false;
  bool _isRewardedAdLoaded = false;
  bool _adRemoved = false;
  String _motivationalQuote = '';
  Timer? _timer;
  bool _isAdStateInitialized = false;
  
  late AnimationController _fadeController;
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  final InAppReview _inAppReview = InAppReview.instance;

  final List<String> motivationalQuotes = [
    '지금의 노력은 반드시 보답받을 거예요.',
    '꿈을 향한 한 걸음, 그대여 오늘도 화이팅!',
    '조금만 더, 합격은 바로 앞에 있어요!',
    '꾸준히 걸어온 길이기에 당신은 꼭 성공할 거예요.',
    '자신을 믿으세요. 당신은 충분히 준비되어 있어요.',
    '목표를 이룰 당신의 모습이 기대돼요.',
    '지금의 노력은 미래의 빛나는 순간으로 돌아옵니다.',
    '오늘 흘린 땀방울은 내일의 미소가 됩니다.',
    '그대의 노력이 결코 헛되지 않을 것입니다.',
    '매일 조금씩 나아가는 당신을 응원합니다.',
    '노력은 당신을 절대 배신하지 않아요.',
    '흔들리지 않고 피는 꽃이 어디 있겠어요? 힘내세요!',
    '스스로를 믿고, 오늘도 최선을 다하세요.',
    '어려운 순간이 오더라도 당신은 이겨낼 수 있어요.',
    '실패는 성공으로 가는 과정 중 하나일 뿐이에요.',
    '오늘 당신의 작은 노력들이 큰 결과를 만듭니다.',
    '포기하지 않는 그 모습이 가장 아름답습니다.',
    '끝까지 가는 사람이 결국 이깁니다.',
    '미래에서 왔습니다. 합격이네요!',
    '자격증 하나가 인생의 터닝포인트가 될 수 있어요.',
    '하루하루가 당신의 합격에 가까워지고 있습니다.',
    '열심히 해온 당신에게 행운이 따를 거예요.',
    '꿈을 현실로 만드는 여정, 지금 시작입니다.',
    '당신의 땀이 성공의 밑거름이 됩니다.',
    '오늘의 피곤함은 내일의 성취감입니다.',
    '불가능해 보였던 것도 해내고 있는 당신, 멋져요!',
    '시작했다는 것 자체가 이미 큰 성과입니다.',
    '합격의 순간, 이제 곧 입니다!',
  ];

@override
void initState() {
  super.initState();
  _initializePurchaseStatus();
  _initializeMotivationalQuote();
  _startQuoteUpdateTimer();

  _fadeController = AnimationController(
    duration: const Duration(milliseconds: 1500),
    vsync: this,
  );
  _slideController = AnimationController(
    duration: const Duration(milliseconds: 1200),
    vsync: this,
  );
  
  _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
    CurvedAnimation(parent: _fadeController, curve: Curves.easeInOut),
  );
  _slideAnimation = Tween<Offset>(begin: Offset(0, 0.3), end: Offset.zero).animate(
    CurvedAnimation(parent: _slideController, curve: Curves.easeOutCubic),
  );

  _fadeController.forward();
  _slideController.forward();

  WidgetsBinding.instance.addPostFrameCallback((_) {
    print("addPostFrameCallback triggered");
    _requestTrackingPermission(context);
  });

  WidgetsBinding.instance.addPostFrameCallback((_) async {
      await _initializeAdState();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _interstitialAd?.dispose();
    _rewardedAd?.dispose();
    _fadeController.dispose();
    _slideController.dispose();
    super.dispose();
  }

  Future<void> _initializeAdState() async {
    print('Initializing AdState...');
    final adState = Provider.of<AdState>(context, listen: false);
    await adState.isInitialized;
    print('AdState initialization complete: adsRemoved = ${adState.adsRemoved}');
    setState(() {
      _isAdStateInitialized = true;
    });
    if (!adState.adsRemoved && !kDisableAdsForTesting) {
      print('AdState indicates ads should load');
      _loadInterstitialAd();
      _loadRewardedAd();
    } else {
      print('AdState indicates ads are removed or testing mode, skipping load');
    }
  }

// _initializePurchaseStatus 메서드를 수정
Future<void> _initializePurchaseStatus() async {
  SharedPreferences prefs = await SharedPreferences.getInstance();
  bool adRemoved = prefs.getBool('ad_removed') ?? false;

  // AdState만 업데이트 (로컬 _adRemoved 상태 제거)
  final adState = Provider.of<AdState>(context, listen: false);
  adState.adsRemoved = adRemoved;

  adsRemovedGlobal = adRemoved;
}

  Future<void> _initializeMotivationalQuote() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    String? storedQuote = prefs.getString('motivational_quote');
    int? lastUpdateTimestamp = prefs.getInt('last_quote_update');

    final currentTimestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;
    const oneHourInSeconds = 3600;

    if (storedQuote != null && lastUpdateTimestamp != null) {
      int timeDifference = currentTimestamp - lastUpdateTimestamp;
      if (timeDifference < oneHourInSeconds) {
        setState(() {
          _motivationalQuote = storedQuote;
        });
        return;
      }
    }

    await _updateMotivationalQuote();
  }

  Future<void> _updateMotivationalQuote() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    String newQuote = motivationalQuotes[Random().nextInt(motivationalQuotes.length)];
    int currentTimestamp = DateTime.now().millisecondsSinceEpoch ~/ 1000;

    await prefs.setString('motivational_quote', newQuote);
    await prefs.setInt('last_quote_update', currentTimestamp);

    setState(() {
      _motivationalQuote = newQuote;
    });
  }

  void _startQuoteUpdateTimer() {
    _timer = Timer.periodic(Duration(hours: 1), (timer) {
      _updateMotivationalQuote();
    });
  }

void _launchReview() async {
  print("Launching review...");
  if (await _inAppReview.isAvailable()) {
    print("In-app review is available, requesting review...");
    await _inAppReview.requestReview();
    print("Review request completed");
  } else {
    print("In-app review not available, redirecting to App Store...");
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(
          '현재 리뷰가 지원되지 않습니다. 앱 스토어로 이동합니다.',
          style: TextStyle(
            color: Theme.of(context).brightness == Brightness.dark
                ? Colors.white
                : Colors.black,
          ),
        ),
      ),
    );
    
    const url = 'https://apps.apple.com/app/id6747970390';
    if (await canLaunchUrl(Uri.parse(url))) {
      await launchUrl(Uri.parse(url));
    } else {
      print("Failed to launch App Store URL");
    }
  }
}

Future<void> _requestTrackingPermission(BuildContext context) async {
  bool isTestEnvironment = Platform.environment.containsKey('FLUTTER_TEST');
  print("isTestEnvironment: $isTestEnvironment");

  final adState = Provider.of<AdState>(context, listen: false);
  bool disableAdsForTesting = adState.adsRemoved || kDisableAdsForTesting;
  print("disableAdsForTesting: $disableAdsForTesting (adsRemoved: ${adState.adsRemoved}, kDisableAdsForTesting: $kDisableAdsForTesting)");

  if (isTestEnvironment || disableAdsForTesting) {
    print("Skipping ATT request due to test environment or ads disabled");
    return;
  }

  SharedPreferences prefs = await SharedPreferences.getInstance();
  bool hasRequestedTracking = prefs.getBool('has_requested_tracking') ?? false;
  print("hasRequestedTracking: $hasRequestedTracking");

  if (hasRequestedTracking) {
    print("Skipping ATT request: already requested");
    return;
  }

  final status = await AppTrackingTransparency.trackingAuthorizationStatus;
  print("Tracking status: $status");
  if (status == TrackingStatus.notDetermined) {
    print("Requesting ATT permission...");
    await AppTrackingTransparency.requestTrackingAuthorization();
    final newStatus = await AppTrackingTransparency.trackingAuthorizationStatus;
    print("New ATT status after request: $newStatus");
    await prefs.setBool('has_requested_tracking', true);
    print("ATT permission requested and saved");
  } else {
    print("ATT status already determined: $status");
  }

  if (!adsRemovedGlobal) {
    _loadInterstitialAd();
    _loadRewardedAd();
  }
}

void _loadInterstitialAd() {
    final adState = Provider.of<AdState>(context, listen: false);
    if (adState.adsRemoved || kDisableAdsForTesting) {
      print("Skipping ad load: ads removed or testing mode");
      return;
    }

    AppTrackingTransparency.trackingAuthorizationStatus.then((status) {
      final bool personalized = status == TrackingStatus.authorized;

      InterstitialAd.load(
        adUnitId: AdHelper.interstitialAdUnitId,
        request: AdRequest(
          nonPersonalizedAds: !personalized,
        ),
        adLoadCallback: InterstitialAdLoadCallback(
          onAdLoaded: (ad) {
            setState(() {
              _interstitialAd = ad;
              _isAdLoaded = true;
            });
            _interstitialAd!.fullScreenContentCallback = FullScreenContentCallback(
              onAdDismissedFullScreenContent: (ad) {
                ad.dispose();
                setState(() {
                  _isAdLoaded = false;
                });
                if (!adState.adsRemoved && !kDisableAdsForTesting) {
                  _loadInterstitialAd();
                }
              },
              onAdFailedToShowFullScreenContent: (ad, error) {
                ad.dispose();
                setState(() {
                  _isAdLoaded = false;
                });
                if (!adState.adsRemoved && !kDisableAdsForTesting) {
                  _loadInterstitialAd();
                }
              },
            );
          },
          onAdFailedToLoad: (error) {
            print('InterstitialAd failed to load: $error');
            setState(() {
              _isAdLoaded = false;
            });
          },
        ),
      );
    });
  }

  void _loadRewardedAd() {
    final adState = Provider.of<AdState>(context, listen: false);
    if (adState.adsRemoved || kDisableAdsForTesting) {
      print("Skipping rewarded ad load: ads removed or testing mode");
      return;
    }

    AppTrackingTransparency.trackingAuthorizationStatus.then((status) {
      final bool personalized = status == TrackingStatus.authorized;

      RewardedAd.load(
        adUnitId: AdHelper.rewardedAdUnitId,
        request: AdRequest(
          nonPersonalizedAds: !personalized,
        ),
        rewardedAdLoadCallback: RewardedAdLoadCallback(
          onAdLoaded: (RewardedAd ad) {
            setState(() {
              _rewardedAd = ad;
              _isRewardedAdLoaded = true;
            });
            _rewardedAd!.fullScreenContentCallback = FullScreenContentCallback(
              onAdDismissedFullScreenContent: (RewardedAd ad) {
                ad.dispose();
                setState(() {
                  _isRewardedAdLoaded = false;
                });
                if (!adState.adsRemoved && !kDisableAdsForTesting) {
                  _loadRewardedAd();
                }
              },
              onAdFailedToShowFullScreenContent: (RewardedAd ad, AdError error) {
                ad.dispose();
                setState(() {
                  _isRewardedAdLoaded = false;
                });
                if (!adState.adsRemoved && !kDisableAdsForTesting) {
                  _loadRewardedAd();
                }
              },
            );
          },
          onAdFailedToLoad: (LoadAdError error) {
            print('RewardedAd failed to load: $error');
            setState(() {
              _isRewardedAdLoaded = false;
            });
          },
        ),
      );
    });
  }

void _showStatsWithAd() {
    final adState = Provider.of<AdState>(context, listen: false);
    if (adState.adsRemoved || kDisableAdsForTesting || !_isAdLoaded || _interstitialAd == null) {
      _navigateToStats();
      return;
    }

    _interstitialAd!.fullScreenContentCallback = FullScreenContentCallback(
      onAdDismissedFullScreenContent: (ad) {
        ad.dispose();
        setState(() {
          _isAdLoaded = false;
        });
        _navigateToStats();
        if (!adState.adsRemoved && !kDisableAdsForTesting) {
          _loadInterstitialAd();
        }
      },
      onAdFailedToShowFullScreenContent: (ad, error) {
        ad.dispose();
        setState(() {
          _isAdLoaded = false;
        });
        _navigateToStats();
        if (!adState.adsRemoved && !kDisableAdsForTesting) {
          _loadInterstitialAd();
        }
      },
    );
    _interstitialAd!.show();
  }

  void _navigateToStats() {
    Navigator.push(context, MaterialPageRoute(builder: (context) => StatisticsPage()));
  }

  // 마인드맵 광고 및 내비게이션 함수 추가






  void _showOXQuizWithAd() {
    final adState = Provider.of<AdState>(context, listen: false);

    if (adState.adsRemoved || kDisableAdsForTesting) {
      _navigateToOXQuiz();
      return;
    }

    if (!_isRewardedAdLoaded) {
      _loadRewardedAd();
    }

    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text("OX 퀴즈"),
        content: Text("OX 퀴즈를 풀기 위해 광고를 시청하시겠습니까?"),
        actions: [
          TextButton(
            child: Text("아니요"),
            onPressed: () => Navigator.pop(context),
          ),
          TextButton(
            child: Text("예: 시청하기"),
            onPressed: () {
              Navigator.pop(context);
              _showRewardedAdAndNavigateToOXQuiz();
            },
          ),
        ],
      ),
    );
  }

  void _showRewardedAdAndNavigateToOXQuiz() {
    if (_rewardedAd != null && _isRewardedAdLoaded) {
      _rewardedAd!.show(
        onUserEarnedReward: (AdWithoutView ad, RewardItem rewardItem) {
          print("User earned reward: ${rewardItem.amount} ${rewardItem.type}");
          _navigateToOXQuiz();
        },
      );
    } else {
      Fluttertoast.showToast(
        msg: '광고가 아직 준비되지 않았습니다. 바로 OX 퀴즈로 이동합니다.',
        toastLength: Toast.LENGTH_SHORT,
        gravity: ToastGravity.BOTTOM,
      );
      _navigateToOXQuiz();
    }
  }

  void _navigateToOXQuiz() {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => OXQuizPage(category: "전체문제"),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;

    // 광고제거 배너 표시 여부 결정
  final adState = Provider.of<AdState>(context);
  bool showBanner = !adState.adsRemoved;
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
                  _buildModernHeader(isDarkMode),
                  
                  if (_motivationalQuote.isNotEmpty)
                    _buildMotivationalCard(isDarkMode),
                  
                  Expanded(
                    child: _buildMainContent(isDarkMode),
                  ),
                  
                  // 광고제거 배너 표시
                  if (showBanner)
                    _buildModernBanner('광고 제거', isDarkMode),
                ],
              ),
            ),
          ),
        ),
      ),
      drawer: _buildModernDrawer(isDarkMode),
    );
  }

  Widget _buildModernHeader(bool isDarkMode) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 20, vertical: 16),
      child: Row(
        children: [
          Builder(
            builder: (context) => GestureDetector(
              onTap: () => Scaffold.of(context).openDrawer(),
              child: Container(
                padding: EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white.withOpacity(0.3)),
                ),
                child: Icon(
                  Icons.menu_rounded,
                  color: isDarkMode ? Colors.white : Colors.black87,
                  size: 24,
                ),
              ),
            ),
          ),
          SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '산업안전기사',
                  style: TextStyle(
                    color: isDarkMode ? Colors.white : Colors.black87,
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.5,
                  ),
                ),
                Text(
                  '합격을 향한 여정을 시작하세요',
                  style: TextStyle(
                    color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54,
                    fontSize: 14,
                    fontWeight: FontWeight.w400,
                  ),
                ),
              ],
            ),
          ),
          Container(
            padding: EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withOpacity(0.3)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMotivationalCard(bool isDarkMode) {
    return Container(
      margin: EdgeInsets.symmetric(horizontal: 20, vertical: 8),
      padding: EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.white.withOpacity(0.7),
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
      child: Row(
        children: [
          Container(
            padding: EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Color(0xFFDAA520).withOpacity(0.3),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              Icons.auto_awesome_rounded,
              color: Color(0xFFDAA520),
              size: 20,
            ),
          ),
          SizedBox(width: 12),
          Expanded(
            child: Text(
              _motivationalQuote,
              style: TextStyle(
                color: isDarkMode ? Colors.white : Colors.black87,
                fontSize: 15,
                fontWeight: FontWeight.w500,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMainContent(bool isDarkMode) {
    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(horizontal: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(height: 20),
          
          Text(
            '학습 메뉴',
            style: TextStyle(
              color: isDarkMode ? Colors.white : Colors.black87,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: 16),
          
          _buildMainFeatureCards(),
          
          SizedBox(height: 24),
          
          Text(
            '추가 기능',
            style: TextStyle(
              color: isDarkMode ? Colors.white : Colors.black87,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: 16),
          
          _buildAdditionalFeatureCards(),
          
          SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildMainFeatureCards() {
    return Column(
      children: [
        Row(
          children: [
            Expanded(
              child: _buildFeatureCard(
                title: '연도별\n문제풀기',
                icon: Icons.calendar_month_rounded,
                color: Color(0xFF00897B),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => QuestionSelectPage())),
              ),
            ),
            SizedBox(width: 12),
            Expanded(
              child: _buildFeatureCard(
                title: '과목별\n문제풀기',
                icon: Icons.library_books_rounded,
                color: Color(0xFF1E88E5),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => CategorySelectPage())),
              ),
            ),
          ],
        ),
        SizedBox(height: 12),
        Row(
          children: [
            Expanded(
              child: _buildFeatureCard(
                title: '랜덤\n문제풀기',
                icon: Icons.shuffle_rounded,
                color: Color(0xFFFB8C00),
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => RandomQuestionSelectPage())),
              ),
            ),
            SizedBox(width: 12),
            Expanded(
              child: _buildFeatureCard(
                title: 'OX\n퀴즈',
                icon: Icons.quiz_rounded,
                color: Color(0xFFE53935),
                onTap: _showOXQuizWithAd,
                isSpecial: true,
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildAdditionalFeatureCards() {
  return Column(
    children: [

      SizedBox(height: 12),
      _buildWideFeatureCard(
        title: '기출 음성듣기',
        subtitle: '이동 중에도 학습하세요',
        icon: Icons.headphones_rounded,
        color: Color(0xFF4CAF50),
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (context) => AudioSelectPage())),
      ),

      SizedBox(height: 12),
      _buildWideFeatureCard(
        title: '학습 통계보기',
        subtitle: '나의 학습 현황을 확인하세요',
        icon: Icons.analytics_rounded,
        color: Color(0xFF795548),
        onTap: _showStatsWithAd,
      ),
    ],
  );
}
  Widget _buildFeatureCard({
    required String title,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
    bool isSpecial = false,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 120,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              color, 
              Color.lerp(color, Colors.black, 0.2)!
            ],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(20),
          boxShadow: [
            BoxShadow(
              color: color.withOpacity(0.3),
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
              Padding(
                padding: EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Container(
                      padding: EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        icon,
                        color: Colors.white,
                        size: 24,
                      ),
                    ),
                    Spacer(),
                    Text(
                      title,
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        height: 1.2,
                      ),
                    ),
                    if (isSpecial) ...[
                      SizedBox(height: 4),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildWideFeatureCard({
    required String title,
    required String subtitle,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return GradientCardWidget(
      title: title,
      subtitle: subtitle,
      icon: icon,
      color: color,
      onTap: onTap,
      isWide: true,
      height: 80,
    );
  }

  Widget _buildModernBanner(String bannerText, bool isDarkMode) {
    return GestureDetector(
      onTap: () {
        Navigator.push(context, MaterialPageRoute(builder: (context) => AdRemovePage())).then((_) {
          _initializePurchaseStatus(); // 광고제거 페이지에서 돌아온 후 상태 업데이트
        });
      },
      child: Container(
        margin: EdgeInsets.all(20),
        padding: EdgeInsets.symmetric(vertical: 16, horizontal: 20),
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: [
              Color(0xFFD4AF37),
              Color(0xFFDAA520),
            ],
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
          ),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: Color(0xFFD4AF37).withOpacity(0.3),
              blurRadius: 10,
              offset: Offset(0, 5),
            ),
          ],
        ),
        child: Row(
          children: [
            Container(
              padding: EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.2),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                Icons.workspace_premium_rounded,
                color: Colors.white,
                size: 20,
              ),
            ),
            SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    bannerText,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    '광고 없이 앱을 사용하세요',
                    style: TextStyle(
                      color: Colors.white.withOpacity(0.8),
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.arrow_forward_ios_rounded,
              color: Colors.white,
              size: 16,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildModernDrawer(bool isDarkMode) {
    return Drawer(
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: isDarkMode
                ? [Color(0xFF2C2C2C), Color(0xFF3E3E3E)]
                : [Color(0xFFF8F9FA), Color(0xFFE9ECEF)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: ListView(
          padding: EdgeInsets.zero,
          children: [
            DrawerHeader(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    Colors.white.withOpacity(0.1),
                    Colors.transparent,
                  ],
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Container(
                    padding: EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      Icons.school_rounded,
                      color: isDarkMode ? Colors.white : Colors.black87,
                      size: 32,
                    ),
                  ),
                  SizedBox(height: 12),
                  Text(
                    '산업안전기사 기출문제',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  Text(
                    '기출문제 학습 앱',
                    style: TextStyle(
                      color: Colors.white70,
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
            _buildDrawerItem(
              icon: Icons.analytics_rounded,
              title: '통계보기',
              isDarkMode: isDarkMode,
              onTap: () {
                Navigator.pop(context);
                _showStatsWithAd();
              },
            ),
            _buildDrawerItem(
              icon: Icons.rate_review_rounded,
              title: '리뷰쓰기',
              isDarkMode: isDarkMode,
              onTap: () {
                Navigator.pop(context);
                _launchReview();
              },
            ),
            _buildDrawerItem(
              icon: Icons.block_rounded,
              title: '광고제거',
              isDarkMode: isDarkMode,
              onTap: () {
                Navigator.pop(context);
                Navigator.push(context, MaterialPageRoute(builder: (context) => AdRemovePage())).then((_) {
                  _initializePurchaseStatus();
                });
              },
            ),
            _buildDrawerItem(
              icon: Icons.settings_rounded,
              title: '설정',
              isDarkMode: isDarkMode,
              onTap: () {
                Navigator.pop(context);
                Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (context) => SettingPage(onThemeChanged: widget.onThemeChanged ?? (mode) {}),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDrawerItem({
    required IconData icon,
    required String title,
    required bool isDarkMode,
    required VoidCallback onTap,
  }) {
    return ListTile(
      leading: Container(
        padding: EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, color: isDarkMode ? Colors.white : Colors.black87, size: 20),
      ),
      title: Text(
        title,
        style: TextStyle(
          fontSize: 16,
          color: isDarkMode ? Colors.white : Colors.black87,
          fontWeight: FontWeight.w500,
        ),
      ),
      onTap: onTap,
      contentPadding: EdgeInsets.symmetric(horizontal: 20, vertical: 4),
    );
  }
}