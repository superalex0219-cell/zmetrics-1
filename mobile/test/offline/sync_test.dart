import 'package:flutter_test/flutter_test.dart';
import 'package:zmetrics_mobile/shared/offline/sync_manager.dart';
import 'package:zmetrics_mobile/shared/offline/sync_processor.dart';

void main() {
  group('InMemorySyncManager', () {
    test('enqueue then read back', () async {
      final sm = InMemorySyncManager();
      await sm.enqueue(
        idempotencyKey: 'k1',
        operationType: 'create_capture_session',
        payload: {'a': 1},
      );
      expect(await sm.pendingCount(), 1);
      final items = await sm.getPendingUploads();
      expect(items.single.idempotencyKey, 'k1');
      expect(items.single.payload['a'], 1);
    });

    test('dedupes on idempotency key', () async {
      final sm = InMemorySyncManager();
      await sm.enqueue(idempotencyKey: 'k1', operationType: 'op', payload: {});
      await sm.enqueue(idempotencyKey: 'k1', operationType: 'op', payload: {});
      expect(await sm.pendingCount(), 1);
    });

    test('markCompleted removes; incrementRetry bumps count', () async {
      final sm = InMemorySyncManager();
      await sm.enqueue(idempotencyKey: 'k1', operationType: 'op', payload: {});
      final id = (await sm.getPendingUploads()).single.id;
      await sm.incrementRetry(id);
      expect((await sm.getPendingUploads()).single.retryCount, 1);
      await sm.markCompleted(id);
      expect(await sm.pendingCount(), 0);
    });
  });

  group('SyncProcessor', () {
    test('drains queue on success', () async {
      final sm = InMemorySyncManager();
      await sm.enqueue(idempotencyKey: 'k1', operationType: 'op', payload: {});
      final processor = SyncProcessor(sm, {'op': (_) async {}});

      final outcome = await processor.process();
      expect(outcome.completed, 1);
      expect(await sm.pendingCount(), 0);
    });

    test('increments retry on handler failure (item stays queued)', () async {
      final sm = InMemorySyncManager();
      await sm.enqueue(idempotencyKey: 'k1', operationType: 'op', payload: {});
      final processor =
          SyncProcessor(sm, {'op': (_) async => throw Exception('boom')});

      final outcome = await processor.process();
      expect(outcome.failed, 1);
      expect(await sm.pendingCount(), 1);
      expect((await sm.getPendingUploads()).single.retryCount, 1);
    });

    test('reports exhausted items beyond maxRetries', () async {
      final sm = InMemorySyncManager();
      await sm.enqueue(idempotencyKey: 'k1', operationType: 'op', payload: {});
      final id = (await sm.getPendingUploads()).single.id;
      for (var i = 0; i < SyncManager.maxRetries; i++) {
        await sm.incrementRetry(id);
      }
      final processor = SyncProcessor(sm, {'op': (_) async {}});

      final outcome = await processor.process();
      expect(outcome.exhausted, 1);
      expect(outcome.completed, 0);
      // Still queued — surfaced to the user, not silently dropped.
      expect(await sm.pendingCount(), 1);
    });
  });
}
