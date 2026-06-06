// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'comment.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$CommentImpl _$$CommentImplFromJson(Map<String, dynamic> json) =>
    _$CommentImpl(
      id: json['id'] as String,
      recommendationId: json['recommendation_id'] as String,
      authorName: json['author_name'] as String,
      body: json['body'] as String,
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$$CommentImplToJson(_$CommentImpl instance) =>
    <String, dynamic>{
      'id': instance.id,
      'recommendation_id': instance.recommendationId,
      'author_name': instance.authorName,
      'body': instance.body,
      'created_at': instance.createdAt?.toIso8601String(),
    };
