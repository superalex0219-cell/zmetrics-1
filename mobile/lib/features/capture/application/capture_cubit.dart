import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../data/capture_repository.dart';
import '../domain/analysis_job.dart';
import '../domain/capture_session.dart';

/// View state for a single blast event's capture sessions + their jobs.
class CaptureView {
  const CaptureView({this.sessions = const [], this.jobs = const []});
  final List<CaptureSession> sessions;
  final List<AnalysisJob> jobs;

  CaptureView copyWith({List<CaptureSession>? sessions, List<AnalysisJob>? jobs}) =>
      CaptureView(sessions: sessions ?? this.sessions, jobs: jobs ?? this.jobs);
}

class CaptureCubit extends Cubit<DataState<CaptureView>> {
  CaptureCubit(this._repo, this.blastEventId) : super(const DataLoading());

  final CaptureRepository _repo;
  final String blastEventId;

  Future<void> load() async {
    emit(const DataLoading());
    try {
      final sessions = await _repo.listSessions(blastEventId);
      emit(DataLoaded(CaptureView(sessions: sessions)));
    } on ApiException catch (e) {
      emit(DataFailure(e.message));
    } catch (e) {
      emit(DataFailure('$e'));
    }
  }

  /// Offline-first: enqueues the create op (returns an unsynced session).
  Future<CaptureSession> createSession({
    String? deviceId,
    String? calibrationId,
    int frameCount = 0,
  }) async {
    final session = await _repo.createCaptureSession(
      NewCaptureSession(
        blastEventId: blastEventId,
        deviceId: deviceId,
        calibrationId: calibrationId,
        frameCount: frameCount,
      ),
    );
    await load();
    return session;
  }

  Future<AnalysisJob> triggerAnalysis(String captureSessionId) async {
    final job = await _repo.triggerAnalysis(captureSessionId);
    final cur = state;
    if (cur is DataLoaded<CaptureView>) {
      emit(DataLoaded(cur.value.copyWith(jobs: [...cur.value.jobs, job])));
    }
    return job;
  }
}
