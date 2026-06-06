import 'pending_upload.dart';
import 'sync_manager.dart';

/// Handles one queued operation by sending it to the backend.
/// Throws to signal failure (the item will be retried).
typedef UploadHandler = Future<void> Function(PendingUpload upload);

/// Outcome of draining the queue once.
class SyncOutcome {
  const SyncOutcome({
    required this.completed,
    required this.failed,
    required this.exhausted,
  });

  final int completed;
  final int failed;

  /// Items that hit [SyncManager.maxRetries] and need user attention.
  final int exhausted;
}

/// Drains the offline queue. Operation type → handler.
///
/// On success an item is removed; on failure its retry count is incremented.
/// After [SyncManager.maxRetries] attempts the item is reported as exhausted
/// (surfaced to the user) rather than retried forever (mobile.md).
class SyncProcessor {
  SyncProcessor(this._sync, this._handlers);

  final SyncManager _sync;
  final Map<String, UploadHandler> _handlers;

  Future<SyncOutcome> process() async {
    final pending = await _sync.getPendingUploads();
    var completed = 0;
    var failed = 0;
    var exhausted = 0;

    for (final upload in pending) {
      if (upload.retryCount >= SyncManager.maxRetries) {
        exhausted++;
        continue;
      }
      final handler = _handlers[upload.operationType];
      if (handler == null) {
        // No handler registered → cannot process; treat as a failed attempt.
        await _sync.incrementRetry(upload.id);
        failed++;
        continue;
      }
      try {
        await handler(upload);
        await _sync.markCompleted(upload.id);
        completed++;
      } catch (_) {
        await _sync.incrementRetry(upload.id);
        failed++;
      }
    }

    return SyncOutcome(
      completed: completed,
      failed: failed,
      exhausted: exhausted,
    );
  }
}
