import 'package:freezed_annotation/freezed_annotation.dart';

import 'passport_status.dart';

part 'blast_passport.freezed.dart';
part 'blast_passport.g.dart';

/// BlastPassport (паспорт БВР) — blast design document.
///
/// Numeric blast-design fields use the units mandated by rules/02-domain.md:
///   - explosive: kilograms (kg)
///   - hole_diameter, P-sizes: millimetres (mm)
///   - burden/spacing/depth/stemming: metres (m)
@freezed
class BlastPassport with _$BlastPassport {
  const factory BlastPassport({
    required String id,
    @JsonKey(name: 'site_section_id') required String siteSectionId,
    required PassportStatus status,
    @JsonKey(name: 'revision_number') @Default(1) int revisionNumber,
    @JsonKey(name: 'superseded_by_id') String? supersededById,
    @JsonKey(name: 'explosive_type') String? explosiveType,
    @JsonKey(name: 'total_explosive_kg') double? totalExplosiveKg,
    @JsonKey(name: 'hole_diameter_mm') double? holeDiameterMm,
    @JsonKey(name: 'hole_depth_m') double? holeDepthM,
    @JsonKey(name: 'burden_m') double? burdenM,
    @JsonKey(name: 'spacing_m') double? spacingM,
    @JsonKey(name: 'stemming_m') double? stemmingM,
    @JsonKey(name: 'target_p80_mm') double? targetP80Mm,
  }) = _BlastPassport;

  factory BlastPassport.fromJson(Map<String, dynamic> json) =>
      _$BlastPassportFromJson(json);
}

/// Payload used to create a new passport. Fields are entered manually by the
/// blaster — they are NEVER prefilled from AI recommendations
/// (rules/product-safety.md hard limit #4).
@freezed
class NewBlastPassport with _$NewBlastPassport {
  const factory NewBlastPassport({
    @JsonKey(name: 'site_section_id') required String siteSectionId,
    @JsonKey(name: 'explosive_type') String? explosiveType,
    @JsonKey(name: 'total_explosive_kg') double? totalExplosiveKg,
    @JsonKey(name: 'hole_diameter_mm') double? holeDiameterMm,
    @JsonKey(name: 'hole_depth_m') double? holeDepthM,
    @JsonKey(name: 'burden_m') double? burdenM,
    @JsonKey(name: 'spacing_m') double? spacingM,
    @JsonKey(name: 'stemming_m') double? stemmingM,
    @JsonKey(name: 'target_p80_mm') double? targetP80Mm,
  }) = _NewBlastPassport;

  factory NewBlastPassport.fromJson(Map<String, dynamic> json) =>
      _$NewBlastPassportFromJson(json);
}
