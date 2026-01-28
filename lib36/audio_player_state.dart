// lib/audio_player_state.dart
import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:audioplayers/audioplayers.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:developer' as developer;
import 'audio_term.dart';

enum RepeatMode { off, one, all }

class AudioPlayerState with ChangeNotifier {
  final AudioPlayer _audioPlayer = AudioPlayer();
  List<AudioTerm> _allAudioTerms = [];
  List<AudioTerm> _currentPlaylist = [];
  Set<String> _favoriteTermNames = {}; // SharedPreferences에서 로드된 실제 즐겨찾기 용어 이름 목록

  AudioTerm? _currentlyPlayingTerm;
  PlayerState _playerState = PlayerState.stopped;
  Duration _currentPosition = Duration.zero;
  Duration _totalDuration = Duration.zero;
  double _playbackSpeed = 1.0;
  RepeatMode _repeatMode = RepeatMode.off;
  bool _isLoadingManifest = false;
  bool _filterFavoritesOnly = false;
  String _currentCategoryFilter = "전체";
  String _searchTerm = "";
  int _currentIndexInPlaylist = -1;
  
  // 자동 재생 확인을 위한 타이머 추가
  Timer? _positionCheckTimer;
  bool _isAutoPlayEnabled = true; // 자동 재생 기본 활성화

  // Getters
  List<AudioTerm> get currentPlaylist => _currentPlaylist;
  AudioTerm? get currentlyPlayingTerm => _currentlyPlayingTerm;
  PlayerState get playerState => _playerState;
  Duration get currentPosition => _currentPosition;
  Duration get totalDuration => _totalDuration;
  double get playbackSpeed => _playbackSpeed;
  RepeatMode get repeatMode => _repeatMode;
  bool get isLoadingManifest => _isLoadingManifest;
  bool get filterFavoritesOnly => _filterFavoritesOnly;
  String get currentCategoryFilter => _currentCategoryFilter;
  int get currentIndexInPlaylist => _currentIndexInPlaylist;
  bool get isAutoPlayEnabled => _isAutoPlayEnabled;

  AudioPlayerState() {
    _initAudioPlayerListeners();
    loadManifestAndTerms();
    _loadFavoriteTermNames(); // 즐겨찾기 이름 미리 로드
    _startPositionCheckTimer(); // 재생 위치 체크 타이머 시작
  }

  void _initAudioPlayerListeners() {
    _audioPlayer.onPlayerStateChanged.listen((state) {
      developer.log('Player state changed: $state');
      _playerState = state;
      notifyListeners();
    });

    _audioPlayer.onDurationChanged.listen((duration) {
      developer.log('Duration changed: $duration');
      _totalDuration = duration;
      notifyListeners();
    });

    _audioPlayer.onPositionChanged.listen((position) {
      _currentPosition = position;
      notifyListeners();
    });
    
    // 플레이어 완료 리스너
    _audioPlayer.onPlayerComplete.listen((event) {
      developer.log('onPlayerComplete event received - auto playing next');
      _handlePlaybackCompletion();
    });
  }
  
  // 재생 위치를 주기적으로 체크하는 타이머 시작
  void _startPositionCheckTimer() {
    _positionCheckTimer?.cancel();
    _positionCheckTimer = Timer.periodic(Duration(milliseconds: 500), (timer) {
      if (_playerState == PlayerState.playing && 
          _currentPosition.inMilliseconds > 0 && 
          _totalDuration.inMilliseconds > 0 &&
          _currentPosition.inMilliseconds >= _totalDuration.inMilliseconds - 200) {
        
        developer.log('Position check detected end of audio - auto playing next');
        _handlePlaybackCompletion();
      }
    });
  }

  Future<void> _loadFavoriteTermNames() async {
    final prefs = await SharedPreferences.getInstance();
    _favoriteTermNames = (prefs.getStringList('dictionary_favorites') ?? []).toSet();
    if (_filterFavoritesOnly) {
      applyFilters();
    }
    notifyListeners();
  }

  Future<void> loadManifestAndTerms() async {
    _isLoadingManifest = true;
    notifyListeners();
    try {
      final String response = await rootBundle.loadString('assets/audio_output/audio_dictionary_manifest.json');
      final List<dynamic> data = json.decode(response);
      _allAudioTerms = data.map((jsonItem) => AudioTerm.fromJson(jsonItem)).toList();
      developer.log('Loaded manifest with ${_allAudioTerms.length} terms');
      applyFilters();
    } catch (e) {
      developer.log("Error loading manifest: $e", error: e);
      _allAudioTerms = [];
      _currentPlaylist = [];
    }
    _isLoadingManifest = false;
    notifyListeners();
  }

