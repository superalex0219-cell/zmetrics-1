import 'package:freezed_annotation/freezed_annotation.dart';

import 'role_level.dart';

part 'auth_user.freezed.dart';
part 'auth_user.g.dart';

/// The locally-held identity of the signed-in user.
///
/// SECURITY: this never carries the raw access/refresh tokens — those live
/// only in flutter_secure_storage (security.md).
@freezed
class AuthUser with _$AuthUser {
  const AuthUser._();

  const factory AuthUser({
    required String id,
    required String displayName,
    String? email,
    /// Keycloak `realm_access.roles` (e.g. `zmetrics-blaster`). Used for coarse
    /// UI gating only — the backend enforces the real per-quarry access.
    @Default(<String>[]) List<String> realmRoles,
  }) = _AuthUser;

  factory AuthUser.fromJson(Map<String, dynamic> json) =>
      _$AuthUserFromJson(json);

  /// Highest role this user holds (approximation; see [RoleLevel]).
  RoleLevel get maxRole => RoleLevel.highestOf(realmRoles);
}
