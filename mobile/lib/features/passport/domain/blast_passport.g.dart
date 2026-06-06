// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'blast_passport.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$BlastPassportImpl _$$BlastPassportImplFromJson(Map<String, dynamic> json) =>
    _$BlastPassportImpl(
      id: json['id'] as String,
      siteSectionId: json['site_section_id'] as String,
      status: $enumDecode(_$PassportStatusEnumMap, json['status']),
      revisionNumber: (json['revision_number'] as num?)?.toInt() ?? 1,
      supersededById: json['superseded_by_id'] as String?,
      explosiveType: json['explosive_type'] as String?,
      totalExplosiveKg: (json['total_explosive_kg'] as num?)?.toDouble(),
      holeDiameterMm: (json['hole_diameter_mm'] as num?)?.toDouble(),
      holeDepthM: (json['hole_depth_m'] as num?)?.toDouble(),
      burdenM: (json['burden_m'] as num?)?.toDouble(),
      spacingM: (json['spacing_m'] as num?)?.toDouble(),
      stemmingM: (json['stemming_m'] as num?)?.toDouble(),
      targetP80Mm: (json['target_p80_mm'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$$BlastPassportImplToJson(_$BlastPassportImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'site_section_id': instance.siteSectionId,
      'status': _$PassportStatusEnumMap[instance.status]!,
      'revision_number': instance.revisionNumber,
      'superseded_by_id': instance.supersededById,
      'explosive_type': instance.explosiveType,
      'total_explosive_kg': instance.totalExplosiveKg,
      'hole_diameter_mm': instance.holeDiameterMm,
      'hole_depth_m': instance.holeDepthM,
      'burden_m': instance.burdenM,
      'spacing_m': instance.spacingM,
      'stemming_m': instance.stemmingM,
      'target_p80_mm': instance.targetP80Mm,
    };

const _$PassportStatusEnumMap = {
  PassportStatus.draft: 'draft',
  PassportStatus.submitted: 'submitted',
  PassportStatus.approved: 'approved',
  PassportStatus.active: 'active',
  PassportStatus.completed: 'completed',
  PassportStatus.cancelled: 'cancelled',
  PassportStatus.superseded: 'superseded',
};

_$NewBlastPassportImpl _$$NewBlastPassportImplFromJson(
        Map<String, dynamic> json) =>
    _$NewBlastPassportImpl(
      siteSectionId: json['site_section_id'] as String,
      explosiveType: json['explosive_type'] as String?,
      totalExplosiveKg: (json['total_explosive_kg'] as num?)?.toDouble(),
      holeDiameterMm: (json['hole_diameter_mm'] as num?)?.toDouble(),
      holeDepthM: (json['hole_depth_m'] as num?)?.toDouble(),
      burdenM: (json['burden_m'] as num?)?.toDouble(),
      spacingM: (json['spacing_m'] as num?)?.toDouble(),
      stemmingM: (json['stemming_m'] as num?)?.toDouble(),
      targetP80Mm: (json['target_p80_mm'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$$NewBlastPassportImplToJson(
        _$NewBlastPassportImpl instance) =>
    <String, dynamic>{
      'site_section_id': instance.siteSectionId,
      'explosive_type': instance.explosiveType,
      'total_explosive_kg': instance.totalExplosiveKg,
      'hole_diameter_mm': instance.holeDiameterMm,
      'hole_depth_m': instance.holeDepthM,
      'burden_m': instance.burdenM,
      'spacing_m': instance.spacingM,
      'stemming_m': instance.stemmingM,
      'target_p80_mm': instance.targetP80Mm,
    };
