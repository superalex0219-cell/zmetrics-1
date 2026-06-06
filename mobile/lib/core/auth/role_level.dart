/// Per-quarry role hierarchy (rules/02-domain.md): user < surveyor < blaster < admin.
///
/// NOTE: the backend is the source of truth and enforces per-quarry access via
/// `QuarryUserAccess`. The client only uses this for **coarse UI gating** to
/// avoid obvious 403 dead-ends. The level here is derived from the JWT
/// `realm_access.roles` (global realm roles), which is an approximation of the
/// real per-quarry role — see TASK-backend-mobile-integration.md (per-quarry
/// role endpoint) for accurate gating.
enum RoleLevel {
  user(1),
  surveyor(2),
  blaster(3),
  admin(4);

  const RoleLevel(this.level);
  final int level;

  bool atLeast(RoleLevel other) => level >= other.level;

  /// Maps a numeric level (backend `role_level`, 1–4) to a [RoleLevel],
  /// defaulting to [user] for anything out of range.
  static RoleLevel fromLevel(int level) => switch (level) {
        >= 4 => RoleLevel.admin,
        3 => RoleLevel.blaster,
        2 => RoleLevel.surveyor,
        _ => RoleLevel.user,
      };

  /// Maps a Keycloak realm role name (e.g. `zmetrics-blaster`) to a level.
  static RoleLevel? fromRealmRole(String role) => switch (role) {
        'zmetrics-admin' => RoleLevel.admin,
        'zmetrics-blaster' => RoleLevel.blaster,
        'zmetrics-surveyor' => RoleLevel.surveyor,
        'zmetrics-user' => RoleLevel.user,
        _ => null,
      };

  /// Highest level among the given realm role names, defaulting to [user].
  static RoleLevel highestOf(Iterable<String> realmRoles) {
    var best = RoleLevel.user;
    for (final r in realmRoles) {
      final level = fromRealmRole(r);
      if (level != null && level.level > best.level) best = level;
    }
    return best;
  }
}
