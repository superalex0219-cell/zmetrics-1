// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'report.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$ReportImpl _$$ReportImplFromJson(Map<String, dynamic> json) => _$ReportImpl(
      id: json['id'] as String,
      analysisMethod: $enumDecodeNullable(
              _$AnalysisMethodEnumMap, json['analysis_method']) ??
          AnalysisMethod.real,
      title: json['title'] as String?,
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
      summary: json['summary'] as String?,
      analysisResult: json['analysis_result'] == null
          ? null
          : AnalysisResult.fromJson(
              json['analysis_result'] as Map<String, dynamic>),
      recommendations: (json['recommendations'] as List<dynamic>?)
              ?.map((e) => Recommendation.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const <Recommendation>[],
    );

Map<String, dynamic> _$$ReportImplToJson(_$ReportImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'analysis_method': _$AnalysisMethodEnumMap[instance.analysisMethod]!,
      'title': instance.title,
      'created_at': instance.createdAt?.toIso8601String(),
      'summary': instance.summary,
      'analysis_result': instance.analysisResult,
      'recommendations': instance.recommendations,
    };

const _$AnalysisMethodEnumMap = {
  AnalysisMethod.mock: 'mock',
  AnalysisMethod.real: 'real',
};