  void applyFilters({String? category, String? searchTerm, bool? filterFavorites}) {
    if (category != null) _currentCategoryFilter = category;
    if (searchTerm != null) _searchTerm = searchTerm.toLowerCase();
    if (filterFavorites != null) _filterFavoritesOnly = filterFavorites;

    _currentPlaylist = _allAudioTerms.where((term) {
      final matchesCategory = _currentCategoryFilter == "전체" || term.category == _currentCategoryFilter;
      final matchesSearch = _searchTerm.isEmpty || term.term.toLowerCase().contains(_searchTerm);
      final matchesFavorites = !_filterFavoritesOnly || _favoriteTermNames.contains(term.term);
      return matchesCategory && matchesSearch && matchesFavorites;
    }).toList();

    if (_currentlyPlayingTerm != null && !_currentPlaylist.contains(_currentlyPlayingTerm)) {
      stop();
    } else if (_currentlyPlayingTerm != null) {
      _currentIndexInPlaylist = _currentPlaylist.indexOf(_currentlyPlayingTerm!);
    } else {
      _currentIndexInPlaylist = -1;
    }

    notifyListeners();
  }

  Future<void> play(AudioTerm term) async {
    try {
      // 현재 재생 중인 항목과 동일한 경우 - 중복 재생 방지
      if (_playerState == PlayerState.playing && _currentlyPlayingTerm?.rowid == term.rowid) {
        developer.log("Already playing this term: ${term.term}");
        return;
      }
      
      String assetPath = 'audio_output/dictionary_audio/${term.filename}';
      
      developer.log("재생 시도: ${term.term}, 파일명: ${term.filename}, 경로: $assetPath");
      
      if (assetPath.startsWith('assets/')) {
        assetPath = assetPath.replaceFirst('assets/', '');
        developer.log("경로 수정됨: $assetPath");
      }
      
      // 기존 재생 중인 항목 정지
      if (_playerState == PlayerState.playing || _playerState == PlayerState.paused) {
        await _audioPlayer.stop();
      }
      
      // 정보 업데이트 (먼저 업데이트하여 UI가 빠르게 반응하도록)
      _currentlyPlayingTerm = term;
      _currentIndexInPlaylist = _currentPlaylist.indexOf(term);
      _playerState = PlayerState.playing;
      _currentPosition = Duration.zero;
      notifyListeners();
      
      // 재생 속도 설정 (play 전에 설정)
      await _audioPlayer.setPlaybackRate(_playbackSpeed);
      
      // 오디오 재생
      await _audioPlayer.play(AssetSource(assetPath));
      developer.log("재생 명령 전송 완료");
    } catch (e) {
      developer.log("오디오 재생 오류: $e", error: e, stackTrace: StackTrace.current);
      _playerState = PlayerState.stopped;
      notifyListeners();
    }
  }

  Future<void> pause() async {
    try {
      await _audioPlayer.pause();
      _playerState = PlayerState.paused;
      developer.log("오디오 일시 정지됨");
    } catch (e) {
      developer.log("오디오 일시 정지 오류: $e", error: e);
    }
    notifyListeners();
  }

  Future<void> resume() async {
    try {
      await _audioPlayer.resume();
      _playerState = PlayerState.playing;
      developer.log("오디오 재개됨");
    } catch (e) {
      developer.log("오디오 재개 오류: $e", error: e);
    }
    notifyListeners();
  }

  Future<void> stop() async {
    try {
      await _audioPlayer.stop();
      _playerState = PlayerState.stopped;
      _currentlyPlayingTerm = null;
      _currentPosition = Duration.zero;
      _totalDuration = Duration.zero;
      _currentIndexInPlaylist = -1;
      developer.log("오디오 정지됨");
    } catch (e) {
      developer.log("오디오 정지 오류: $e", error: e);
    }
    notifyListeners();
  }

  Future<void> seek(Duration position) async {
    try {
      await _audioPlayer.seek(position);
      _currentPosition = position;
      developer.log("오디오 탐색: $position");
    } catch (e) {
      developer.log("오디오 탐색 오류: $e", error: e);
    }
    notifyListeners();
  }

  Future<void> setPlaybackSpeed(double speed) async {
    try {
      _playbackSpeed = speed;
      await _audioPlayer.setPlaybackRate(speed);
      developer.log("재생 속도 변경: $speed");
    } catch (e) {
      developer.log("재생 속도 변경 오류: $e", error: e);
    }
    notifyListeners();
  }

