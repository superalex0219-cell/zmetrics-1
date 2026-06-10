import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/network/paginated.dart';
import '../../../shared/offline/sync_manager.dart';
import '../domain/analysis_job.dart';
import '../domain/capture_session.dart';

/// Operation type tags used in the offline queue.
const String kOpCreateCaptureSession = 'create_capture_session';

/// Data access for capture sessions and analysis jobs.
///
/// Offline-first: [createCaptureSession] always enqueues through [SyncManager]
/// with a client-generated idempotency key (mobile.md). It returns an
/// optimistic [CaptureSession] with `synced: false`; the queue is drained by
/// the SyncProcessor when connectivity returns.
abstract class CaptureRepository {
  Future<CaptureSession> createCaptureSession(NewCaptureSession draft);
  Future<CaptureSession> createCaptureSessionOnline(NewCaptureSession draft);
  Future<void> uploadFrameArtifact(
    String captureSessionId,
    List<int> jpegBytes, {
    required String artifactType,
    required int frameIndex,
  });
  Future<List<CaptureSession>> listSessions(String quarryId, String passportId);
  Future<AnalysisJob> triggerAnalysis(String captureSessionId);
  Future<List<AnalysisJob>> listJobs(String captureSessionId);
  Future<AnalysisJob> getJob(String captureSessionId, String jobId);
}

/// In-memory stub backed by the real [SyncManager] so the offline queue is
/// exercised even without a backend.
class MockCaptureRepository implements CaptureRepository {
  MockCaptureRepository(this._sync);

  final SyncManager _sync;
  static const _uuid = Uuid();

  final List<CaptureSession> _sessions = [];
  final List<AnalysisJob> _jobs = [];

  @override
  Future<CaptureSession> createCaptureSession(NewCaptureSession draft) async {
    final idempotencyKey = _uuid.v4();
    await _sync.enqueue(
      idempotencyKey: idempotencyKey,
      operationType: kOpCreateCaptureSession,
      payload: draft.toJson(),
    );
    final session = CaptureSession(
      id: idempotencyKey,
      blastEventId: draft.blastEventId,
      deviceId: draft.deviceId,
      calibrationId: draft.calibrationId,
      frameCount: draft.frameCount,
      createdAt: DateTime.now(),
      synced: false,
    );
    _sessions.add(session);
    return session;
  }

  @override
  Future<CaptureSession> createCaptureSessionOnline(
      NewCaptureSession draft) async {
    final session = CaptureSession(
      id: _uuid.v4(),
      blastEventId: draft.blastEventId,
      deviceId: draft.deviceId,
      calibrationId: draft.calibrationId,
      frameCount: draft.frameCount,
      createdAt: DateTime.now(),
      synced: true,
    );
    _sessions.add(session);
    return session;
  }

  @override
  Future<void> uploadFrameArtifact(
    String captureSessionId,
    List<int> jpegBytes, {
    required String artifactType,
    required int frameIndex,
  }) async {
    final idx = _sessions.indexWhere((s) => s.id == captureSessionId);
    if (idx == -1) {
      throw ApiException('Capture session not found', statusCode: 404);
    }
    _sessions[idx] = _sessions[idx].copyWith(
      frameCount: _sessions[idx].frameCount + 1,
    );
  }

  @override
  Future<List<CaptureSession>> listSessions(
          String quarryId, String passportId) async =>
      List.unmodifiable(_sessions);

  @override
  Future<AnalysisJob> triggerAnalysis(String captureSessionId) async {
    final job = AnalysisJob(
      id: _uuid.v4(),
      captureSessionId: captureSessionId,
      status: AnalysisJobStatus.queued,
      createdAt: DateTime.now(),
    );
    _jobs.add(job);
    return job;
  }

  @override
  Future<List<AnalysisJob>> listJobs(String captureSessionId) async =>
      _jobs.where((j) => j.captureSessionId == captureSessionId).toList();

