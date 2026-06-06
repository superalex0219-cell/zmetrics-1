// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'site_section.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$SiteSectionImpl _$$SiteSectionImplFromJson(Map<String, dynamic> json) =>
    _$SiteSectionImpl(
      id: json['id'] as String,
      quarryId: json['quarry_id'] as String,
      name: json['name'] as String,
      blockNumber: json['block_number'] as String?,
    );

Map<String, dynamic> _$$SiteSectionImplToJson(_$SiteSectionImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'quarry_id': instance.quarryId,
      'name': instance.name,
      'block_number': instance.blockNumber,
    };
