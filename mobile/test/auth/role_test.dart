import 'package:flutter/widgets.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:zmetrics_mobile/core/auth/access_cubit.dart';
import 'package:zmetrics_mobile/core/auth/access_repository.dart';
import 'package:zmetrics_mobile/core/auth/auth_context.dart';
import 'package:zmetrics_mobile/core/auth/auth_user.dart';
import 'package:zmetrics_mobile/core/auth/quarry_access.dart';
import 'package:zmetrics_mobile/core/auth/role_level.dart';

class _FakeAccessRepo implements AccessRepository {
  _FakeAccessRepo(this.entries);
  final List<QuarryAccess> entries;
  @override
  Future<List<QuarryAccess>> myAccess() async => entries;
}

class _ThrowingAccessRepo implements AccessRepository {
  @override
  Future<List<QuarryAccess>> myAccess() async => throw Exception('404');
}

void main() {
  group('RoleLevel', () {
    test('maps realm roles and numeric levels', () {
      expect(RoleLevel.fromRealmRole('zmetrics-admin'), RoleLevel.admin);
      expect(RoleLevel.fromRealmRole('nope'), isNull);
      expect(RoleLevel.fromLevel(3), RoleLevel.blaster);
      expect(RoleLevel.fromLevel(99), RoleLevel.admin);
      expect(RoleLevel.fromLevel(0), RoleLevel.user);
    });

    test('AuthUser.maxRole from realm roles', () {
      const u = AuthUser(id: 'x', displayName: 'X', realmRoles: ['zmetrics-blaster']);
      expect(u.maxRole, RoleLevel.blaster);
    });
  });

  test('QuarryAccess JSON parses snake_case + derives RoleLevel', () {
    final a = QuarryAccess.fromJson({
      'quarry_id': 'q1',
      'quarry_name': 'Demo',
      'role_name': 'blaster',
      'role_level': 3,
    });
    expect(a.quarryId, 'q1');
    expect(a.role, RoleLevel.blaster);
  });

  group('AccessCubit', () {
    const user = AuthUser(id: 'u', displayName: 'U', realmRoles: ['zmetrics-user']);

    test('loads per-quarry roles', () async {
      final cubit = AccessCubit(_FakeAccessRepo(const [
        QuarryAccess(quarryId: 'qA', quarryName: 'A', roleName: 'blaster', roleLevel: 3),
        QuarryAccess(quarryId: 'qB', quarryName: 'B', roleName: 'user', roleLevel: 1),
      ]));
      await cubit.load(user);
      expect(cubit.state.usingFallback, isFalse);
      expect(cubit.state.roleFor('qA'), RoleLevel.blaster);
      expect(cubit.state.roleFor('qB'), RoleLevel.user);
      expect(cubit.state.roleFor('unknown'), RoleLevel.user);
      expect(cubit.state.isAdminAnywhere, isFalse);
      await cubit.close();
    });

    test('falls back to realm role when endpoint fails', () async {
      const admin = AuthUser(id: 'u', displayName: 'U', realmRoles: ['zmetrics-admin']);
      final cubit = AccessCubit(_ThrowingAccessRepo());
      await cubit.load(admin);
      expect(cubit.state.usingFallback, isTrue);
      expect(cubit.state.roleFor('anything'), RoleLevel.admin);
      expect(cubit.state.isAdminAnywhere, isTrue);
      await cubit.close();
    });
  });

  group('AuthContext per-quarry gating', () {
    Future<({bool manage, bool approve, bool adminAnywhere})> gate(
        WidgetTester tester, List<QuarryAccess> entries) async {
      final cubit = AccessCubit(_FakeAccessRepo(entries));
      await cubit.load(const AuthUser(id: 'u', displayName: 'U'));
      late bool manage, approve, adminAnywhere;
      await tester.pumpWidget(
        BlocProvider<AccessCubit>.value(
          value: cubit,
          child: Builder(builder: (ctx) {
            manage = ctx.canManageBlastingOn('qA');
            approve = ctx.canApproveOn('qA');
            adminAnywhere = ctx.isAdminAnywhere;
            return const SizedBox();
          }),
        ),
      );
      await cubit.close();
      return (manage: manage, approve: approve, adminAnywhere: adminAnywhere);
    }

    testWidgets('blaster on qA can manage but not approve', (t) async {
      final g = await gate(t, const [
        QuarryAccess(quarryId: 'qA', quarryName: 'A', roleName: 'blaster', roleLevel: 3),
      ]);
      expect(g.manage, isTrue);
      expect(g.approve, isFalse);
      expect(g.adminAnywhere, isFalse);
    });

    testWidgets('admin on qA can approve and is admin somewhere', (t) async {
      final g = await gate(t, const [
        QuarryAccess(quarryId: 'qA', quarryName: 'A', roleName: 'admin', roleLevel: 4),
      ]);
      expect(g.manage, isTrue);
      expect(g.approve, isTrue);
      expect(g.adminAnywhere, isTrue);
    });

    testWidgets('user with access only to other quarry cannot manage qA', (t) async {
      final g = await gate(t, const [
        QuarryAccess(quarryId: 'qB', quarryName: 'B', roleName: 'admin', roleLevel: 4),
      ]);
      expect(g.manage, isFalse); // no qA access
      expect(g.approve, isFalse);
      expect(g.adminAnywhere, isTrue); // admin on qB
    });
  });
}
