import 'package:freezed_annotation/freezed_annotation.dart';

part 'analysis_job.freezed.dart';
part 'analysis_job.g.dart';

/// AnalysisJob (Celery job) status. JSON values match the backend enum.
@JsonEnum()
enum AnalysisJobStatus {
  @JsonValue('queued')
  queued,
  @JsonValue('running')
  running,
  @JsonValue('completed')
  completed,
  @JsonValue('failed')
  failed;

  String get label => switch (this) {
        AnalysisJobStatus.queued => 'Queued',
        AnalysisJobStatus.running => 'Running',
        AnalysisJobStatus.completed => 'Completed',
        AnalysisJobStatus.failed => 'Failed',
      };

  bool get isTerminal =>
      this == AnalysisJobStatus.completed || this == AnalysisJobStatus.failed;
}

/// AnalysisJob — links a CaptureSession to its CV/ML processing run.
///
/// SAFETY: a failed job produces no Report/Recommendation; [errorMessage] is
/// surfaced rather than silently dropped (rules/01-safety.md error handling).
@freezed
class AnalysisJob with _$AnalysisJob {
  const factory AnalysisJob({
    required String id,
    @JsonKey(name: 'capture_session_id') required String captureSessionId,
    required AnalysisJobStatus status,
    @JsonKey(name: 'model_version_id') String? modelVersionId,
    @JsonKey(name: 'report_id') String? reportId,
    @JsonKey(name: 'error_message') String? errorMessage,
    @JsonKey(name: 'created_at') DateTime? createdAt,
  }) = _AnalysisJob;

  factory AnalysisJob.fromJson(Map<String, dynamic> json) =>
      _$AnalysisJobFromJson(json);
}
