import 'package:freezed_annotation/freezed_annotation.dart';

import 'analysis_result.dart';
import 'recommendation.dart';

part 'report.freezed.dart';
part 'report.g.dart';

/// How the analysis behind a report was produced.
///
/// SAFETY: reports MUST display the method prominently. The mock pipeline is
/// synthetic and labelled as such (rules/product-safety.md AI/ML labelling).
@JsonEnum()
enum AnalysisMethod {
  @JsonValue('mock')
  mock,
  @JsonValue('real')
  real;

  bool get isMock => this == AnalysisMethod.mock;
}

/// Report — generated from a completed [AnalysisResult].
@freezed
class Report with _$Report {
  const factory Report({
    required String id,
    @JsonKey(name: 'analysis_result_id') String? analysisResultId,
    // Backend always sends analysis_method; default .mock is fail-safe —
    // shows warning badge if the field is absent rather than silently hiding it.
    @JsonKey(name: 'analysis_method')
    @Default(AnalysisMethod.mock)
    AnalysisMethod analysisMethod,
    String? title,
    @JsonKey(name: 'created_at') DateTime? createdAt,
    String? summary,
    @JsonKey(name: 'analysis_result') AnalysisResult? analysisResult,
    @Default(<Recommendation>[]) List<Recommendation> recommendations,
  }) = _Report;

  factory Report.fromJson(Map<String, dynamic> json) =>
      _$ReportFromJson(json);
}
