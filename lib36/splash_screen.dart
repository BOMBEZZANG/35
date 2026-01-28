import 'dart:async';
import 'package:flutter/material.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'home.dart';
import 'ad_helper.dart';
import 'ad_config.dart';
import 'ad_state.dart';
import 'config.dart';
import 'statistics.dart';
import 'widgets/common/index.dart';

class SplashScreen extends StatefulWidget {
  final Function(ThemeMode) onThemeChanged;

  const SplashScreen({Key? key, required this.onThemeChanged}) : super(key: key);

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> with SingleTickerProviderStateMixin {
  AppOpenAd? _appOpenAd;
  bool _isShowingAd = false;
  late AnimationController _animationController;
  late Animation<double> _animation;

  // 최소 스플래시 시간 (애니메이션 등을 보여주기 위함)
  static const int _minimumSplashTime = 2000; // 2초

  @override
  void initState() {
    super.initState();
    recordAppAccess(); // 앱 접속 기록

    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    );

    _animation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeInOut,
    );

    _animationController.forward();

    // 앱 초기화 시작
    _initializeApp();
  }

  /// 비동기 초기화 작업을 병렬로 처리하고 광고를 미리 로드합니다.
  Future<void> _initializeApp() async {
    print('SplashScreen: 앱 초기화 시작');
    
    // 시작 시간 기록
    final startTime = DateTime.now();

    try {
      // 1. 필수 초기화 작업들을 동시에 실행 (병렬 처리)
      final adState = Provider.of<AdState>(context, listen: false);
      await Future.wait([
        adState.isInitialized, // 광고 제거 상태 로드
        _loadAppOpenAd(),     // 앱 오픈 광고 미리 로드 시작
      ]);

      // 2. 광고를 보여줘야 하는지 최종 결정
      final bool shouldShowAd = !adState.adsRemoved && !kDisableAdsForTesting;
      print('SplashScreen: 광고 표시 여부 = $shouldShowAd');

      // 3. 최소 스플래시 시간 보장
      final elapsedTime = DateTime.now().difference(startTime).inMilliseconds;
      if (elapsedTime < _minimumSplashTime) {
        await Future.delayed(Duration(milliseconds: _minimumSplashTime - elapsedTime));
      }
      
      // 4. 광고 표시 또는 홈 화면으로 이동
      if (shouldShowAd && _appOpenAd != null) {
        _showAppOpenAd();
      } else {
        _goToHome();
      }

    } catch (e) {
      print('SplashScreen: 초기화 중 오류 발생 - $e');
      _goToHome(); // 오류 발생 시에도 홈으로 이동
    }
  }

  /// 앱 오픈 광고를 미리 로드합니다.
 Future<void> _loadAppOpenAd() async {
  final adState = Provider.of<AdState>(context, listen: false);
  if (adState.adsRemoved || kDisableAdsForTesting) {
    print('SplashScreen: 광고가 제거되었거나 테스트 모드이므로 앱 오픈 광고를 로드하지 않습니다.');
    return;
  }

  try {
    await AppOpenAd.load(
      adUnitId: AdHelper.appOpenAdUnitId,
      request: const AdRequest(),
      // orientation 파라미터 제거
      adLoadCallback: AppOpenAdLoadCallback(
        onAdLoaded: (ad) {
          print("SplashScreen: AppOpenAd 로드 성공");
          _appOpenAd = ad;
        },
        onAdFailedToLoad: (error) {
          print("SplashScreen: AppOpenAd 로드 실패: $error");
          _appOpenAd = null;
        },
      ),
    );
  } catch (e) {
    print("SplashScreen: AppOpenAd.load() 호출 중 예외 발생: $e");
    _appOpenAd = null;
  }
}

  /// 로드된 앱 오픈 광고를 표시합니다.
  void _showAppOpenAd() {
    if (_isShowingAd) {
      print("SplashScreen: 이미 광고를 표시하고 있습니다.");
      return;
    }

    if (_appOpenAd == null) {
      print("SplashScreen: 표시할 광고가 없습니다. 홈으로 바로 이동합니다.");
      _goToHome();
      return;
    }
    
    print("SplashScreen: 앱 오픈 광고 표시 시도");
    _isShowingAd = true;

    _appOpenAd!.fullScreenContentCallback = FullScreenContentCallback(
      onAdShowedFullScreenContent: (ad) {
        print("SplashScreen: AppOpenAd 표시됨");
      },
      onAdDismissedFullScreenContent: (ad) {
        print("SplashScreen: AppOpenAd 닫힘");
        ad.dispose();
        _appOpenAd = null;
        _goToHome();
      },
      onAdFailedToShowFullScreenContent: (ad, error) {
        print("SplashScreen: AppOpenAd 표시 실패: $error");
        ad.dispose();
        _appOpenAd = null;
        _isShowingAd = false;
        _goToHome();
      },
    );

    _appOpenAd!.show();
  }

  /// 홈 화면으로 이동합니다.
  void _goToHome() {
    if (mounted) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(
          builder: (context) => HomePage(onThemeChanged: widget.onThemeChanged),
        ),
      );
    }
  }

  @override
  void dispose() {
    _animationController.dispose();
    _appOpenAd?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: ThemedBackgroundWidget(
        isDarkMode: isDarkMode,
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              FadeTransition(
                opacity: _animation,
                child: Image.asset(
                  'assets/splash_logo.png', // 로고 이미지가 assets 폴더에 있어야 합니다.
                  width: 150,
                  height: 150,
                  errorBuilder: (context, error, stackTrace) {
                    return Container(
                      width: 150,
                      height: 150,
                      decoration: BoxDecoration(
                        color: Colors.blueAccent,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Icon(Icons.school, size: 80, color: Colors.white),
                    );
                  },
                ),
              ),
              const SizedBox(height: 20),
              Text(
                "산업안전기사 기출문제",
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: isDarkMode ? Colors.white : Colors.black,
                ),
              ),
              const SizedBox(height: 40),
              CircularProgressIndicator(
                color: isDarkMode ? Colors.white : Colors.blueAccent,
              ),
              const SizedBox(height: 16),
              Text(
                "앱을 준비하고 있습니다...",
                style: TextStyle(
                  fontSize: 16,
                  color: isDarkMode ? Colors.white70 : Colors.black54,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}