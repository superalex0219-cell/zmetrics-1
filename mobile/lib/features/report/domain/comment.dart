import 'package:freezed_annotation/freezed_annotation.dart';

part 'comment.freezed.dart';
part 'comment.g.dart';

/// Comment on a [Recommendation].
@freezed
class Comment with _$Comment {
  const factory Comment({
    required String id,
    @JsonKey(name: 'recommendation_id') required String recommendationId,
    @JsonKey(name: 'author_name') required String authorName,
    required String body,
    @JsonKey(name: 'created_at') DateTime? createdAt,
  }) = _Comment;

  factory Comment.fromJson(Map<String, dynamic> json) =>
      _$CommentFromJson(json);
}
