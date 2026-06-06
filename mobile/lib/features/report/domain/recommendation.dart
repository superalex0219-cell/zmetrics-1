import 'package:freezed_annotation/freezed_annotation.dart';

import 'comment.dart';

part 'recommendation.freezed.dart';
part 'recommendation.g.dart';

/// Recommendation review lifecycle. JSON values match the backend
/// `RecommendationStatus` enum.
///
/// SAFETY: created records are ALWAYS [requiresHumanReview]; the system never
/// auto-advances past it (rules/product-safety.md). The client offers the
/// human-driven transitions: requires_human_review → reviewed → accepted/rejected.
@JsonEnum()
enum RecommendationStatus {
  @JsonValue('requires_human_review')
  requiresHumanReview,
  @JsonValue('reviewed')
  reviewed,
  @JsonValue('accepted')
  accepted,
  @JsonValue('rejected')
  rejected;

  String get label => switch (this) {
        RecommendationStatus.requiresHumanReview => 'Requires human review',
        RecommendationStatus.reviewed => 'Reviewed',
        RecommendationStatus.accepted => 'Accepted',
        RecommendationStatus.rejected => 'Rejected',
      };

  bool get isReviewed => this != RecommendationStatus.requiresHumanReview;
}

/// Recommendation — AI-assisted BVR suggestion attached to a [Report].
///
/// SAFETY: [parameterSuggestions] are reference-only. There is NO client code
/// path that reads this map and writes it into a passport
/// (rules/product-safety.md). They are rendered read-only.
@freezed
class Recommendation with _$Recommendation {
  const factory Recommendation({
    required String id,
    @JsonKey(name: 'report_id') required String reportId,
    required RecommendationStatus status,
    @JsonKey(name: 'recommendation_text') required String recommendationText,
    @JsonKey(name: 'confidence_notes') String? confidenceNotes,
    @JsonKey(name: 'parameter_suggestions')
    @Default(<String, dynamic>{})
    Map<String, dynamic> parameterSuggestions,
    @Default(<Comment>[]) List<Comment> comments,
  }) = _Recommendation;

  factory Recommendation.fromJson(Map<String, dynamic> json) =>
      _$RecommendationFromJson(json);
}