  void setRepeatMode(RepeatMode mode) {
    _repeatMode = mode;
    developer.log("반복 모드 설정: $mode");
    
    switch (mode) {
      case RepeatMode.off:
        _audioPlayer.setReleaseMode(ReleaseMode.release);
        break;
      case RepeatMode.one:
        _audioPlayer.setReleaseMode(ReleaseMode.loop);
        break;
      case RepeatMode.all:
        _audioPlayer.setReleaseMode(ReleaseMode.release);
        break;
    }
    
    notifyListeners();
  }
  
  void toggleAutoPlay() {
    _isAutoPlayEnabled = !_isAutoPlayEnabled;
    developer.log("자동 재생 모드 변경: $_isAutoPlayEnabled");
    notifyListeners();
  }

  void _handlePlaybackCompletion() {
    // 이미 완료 처리 중인지 확인 (중복 호출 방지)
    if (_playerState == PlayerState.stopped) {
      developer.log("이미 재생 완료 처리됨, 중복 처리 방지");
      return;
    }
    
    developer.log("재생 완료 처리 시작");
    
    // 재생이 완료되면 상태 업데이트
    _playerState = PlayerState.stopped;
    _currentPosition = Duration.zero;
    
    // 자동 재생이 비활성화되어 있으면 처리하지 않음
    if (!_isAutoPlayEnabled) {
      developer.log("자동 재생이 비활성화되어 있음, 다음 곡 재생 안함");
      notifyListeners();
      return;
    }
    
    if (_repeatMode == RepeatMode.one && _currentlyPlayingTerm != null) {
      // 한 곡 반복 모드인 경우만 처리
      developer.log("반복 모드 ONE - 같은 용어 재생");
      
      // 지연 추가 (UI가 업데이트되고 오디오 플레이어가 리셋될 시간을 주기 위해)
      Future.delayed(Duration(milliseconds: 500), () {
        if (_currentlyPlayingTerm != null) {
          play(_currentlyPlayingTerm!);
        }
      });
    } else if (_currentIndexInPlaylist < _currentPlaylist.length - 1) {
      // 다음 용어 자동 재생
      developer.log("다음 용어 자동 재생");
      
      // 지연 추가
      Future.delayed(Duration(milliseconds: 500), () {
        _currentIndexInPlaylist++;
        play(_currentPlaylist[_currentIndexInPlaylist]);
      });
    } else if (_repeatMode == RepeatMode.all && _currentPlaylist.isNotEmpty) {
      // 전체 반복 모드일 때 처음으로 돌아가서 재생
      developer.log("반복 모드 ALL - 처음 용어로 돌아가서 재생");
      
      // 지연 추가
      Future.delayed(Duration(milliseconds: 500), () {
        _currentIndexInPlaylist = 0;
        play(_currentPlaylist[_currentIndexInPlaylist]);
      });
    } else {
      // 마지막 용어이고 반복 모드가 아니면 정지
      developer.log("마지막 용어 재생 완료 - 정지");
      notifyListeners();
    }
  }

  void playNext() {
    if (_currentPlaylist.isEmpty) return;

    if (_currentIndexInPlaylist < _currentPlaylist.length - 1) {
      _currentIndexInPlaylist++;
      play(_currentPlaylist[_currentIndexInPlaylist]);
      developer.log("다음 곡 재생: ${_currentPlaylist[_currentIndexInPlaylist].term}");
    } else if (_repeatMode == RepeatMode.all && _currentPlaylist.isNotEmpty) {
      _currentIndexInPlaylist = 0;
      play(_currentPlaylist[_currentIndexInPlaylist]);
      developer.log("전체 반복 - 처음으로 돌아가서 재생: ${_currentPlaylist[_currentIndexInPlaylist].term}");
    } else {
      stop();
      developer.log("마지막 곡이므로 정지");
    }
  }

  void playPrevious() {
    if (_currentPlaylist.isEmpty || _currentIndexInPlaylist <= 0) return;
    _currentIndexInPlaylist--;
    play(_currentPlaylist[_currentIndexInPlaylist]);
    developer.log("이전 곡 재생: ${_currentPlaylist[_currentIndexInPlaylist].term}");
  }

  void toggleFavoriteFilter() async {
    _filterFavoritesOnly = !_filterFavoritesOnly;
    await _loadFavoriteTermNames();
    applyFilters();
  }
  
  void updateSearchTerm(String term) {
    _searchTerm = term.toLowerCase();
    applyFilters();
  }

  void updateCategoryFilter(String category) {
    _currentCategoryFilter = category;
    applyFilters();
  }

  @override
  void dispose() {
    _positionCheckTimer?.cancel();
    _audioPlayer.dispose();
    developer.log("AudioPlayerState 및 AudioPlayer 해제됨");
    super.dispose();
  }
}