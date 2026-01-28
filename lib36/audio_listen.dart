import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:path/path.dart' as path;
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'database_helper.dart';
import 'constants.dart';
import 'dart:developer' as developer;
import 'dart:async'; // Timer 사용을 위해 추가
import 'home.dart';
import 'ad_helper.dart';
import 'ad_config.dart'; // 광고 제거 상태 관리 파일 추가
import 'dart:typed_data'; // Uint8List 처리를 위해 추가
import 'package:flutter_html/flutter_html.dart';

class AudioListenPage extends StatefulWidget {
  final String? round;
  final String? category;

  const AudioListenPage({Key? key, this.round, this.category})
      : super(key: key);

  @override
  _AudioListenPageState createState() => _AudioListenPageState();
}

class _AudioListenPageState extends State<AudioListenPage>
    with WidgetsBindingObserver {
  late AudioPlayer _audioPlayer;
  List<Map<String, dynamic>> _questions = [];
  int _currentIndex = 0;
  bool _isPlaying = false;
  bool _loop = false;
  Duration _duration = Duration.zero;
  Duration _position = Duration.zero;
  late DatabaseHelper _dbHelper;
  double _playbackRate = 1.0;
  final List<double> _playbackRates = [0.8, 1.0, 1.2, 1.5, 2.0];

  // 광고 관련 변수
  InterstitialAd? _interstitialAd;
  int _questionCount = 0;
  static const int _adInterval = 6;
  bool _wasPlayingBeforeNavigation = false;

  // 테스트 모드 관련 변수 추가
  bool _isTestMode = false;
  Timer? _testModeTimer;
  static const Duration _testModeDuration = Duration(seconds: 10);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    // 테스트 모드 감지
    _isTestMode =
        const bool.fromEnvironment('DISABLE_ADS', defaultValue: false);
    developer.log('Test mode enabled: $_isTestMode');

    _audioPlayer = AudioPlayer();
    String dbPath = widget.round != null
        ? 'assets/question${widget.round}.db'
        : widget.category != null
            ? 'assets/question1.db'
            : 'assets/question1.db';
    if (widget.category != null) {
      developer.log(
          'Warning: Category-based DB not fully supported yet. Using default: $dbPath');
    }
    _dbHelper = DatabaseHelper.getInstance(dbPath);
    _loadQuestions();
    _setupAudioPlayer();
    if (!adsRemovedGlobal) {
      _loadInterstitialAd(); // 광고 제거가 안 된 경우에만 광고 로드
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);

    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
      // 앱이 백그라운드로 가거나 비활성화될 때
      if (_isPlaying) {
        _wasPlayingBeforeNavigation = true;
        _audioPlayer.pause();
        _cancelTestModeTimer(); // 테스트 모드 타이머 취소
      }
    } else if (state == AppLifecycleState.resumed) {
      // 앱이 포그라운드로 돌아올 때
      if (_wasPlayingBeforeNavigation) {
        _wasPlayingBeforeNavigation = false;
        // 자동 재생을 원하면 아래 줄 주석 해제
        // _audioPlayer.play();
      }
    }
  }

  // 페이지 이동 감지를 위한 메서드 추가
  @override
  void deactivate() {
    // 페이지가 네비게이션 스택에서 빠질 때
    if (_isPlaying) {
      _audioPlayer.pause();
      _wasPlayingBeforeNavigation = true;
    }
    _cancelTestModeTimer(); // 테스트 모드 타이머 취소
    super.deactivate();
  }

  // 테스트 모드 타이머 시작
  void _startTestModeTimer() {
    if (!_isTestMode) return;

    _cancelTestModeTimer(); // 기존 타이머가 있다면 취소

    developer.log(
        'Starting test mode timer: ${_testModeDuration.inSeconds} seconds');
    _testModeTimer = Timer(_testModeDuration, () {
      developer.log('Test mode timer expired - stopping audio');
      if (mounted && _isPlaying) {
        _stopAudio();
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(''),
            duration: Duration(seconds: 2),
          ),
        );
      }
    });
  }

  // 테스트 모드 타이머 취소
  void _cancelTestModeTimer() {
    if (_testModeTimer != null) {
      developer.log('Cancelling test mode timer');
      _testModeTimer!.cancel();
      _testModeTimer = null;
    }
  }

  // audio_listen.dart의 _loadQuestions 함수
