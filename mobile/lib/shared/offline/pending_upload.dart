import 'dart:convert';

/// A queued write operation awaiting upload to the backend.
class PendingUpload {
  const PendingUpload({
    required this.id,
    required this.idempotencyKey,
    required this.operationType,
    required this.payload,
    required this.retryCount,
    required this.createdAt,
    this.lastAttemptAt,
  });

  /// Local autoincrement id (SQLite) or sequence id (in-memory).
  final int id;

  /// Client-generated UUID v4 ensuring the backend dedupes retries.
  final String idempotencyKey;

  /// e.g. `create_capture_session`, `upload_frame`.
  final String operationType;

  final Map<String, dynamic> payload;
  final int retryCount;
  final DateTime createdAt;
  final DateTime? lastAttemptAt;

  factory PendingUpload.fromRow(Map<String, dynamic> row) {
    return PendingUpload(
      id: row['id'] as int,
      idempotencyKey: row['idempotency_key'] as String,
      operationType: row['operation_type'] as String,
      payload: jsonDecode(row['payload_json'] as String) as Map<String, dynamic>,
      retryCount: row['retry_count'] as int,
      createdAt: DateTime.parse(row['created_at'] as String),
      lastAttemptAt: row['last_attempt_at'] == null
          ? null
          : DateTime.parse(row['last_attempt_at'] as String),
    );
  }
}
