// # 테스트 광고 코드z
// # 테스트 광고 코드



import 'dart:io';
  
class AdHelper {

  static String get bannerAdUnitId {
    if (Platform.isAndroid) {
      return 'ca-app-pub-3940256099942544/6300978111';
    } else if (Platform.isIOS) {
      return 'ca-app-pub-3940256099942544/2934735716';
    } else {
      throw new UnsupportedError('Unsupported platform');
    }
  }

  static String get interstitialAdUnitId {
    if (Platform.isAndroid) {
      return "ca-app-pub-3940256099942544/1033173712";
    } else if (Platform.isIOS) {
      return 'ca-app-pub-3940256099942544/4411468910';
    } else {
      throw new UnsupportedError("Unsupported platform");
    }
  }

  static String get rewardedAdUnitId {
    if (Platform.isAndroid) {
      return "ca-app-pub-3940256099942544/5224354917";
    } else if (Platform.isIOS) {
      return 'ca-app-pub-3940256099942544/1712485313';
    } else {
      throw new UnsupportedError("Unsupported platform");
    }
  }


  // **앱 열기 광고(AppOpenAd) ID 추가** 
  static String get appOpenAdUnitId {
    if (Platform.isAndroid) {
      return 'ca-app-pub-3940256099942544/3419835294'; // 테스트용
    } else if (Platform.isIOS) {
      return 'ca-app-pub-3940256099942544/5575463023'; // 테스트용
    } else {
      throw UnsupportedError('Unsupported platform');
    }
  }
}




