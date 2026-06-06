import 'package:freezed_annotation/freezed_annotation.dart';

part 'capture_session.freezed.dart';
part 'capture_session.g.dart';

/// CaptureSession (сессия съемки) — a set of stereo frames captured for a
/// BlastEvent with a given Device + Calibration.
@freezed
class CaptureSession with _$CaptureSession {
  const factory CaptureSession({
    required String id,
    @JsonKey(name: 'blast_event_id') required String blastEventId,
    @JsonKey(name: 'device_id') String? deviceId,
    @JsonKey(name: 'calibration_id') String? calibrationId,
    @JsonKey(name: 'frame_count') @Default(0) int frameCount,
    @JsonKey(name: 'created_at') DateTime? createdAt,
    /// Local-only flag: false while the create op is still in the offline
    /// queue, true once the backend has acknowledged it.
    @JsonKey(includeToJson: false, includeFromJson: false)
    @Default(true)
    bool synced,
  }) = _CaptureSession;

  factory CaptureSession.fromJson(Map<String, dynamic> json) =>
      _$CaptureSessionFromJson(json);
}

/// Payload to create a capture session. Sent through the offline SyncManager
/// with a client-generated idempotency key.
@freezed
class NewCaptureSession with _$NewCaptureSession {
  const factory NewCaptureSession({
    @JsonKey(name: 'blast_event_id') required String blastEventId,
    @JsonKey(name: 'device_id') String? deviceId,
    @JsonKey(name: 'calibration_id') String? calibrationId,
    @JsonKey(name: 'frame_count') @Default(0) int frameCount,
  }) = _NewCaptureSession;

  factory NewCaptureSession.fromJson(Map<String, dynamic> json) =>
      _$NewCaptureSessionFromJson(json);
}
