import 'package:flutter_test/flutter_test.dart';
import 'package:zmetrics_mobile/features/capture/application/capture_cubit.dart';
import 'package:zmetrics_mobile/features/capture/data/capture_repository.dart';
import 'package:zmetrics_mobile/features/capture/data/device_repository.dart';
import 'package:zmetrics_mobile/features/capture/domain/analysis_job.dart';
import 'package:zmetrics_mobile/features/capture/domain/capture_session.dart';
import 'package:zmetrics_mobile/shared/bloc/data_state.dart';
import 'package:zmetrics_mobile/shared/offline/sync_manager.dart';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Repo that always returns a single pre-baked completed job.
class _TerminalJobRepo implements CaptureRepository {
  _TerminalJobRepo(this._job);
  final AnalysisJob _job;

  @override
  Future<List<CaptureSession>> listSessions(
          String quarryId, String passportId) async =>
      [];

  @override
  Future<CaptureSession> createCaptureSession(NewCaptureSession draft) async =>
      CaptureSession(id: 'sess-x', blastEventId: '');

  @override
  Future<AnalysisJob> triggerAnalysis(String captureSessionId) async => _job;

  @override
  Future<List<AnalysisJob>> listJobs(String captureSessionId) async => [_job];

  @override
  Future<AnalysisJob> getJob(String captureSessionId, String jobId) async =>
      _job;
}

CaptureCubit _mockCubit({
  CaptureRepository? captureRepo,
  Duration pollInterval = Duration.zero,
}) =>
    CaptureCubit(
      captureRepo ?? MockCaptureRepository(InMemorySyncManager()),
      MockDeviceRepository(),
      'q-test',
      'p-test',
      pollInterval: pollInterval,
    );

DataLoaded<CaptureView> _loaded(CaptureCubit cubit) =>
    cubit.state as DataLoaded<CaptureView>;

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  group('CaptureCubit.selectDevice', () {
    test('loads calibrations and clears prior calibration selection', () async {
      final cubit = _mockCubit();
      await cubit.load();

      expect(_loaded(cubit).value.devices, hasLength(1));
      expect(_loaded(cubit).value.calibrations, isEmpty);

      await cubit.selectDevice('mock-device-001');

      final view = _loaded(cubit).value;
      expect(view.selectedDeviceId, 'mock-device-001');
      expect(view.calibrations, hasLength(1));
      expect(view.calibrations.first.id, 'mock-cal-001');
      expect(view.selectedCalibrationId, isNull,
          reason: 'selecting a new device clears prior calibration');
      await cubit.close();
    });
  });

  group('CaptureCubit.createSession', () {
    test('throws StateError when no device + calibration selected', () async {
      final cubit = _mockCubit();
      await cubit.load();

      await expectLater(
        cubit.createSession(),
        throwsA(isA<StateError>()),
      );
      await cubit.close();
    });

    test('creates session and reloads after full selection', () async {
      final cubit = _mockCubit();
      await cubit.load();
      await cubit.selectDevice('mock-device-001');
      cubit.selectCalibration('mock-cal-001');

      expect(_loaded(cubit).value.canCreateSession, isTrue);

      final session = await cubit.createSession();
      expect(session.synced, isFalse);
      expect(_loaded(cubit).value.sessions, hasLength(1));
      await cubit.close();
    });
  });

  group('CaptureCubit.pollJobUntilTerminal', () {
    test('sets pollingJob to null when getJob returns terminal status', () async {
      final completedJob = AnalysisJob(
        id: 'job-1',
        captureSessionId: 'sess-x',
        status: AnalysisJobStatus.completed,
      );

      final cubit = _mockCubit(
        captureRepo: _TerminalJobRepo(completedJob),
        pollInterval: Duration.zero,
      );
      await cubit.load();

      // triggerAnalysis sets pollingJob in state.
      await cubit.triggerAnalysis('sess-x');
      expect(_loaded(cubit).value.pollingJob, isNotNull);

      // Poll once — repo returns a completed job → pollingJob cleared.
      await cubit.pollJobUntilTerminal('sess-x', 'job-1');

      expect(_loaded(cubit).value.pollingJob, isNull,
          reason: 'pollingJob must be null after terminal status');
      expect(
        _loaded(cubit).value.jobs.first.status,
        AnalysisJobStatus.completed,
      );
      await cubit.close();
    });

    test('keeps polling when job is not yet terminal', () async {
      var callCount = 0;
      final runningJob = AnalysisJob(
        id: 'job-2',
        captureSessionId: 'sess-y',
        status: AnalysisJobStatus.running,
      );
      final completedJob = runningJob.copyWith(status: AnalysisJobStatus.completed);

      // Repo returns running twice, then completed.
      final repo = _CallCountingRepo(
        jobs: [runningJob, runningJob, completedJob],
        onGetJob: () => callCount++,
      );

      final cubit = _mockCubit(
        captureRepo: repo,
        pollInterval: Duration.zero,
      );
      await cubit.load();
      await cubit.triggerAnalysis('sess-y');

      await cubit.pollJobUntilTerminal('sess-y', 'job-2');

      expect(callCount, 3,
          reason: 'should poll until terminal (2 running + 1 completed)');
      expect(_loaded(cubit).value.pollingJob, isNull);
      await cubit.close();
    });
  });
}

/// Repo that cycles through a pre-defined list of jobs on each getJob call.
class _CallCountingRepo implements CaptureRepository {
  _CallCountingRepo({required List<AnalysisJob> jobs, required this.onGetJob})
      : _jobs = List.unmodifiable(jobs);

  final List<AnalysisJob> _jobs;
  final void Function() onGetJob;
  int _index = 0;

  @override
  Future<List<CaptureSession>> listSessions(
          String quarryId, String passportId) async =>
      [];

  @override
  Future<CaptureSession> createCaptureSession(NewCaptureSession draft) async =>
      CaptureSession(id: 'sess-y', blastEventId: '');

  @override
  Future<AnalysisJob> triggerAnalysis(String captureSessionId) async =>
      _jobs.first;

  @override
  Future<List<AnalysisJob>> listJobs(String captureSessionId) async =>
      [_jobs[_index]];

  @override
  Future<AnalysisJob> getJob(String captureSessionId, String jobId) async {
    onGetJob();
    final job = _jobs[_index];
    if (_index < _jobs.length - 1) _index++;
    return job;
  }
}