Future<void> _loadQuestions() async {
  try {
    if (widget.round != null) {
      int examSession = int.parse(widget.round!);
      _questions = await _dbHelper.getQuestions(examSession);
      developer.log('Loaded ${widget.round} questions: ${_questions.length}');
    } else if (widget.category != null) {
      _questions = await _dbHelper.getQuestionsByCategory(widget.category!);
      developer.log('Loaded ${widget.category} questions: ${_questions.length}');
    }

    // ================================================================
    // ===== 근본 원인 파악을 위한 디버깅 로그 추가 =====
    if (_questions.isNotEmpty) {
      developer.log('--- Platform Specific Data Debug Start ---');
      // 첫 번째 질문 전체 데이터를 출력하여 구조를 확인합니다.
      developer.log('First question data structure: ${_questions.first}');
      
      // 첫 번째 질문의 'audio' 필드 값과 타입을 직접 확인합니다.
      var firstAudioValue = _questions.first['audio'];
      developer.log('Value of "audio" field: $firstAudioValue');
      developer.log('Type of "audio" field: ${firstAudioValue.runtimeType}');
      developer.log('--- Platform Specific Data Debug End ---');
    }
    // ================================================================

    if (!mounted) return;

    setState(() {
      // _questions = _questions; // 이 줄은 불필요하므로 제거해도 됩니다.
    });

    if (_questions.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('해당 조건에 맞는 질문이 없습니다.')),
      );
    }
  } catch (e) {
    developer.log('Error loading questions: $e', level: 1000);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('질문을 불러오는 중 오류 발생: $e')),
    );
  }
}
  void _setupAudioPlayer() {
    _audioPlayer.onPlayerStateChanged.listen((state) {
      if (mounted) {
        setState(() {
          _isPlaying = state == PlayerState.playing;
        });
      }
    });

    _audioPlayer.onDurationChanged.listen((d) {
      if (mounted) {
        setState(() {
          _duration = d;
        });
      }
    });

    _audioPlayer.onPositionChanged.listen((p) {
      if (mounted) {
        setState(() {
          _position = p;
        });
      }
    });

    _audioPlayer.onPlayerComplete.listen((event) {
      if (mounted) {
        _cancelTestModeTimer(); // 오디오 완료 시 타이머 취소
        _questionCount++;
        developer.log('Question completed. Count: $_questionCount');

        if (!adsRemovedGlobal &&
            _questionCount % _adInterval == 0 &&
            _currentIndex < _questions.length - 1) {
          // 광고 제거가 안 된 경우에만 8문제마다 광고 표시
          _showInterstitialAd();
        } else if (_loop) {
          _playAudio(_currentIndex);
        } else if (_currentIndex < _questions.length - 1) {
          setState(() {
            _currentIndex++;
          });
          _playAudio(_currentIndex);
        } else {
          setState(() {
            _isPlaying = false;
          });
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('모든 음성 재생 완료')),
          );
        }
      }
    });
  }

  Future<void> _playAudio(int index) async {
    if (index >= 0 && index < _questions.length) {
      String audioPath = _questions[index]['audio'];
      try {
        if (audioPath.startsWith('assets/')) {
          audioPath = audioPath.replaceFirst('assets/', '');
        }
        developer.log(
            'Playing audio: $audioPath with playback rate: $_playbackRate');
        await _audioPlayer.setPlaybackRate(_playbackRate);
        await _audioPlayer.play(AssetSource(audioPath));

        if (mounted) {
          setState(() {
            _currentIndex = index;
            _isPlaying = true;
          });

          // 테스트 모드일 때 10초 타이머 시작
          if (_isTestMode) {
            _startTestModeTimer();
          }
        }
      } catch (e) {
        developer.log('Error playing audio: $e', level: 1000);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('음성 재생 오류: $e')),
          );
        }
      }
    }
  }

  Future<void> _pauseAudio() async {
    _cancelTestModeTimer(); // 일시정지 시 타이머 취소
    await _audioPlayer.pause();
    if (mounted) {
      setState(() {
        _isPlaying = false;
      });
    }
  }

  Future<void> _stopAudio() async {
    _cancelTestModeTimer(); // 정지 시 타이머 취소
    await _audioPlayer.stop();
    if (mounted) {
      setState(() {
        _isPlaying = false;
        _position = Duration.zero;
      });
    }
  }

  Future<void> _changePlaybackRate(double rate) async {
    setState(() {
      _playbackRate = rate;
    });
    await _audioPlayer.setPlaybackRate(rate);
    developer.log('Playback rate changed to: $rate');
  }

  // 광고 로드 함수
  void _loadInterstitialAd() {
    if (adsRemovedGlobal) return; // 광고 제거 상태면 로드하지 않음

    InterstitialAd.load(
      adUnitId: AdHelper.interstitialAdUnitId,
      request: const AdRequest(),
      adLoadCallback: InterstitialAdLoadCallback(
        onAdLoaded: (ad) {
          developer.log('InterstitialAd loaded');
          _interstitialAd = ad;
          _interstitialAd!.fullScreenContentCallback =
              FullScreenContentCallback(
            onAdDismissedFullScreenContent: (ad) {
              ad.dispose();
              _loadInterstitialAd(); // 광고 닫히면 새 광고 로드
              if (_currentIndex < _questions.length - 1) {
                setState(() {
                  _currentIndex++;
                });
                _playAudio(_currentIndex);
              }
            },
            onAdFailedToShowFullScreenContent: (ad, error) {
              developer.log('Failed to show ad: $error');
              ad.dispose();
              _loadInterstitialAd();
              if (_currentIndex < _questions.length - 1) {
                setState(() {
                  _currentIndex++;
                });
                _playAudio(_currentIndex);
              }
            },
          );
        },
        onAdFailedToLoad: (error) {
          developer.log('InterstitialAd failed to load: $error');
          _interstitialAd = null;
          _loadInterstitialAd(); // 실패 시 재시도
        },
      ),
    );
  }

  // 광고 표시 함수
  void _showInterstitialAd() {
    if (adsRemovedGlobal) {
      // 광고 제거 상태면 광고 표시 없이 다음 문제로 진행
      if (_currentIndex < _questions.length - 1) {
        setState(() {
          _currentIndex++;
        });
        _playAudio(_currentIndex);
      }
      return;
    }

    if (_interstitialAd != null) {
      _interstitialAd!.show();
      _interstitialAd = null;
    } else {
      developer.log('Ad not ready yet, loading new one');
      _loadInterstitialAd();
      if (_currentIndex < _questions.length - 1) {
        setState(() {
          _currentIndex++;
        });
        _playAudio(_currentIndex);
      }
    }
  }

  @override
  void dispose() {
    // 페이지가 제거될 때 오디오 정지 및 자원 해제
    _cancelTestModeTimer(); // 타이머 정리
    _audioPlayer.stop();
    _audioPlayer.dispose();
    // WidgetsBindingObserver 등록 해제
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  // Question을 문자열 또는 이미지로 렌더링
  Widget _buildQuestionOrImage(dynamic data) {
    if (data is String) {
      if (data.startsWith('assets/')) {
        return Image.asset(
          data,
          width: double.infinity,
          fit: BoxFit.cover,
        );
      } else {
        return Container(
          padding: const EdgeInsets.all(8.0),
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey),
            borderRadius: BorderRadius.circular(4.0),
          ),
          child: Html(
            data: data,
            style: {"body": Style(
              fontSize: FontSize(18),
              margin: Margins.zero,
              padding: HtmlPaddings.zero,
            )},
          ),
        );
      }
    } else if (data is Uint8List) {
      return Image.memory(
        data,
        width: double.infinity,
        fit: BoxFit.cover,
      );
    } else {
      return const Text(
        '[지원되지 않는 데이터 형식]',
        style: TextStyle(fontSize: 18, color: Colors.red),
      );
    }
  }

  Widget _buildBigQuestionSpecialWidget(Map<String, dynamic> question, bool isDarkMode) {
    final bigQSpecial = question['Big_Question_Special'];

    if (bigQSpecial is Uint8List && bigQSpecial.isNotEmpty) {
      return Container(
        width: double.infinity,
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: isDarkMode ? Colors.white.withOpacity(0.1) : Colors.grey.shade200),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(10.0),
          child: Image.memory(
            bigQSpecial,
            fit: BoxFit.contain,
          ),
        ),
      );
    }
    return const SizedBox.shrink();
  }

  // Option을 문자열 또는 이미지로 렌더링
  Widget _buildOptionOrImage(dynamic data, bool isCorrect) {
    if (data is String) {
      return Html(
        data: data,
        style: {"body": Style(
          fontSize: FontSize(18),
          color: isCorrect ? Colors.blue : null,
          fontWeight: isCorrect ? FontWeight.bold : null,
          margin: Margins.zero,
          padding: HtmlPaddings.zero,
        )},
      );
    } else if (data is Uint8List) {
      return Image.memory(
        data,
        fit: BoxFit.contain,
      );
    } else {
      return Text(
        '[지원되지 않는 데이터 형식]',
        style: TextStyle(
          fontSize: 18,
          color: isCorrect ? Colors.blue : Colors.red,
          fontWeight: isCorrect ? FontWeight.bold : null,
        ),
      );
    }
  }

  // build 메서드의 재생 버튼 부분을 다음과 같이 수정하세요:

  // build 메서드의 재생 버튼 부분을 다음과 같이 수정하세요:

  @override
  Widget build(BuildContext context) {
    bool isDarkMode = Theme.of(context).brightness == Brightness.dark;

    String currentCategory = widget.category ??
        (_questions.isNotEmpty
            ? _questions[_currentIndex]['Category'] ?? '알 수 없음'
            : '알 수 없음');

    String currentRound;
    if (widget.round != null) {
      currentRound = reverseRoundMapping[int.parse(widget.round!)] ?? '기타';
    } else if (_questions.isNotEmpty &&
        _questions[_currentIndex]['ExamSession'] != null) {
      final examSession = _questions[_currentIndex]['ExamSession'];
      currentRound = reverseRoundMapping[
              examSession is String ? int.parse(examSession) : examSession] ??
          '기타';
    } else {
      currentRound = '기타';
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.round != null
            ? '${reverseRoundMapping[int.parse(widget.round!)]} 듣기'
            : '${widget.category ?? '기타'} 듣기'),
        backgroundColor:
            isDarkMode ? const Color(0xFF4A5A78) : const Color(0xFF6AA8F7),
        actions: [
          IconButton(
            key: Key('home_button'),
            icon: const Icon(Icons.home, color: Colors.white), // 색상을 흰색으로 명시
            onPressed: () {
              if (_isPlaying) {
                _audioPlayer.pause();
              }
              _cancelTestModeTimer();
              Navigator.push(
                  context, MaterialPageRoute(builder: (_) => HomePage()));
            },
          ),
        ],
      ),
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: isDarkMode
                ? [const Color(0xFF2D2D41), const Color(0xFF4A5A78)]
                : [const Color(0xFFE0EAFD), const Color(0xFFC4D7F2)],
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
          ),
        ),
        child: Column(
          children: [
            // 컨트롤 패널을 Container로 감싸서 배경색 추가
            Container(
              margin: const EdgeInsets.all(12.0),
              padding: const EdgeInsets.all(12.0),
              decoration: BoxDecoration(
                color: isDarkMode
                    ? Colors.grey[800]?.withOpacity(0.9)
                    : Colors.white.withOpacity(0.9),
                borderRadius: BorderRadius.circular(8),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.1),
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  ),
                ],
              ),
              child: Column(
                children: [
                  // 메인 재생 버튼 - 크기 축소
                  ElevatedButton(
                    onPressed: _questions.isNotEmpty
                        ? () => _playAudio(_currentIndex)
                        : null,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: isDarkMode
                          ? const Color(0xFF6AA8F7)
                          : const Color(0xFF4A90E2),
                      foregroundColor: Colors.white,
                      minimumSize: const Size(double.infinity, 40),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(6),
                      ),
                      elevation: 1,
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          _isPlaying ? Icons.pause : Icons.play_arrow,
                          color: Colors.white,
                          size: 20,
                        ),
                        const SizedBox(width: 6),
                        Text(
                          _isPlaying ? 'Pause' : 'Play',
                          style: const TextStyle(
                            fontSize: 16,
                            color: Colors.white,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 12),

                  // 컨트롤 버튼들 - 크기 축소
                  Container(
                    padding:
                        const EdgeInsets.symmetric(vertical: 6, horizontal: 4),
                    decoration: BoxDecoration(
                      color: isDarkMode ? Colors.grey[700] : Colors.grey[100],
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                      children: [
                        // 이전 버튼
                        _buildControlButton(
                          icon: Icons.skip_previous,
                          onPressed: _currentIndex > 0
                              ? () => _playAudio(_currentIndex - 1)
                              : null,
                          isDarkMode: isDarkMode,
                          tooltip: '이전',
                        ),
                        // 다음 버튼
                        _buildControlButton(
                          icon: Icons.skip_next,
                          onPressed: _currentIndex < _questions.length - 1
                              ? () => _playAudio(_currentIndex + 1)
                              : null,
                          isDarkMode: isDarkMode,
                          tooltip: '다음',
                        ),
                        // 일시정지 버튼
                        _buildControlButton(
                          icon: Icons.pause,
                          onPressed: _isPlaying ? _pauseAudio : null,
                          isDarkMode: isDarkMode,
                          tooltip: '일시정지',
                        ),
                        // 정지 버튼
                        _buildControlButton(
                          icon: Icons.stop,
                          onPressed: _stopAudio,
                          isDarkMode: isDarkMode,
                          tooltip: '정지',
                        ),
                        // 반복 버튼
                        _buildControlButton(
                          icon: _loop ? Icons.repeat_one : Icons.repeat,
                          onPressed: () {
                            if (mounted) {
                              setState(() {
                                _loop = !_loop;
                                _audioPlayer.setReleaseMode(_loop
                                    ? ReleaseMode.loop
                                    : ReleaseMode.release);
                              });
                            }
                          },
                          isDarkMode: isDarkMode,
                          tooltip: '반복',
                          isActive: _loop,
                        ),
                        // 재생 속도 드롭다운
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 6, vertical: 2),
                          decoration: BoxDecoration(
                            color: isDarkMode ? Colors.grey[600] : Colors.white,
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(
                              color: isDarkMode
                                  ? Colors.grey[500]!
                                  : Colors.grey[300]!,
                            ),
                          ),
                          child: DropdownButton<double>(
                            value: _playbackRate,
                            underline: Container(),
                            icon: Icon(
                              Icons.arrow_drop_down,
                              color: isDarkMode ? Colors.white : Colors.black,
                              size: 16,
                            ),
                            dropdownColor:
                                isDarkMode ? Colors.grey[700] : Colors.white,
                            onChanged: (double? newValue) {
                              if (newValue != null) {
                                _changePlaybackRate(newValue);
                              }
                            },
                            items: _playbackRates
                                .map<DropdownMenuItem<double>>((double value) {
                              return DropdownMenuItem<double>(
                                value: value,
                                child: Text(
                                  '${value}x',
                                  style: TextStyle(
                                    color: isDarkMode
                                        ? Colors.white
                                        : Colors.black,
                                    fontWeight: FontWeight.bold,
                                    fontSize: 12,
                                  ),
                                ),
                              );
                            }).toList(),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            // 진행바 - 크기 축소
            Container(
              margin:
                  const EdgeInsets.symmetric(horizontal: 12.0, vertical: 4.0),
              padding: const EdgeInsets.all(6.0),
              decoration: BoxDecoration(
                color: isDarkMode
                    ? Colors.grey[800]?.withOpacity(0.9)
                    : Colors.white.withOpacity(0.9),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Column(
                children: [
                  Slider(
                    value: _position.inSeconds.toDouble(),
                    max: _duration.inSeconds.toDouble() > 0
                        ? _duration.inSeconds.toDouble()
                        : 1.0,
                    onChanged: (value) async {
                      await _audioPlayer.seek(Duration(seconds: value.toInt()));
                    },
                    activeColor: isDarkMode
                        ? const Color(0xFF6AA8F7)
                        : const Color(0xFF4A90E2),
                    inactiveColor:
                        isDarkMode ? Colors.grey[600] : Colors.grey[300],
                    thumbColor: isDarkMode
                        ? const Color(0xFF6AA8F7)
                        : const Color(0xFF4A90E2),
                  ),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        '${_position.inMinutes}:${(_position.inSeconds % 60).toString().padLeft(2, '0')}',
                        style: TextStyle(
                          fontSize: 12,
                          color: isDarkMode ? Colors.white : Colors.black,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Text(
                        '${_duration.inMinutes}:${(_duration.inSeconds % 60).toString().padLeft(2, '0')}',
                        style: TextStyle(
                          fontSize: 12,
                          color: isDarkMode ? Colors.white : Colors.black,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),

            // 질문 카드 부분은 기존과 동일
            Expanded(
              child: _questions.isEmpty
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const CircularProgressIndicator(),
                          const SizedBox(height: 16),
                          Text(
                            '질문을 로드하는 중...',
                            style: TextStyle(
                              color: isDarkMode ? Colors.white : Colors.black,
                              fontSize: 16,
                            ),
                          ),
                        ],
                      ),
                    )
                  : Card(
                      margin: const EdgeInsets.all(16.0),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(12)),
                      elevation: 4,
                      child: Padding(
                        padding: const EdgeInsets.all(16.0),
                        child: SingleChildScrollView(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '$currentRound - $currentCategory',
                                style: const TextStyle(fontSize: 18),
                              ),
                              const SizedBox(height: 8),
                              Text(
                                '${_questions[_currentIndex]['Question_id']}. ${_questions[_currentIndex]['Big_Question'] ?? '[질문 없음]'}',
                                style: const TextStyle(fontSize: 20),
                              ),
                              const SizedBox(height: 12),
                              _buildBigQuestionSpecialWidget(_questions[_currentIndex], isDarkMode),
                              // Question 처리 (문자열 또는 이미지)
                              if (_questions[_currentIndex]['Question'] !=
                                  null) ...[
                                _buildQuestionOrImage(
                                    _questions[_currentIndex]['Question']),
                                const SizedBox(height: 12),
                              ],
                              // Option1~4 처리 (문자열 또는 이미지)
                              ...List.generate(4, (index) {
                                final optionKey = 'Option${index + 1}';
                                final optionData = _questions[_currentIndex]
                                        [optionKey] ??
                                    '[옵션 없음]';
                                final correctOption =
                                    _questions[_currentIndex]['Correct_Option'];
                                final isCorrect = correctOption == (index + 1);
                                return Padding(
                                  padding: const EdgeInsets.only(bottom: 4.0),
                                  child: Row(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        '${['➀', '➁', '➂', '➃'][index]} ',
                                        style: TextStyle(
                                          fontSize: 18,
                                          color: isCorrect ? Colors.blue : null,
                                          fontWeight: isCorrect
                                              ? FontWeight.bold
                                              : null,
                                        ),
                                      ),
                                      Expanded(
                                        child: _buildOptionOrImage(
                                            optionData, isCorrect),
                                      ),
                                    ],
                                  ),
                                );
                              }),
                              const SizedBox(height: 12),
                              Divider(
                                  color: isDarkMode
                                      ? Colors.grey[600]
                                      : Colors.grey[300]),
                              const SizedBox(height: 8),
                              Text(
                                _questions[_currentIndex]
                                        ['Answer_description'] ??
                                    '정답 설명 없음',
                                style: const TextStyle(
                                    fontSize: 16, color: Colors.black54),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
            ),
          ],
        ),
      ),
    );
  }

// 컨트롤 버튼을 위한 헬퍼 메서드 - 크기 축소
  Widget _buildControlButton({
    required IconData icon,
    required VoidCallback? onPressed,
    required bool isDarkMode,
    required String tooltip,
    bool isActive = false,
  }) {
    return Tooltip(
      message: tooltip,
      child: Container(
        decoration: BoxDecoration(
          color: isActive
              ? (isDarkMode ? Colors.blue[600] : Colors.blue[500])
              : (onPressed == null
                  ? (isDarkMode ? Colors.grey[600] : Colors.grey[300])
                  : (isDarkMode ? Colors.grey[600] : Colors.white)),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isDarkMode ? Colors.grey[500]! : Colors.grey[300]!,
            width: 1,
          ),
        ),
        child: IconButton(
          icon: Icon(
            icon,
            size: 18,
            color: onPressed == null
                ? Colors.grey[400]
                : (isActive || isDarkMode ? Colors.white : Colors.black),
          ),
          onPressed: onPressed,
          splashRadius: 16,
          constraints: const BoxConstraints(
            minWidth: 36,
            minHeight: 36,
          ),
          padding: const EdgeInsets.all(4),
        ),
      ),
    );
  }
}
