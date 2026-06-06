import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zmetrics_mobile/features/capture/data/capture_repository.dart';
import 'package:zmetrics_mobile/shared/offline/sync_manager.dart';

// ---------------------------------------------------------------------------
// Minimal Dio interceptor that captures the request and returns a canned
// response, so no real HTTP connection is needed.
// ---------------------------------------------------------------------------

class _CapturedRequest {
  _CapturedRequest({
    required this.method,
    required this.path,
    this.data,
    this.headers = const {},
  });
  final String method;
  final String path;
  final dynamic data;
  final Map<String, dynamic> headers;
}

Dio _buildDio(
  Map<String, dynamic> responseData,
  void Function(_CapturedRequest) onRequest,
) {
  final dio = Dio(BaseOptions(baseUrl: 'http://test'));
  dio.interceptors.add(
    InterceptorsWrapper(
      onRequest: (options, handler) {
        onRequest(_CapturedRequest(
          method: options.method,
          path: options.path,
          data: options.data,
          headers: Map<String, dynamic>.from(options.headers),
        ));
        handler.resolve(Response(
          requestOptions: options,
          statusCode: 200,
          data: responseData,
        ));
      },
    ),
  );
  return dio;
}

void main() {
  group('RemoteCaptureRepository.listSessions', () {
    test('builds correct URL from quarryId + passportId', () async {
      _CapturedRequest? captured;
      final dio = _buildDio(
        {'items': [], 'total': 0, 'page': 1, 'page_size': 20},
        (r) => captured = r,
      );

      final repo = RemoteCaptureRepository(dio, InMemorySyncManager());
      final sessions = await repo.listSessions('quarry-abc', 'passport-xyz');

      expect(sessions, isEmpty);
      expect(captured!.path,
          '/api/v1/quarries/quarry-abc/passports/passport-xyz/blast-event/capture-sessions');
      expect(captured!.method, 'GET');
    });
  });

  group('RemoteCaptureRepository.postQueuedCaptureSession', () {
    test('builds correct URL and sends device/calibration/datetime body', () async {
      _CapturedRequest? captured;
      final dio = _buildDio(
        {
          'id': 'sess-1',
          'blast_event_id': 'be-1',
          'device_id': 'dev-1',
          'calibration_id': 'cal-1',
          'capture_datetime': '2026-06-06T10:00:00Z',
          'frame_count': 0,
          'captured_by_id': 'user-1',
          'notes': null,
          'created_at': '2026-06-06T10:00:00Z',
          'updated_at': '2026-06-06T10:00:00Z',
        },
        (r) => captured = r,
      );

      final repo = RemoteCaptureRepository(dio, InMemorySyncManager());
      await repo.postQueuedCaptureSession(
        'idem-key-001',
        {
          'quarry_id': 'q-1',
          'passport_id': 'p-1',
          'device_id': 'dev-1',
          'calibration_id': 'cal-1',
          'capture_datetime': '2026-06-06T10:00:00Z',
          'blast_event_id': '',
          'frame_count': 0,
        },
      );

      expect(captured!.path,
          '/api/v1/quarries/q-1/passports/p-1/blast-event/capture-sessions');
      expect(captured!.method, 'POST');
      final body = captured!.data as Map<String, dynamic>;
      expect(body['device_id'], 'dev-1');
      expect(body['calibration_id'], 'cal-1');
      expect(body['capture_datetime'], '2026-06-06T10:00:00Z');
      expect(body.containsKey('quarry_id'), isFalse,
          reason: 'quarry_id must not be sent in the body');
      expect(body.containsKey('passport_id'), isFalse,
          reason: 'passport_id must not be sent in the body');
      expect(captured!.headers['Idempotency-Key'], 'idem-key-001');
    });
  });
}
