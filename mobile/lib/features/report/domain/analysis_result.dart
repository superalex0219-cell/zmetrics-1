import 'package:freezed_annotation/freezed_annotation.dart';

part 'analysis_result.freezed.dart';
part 'analysis_result.g.dart';

/// A single point on the cumulative passing curve.
@freezed
class SizeBin with _$SizeBin {
  const factory SizeBin({
    @JsonKey(name: 'size_mm') required double sizeMm,
    @JsonKey(name: 'cumulative_passing_pct') required double cumulativePassingPct,
  }) = _SizeBin;

  factory SizeBin.fromJson(Map<String, dynamic> json) =>
      _$SizeBinFromJson(json);
}

/// AnalysisResult — granulometry metrics. All sizes are millimetres;
/// confidence_score is 0.0–1.0 (rules/02-domain.md units).
///
/// SAFETY: P10/P50/P80 are scientific outputs and are displayed at full
/// precision — never rounded/truncated (rules/01-safety.md data integrity).
@freezed
class AnalysisResult with _$AnalysisResult {
  const factory AnalysisResult({
    required String id,
    @JsonKey(name: 'p10_mm') required double p10Mm,
    @JsonKey(name: 'p50_mm') required double p50Mm,
    @JsonKey(name: 'p80_mm') required double p80Mm,
    @JsonKey(name: 'rosin_rammler_n') double? rosinRammlerN,
    @JsonKey(name: 'rosin_rammler_xc') double? rosinRammlerXc,
    @JsonKey(name: 'oversize_percent') double? oversizePercent,
    @JsonKey(name: 'fines_percent') double? finesPercent,
    @JsonKey(name: 'confidence_score') double? confidenceScore,
    @JsonKey(name: 'size_distribution') @Default(<SizeBin>[]) List<SizeBin> sizeDistribution,
  }) = _AnalysisResult;

  factory AnalysisResult.fromJson(Map<String, dynamic> json) =>
      _$AnalysisResultFromJson(json);
}
