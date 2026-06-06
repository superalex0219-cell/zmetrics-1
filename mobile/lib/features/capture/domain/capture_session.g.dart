// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'capture_session.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$CaptureSessionImpl _$$CaptureSessionImplFromJson(Map<String, dynamic> json) =>
    _$CaptureSessionImpl(
      id: json['id'] as String,
      blastEventId: json['blast_event_id'] as String,
      deviceId: json['device_id'] as String?,
      calibrationId: json['calibration_id'] as String?,
      frameCount: (json['frame_count'] as num?)?.toInt() ?? 0,
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$$CaptureSessionImplToJson(
        _$CaptureSessionImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'blast_event_id': instance.blastEventId,
      'device_id': instance.deviceId,
      'calibration_id': instance.calibrationId,
      'frame_count': instance.frameCount,
      'created_at': instance.createdAt?.toIso8601String(),
    };

_$NewCaptureSessionImpl _$$NewCaptureSessionImplFromJson(
        Map<String, dynamic> json) =>
    _$NewCaptureSessionImpl(
      blastEventId: json['blast_event_id'] as String,
      deviceId: json['device_id'] as String?,
      calibrationId: json['calibration_id'] as String?,
      frameCount: (json['frame_count'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$$NewCaptureSessionImplToJson(
        _$NewCaptureSessionImpl instance) =>
    <String, dynamic>{
      'blast_event_id': instance.blastEventId,
      'device_id': instance.deviceId,
      'calibration_id': instance.calibrationId,
      'frame_count': instance.frameCount,
    };
