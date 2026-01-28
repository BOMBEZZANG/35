import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import 'dart:developer';
import 'dart:io';
import 'package:flutter/services.dart';

class DatabaseHelper {
  static DatabaseHelper? _instance;
  static final Map<String, DatabaseHelper> _instances = {};
  
  Database? _database;
  final String _assetDbPath; // assets 내의 DB 경로

  // Private constructor
  DatabaseHelper._internal(this._assetDbPath);

  // Factory constructor for Singleton pattern
  factory DatabaseHelper(String assetDbPath) {
    if (!_instances.containsKey(assetDbPath)) {
      _instances[assetDbPath] = DatabaseHelper._internal(assetDbPath);
    }
    return _instances[assetDbPath]!;
  }

  // Static method to get instance for specific database
  static DatabaseHelper getInstance(String assetDbPath) {
    return DatabaseHelper(assetDbPath);
  }

  // 데이터베이스 게터
  Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDB();
    return _database!;
  }

  // database_helper.dart에 추가할 메서드들

// 모든 용어 가져오기
Future<List<Map<String, dynamic>>> getAllTerms() async {
  try {
    final db = await database;
    final result = await db.query('dictionary', orderBy: 'term ASC');
    print('Fetched ${result.length} terms from dictionary');
    return result;
  } catch (e) {
    print('Error in getAllTerms: $e');
    return [];
  }
}

// 카테고리별 용어 가져오기
Future<List<Map<String, dynamic>>> getTermsByCategory(String category) async {
  try {
    final db = await database;
    final result = await db.query(
      'dictionary',
      where: 'category = ?',
      whereArgs: [category],
      orderBy: 'term ASC',
    );
    print('Fetched ${result.length} terms for category: $category');
    return result;
  } catch (e) {
    print('Error in getTermsByCategory: $e');
    return [];
  }
}


// database_helper.dart 파일

// ... 다른 함수들 ...

// 특정 Question_id로 문제 하나만 가져오기
Future<Map<String, dynamic>?> getQuestion(int questionId) async {
  try {
    final db = await database;
    final result = await db.query(
      'questions',
      where: 'Question_id = ?', // Question_id만으로 조회
      whereArgs: [questionId],
      limit: 1, // ID는 고유하므로 1개만 가져옴
    );

    if (result.isNotEmpty) {
      return result.first;
    }
    return null;
  } catch (e) {
    print('Error in getQuestion: $e');
    return null;
  }
}

// 용어 검색 (용어명 또는 정의에서)
Future<List<Map<String, dynamic>>> searchTerms(String query, {String? category}) async {
  try {
    final db = await database;
    String whereClause = 'term LIKE ? OR definition LIKE ?';
    List<dynamic> whereArgs = ['%$query%', '%$query%'];
    
    if (category != null && category.isNotEmpty) {
      whereClause += ' AND category = ?';
      whereArgs.add(category);
    }
    
    final result = await db.query(
      'dictionary',
      where: whereClause,
      whereArgs: whereArgs,
      orderBy: 'term ASC',
    );
    print('Search found ${result.length} terms for query: "$query"');
    return result;
  } catch (e) {
    print('Error in searchTerms: $e');
    return [];
  }
}

// 특정 용어 가져오기
Future<Map<String, dynamic>?> getTermByName(String termName) async {
  try {
    final db = await database;
    final result = await db.query(
      'dictionary',
      where: 'term = ?',
      whereArgs: [termName],
      limit: 1,
    );
    
    if (result.isNotEmpty) {
      return result.first;
    }
    return null;
  } catch (e) {
    print('Error in getTermByName: $e');
    return null;
  }
}

