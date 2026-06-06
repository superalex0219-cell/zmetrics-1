import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../data/capture_repository.dart';
import '../data/device_repository.dart';
import '../domain/analysis_job.dart';
import '../domain/capture_session.dart';
import '../domain/device.dart';

// Sentinel used to distinguish "not provided" from "explicitly set to null"
// in nullable copyWith parameters.
const _kKeep = Object();

/// View state for the capture screen.
class CaptureView {
  const CaptureView({
    this.sessions = const [],
    this.jobs = const [],
    this.devices = const [],
    this.calibrations = const [],
    this.selectedDeviceId,
    this.selectedCalibrationId,
    this.pollingJob,
  });

  final List<CaptureSession> sessions;
  final List<AnalysisJob> jobs;
  final List<Device> devices;
  final List<DeviceCalibration> calibrations;
  final String? selectedDeviceId;
  final String? selectedCalibrationId;

  /// Non-null while a job is being polled (status queued or running).
  final AnalysisJob? pollingJob;

  bool get canCreateSession =>
      selectedDeviceId != null && selectedCalibrationId != null;

  CaptureView copyWith({
    List<CaptureSession>? sessions,
    List<AnalysisJob>? jobs,
    List<Device>? devices,
    List<DeviceCalibration>? calibrations,
    Object? selectedDeviceId = _kKeep,
    Object? selectedCalibrationId = _kKeep,
    Object? pollingJob = _kKeep,
  }) =>
      CaptureView(
        sessions: sessions ?? this.sessions,
        jobs: jobs ?? this.jobs,
        devices: devices ?? this.devices,
        calibrations: calibrations ?? this.calibrations,
        selectedDeviceId: identical(selectedDeviceId, _kKeep)
            ? this.selectedDeviceId
            : selectedDeviceId as String?,
        selectedCalibrationId: identical(selectedCalibrationId, _kKeep)
            ? this.selectedCalibrationId
            : selectedCalibrationId as String?,
        pollingJob: identical(pollingJob, _kKeep)
            ? this.pollingJob
            : pollingJob as AnalysisJob?,
      );
}

class CaptureCubit extends Cubit<DataState<CaptureView>> {
  CaptureCubit(
    this._captureRepo,
    this._deviceRepo,
    this.quarryId,
    this.passportId, {
    Duration pollInterval = const Duration(seconds: 3),
  })  : _pollInterval = pollInterval,
        super(const DataLoading());

  final CaptureRepository _captureRepo;
  final DeviceRepository _deviceRepo;
  final String quarryId;
  final String passportId;
  final Duration _pollInterval;

  Future<void> load() async {
    emit(const DataLoading());
    try {
      final sessions = await _captureRepo.listSessions(quarryId, passportId);
      final devices = await _deviceRepo.listDevices();
      emit(DataLoaded(CaptureView(sessions: sessions, devices: devices)));
    } on ApiException catch (e) {
      emit(DataFailure(e.message));
    } catch (e) {
      emit(DataFailure('$e'));
    }
  }

  /// Loads calibrations for [deviceId] and marks it selected.
  Future<void> selectDevice(String deviceId) async {
    final cur = state;
    if (cur is! DataLoaded<CaptureView>) return;
    try {
      final cals = await _deviceRepo.listCalibrations(deviceId);
      emit(DataLoaded(cur.value.copyWith(
        selectedDeviceId: deviceId,
        calibrations: cals,
        selectedCalibrationId: null,
      )));
    } on ApiException catch (e) {
      emit(DataFailure(e.message));
    }
  }

  void selectCalibration(String calibrationId) {
    final cur = state;
    if (cur is! DataLoaded<CaptureView>) return;
    emit(DataLoaded(cur.value.copyWith(selectedCalibrationId: calibrationId)));
  }

  /// Offline-first: enqueues the create op (returns an unsynced session).
  /// Requires both a device and calibration to be selected.
  Future<CaptureSession> createSession() async {
    final cur = state;
    if (cur is! DataLoaded<CaptureView>) throw StateError('Not loaded');
    final view = cur.value;
    if (!view.canCreateSession) {
      throw StateError('Device and calibration required');
    }

    final session = await _captureRepo.createCaptureSession(NewCaptureSession(
      blastEventId: '', // not used for URL routing; quarryId + passportId are
      quarryId: quarryId,
      passportId: passportId,
      deviceId: view.selectedDeviceId!,
      calibrationId: view.selectedCalibrationId!,
      captureDateTime: DateTime.now().toUtc().toIso8601String(),
    ));
    await load();
    return session;
  }

  Future<AnalysisJob> triggerAnalysis(String captureSessionId) async {
    final job = await _captureRepo.triggerAnalysis(captureSessionId);
    final cur = state;
    if (cur is DataLoaded<CaptureView>) {
      emit(DataLoaded(cur.value.copyWith(
        jobs: [...cur.value.jobs, job],
        pollingJob: job,
      )));
    }
    return job;
  }

  /// Polls [jobId] every [_pollInterval] until it reaches a terminal status
  /// (completed or failed). Sets [CaptureView.pollingJob] to null on terminal.
  /// The [isClosed] guard prevents emitting on a disposed cubit.
  Future<void> pollJobUntilTerminal(String sessionId, String jobId) async {
    while (true) {
      await Future.delayed(_pollInterval);
      if (isClosed) return;

      AnalysisJob job;
      try {
        job = await _captureRepo.getJob(sessionId, jobId);
      } catch (_) {
        // Network error — stop polling, let user retry.
        return;
      }

      final cur = state;
      if (cur is DataLoaded<CaptureView>) {
        emit(DataLoaded(cur.value.copyWith(
          pollingJob: job.status.isTerminal ? null : job,
          jobs: [
            ...cur.value.jobs.where((j) => j.id != job.id),
            job,
          ],
        )));
      }
      if (job.status.isTerminal) return;
    }
  }
}
