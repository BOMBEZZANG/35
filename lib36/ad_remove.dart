import 'dart:async';
import 'package:flutter/material.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AdRemovePage extends StatefulWidget {
  @override
  _AdRemovePageState createState() => _AdRemovePageState();
}

class _AdRemovePageState extends State<AdRemovePage> with TickerProviderStateMixin {
  bool _isAvailable = false;
  List<ProductDetails> _products = [];
  bool _loading = true;
  final String _adRemovalProductId = 'ad_remove_abyeonginuengjang'; // 광고 제거 상품 ID
  late StreamSubscription<List<PurchaseDetails>> _subscription;
  bool _adRemoved = false; // 광고 제거 상태
  
  // 애니메이션 컨트롤러
  late AnimationController _fadeController;
  late AnimationController _slideController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _initInAppPurchase();
    _loadPurchaseStatus();

    final purchaseUpdated = InAppPurchase.instance.purchaseStream;
    _subscription = purchaseUpdated.listen(
      (purchaseDetailsList) {
        _listenToPurchaseUpdated(purchaseDetailsList);
      },
      onError: (error) {
        print("Purchase Stream Error: $error");
      },
    );
    
    // 애니메이션 초기화
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

    _fadeController.forward();
    _slideController.forward();
  }

  @override
  void dispose() {
    _subscription.cancel();
    _fadeController.dispose();
    _slideController.dispose();
    super.dispose();
  }

  // 인앱 구매 초기화 및 상품 정보 조회
  Future<void> _initInAppPurchase() async {
    final bool available = await InAppPurchase.instance.isAvailable();
    if (!available) {
      setState(() {
        _loading = false;
      });
      return;
    }

    final Set<String> ids = {_adRemovalProductId};
    final ProductDetailsResponse response = await InAppPurchase.instance.queryProductDetails(ids);

    if (response.error != null) {
      print("상품 조회 에러: ${response.error}");
      setState(() {
        _loading = false;
      });
      return;
    }

    if (response.productDetails.isEmpty) {
      print("조회된 상품이 없습니다.");
      setState(() {
        _loading = false;
      });
      return;
    }

    setState(() {
      _isAvailable = available;
      _products = response.productDetails;
      _loading = false;
    });
  }

  // 광고 제거 구매 요청
  Future<void> _purchaseAdRemoval() async {
    if (_products.isEmpty) return;

    ProductDetails? product;
    for (var p in _products) {
      if (p.id == _adRemovalProductId) {
        product = p;
        break;
      }
    }

    if (product != null) {
      final PurchaseParam purchaseParam = PurchaseParam(productDetails: product);
      InAppPurchase.instance.buyNonConsumable(purchaseParam: purchaseParam);
    }
  }

  // 구매 복원
  Future<void> _restorePurchases() async {
    setState(() {
      _loading = true;
    });
    
    await InAppPurchase.instance.restorePurchases();
    
    // 복원 요청 후 약간의 딜레이를 주어 UI에 로딩 상태를 표시
    await Future.delayed(Duration(seconds: 1));
    
    setState(() {
      _loading = false;
    });
  }

  // 구매 업데이트 처리
  void _listenToPurchaseUpdated(List<PurchaseDetails> purchaseDetailsList) {
    for (var purchase in purchaseDetailsList) {
      if (purchase.status == PurchaseStatus.pending) {
        setState(() {
          _loading = true;
        });
        print("Purchase is pending...");
      } else if (purchase.status == PurchaseStatus.error) {
        setState(() {
          _loading = false;
        });
        print("Purchase error: ${purchase.error}");
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text("구매 중 오류가 발생했습니다."),
            backgroundColor: Colors.red,
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );
      } else if (purchase.status == PurchaseStatus.purchased || purchase.status == PurchaseStatus.restored) {
        if (purchase.productID == _adRemovalProductId) {
          _handleAdRemovalSuccess(purchase);
        }
      }
      if (purchase.pendingCompletePurchase) {
        InAppPurchase.instance.completePurchase(purchase);
      }
    }
  }

  // 광고 제거 구매 성공 처리
  void _handleAdRemovalSuccess(PurchaseDetails purchase) async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    await prefs.setBool('ad_removed', true);

    setState(() {
      _adRemoved = true;
      _loading = false;
    });

    print("Ad Removal Purchase successful: ${purchase.productID}");

    showDialog(
      context: context,
      builder: (BuildContext context) {
        final isDarkMode = Theme.of(context).brightness == Brightness.dark;
        
        return AlertDialog(
          backgroundColor: isDarkMode ? Color(0xFF3A3A3A) : Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: [
              Container(
                padding: EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: Color(0xFFD4AF37).withOpacity(0.2),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(Icons.workspace_premium, color: Color(0xFFD4AF37)),
              ),
              SizedBox(width: 12),
              Text(
                "광고 제거 완료",
                style: TextStyle(
                  color: isDarkMode ? Colors.white : Colors.black87,
                ),
              ),
            ],
          ),
          content: Text(
            "광고 제거가 성공적으로 완료되었습니다!\n앱을 더욱 쾌적하게 이용하실 수 있습니다. 감사합니다! 🙏",
            style: TextStyle(
              color: isDarkMode ? Colors.white70 : Colors.black87,
            ),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.of(context).pop();
              },
              child: Text(
                "확인",
                style: TextStyle(
                  color: Color(0xFFD4AF37),
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  // SharedPreferences에서 구매 상태 로드
  Future<void> _loadPurchaseStatus() async {
    SharedPreferences prefs = await SharedPreferences.getInstance();
    bool? adRemoved = prefs.getBool('ad_removed');
    
    setState(() {
      _adRemoved = adRemoved ?? false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: isDarkMode
                ? [Color(0xFF2C2C2C), Color(0xFF3E3E3E), Color(0xFF4A4A4A)]
                : [Color(0xFFF5F7FA), Color(0xFFE8ECF0), Color(0xFFDDE4EA)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
        ),
        child: SafeArea(
          child: FadeTransition(
            opacity: _fadeAnimation,
            child: SlideTransition(
              position: _slideAnimation,
              child: Column(
                children: [
                  _buildModernHeader(isDarkMode),
                  
                  Expanded(
                    child: _loading
                      ? _buildLoadingState(isDarkMode)
                      : _adRemoved
                        ? _buildPurchasedState(isDarkMode)
                        : _buildPurchaseOptions(isDarkMode),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
  
  Widget _buildModernHeader(bool isDarkMode) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      child: Row(
        children: [
          GestureDetector(
            onTap: () => Navigator.pop(context),
            child: Container(
              padding: EdgeInsets.all(5),
              decoration: BoxDecoration(
                color: isDarkMode ? Colors.white.withOpacity(0.15) : Colors.white.withOpacity(0.7),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.2) : Colors.black.withOpacity(0.1)),
              ),
              child: Icon(
                Icons.arrow_back_ios_rounded,
                color: isDarkMode ? Colors.white : Colors.black87,
                size: 16,
              ),
            ),
          ),
          SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '광고 제거',
                  style: TextStyle(
                    color: isDarkMode ? Colors.white : Colors.black87,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.3,
                  ),
                ),
                Text(
                  '앱을 더 쾌적하게 이용해보세요',
                  style: TextStyle(
                    color: isDarkMode ? Colors.white.withOpacity(0.8) : Colors.black54,
                    fontSize: 11,
                    fontWeight: FontWeight.w400,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildLoadingState(bool isDarkMode) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          CircularProgressIndicator(
            color: Color(0xFFD4AF37),
          ),
          SizedBox(height: 24),
          Text(
            "잠시만 기다려주세요...",
            style: TextStyle(
              color: isDarkMode ? Colors.white70 : Colors.black54,
              fontSize: 16,
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildPurchasedState(bool isDarkMode) {
    return SingleChildScrollView(
      padding: EdgeInsets.all(20),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(height: 30),
          Container(
            padding: EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Color(0xFFD4AF37).withOpacity(0.15),
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.workspace_premium,
              color: Color(0xFFD4AF37),
              size: 60,
            ),
          ),
          SizedBox(height: 30),
          Text(
            "프리미엄 사용자",
            style: TextStyle(
              color: Color(0xFFD4AF37),
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
          SizedBox(height: 16),
          Container(
            padding: EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.white.withOpacity(0.9),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 10,
                  offset: Offset(0, 5),
                ),
              ],
            ),
            child: Column(
              children: [
                Text(
                  "광고가 제거되었습니다!",
                  style: TextStyle(
                    color: isDarkMode ? Colors.white : Colors.black87,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 12),
                Text(
                  "앱의 모든 기능을 광고 없이 이용하실 수 있습니다. 구매해주셔서 감사합니다! 🙏",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: isDarkMode ? Colors.white70 : Colors.black54,
                    fontSize: 15,
                    height: 1.4,
                  ),
                ),
                SizedBox(height: 8),
                Text(
                  "혹시 광고가 계속 표시된다면 앱을 재시작해주세요.",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: isDarkMode ? Colors.white70 : Colors.black45,
                    fontSize: 13,
                    fontStyle: FontStyle.italic,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildPurchaseOptions(bool isDarkMode) {
    // 상품 가격 가져오기
    String price = "₩8,800";
    if (_products.isNotEmpty) {
      // firstWhere 대신 for 루프 사용
      for (var product in _products) {
        if (product.id == _adRemovalProductId) {
          price = product.price;
          break;
        }
      }
    }
    
    return SingleChildScrollView(
      padding: EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: EdgeInsets.all(20),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  Color(0xFFD4AF37),
                  Color(0xFFDAA520),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Color(0xFFD4AF37).withOpacity(0.3),
                  blurRadius: 12,
                  offset: Offset(0, 6),
                ),
              ],
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    Container(
                      padding: EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        Icons.workspace_premium,
                        color: Colors.white,
                        size: 24,
                      ),
                    ),
                    SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "프리미엄 업그레이드",
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        Text(
                          "광고 없이 사용하기",
                          style: TextStyle(
                            color: Colors.white.withOpacity(0.8),
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                SizedBox(height: 16),
                Text(
                  "단 한 번의 결제로 모든 광고를 제거하고 앱을 더 쾌적하게 이용하세요!",
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
          SizedBox(height: 24),
          Container(
            padding: EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.white.withOpacity(0.9),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 10,
                  offset: Offset(0, 5),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  "프리미엄 혜택",
                  style: TextStyle(
                    color: isDarkMode ? Colors.white : Colors.black87,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(height: 16),
                _buildFeatureItem(
                  icon: Icons.block,
                  title: "모든 광고 제거",
                  description: "앱 내의 모든 광고가 제거됩니다",
                  isDarkMode: isDarkMode,
                ),
                SizedBox(height: 12),
                _buildFeatureItem(
                  icon: Icons.electric_bolt,
                  title: "더 빠른 실행",
                  description: "광고 로딩 없이 더 빠르게 실행됩니다",
                  isDarkMode: isDarkMode,
                ),
                SizedBox(height: 12),
                _buildFeatureItem(
                  icon: Icons.sync,
                  title: "영구적인 혜택",
                  description: "한 번 구매로 평생 이용 가능합니다",
                  isDarkMode: isDarkMode,
                ),
                SizedBox(height: 24),
                ElevatedButton(
                  onPressed: _purchaseAdRemoval,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Color(0xFFD4AF37),
                    foregroundColor: Colors.white,
                    padding: EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(12),
                    ),
                    elevation: 5,
                    shadowColor: Color(0xFFD4AF37).withOpacity(0.5),
                  ),
                  child: Text(
                    "광고 제거 구매하기 ($price)",
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                SizedBox(height: 16),
                Center(
                  child: TextButton.icon(
                    onPressed: _restorePurchases,
                    icon: Icon(
                      Icons.restore,
                      size: 16,
                      color: isDarkMode ? Colors.white70 : Colors.black54,
                    ),
                    label: Text(
                      "이전 구매 복원하기",
                      style: TextStyle(
                        color: isDarkMode ? Colors.white70 : Colors.black54,
                        fontSize: 14,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildFeatureItem({
    required IconData icon,
    required String title,
    required String description,
    required bool isDarkMode,
  }) {
    return Row(
      children: [
        Container(
          padding: EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Color(0xFFD4AF37).withOpacity(0.1),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Icon(
            icon,
            color: Color(0xFFD4AF37),
            size: 20,
          ),
        ),
        SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  color: isDarkMode ? Colors.white : Colors.black87,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              SizedBox(height: 2),
              Text(
                description,
                style: TextStyle(
                  color: isDarkMode ? Colors.white70 : Colors.black54,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}