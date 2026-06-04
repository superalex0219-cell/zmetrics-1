import 'dart:convert';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

/// Manages offline upload queue for capture sessions and frame uploads.
/// Operations are queued when offline and processed when connectivity is restored.
class SyncManager {
  static Database? _db;

  Future<Database> get database async {
    _db ??= await _initDb();
    return _db!;
  }

  Future<Database> _initDb() async {
    final path = join(await getDatabasesPath(), 'zmetrics_sync.db');
    return openDatabase(
      path,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE pending_uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            idempotency_key TEXT NOT NULL UNIQUE,
            operation_type TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            last_attempt_at TEXT
          )
        ''');
      },
    );
  }

  Future<void> enqueue({
    required String idempotencyKey,
    required String operationType,
    required Map<String, dynamic> payload,
  }) async {
    final db = await database;
    await db.insert(
      'pending_uploads',
      {
        'idempotency_key': idempotencyKey,
        'operation_type': operationType,
        'payload_json': jsonEncode(payload),
        'retry_count': 0,
        'created_at': DateTime.now().toIso8601String(),
      },
      conflictAlgorithm: ConflictAlgorithm.ignore,
    );
  }

  Future<List<Map<String, dynamic>>> getPendingUploads({int limit = 20}) async {
    final db = await database;
    return db.query(
      'pending_uploads',
      orderBy: 'created_at ASC',
      limit: limit,
    );
  }

  Future<void> markCompleted(int id) async {
    final db = await database;
    await db.delete('pending_uploads', where: 'id = ?', whereArgs: [id]);
  }

  Future<void> incrementRetry(int id) async {
    final db = await database;
    await db.rawUpdate(
      'UPDATE pending_uploads SET retry_count = retry_count + 1, last_attempt_at = ? WHERE id = ?',
      [DateTime.now().toIso8601String(), id],
    );
  }

  Future<int> pendingCount() async {
    final db = await database;
    final result = await db.rawQuery('SELECT COUNT(*) as count FROM pending_uploads');
    return result.first['count'] as int;
  }
}
