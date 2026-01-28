// lib/audio_term.dart
class AudioTerm {
  final int rowid;
  final String term;
  final String category;
  final String filename;
  final String definition; // 정의 필드 추가

  AudioTerm({
    required this.rowid,
    required this.term,
    required this.category,
    required this.filename,
    required this.definition,
  });

  factory AudioTerm.fromJson(Map<String, dynamic> json) {
    return AudioTerm(
      rowid: json['rowid'] as int,
      term: json['term'] as String,
      category: json['category'] as String,
      filename: json['filename'] as String,
      definition: json['definition'] as String? ?? '', // manifest에 definition이 없을 경우 대비
    );
  }
}