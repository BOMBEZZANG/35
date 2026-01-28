import 'package:flutter/material.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:provider/provider.dart'; // Provider 추가
import 'home.dart';
import 'widgets/common/index.dart';
import 'ad_helper.dart';
import 'constants.dart';
import 'audio_listen.dart';
import 'ad_state.dart'; // AdState 추가

class AudioSelectPage extends StatefulWidget {
  const AudioSelectPage({Key? key}) : super(key: key);

  @override
  _AudioSelectPageState createState() => _AudioSelectPageState();
}

class _AudioSelectPageState extends State<AudioSelectPage> {
  bool _isYearExpanded = false;
  bool _isCategoryExpanded = false;
  RewardedAd? _rewardedAd;
  bool _isAdLoaded = false;
  bool _isAdStateInitialized = false; // AdState 초기화 상태 추적

  @override
  void initState() {
    super.initState();
    print('AudioSelectPage initState called');
    _initializeAdState();
  }

  Future<void> _initializeAdState() async {
    print('Initializing AdState...');
    final adState = Provider.of<AdState>(context, listen: false);
    await adState.isInitialized; // AdState 초기화 대기
    print('AdState initialization complete: adsRemoved = ${adState.adsRemoved}');
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

  void _loadRewardedAd() {
    print('Attempting to load RewardedAd...');
    RewardedAd.load(
      adUnitId: AdHelper.rewardedAdUnitId,
      request: const AdRequest(),
      rewardedAdLoadCallback: RewardedAdLoadCallback(
        onAdLoaded: (ad) {
          print('RewardedAd loaded successfully');
          setState(() {
            _rewardedAd = ad;
            _isAdLoaded = true;
          });
          _rewardedAd!.fullScreenContentCallback = FullScreenContentCallback(
            onAdDismissedFullScreenContent: (ad) {
              print('Ad dismissed');
              ad.dispose();
              setState(() {
                _isAdLoaded = false;
              });
              final adState = Provider.of<AdState>(context, listen: false);
              if (!adState.adsRemoved) {
                _loadRewardedAd();
              }
            },
            onAdFailedToShowFullScreenContent: (ad, error) {
              print('Ad failed to show: $error');
              ad.dispose();
              setState(() {
                _isAdLoaded = false;
              });
              final adState = Provider.of<AdState>(context, listen: false);
              if (!adState.adsRemoved) {
                _loadRewardedAd();
              }
            },
          );
        },
        onAdFailedToLoad: (error) {
          print('RewardedAd failed to load: $error');
          setState(() {
            _isAdLoaded = false;
            _rewardedAd = null;
          });
        },
      ),
    );
  }

  Future<void> _showAdDialog(String selection, bool isYear) async {
    final adState = Provider.of<AdState>(context, listen: false);

    if (adState.adsRemoved) {
      // 광고 제거 상태(구매자 또는 테스트 모드)일 경우 바로 이동
      print('Ads removed, navigating directly to $selection');
      _navigateToAudioPlay(selection, isYear);
      return;
    }

    print('Showing ad dialog for $selection');
    bool? shouldWatchAd = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('광고 시청'),
        content: Text('음성을 듣기 위해 광고를 시청하시겠습니까?'),
        actions: [
          TextButton(
            onPressed: () {
              print('User declined ad');
              Navigator.pop(context, false);
            },
            child: Text('아니오'),
          ),
          TextButton(
            onPressed: () {
              print('User accepted ad');
              Navigator.pop(context, true);
            },
            child: Text('예: 시청하기'),
          ),
        ],
      ),
    );

