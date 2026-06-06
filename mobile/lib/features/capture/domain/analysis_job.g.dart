// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'analysis_job.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$AnalysisJobImpl _$$AnalysisJobImplFromJson(Map<String, dynamic> json) =>
    _$AnalysisJobImpl(
      id: json['id'] as String,
      captureSessionId: json['capture_session_id'] as String,
      status: $enumDecode(_$AnalysisJobStatusEnumMap, json['status']),
      modelVersionId: json['model_version_id'] as String?,
      reportId: json['report_id'] as String?,
      errorMessage: json['error_message'] as String?,
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$$AnalysisJobImplToJson(_$AnalysisJobImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'capture_session_id': instance.captureSessionId,
      'status': _$AnalysisJobStatusEnumMap[instance.status]!,
      'model_version_id': instance.modelVersionId,
      'report_id': instance.reportId,
      'error_message': instance.errorMessage,
      'created_at': instance.createdAt?.toIso8601String(),
    };

const _$AnalysisJobStatusEnumMap = {
  AnalysisJobStatus.queued: 'queued',
  AnalysisJobStatus.running: 'running',
  AnalysisJobStatus.completed: 'completed',
  AnalysisJobStatus.failed: 'failed',
};