  @override
  Future<AnalysisJob> getJob(String captureSessionId, String jobId) async {
    final idx = _jobs.indexWhere((j) => j.id == jobId);
    if (idx == -1) throw ApiException('Job not found', statusCode: 404);
    return _jobs[idx];
  }
}

/// Live implementation. [createCaptureSession] still enqueues (offline-first);
/// the SyncProcessor performs the actual POST via [postQueuedCaptureSession].
class RemoteCaptureRepository implements CaptureRepository {
  RemoteCaptureRepository(this._dio, this._sync);

  final Dio _dio;
  final SyncManager _sync;
  static const _uuid = Uuid();

  @override
  Future<CaptureSession> createCaptureSession(NewCaptureSession draft) async {
    final idempotencyKey = _uuid.v4();
    await _sync.enqueue(
      idempotencyKey: idempotencyKey,
      operationType: kOpCreateCaptureSession,
      payload: draft.toJson(),
    );
    return CaptureSession(
      id: idempotencyKey,
      blastEventId: draft.blastEventId,
      deviceId: draft.deviceId,
      calibrationId: draft.calibrationId,
      frameCount: draft.frameCount,
      createdAt: DateTime.now(),
      synced: false,
    );
  }

  @override
  Future<CaptureSession> createCaptureSessionOnline(
      NewCaptureSession draft) async {
    try {
      final res = await _dio.post(
        '/api/v1/quarries/${draft.quarryId}/passports/${draft.passportId}/blast-event/capture-sessions',
        data: {
          'device_id': draft.deviceId,
          'calibration_id': draft.calibrationId,
          'capture_datetime': draft.captureDateTime,
        },
      );
      return CaptureSession.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<void> uploadFrameArtifact(
    String captureSessionId,
    List<int> jpegBytes, {
    required String artifactType,
    required int frameIndex,
  }) async {
    try {
      final form = FormData.fromMap({
        'artifact_type': artifactType,
        'frame_index': frameIndex.toString(),
        'file': MultipartFile.fromBytes(
          jpegBytes,
          filename: '${artifactType}_$frameIndex.jpg',
          contentType: DioMediaType('image', 'jpeg'),
        ),
      });
      await _dio.post(
        '/api/v1/capture-sessions/$captureSessionId/artifacts',
        data: form,
      );
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  /// Drains one queued capture-session create. Used by the SyncProcessor.
  Future<void> postQueuedCaptureSession(
    String idempotencyKey,
    Map<String, dynamic> payload,
  ) async {
    final quarryId = payload['quarry_id'] as String;
    final passportId = payload['passport_id'] as String;
    try {
      await _dio.post(
        '/api/v1/quarries/$quarryId/passports/$passportId/blast-event/capture-sessions',
        data: {
          'device_id': payload['device_id'],
          'calibration_id': payload['calibration_id'],
          'capture_datetime': payload['capture_datetime'],
        },
        options: Options(headers: {'Idempotency-Key': idempotencyKey}),
      );
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<List<CaptureSession>> listSessions(
      String quarryId, String passportId) async {
    try {
      final res = await _dio.get(
        '/api/v1/quarries/$quarryId/passports/$passportId/blast-event/capture-sessions',
      );
      return Paginated<CaptureSession>.fromJson(
        res.data as Map<String, dynamic>,
        CaptureSession.fromJson,
      ).items;
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<AnalysisJob> triggerAnalysis(String captureSessionId) async {
    try {
      final res = await _dio.post('/api/v1/captures/$captureSessionId/jobs');
      return AnalysisJob.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<List<AnalysisJob>> listJobs(String captureSessionId) async {
    try {
      final res = await _dio.get('/api/v1/captures/$captureSessionId/jobs');
      return Paginated<AnalysisJob>.fromJson(
        res.data as Map<String, dynamic>,
        AnalysisJob.fromJson,
      ).items;
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<AnalysisJob> getJob(String captureSessionId, String jobId) async {
    try {
      final res =
          await _dio.get('/api/v1/captures/$captureSessionId/jobs/$jobId');
      return AnalysisJob.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }
}
