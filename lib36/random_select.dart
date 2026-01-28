import 'package:flutter/material.dart';
import 'package:fluttertoast/fluttertoast.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:provider/provider.dart';
import 'widgets/common/index.dart';
import 'random_question_screen.dart';
import 'ad_helper.dart';
import 'constants.dart';
import 'ad_state.dart';
import 'home.dart';

class RandomQuestionSelectPage extends StatefulWidget {
  const RandomQuestionSelectPage({Key? key}) : super(key: key);

  @override
  _RandomQuestionSelectPageState createState() => _RandomQuestionSelectPageState();
}

class _RandomQuestionSelectPageState extends State<RandomQuestionSelectPage> with TickerProviderStateMixin {
  RewardedAd? _rewardedAd;
  bool _isAdLoaded = false;
  bool _isAdStateInitialized = false;

  late AnimationController _fadeController;
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    print('[RS_SELECT] initState called');
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _initializeAdState();
    });

    _fadeController = AnimationController(duration: const Duration(milliseconds: 1200), vsync: this);
    _slideController = AnimationController(duration: const Duration(milliseconds: 1000), vsync: this);
    _fadeAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(CurvedAnimation(parent: _fadeController, curve: Curves.easeInOut));
    _slideAnimation = Tween<Offset>(begin: Offset(0, 0.2), end: Offset.zero).animate(CurvedAnimation(parent: _slideController, curve: Curves.easeOutCubic));
    _fadeController.forward();
    _slideController.forward();
  }

  Future<void> _initializeAdState() async {
    print('[RS_SELECT] Initializing AdState...');
    final adState = Provider.of<AdState>(context, listen: false);
    await adState.isInitialized;
    print('[RS_SELECT] AdState initialization complete: adsRemoved = ${adState.adsRemoved}');
    if (mounted) {
      setState(() {
        _isAdStateInitialized = true;
      });
      if (!adState.adsRemoved) {
        print('[RS_SELECT] AdState indicates ads should load');
        _loadRewardedAd();
      } else {
        print('[RS_SELECT] AdState indicates ads are removed, skipping load');
      }
    }
  }

  void _loadRewardedAd() {
    print('[RS_SELECT] Attempting to load RewardedAd...');
    final adState = Provider.of<AdState>(context, listen: false);
    if (adState.adsRemoved) {
        print('[RS_SELECT] Ads are removed by purchase, skipping RewardedAd load.');
        return;
    }

    RewardedAd.load(
      adUnitId: AdHelper.rewardedAdUnitId,
      request: const AdRequest(),
      rewardedAdLoadCallback: RewardedAdLoadCallback(
        onAdLoaded: (ad) {
          print('[RS_SELECT] RewardedAd loaded successfully (instance: ${ad.hashCode})');
          if (mounted) {
            setState(() {
              _rewardedAd = ad;
              _isAdLoaded = true;
            });
          }
          _rewardedAd!.fullScreenContentCallback = FullScreenContentCallback(
            onAdDismissedFullScreenContent: (currentAd) {
              print('[RS_SELECT] RewardedAd (instance: ${currentAd.hashCode}) dismissed.');
              currentAd.dispose();
              if (mounted) {
                setState(() {
                  _rewardedAd = null;
                  _isAdLoaded = false;
                });
                final adState = Provider.of<AdState>(context, listen: false);
                if (!adState.adsRemoved) {
                  _loadRewardedAd();
                }
              }
            },
            onAdFailedToShowFullScreenContent: (currentAd, error) {
              print('[RS_SELECT] RewardedAd (instance: ${currentAd.hashCode}) failed to show: $error');
              currentAd.dispose();
              if (mounted) {
                setState(() {
                  _rewardedAd = null;
                  _isAdLoaded = false;
                });
                final adState = Provider.of<AdState>(context, listen: false);
                if (!adState.adsRemoved) {
                  _loadRewardedAd();
                }
              }
            },
            onAdShowedFullScreenContent: (currentAd) {
              print('[RS_SELECT] RewardedAd (instance: ${currentAd.hashCode}) showed full screen content.');
            },
          );
        },
        onAdFailedToLoad: (error) {
          print('[RS_SELECT] RewardedAd failed to load: $error');
          if (mounted) {
            setState(() {
              _isAdLoaded = false;
              _rewardedAd = null;
            });
          }
        },
      ),
    );
  }

  Future<void> _showAdDialog(String category) async {
    final adState = Provider.of<AdState>(context, listen: false);
    if (adState.adsRemoved) {
      print('[RS_SELECT] Ads removed, navigating directly to $category');
      _navigateToRandomQuestion(category);
      return;
    }

    print('[RS_SELECT] Showing ad dialog for $category');
    bool? shouldWatchAd = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(children: [
          Container(padding: EdgeInsets.all(8), decoration: BoxDecoration(color: Color(0xFF8E9AAF).withOpacity(0.2), borderRadius: BorderRadius.circular(8)), child: Icon(Icons.play_circle_outline, color: Color(0xFF8E9AAF))),
          SizedBox(width: 12),
          Text("광고 시청"),
        ]),
        content: Text("문제를 풀기 위해 광고를 시청하시겠습니까?"),
        actions: [
          TextButton(child: Text("아니요", style: TextStyle(color: Colors.grey[600])), onPressed: () => Navigator.pop(context, false)),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Color(0xFF8E9AAF), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8))),
            child: Text("예: 시청하기", style: TextStyle(color: Colors.white)),
            onPressed: () {
              Navigator.pop(context, true);
            },
          ),
        ],
      ),
    );

    if (shouldWatchAd == true) {
      print('[RS_SELECT] User chose to watch ad for $category.');
      _showRewardedAdAndNavigate(category);
    } else {
      print('[RS_SELECT] User chose not to watch ad for $category.');
    }
  }

  void _showRewardedAdAndNavigate(String category) {
    final RewardedAd? adToShow = _rewardedAd;
    final bool adIsCurrentlyLoaded = _isAdLoaded;
    print('[RS_SELECT] Attempting to show ad for $category. Ad instance: ${adToShow?.hashCode}, IsLoaded: $adIsCurrentlyLoaded');

    if (adToShow != null && adIsCurrentlyLoaded) {
      adToShow.show(
        onUserEarnedReward: (AdWithoutView ad, RewardItem reward) {
          print('[RS_SELECT] onUserEarnedReward CALLED for ad ${ad.hashCode}, category $category. Reward: ${reward.amount} ${reward.type}');
          if (mounted) {
            print('[RS_SELECT] Widget is mounted. Calling _navigateToRandomQuestion for $category.');
            _navigateToRandomQuestion(category);
          } else {
            print('[RS_SELECT] Widget NOT MOUNTED when onUserEarnedReward was called. Navigation SKIPPED for $category.');
          }
        },
      );
    } else {
      print('[RS_SELECT] Ad not ready to show for $category. _rewardedAd is null: ${_rewardedAd == null}, _isAdLoaded: $_isAdLoaded. Navigating directly.');
      Fluttertoast.showToast(
        msg: '광고가 아직 준비되지 않았습니다. 바로 문제를 풀러 갑니다.',
        toastLength: Toast.LENGTH_SHORT,
        gravity: ToastGravity.BOTTOM,
      );
      _navigateToRandomQuestion(category);
    }
  }

  void _navigateToRandomQuestion(String category) {
    print('[RS_SELECT] _navigateToRandomQuestion CALLED for category: $category. Current context: $context');
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (context) => RandomQuestionPage(category: category),
      ),
    ).then((_) {
      print('[RS_SELECT] Returned from RandomQuestionPage for category $category');
      final adState = Provider.of<AdState>(context, listen: false);
      if(!adState.adsRemoved && !_isAdLoaded && _rewardedAd == null){
          _loadRewardedAd();
      }
    }).catchError((error) {
      print('[RS_SELECT] ERROR during navigation to RandomQuestionPage for $category: $error');
    });
  }

  @override
  void dispose() {
    _rewardedAd?.dispose();
    _fadeController.dispose();
    _slideController.dispose();
    super.dispose();
  }


  @override
  Widget build(BuildContext context) {
    if (!_isAdStateInitialized) {
      return Scaffold(body: Center(child: CircularProgressIndicator(color: Theme.of(context).primaryColor)));
    }
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    return Scaffold(
      body: ThemedBackgroundWidget(
        isDarkMode: isDarkMode,
        child: SafeArea(child: FadeTransition(opacity: _fadeAnimation, child: SlideTransition(position: _slideAnimation, child: Column(
          children: [
            CommonHeaderWidget(
              title: '랜덤 문제 선택',
              subtitle: '원하는 옵션을 선택하세요',
            ),
            Expanded(child: SingleChildScrollView(
              padding: EdgeInsets.all(20),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(height: 16),
                GestureDetector(
                  onTap: () => _showAdDialog("ALL"),
                  child: Container(height: 130, decoration: BoxDecoration(gradient: LinearGradient(colors: [Color(0xFF9B59B6), Color(0xFF8E44AD)], begin: Alignment.topLeft, end: Alignment.bottomRight), borderRadius: BorderRadius.circular(20), boxShadow: [BoxShadow(color: Color(0xFF9B59B6).withOpacity(0.3), blurRadius: 12, offset: Offset(0, 6))]),
                    child: Container(decoration: BoxDecoration(borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.white.withOpacity(0.2),width: 1)),
                      child: Stack(children: [
                        Positioned(top: -10, right: -10, child: Container(width: 60, height: 60, decoration: BoxDecoration(color: Colors.white.withOpacity(0.1), shape: BoxShape.circle))),
                        Padding(padding: EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Container(padding: EdgeInsets.all(10), decoration: BoxDecoration(color: Colors.white.withOpacity(0.2), borderRadius: BorderRadius.circular(15)), child: Icon(Icons.shuffle_rounded, color: Colors.white, size: 28)),
                          Spacer(),
                          Text('전체 문제 랜덤 풀기', style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold)), SizedBox(height: 5),
                        ])),
                      ]),
                    ),
                  ),
                ),
                SizedBox(height: 24),
                Text('과목별 랜덤 풀기', style: TextStyle(color: isDarkMode ? Colors.white : Colors.black87, fontSize: 18, fontWeight: FontWeight.bold)), SizedBox(height: 16),
                GridView.builder(
                  shrinkWrap: true, 
                  physics: NeverScrollableScrollPhysics(),
                  gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2, 
                    childAspectRatio: 0.95, // Increased from 0.85 to give more height
                    crossAxisSpacing: 12, 
                    mainAxisSpacing: 12
                  ),
                  itemCount: categories.length,
                  itemBuilder: (context, index) {
                    final categoryName = categories[index];
                    final Color cardColor = [Color(0xFF2d2d41), Color(0xFF8E9AAF), Color(0xFFAA88BB)][index % 3];
                    return GestureDetector(
                      onTap: () => _showAdDialog(categoryName),
                      child: Container(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            colors: [cardColor, cardColor.withOpacity(0.8)], 
                            begin: Alignment.topLeft, 
                            end: Alignment.bottomRight
                          ), 
                          borderRadius: BorderRadius.circular(20), 
                          boxShadow: [BoxShadow(color: cardColor.withOpacity(0.3), blurRadius: 10, offset: Offset(0, 5))]
                        ),
                        child: Container(
                          decoration: BoxDecoration(
                            borderRadius: BorderRadius.circular(20), 
                            border: Border.all(color: Colors.white.withOpacity(0.2), width: 1)
                          ),
                          child: Stack(
                            children: [
                              Positioned(
                                top: -5, 
                                right: -5, 
                                child: Container(
                                  width: 30, 
                                  height: 30, 
                                  decoration: BoxDecoration(
                                    color: Colors.white.withOpacity(0.1), 
                                    shape: BoxShape.circle
                                  )
                                )
                              ),
                              Padding(
                                padding: EdgeInsets.all(10), // Reduced from 12
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      padding: EdgeInsets.all(5), // Reduced from 6
                                      decoration: BoxDecoration(
                                        color: Colors.white.withOpacity(0.2), 
                                        borderRadius: BorderRadius.circular(10)
                                      ),
                                      child: Icon(
                                        Icons.category_rounded, 
                                        color: Colors.white, 
                                        size: 18 // Reduced from 20
                                      )
                                    ),
                                    Expanded(
                                      child: Align(
                                        alignment: Alignment.bottomLeft,
                                        child: Column(
                                          mainAxisSize: MainAxisSize.min,
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              categoryName,
                                              style: TextStyle(
                                                color: Colors.white, 
                                                fontSize: 13, // Reduced from 14
                                                fontWeight: FontWeight.bold
                                              ),
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis
                                            ),
                                            Text(
                                              '랜덤 문제 풀기',
                                              style: TextStyle(
                                                color: Colors.white.withOpacity(0.8), 
                                                fontSize: 11 // Reduced from 12
                                              )
                                            ),
                                          ],
                                        ),
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
                  },
                ),
              ]),
            )),
          ],
        )))),
      ),
    );
  }
}