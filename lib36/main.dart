import 'package:flutter/material.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:provider/provider.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'splash_screen.dart';
import 'home.dart';
import 'setting.dart';
import 'ad_state.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // AdMob 초기화 (AdMob만 사용)
  await MobileAds.instance.initialize();
  
  // 테스트 디바이스 설정 (개발 중에만 사용)
  MobileAds.instance.updateRequestConfiguration(
    RequestConfiguration(
      testDeviceIds: ['090C3965-9B2E-425C-9DB4-BE0474175434'],
    ),
  );
  
  await initializeDateFormatting('ko_KR', null);

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider<AdState>(create: (_) => AdState()),
      ],
      child: MyApp(),
    ),
  );
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '산업안전기사 기출문제',
      theme: ThemeData(
        brightness: Brightness.light,
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green),
        useMaterial3: true,
        scaffoldBackgroundColor: Color(0xFFf2f4f8),
      ),
      themeMode: ThemeMode.light,
      home: SplashScreen(
        onThemeChanged: (_) {},
      ),
    );
  }
}