    if (shouldWatchAd == true) {
      if (_isAdLoaded && _rewardedAd != null) {
        print('Showing RewardedAd...');
        _rewardedAd!.show(
          onUserEarnedReward: (ad, reward) {
            print('User earned reward: ${reward.amount} ${reward.type}');
            _navigateToAudioPlay(selection, isYear);
          },
        );
      } else {
        print('Ad not loaded, proceeding without ad');
        Fluttertoast.showToast(
          msg: '광고를 로드할 수 없습니다. 바로 음성을 재생합니다.',
          toastLength: Toast.LENGTH_SHORT,
          gravity: ToastGravity.BOTTOM,
        );
        _navigateToAudioPlay(selection, isYear);
      }
    } else if (shouldWatchAd == false) {
      print('User canceled ad');
      Fluttertoast.showToast(
        msg: '광고 시청을 취소했습니다.',
        toastLength: Toast.LENGTH_SHORT,
        gravity: ToastGravity.BOTTOM,
      );
    }
  }

  void _navigateToAudioPlay(String selection, bool isYear) {
    print('Navigating to AudioListenPage for selection: $selection, isYear: $isYear');
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => AudioListenPage(
          round: isYear ? selection : null,
          category: isYear ? null : selection,
        ),
      ),
    );
  }

  @override
  void dispose() {
    _rewardedAd?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_isAdStateInitialized) {
      print('AdState not initialized, showing loading screen');
      return Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    bool isDarkMode = Theme.of(context).brightness == Brightness.dark;

    final filteredRounds = Map.fromEntries(
      reverseRoundMapping.entries.where((entry) => entry.key >= 1 && entry.key <= 3),
    );

    return Scaffold(
      body: ThemedBackgroundWidget(
        isDarkMode: isDarkMode,
        child: SafeArea(
          child: Column(
            children: [
              CommonHeaderWidget(
                title: '기출문제 듣기',
                subtitle: '음성 학습을 시작하세요',
                  // ▼▼▼▼▼ 이 줄을 추가해 주세요! ▼▼▼▼▼
                  onHomePressed: () => Navigator.pushAndRemoveUntil(
                    context,
                    MaterialPageRoute(builder: (_) => HomePage()),
                    (route) => false,
                  ),
                ),              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(16.0),
                  children: [
            Card(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12.0),
              ),
              elevation: 3,
              child: ExpansionTile(
                initiallyExpanded: _isYearExpanded,
                onExpansionChanged: (val) {
                  setState(() {
                    _isYearExpanded = val;
                  });
                },
                title: Text(
                  '연도별 듣기',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                childrenPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                children: [
                  ...filteredRounds.entries.map((entry) {
                    return Container(
                      margin: EdgeInsets.only(bottom: 8.0),
                      width: double.infinity,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          foregroundColor: Colors.white,
                          backgroundColor: Color(0xFF00BCD4),
                          padding: EdgeInsets.symmetric(vertical: 16.0, horizontal: 24.0),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12.0),
                          ),
                          elevation: 3,
                        ),
                        onPressed: () => _showAdDialog(entry.key.toString(), true),
                        child: Text(
                          '${entry.value} 듣기',
                          style: TextStyle(fontSize: 16),
                        ),
                      ),
                    );
                  }).toList(),
                ],
              ),
            ),
            SizedBox(height: 20),
            Card(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12.0),
              ),
              elevation: 3,
              child: ExpansionTile(
                initiallyExpanded: _isCategoryExpanded,
                onExpansionChanged: (val) {
                  setState(() {
                    _isCategoryExpanded = val;
                  });
                },
                title: Text(
                  '과목별 듣기',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                childrenPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                children: [
                  ...categories.map((cat) {
                    return Container(
                      margin: EdgeInsets.only(bottom: 8.0),
                      width: double.infinity,
                      child: ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          foregroundColor: Colors.white,
                          backgroundColor: Color(0xFF2d2d41),
                          padding: EdgeInsets.symmetric(vertical: 16.0, horizontal: 24.0),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12.0),
                          ),
                          elevation: 3,
                        ),
                        onPressed: () => _showAdDialog(cat, false),
                        child: Text(
                          '$cat 듣기',
                          style: TextStyle(fontSize: 16),
                        ),
                      ),
                    );
                  }).toList(),
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
}