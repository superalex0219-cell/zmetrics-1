import 'dart:convert';

import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';

import 'pending_upload.dart';

/// Offline upload queue (mobile.md offline-first rules).
///
/// All write operations (create capture_session, create passport, upload
/// frames) are enqueued here with a client-generated `idempotency_key`, then
/// drained when connectivity is restored.
///
/// This is an interface so it can be backed by SQLite on device
/// ([SqfliteSyncManager]) or by memory on web/tests ([InMemorySyncManager]) —
/// sqflite has no web implementation.
abstract class SyncManager {
  /// After this many failed attempts an item is surfaced to the user as an
  /// error rather than retried (mobile.md: max retry 5).
  static const int maxRetries = 5;

  Future<void> enqueue({
    required String idempotencyKey,
    required String operationType,
    required Map<String, dynamic> payload,
  });

  Future<List<PendingUpload>> getPendingUploads({int limit = 20});

  Future<void> markCompleted(int id);

  Future<void> incrementRetry(int id);

  Future<int> pendingCount();
}

/// SQLite-backed queue for Android/iOS/desktop.
class SqfliteSyncManager implements SyncManager {
  SqfliteSyncManager({Database? db}) : _db = db;

  Database? _db;

  Future<Database> get _database async => _db ??= await _initDb();

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

  @override
  Future<void> enqueue({
    required String idempotencyKey,
    required String operationType,
    required Map<String, dynamic> payload,
  }) async {
    final db = await _database;
    await db.insert(
      'pending_uploads',
      {
        'idempotency_key': idempotencyKey,
        'operation_type': operationType,
        'payload_json': jsonEncode(payload),
        'retry_count': 0,
        'created_at': DateTime.now().toIso8601String(),
      },
      // Re-enqueuing the same idempotency key is a no-op (dedupe).
      conflictAlgorithm: ConflictAlgorithm.ignore,
    );
  }

  @override
  Future<List<PendingUpload>> getPendingUploads({int limit = 20}) async {
    final db = await _database;
    final rows = await db.query(
      'pending_uploads',
      orderBy: 'created_at ASC',
      limit: limit,
    );
    return rows.map(PendingUpload.fromRow).toList();
  }

  @override
  Future<void> markCompleted(int id) async {
    final db = await _database;
    await db.delete('pending_uploads', where: 'id = ?', whereArgs: [id]);
  }

  @override
  Future<void> incrementRetry(int id) async {
    final db = await _database;
    await db.rawUpdate(
      'UPDATE pending_uploads SET retry_count = retry_count + 1, '
      'last_attempt_at = ? WHERE id = ?',
      [DateTime.now().toIso8601String(), id],
    );
  }

  @override
  Future<int> pendingCount() async {
    final db = await _database;
    final result =
        await db.rawQuery('SELECT COUNT(*) as count FROM pending_uploads');
    return Sqflite.firstIntValue(result) ?? 0;
  }
}

/// In-memory queue for Flutter Web (no sqflite) and unit tests.
class InMemorySyncManager implements SyncManager {
  final List<PendingUpload> _items = [];
  int _seq = 0;

  @override
  Future<void> enqueue({
    required String idempotencyKey,
    required String operationType,
    required Map<String, dynamic> payload,
  }) async {
    // Dedupe on idempotency key, matching the SQLite UNIQUE constraint.
    if (_items.any((e) => e.idempotencyKey == idempotencyKey)) return;
    _items.add(PendingUpload(
      id: ++_seq,
      idempotencyKey: idempotencyKey,
      operationType: operationType,
      payload: payload,
      retryCount: 0,
      createdAt: DateTime.now(),
    ));
  }

  @override
  Future<List<PendingUpload>> getPendingUploads({int limit = 20}) async {
    final sorted = [..._items]
      ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
    return sorted.take(limit).toList();
  }

  @override
  Future<void> markCompleted(int id) async {
    _items.removeWhere((e) => e.id == id);
  }

  @override
  Future<void> incrementRetry(int id) async {
    final idx = _items.indexWhere((e) => e.id == id);
    if (idx == -1) return;
    final cur = _items[idx];
    _items[idx] = PendingUpload(
      id: cur.id,
      idempotencyKey: cur.idempotencyKey,
      operationType: cur.operationType,
      payload: cur.payload,
      retryCount: cur.retryCount + 1,
      createdAt: cur.createdAt,
      lastAttemptAt: DateTime.now(),
    );
  }

  @override
  Future<int> pendingCount() async => _items.length;
}
