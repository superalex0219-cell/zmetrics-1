import 'package:freezed_annotation/freezed_annotation.dart';

import 'role_level.dart';

part 'quarry_access.freezed.dart';
part 'quarry_access.g.dart';

/// One entry from `GET /api/v1/me/access` — the caller's effective role on a
/// quarry they have active (non-revoked) access to.
@freezed
class QuarryAccess with _$QuarryAccess {
  const QuarryAccess._();

  const factory QuarryAccess({
    @JsonKey(name: 'quarry_id') required String quarryId,
    @JsonKey(name: 'quarry_name') required String quarryName,
    @JsonKey(name: 'role_name') required String roleName,
    @JsonKey(name: 'role_level') required int roleLevel,
  }) = _QuarryAccess;

  factory QuarryAccess.fromJson(Map<String, dynamic> json) =>
      _$QuarryAccessFromJson(json);

  RoleLevel get role => RoleLevel.fromLevel(roleLevel);
}
