// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'quarry.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$QuarryImpl _$$QuarryImplFromJson(Map<String, dynamic> json) => _$QuarryImpl(
      id: json['id'] as String,
      name: json['name'] as String,
      latitude: (json['latitude'] as num?)?.toDouble(),
      longitude: (json['longitude'] as num?)?.toDouble(),
    );

Map<String, dynamic> _$$QuarryImplToJson(_$QuarryImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'latitude': instance.latitude,
      'longitude': instance.longitude,
    };
