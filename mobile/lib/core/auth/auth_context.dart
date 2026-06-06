import 'package:flutter/widgets.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'access_cubit.dart';
import 'role_level.dart';

/// Per-quarry role gating for the UI, backed by [AccessCubit]
/// (`GET /me/access`, GAP-4). The backend remains authoritative and still
/// enforces access (403); these accessors only hide obvious dead-ends.
///
/// Uses `watch` so gated widgets rebuild once per-quarry roles finish loading.
extension AuthContext on BuildContext {
  RoleLevel roleForQuarry(String quarryId) =>
      watch<AccessCubit>().state.roleFor(quarryId);

  /// Blaster+ on this quarry: create/submit/revise passports, create sections,
  /// export reports.
  bool canManageBlastingOn(String quarryId) =>
      roleForQuarry(quarryId).atLeast(RoleLevel.blaster);

  /// Admin on this quarry: approve/complete passports.
  bool canApproveOn(String quarryId) =>
      roleForQuarry(quarryId).atLeast(RoleLevel.admin);

  /// Admin on at least one quarry: may create a new quarry (mobile-auth-notes §5).
  bool get isAdminAnywhere => watch<AccessCubit>().state.isAdminAnywhere;
}
