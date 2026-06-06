// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'analysis_result.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$SizeBinImpl _$$SizeBinImplFromJson(Map<String, dynamic> json) =>
    _$SizeBinImpl(
      sizeMm: (json['size_mm'] as num).toDouble(),
      cumulativePassingPct: (json['cumulative_passing_pct'] as num).toDouble(),
    );

Map<String, dynamic> _$$SizeBinImplToJson(_$SizeBinImpl instance) =>
    <String, dynamic>{
      'size_mm': instance.sizeMm,
      'cumulative_passing_pct': instance.cumulativePassingPct,
    };

_$AnalysisResultImpl _$$AnalysisResultImplFromJson(Map<String, dynamic> json) =>
    _$AnalysisResultImpl(
      id: json['id'] as String,
      p10Mm: (json['p10_mm'] as num).toDouble(),
      p50Mm: (json['p50_mm'] as num).toDouble(),
      p80Mm: (json['p80_mm'] as num).toDouble(),
      rosinRammlerN: (json['rosin_rammler_n'] as num?)?.toDouble(),
      rosinRammlerXc: (json['rosin_rammler_xc'] as num?)?.toDouble(),
      oversizePercent: (json['oversize_percent'] as num?)?.toDouble(),
      finesPercent: (json['fines_percent'] as num?)?.toDouble(),
      confidenceScore: (json['confidence_score'] as num?)?.toDouble(),
      sizeDistribution: (json['size_distribution'] as List<dynamic>?)
              ?.map((e) => SizeBin.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const <SizeBin>[],
    );

Map<String, dynamic> _$$AnalysisResultImplToJson(
        _$AnalysisResultImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'p10_mm': instance.p10Mm,
      'p50_mm': instance.p50Mm,
      'p80_mm': instance.p80Mm,
      'rosin_rammler_n': instance.rosinRammlerN,
      'rosin_rammler_xc': instance.rosinRammlerXc,
      'oversize_percent': instance.oversizePercent,
      'fines_percent': instance.finesPercent,
      'confidence_score': instance.confidenceScore,
      'size_distribution': instance.sizeDistribution,
    };
