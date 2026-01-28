import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'home.dart';
import 'widgets/common/index.dart';

class SettingPage extends StatefulWidget {
  final Function(ThemeMode) onThemeChanged;

  SettingPage({required this.onThemeChanged});

  @override
  _SettingPageState createState() => _SettingPageState();
}

class _SettingPageState extends State<SettingPage> {
  @override
  Widget build(BuildContext context) {
    final isDarkMode = Theme.of(context).brightness == Brightness.dark;
    
    return Scaffold(
      body: ThemedBackgroundWidget(
        isDarkMode: isDarkMode,
        child: SafeArea(
          child: Column(
            children: [
              CommonHeaderWidget(
                title: '설정',
                subtitle: '앱 설정을 관리하세요',
                  // ▼▼▼▼▼ 이 줄을 추가해 주세요! ▼▼▼▼▼
                  onHomePressed: () => Navigator.pushAndRemoveUntil(
                    context,
                    MaterialPageRoute(builder: (_) => HomePage()),
                    (route) => false,
                  ),
                ),              Expanded(
                child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: ListView(
          children: [
            // 테마 설정 UI 주석 처리
            /*
            ListTile(
              title: Text('테마 설정', style: TextStyle(fontSize: 18)),
              subtitle: Text('라이트/다크 모드 선택', style: TextStyle(fontSize: 14)),
            ),
            RadioListTile<ThemeMode>(
              title: Text('라이트 모드'),
              value: ThemeMode.light,
              groupValue: _selectedThemeMode,
              onChanged: (value) {
                if (value != null) _saveThemeMode(value);
              },
            ),
            RadioListTile<ThemeMode>(
              title: Text('다크 모드'),
              value: ThemeMode.dark,
              groupValue: _selectedThemeMode,
              onChanged: (value) {
                if (value != null) _saveThemeMode(value);
              },
            ),
            Divider(),
            */
ListTile(
  title: Text('데이터 초기화', style: TextStyle(fontSize: 18)),
  subtitle: Text('문제 풀이 기록 및 설정 초기화\n(통계 데이터는 유지됩니다)', style: TextStyle(fontSize: 14)),
  trailing: ElevatedButton(
    onPressed: () async {
      bool? confirm = await showDialog(
        context: context,
        builder: (ctx) => AlertDialog(
          title: Text('데이터 초기화'),
          content: Text('문제 풀이 기록과 북마크를 초기화하시겠습니까?\n\n✅ 유지되는 것:\n- 통계 및 학습 기록\n- 광고 제거 상태\n- 후원 상태\n\n❌ 삭제되는 것:\n- 문제별 정오답 기록\n- 북마크 목록\n- 기타 설정'),
          actions: [
            TextButton(
              child: Text('취소'),
              onPressed: () => Navigator.pop(ctx, false),
            ),
            TextButton(
              child: Text('확인'),
              onPressed: () => Navigator.pop(ctx, true),
            ),
          ],
        ),
      );
      if (confirm == true) {
        await _resetData();
      }
    },
    child: Text('초기화'),
    style: ElevatedButton.styleFrom(
      backgroundColor: Colors.red,
      foregroundColor: Colors.white,
    ),
  ),
),
            Divider(),
            ListTile(
              title: Text('통계 데이터 초기화', style: TextStyle(fontSize: 18)),
              subtitle: Text('통계 및 학습 기록만 초기화', style: TextStyle(fontSize: 14, color: Colors.red)),
              trailing: ElevatedButton(
                onPressed: () async {
                  bool? confirm = await showDialog(
                    context: context,
                    builder: (ctx) => AlertDialog(
                      title: Text('통계 데이터 초기화'),
                      content: Text('통계 및 학습 기록을 초기화하시겠습니까?\n\n❌ 삭제되는 것:\n- 앱 접속 기록\n- 학습 세션 기록\n- 연속 공부일 기록\n- 통계 차트 데이터\n\n이 작업은 되돌릴 수 없습니다!'),
                      actions: [
                        TextButton(
                          child: Text('취소'),
                          onPressed: () => Navigator.pop(ctx, false),
                        ),
                        TextButton(
                          child: Text('확인', style: TextStyle(color: Colors.red)),
                          onPressed: () => Navigator.pop(ctx, true),
                        ),
                      ],
                    ),
                  );
                  if (confirm == true) {
                    await _resetStatisticsData();
                  }
                },
                child: Text('통계 초기화'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.orange,
                  foregroundColor: Colors.white,
                ),
              ),
            ),
            Divider(),
            ListTile(
              title: Text('Contact', style: TextStyle(fontSize: 18)),
              subtitle: Text('E-mail: jongmin@kanomsoft.com', style: TextStyle(fontSize: 14)),
            ),
          ],
        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _resetData() async {
    final prefs = await SharedPreferences.getInstance();
    
    // 보존할 데이터들 백업
    Map<String, dynamic> backupData = {};
    
    // 1. 결제 관련 데이터 백업
    backupData['ad_removed'] = prefs.getBool('ad_removed') ?? false;
    backupData['support_developer_purchased'] = prefs.getBool('support_developer_purchased') ?? false;
    
    // 2. 통계 관련 데이터 백업
    backupData['access_log'] = prefs.getStringList('access_log') ?? [];
    backupData['learning_sessions'] = prefs.getStringList('learning_sessions') ?? [];
    backupData['motivational_quote'] = prefs.getString('motivational_quote');
    backupData['last_quote_update'] = prefs.getInt('last_quote_update');
    
    // 3. 앱 추적 허용 관련 데이터 백업
    backupData['has_requested_tracking'] = prefs.getBool('has_requested_tracking') ?? false;
    
    // 4. 기타 중요한 설정값들 백업 (필요에 따라 추가)
    // backupData['some_other_setting'] = prefs.get('some_other_setting');
    
    // 모든 데이터 초기화
    await prefs.clear();
    
    // 백업한 데이터 복원
    for (String key in backupData.keys) {
      var value = backupData[key];
      if (value != null) {
        if (value is bool) {
          await prefs.setBool(key, value);
        } else if (value is int) {
          await prefs.setInt(key, value);
        } else if (value is double) {
          await prefs.setDouble(key, value);
        } else if (value is String) {
          await prefs.setString(key, value);
        } else if (value is List<String>) {
          await prefs.setStringList(key, value);
        }
      }
    }
    
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('문제 풀이 기록이 초기화되었습니다.\n통계 데이터와 결제 정보는 유지됩니다.'),
        duration: Duration(seconds: 3),
        backgroundColor: Colors.green,
      ),
    );
  }

  Future<void> _resetStatisticsData() async {
    final prefs = await SharedPreferences.getInstance();
    
    // 통계 관련 키들만 삭제
    List<String> statisticsKeys = [
      'access_log',
      'learning_sessions',
      'motivational_quote',
      'last_quote_update',
    ];
    
    for (String key in statisticsKeys) {
      await prefs.remove(key);
    }
    
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('통계 데이터가 초기화되었습니다.\n문제 풀이 기록과 결제 정보는 유지됩니다.'),
        duration: Duration(seconds: 3),
        backgroundColor: Colors.orange,
      ),
    );
  }
}