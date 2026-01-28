// ad_state.dart
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

class AdState with ChangeNotifier {
  bool _adsRemoved = false;

  AdState() {
    _initializeAdState(); // 초기화 메서드 호출
  }

  bool get adsRemoved => _adsRemoved;

  set adsRemoved(bool value) {
    _adsRemoved = value;
    _saveToPrefs(value); // 변경 시 SharedPreferences에 저장
    notifyListeners();
  }

  // 초기화 메서드 (비동기)
  Future<void> _initializeAdState() async {
    const bool kDisableAdsForTesting = bool.fromEnvironment(
      'DISABLE_ADS',
      defaultValue: false,
    );

    // 테스트 모드에서는 kDisableAdsForTesting 우선 적용
    if (kDisableAdsForTesting) {
      _adsRemoved = true;
    } else {
      // 일반 모드에서는 SharedPreferences에서 값 로드
      final prefs = await SharedPreferences.getInstance();
      _adsRemoved = prefs.getBool('ad_removed') ?? false;
    }

    print('AdState initialized with adsRemoved: $_adsRemoved');
    notifyListeners(); // 초기화 후 UI 업데이트
  }

  // SharedPreferences에 저장
  Future<void> _saveToPrefs(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('ad_removed', value);
  }

  // 초기화 완료 여부를 확인하기 위한 Future (선택적)
  Future<bool> get isInitialized => _initializeAdState().then((_) => true);
}