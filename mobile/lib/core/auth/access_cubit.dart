import 'package:flutter_bloc/flutter_bloc.dart';

import 'access_repository.dart';
import 'auth_user.dart';
import 'quarry_access.dart';
import 'role_level.dart';

/// Holds the caller's per-quarry roles for UI gating.
///
/// Resilience: if `GET /me/access` is unavailable (e.g. the backend image
/// predates GAP-4 and returns 404), we fall back to the coarse realm-role from
/// the JWT so gating still works. The backend remains authoritative (403).
class AccessState {
  const AccessState({
    this.byQuarry = const {},
    this.fallbackRole = RoleLevel.user,
    this.loaded = false,
    this.usingFallback = false,
  });

  final Map<String, RoleLevel> byQuarry;
  final RoleLevel fallbackRole;
  final bool loaded;
  final bool usingFallback;

  /// Effective role on [quarryId]. Uses precise per-quarry data when available,
  /// otherwise the realm-role fallback.
  RoleLevel roleFor(String quarryId) =>
      usingFallback ? fallbackRole : (byQuarry[quarryId] ?? RoleLevel.user);

  bool get isAdminAnywhere => usingFallback
      ? fallbackRole.atLeast(RoleLevel.admin)
      : byQuarry.values.any((r) => r.atLeast(RoleLevel.admin));

  AccessState copyWith({
    Map<String, RoleLevel>? byQuarry,
    RoleLevel? fallbackRole,
    bool? loaded,
    bool? usingFallback,
  }) =>
      AccessState(
        byQuarry: byQuarry ?? this.byQuarry,
        fallbackRole: fallbackRole ?? this.fallbackRole,
        loaded: loaded ?? this.loaded,
        usingFallback: usingFallback ?? this.usingFallback,
      );
}

class AccessCubit extends Cubit<AccessState> {
  AccessCubit(this._repo) : super(const AccessState());

  final AccessRepository _repo;

  /// Loads per-quarry roles after sign-in. [user] provides the realm-role
  /// fallback used if the endpoint is unavailable.
  Future<void> load(AuthUser user) async {
    final fallback = user.maxRole;
    try {
      final entries = await _repo.myAccess();
      emit(AccessState(
        byQuarry: {for (final QuarryAccess e in entries) e.quarryId: e.role},
        fallbackRole: fallback,
        loaded: true,
        usingFallback: false,
      ));
    } catch (_) {
      // Endpoint missing/unreachable → degrade to realm-role gating.
      emit(AccessState(
        fallbackRole: fallback,
        loaded: true,
        usingFallback: true,
      ));
    }
  }

  void clear() => emit(const AccessState());
}
