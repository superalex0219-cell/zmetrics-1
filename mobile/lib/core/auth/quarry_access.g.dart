// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'quarry_access.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$QuarryAccessImpl _$$QuarryAccessImplFromJson(Map<String, dynamic> json) =>
    _$QuarryAccessImpl(
      quarryId: json['quarry_id'] as String,
      quarryName: json['quarry_name'] as String,
      roleName: json['role_name'] as String,
      roleLevel: (json['role_level'] as num).toInt(),
    );

Map<String, dynamic> _$$QuarryAccessImplToJson(_$QuarryAccessImpl instance) =>
    <String, dynamic>{
      'quarry_id': instance.quarryId,
      'quarry_name': instance.quarryName,
      'role_name': instance.roleName,
      'role_level': instance.roleLevel,
    };