// 카테고리별 용어 개수 가져오기
Future<Map<String, int>> getTermsCountByCategory() async {
  try {
    final db = await database;
    final result = await db.rawQuery('''
      SELECT category, COUNT(*) as count 
      FROM dictionary 
      GROUP BY category
    ''');
    
    Map<String, int> categoryStats = {};
    for (var row in result) {
      categoryStats[row['category'] as String] = row['count'] as int;
    }
    return categoryStats;
  } catch (e) {
    print('Error in getTermsCountByCategory: $e');
    return {};
  }
}

  // 데이터베이스 초기화 (assets에서 문서 디렉터리로 복사 후 사용)
  Future<Database> _initDB() async {
    try {
      // 앱 문서 디렉터리 경로 가져오기
      final dbPath = await getDatabasesPath();
      final dbFileName = basename(_assetDbPath); // 파일명만 추출 (예: question1.db)
      final path = join(dbPath, dbFileName);

      // 파일이 이미 존재하는지 확인
      final exists = await databaseExists(path);

      if (!exists) {
        print('Copying database from assets: $_assetDbPath to $path');
        
        // 디렉터리 생성
        try {
          await Directory(dirname(path)).create(recursive: true);
        } catch (e) {
          print('Error creating directory: $e');
        }
        
        // Assets에서 데이터 불러오기
        ByteData data = await rootBundle.load(_assetDbPath);
        List<int> bytes = data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes);
        
        // 파일 쓰기
        await File(path).writeAsBytes(bytes, flush: true);
        print('DB file copied successfully to $path');
      } else {
        print('Opening existing database at $path');
      }

      // 읽기/쓰기 모드로 데이터베이스 열기 (readOnly: false는 기본값)
      return await openDatabase(path);
    } catch (e) {
      print('Error in _initDB: $e');
      rethrow; // 에러를 상위로 전파하여 UI에서 처리
    }
  }

  // 특정 카테고리의 문제 가져오기
  Future<List<Map<String, dynamic>>> getQuestionsByCategory(String category) async {
    try {
      final db = await database;

      final result = await db.query(
        'questions',
        where: 'Category = ?',
        whereArgs: [category],
      );

      log('Fetched questions count for $category: ${result.length}');
      return result;
    } catch (e) {
      print('Error in getQuestionsByCategory: $e');
      return []; // 오류 시 빈 목록 반환
    }
  }

  // 카테고리 및 ID로 문제 가져오기
  Future<Map<String, dynamic>?> getQuestionByCategoryAndId(String category, int questionId) async {
    try {
      final db = await database;
      print('[getQuestionByCategoryAndId] category=$category, questionId=$questionId');

      List<Map<String, dynamic>> results = await db.query(
        'questions',
        where: 'category = ? AND question_id = ?',
        whereArgs: [category, questionId],
      );

      print('[getQuestionByCategoryAndId] query results length: ${results.length}');
      if (results.isNotEmpty) {
        return results.first;
      } else {
        return null;
      }
    } catch (e) {
      print('Error in getQuestionByCategoryAndId: $e');
      return null; // 오류 시 null 반환
    }
  }

  // 특정 시험 회차의 모든 문제 가져오기
  Future<List<Map<String, dynamic>>> getQuestions(int examSession) async {
    try {
      final db = await database;

      final result = await db.query(
        'questions',
        where: 'ExamSession = ?',
        whereArgs: [examSession],
      );

      log('DB Query result: ${result.length} questions found for ExamSession $examSession');
      return result;
    } catch (e) {
      print('Error in getQuestions: $e');
      return []; // 오류 시 빈 목록 반환
    }
  }

  // 시험 회차와 문제 ID로 특정 문제 가져오기
  Future<Map<String, dynamic>?> getQuestionById(int examSession, int questionId) async {
    try {
      final db = await database;

      final result = await db.query(
        'questions',
        where: 'ExamSession = ? AND Question_id = ?',
        whereArgs: [examSession, questionId],
      );

      if (result.isNotEmpty) {
        return result.first;
      } else {
        return null;
      }
    } catch (e) {
      print('Error in getQuestionById: $e');
      return null; // 오류 시 null 반환
    }
  }

  // 리소스 해제
  Future<void> dispose() async {
    try {
      if (_database != null) {
        await _database!.close();
        _database = null;
      }
    } catch (e) {
      print('Error in dispose: $e');
    }
  }

  // 모든 인스턴스 해제 (앱 종료 시 사용)
  static Future<void> disposeAll() async {
    try {
      for (var instance in _instances.values) {
        await instance.dispose();
      }
      _instances.clear();
    } catch (e) {
      print('Error in disposeAll: $e');
    }
  }

  // 특정 데이터베이스 인스턴스 해제
  static Future<void> disposeInstance(String assetDbPath) async {
    try {
      if (_instances.containsKey(assetDbPath)) {
        await _instances[assetDbPath]!.dispose();
        _instances.remove(assetDbPath);
      }
    } catch (e) {
      print('Error in disposeInstance: $e');
    }
  }

  // 특정 시험 회차의 문제 수 가져오기
  Future<int> getQuestionsCount(int examSession) async {
    try {
      final db = await database;
      final result = await db.rawQuery('SELECT COUNT(*) as cnt FROM questions WHERE ExamSession = ?', [examSession]);
      int count = Sqflite.firstIntValue(result) ?? 0;
      return count;
    } catch (e) {
      print('Error in getQuestionsCount: $e');
      return 0; // 오류 시 0 반환
    }
  }
  
  // 모든 문제 가져오기
  Future<List<Map<String, dynamic>>> getAllQuestions() async {
    try {
      final db = await database;
      // 'questions' 테이블에서 모든 행을 SELECT
      final result = await db.query('questions');
      return result;
    } catch (e) {
      print('Error in getAllQuestions: $e');
      return []; // 오류 시 빈 목록 반환
    }
  }
}