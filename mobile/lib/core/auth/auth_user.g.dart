// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'auth_user.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$AuthUserImpl _$$AuthUserImplFromJson(Map<String, dynamic> json) =>
    _$AuthUserImpl(
      id: json['id'] as String,
      displayName: json['displayName'] as String,
      email: json['email'] as String?,
      realmRoles: (json['realmRoles'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const <String>[],
    );

Map<String, dynamic> _$$AuthUserImplToJson(_$AuthUserImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'displayName': instance.displayName,
      'email': instance.email,
      'realmRoles': instance.realmRoles,
    };
