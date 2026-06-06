// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'recommendation.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$RecommendationImpl _$$RecommendationImplFromJson(Map<String, dynamic> json) =>
    _$RecommendationImpl(
      id: json['id'] as String,
      reportId: json['report_id'] as String,
      status: $enumDecode(_$RecommendationStatusEnumMap, json['status']),
      recommendationText: json['recommendation_text'] as String,
      confidenceNotes: json['confidence_notes'] as String?,
      parameterSuggestions:
          json['parameter_suggestions'] as Map<String, dynamic>? ??
              const <String, dynamic>{},
      comments: (json['comments'] as List<dynamic>?)
              ?.map((e) => Comment.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const <Comment>[],
    );

Map<String, dynamic> _$$RecommendationImplToJson(
        _$RecommendationImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'report_id': instance.reportId,
      'status': _$RecommendationStatusEnumMap[instance.status]!,
      'recommendation_text': instance.recommendationText,
      'confidence_notes': instance.confidenceNotes,
      'parameter_suggestions': instance.parameterSuggestions,
      'comments': instance.comments,
    };

const _$RecommendationStatusEnumMap = {
  RecommendationStatus.requiresHumanReview: 'requires_human_review',
  RecommendationStatus.reviewed: 'reviewed',
  RecommendationStatus.accepted: 'accepted',
  RecommendationStatus.rejected: 'rejected',
};
