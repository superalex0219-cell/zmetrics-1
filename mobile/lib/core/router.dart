import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../features/auth/presentation/login_screen.dart';
import '../features/capture/application/capture_cubit.dart';
import '../features/capture/data/capture_repository.dart';
import '../features/capture/data/device_repository.dart';
import '../features/capture/presentation/capture_screen.dart';
import '../features/passport/application/passport_detail_cubit.dart';
import '../features/passport/application/passport_list_cubit.dart';
import '../features/passport/data/passport_repository.dart';
import '../features/passport/presentation/passport_create_screen.dart';
import '../features/passport/presentation/passport_detail_screen.dart';
import '../features/passport/presentation/passport_list_screen.dart';
import '../features/quarries/application/quarries_cubit.dart';
import '../features/quarries/application/sections_cubit.dart';
import '../features/quarries/data/quarry_repository.dart';
import '../features/quarries/presentation/quarries_screen.dart';
import '../features/quarries/presentation/sections_screen.dart';
import '../features/report/application/report_cubit.dart';
import '../features/report/application/reports_list_cubit.dart';
import '../features/report/data/report_repository.dart';
import '../features/report/presentation/report_screen.dart';
import '../features/report/presentation/reports_list_screen.dart';
import 'auth/auth_cubit.dart';

/// Bridges a [Stream] (bloc state changes) to the [Listenable] go_router wants.
class GoRouterRefreshStream extends ChangeNotifier {
  GoRouterRefreshStream(Stream<dynamic> stream) {
    notifyListeners();
    _sub = stream.asBroadcastStream().listen((_) => notifyListeners());
  }

  late final StreamSubscription<dynamic> _sub;

  @override
  void dispose() {
    _sub.cancel();
    super.dispose();
  }
}

GoRouter buildRouter(AuthCubit authCubit) {
  return GoRouter(
    initialLocation: '/',
    refreshListenable: GoRouterRefreshStream(authCubit.stream),
    redirect: (context, state) {
      final authed = authCubit.state is Authenticated;
      final atLogin = state.matchedLocation == '/login';
      // While restoring (AuthInitial/AuthInProgress) treat as unauthenticated.
      if (!authed) return atLogin ? null : '/login';
      if (atLogin) return '/';
      return null;
    },
    routes: [
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/',
        builder: (context, state) => BlocProvider(
          create: (ctx) =>
              QuarriesCubit(ctx.read<QuarryRepository>())..load(),
          child: const QuarriesScreen(),
        ),
      ),
      GoRoute(
        path: '/quarries/:qid',
        builder: (context, state) {
          final qid = state.pathParameters['qid']!;
          return BlocProvider(
            create: (ctx) =>
                SectionsCubit(ctx.read<QuarryRepository>(), qid)..load(),
            child: SectionsScreen(quarryId: qid),
          );
        },
      ),
      GoRoute(
        path: '/quarries/:qid/reports',
        builder: (context, state) {
          final qid = state.pathParameters['qid']!;
          return BlocProvider(
            create: (ctx) =>
                ReportsListCubit(ctx.read<ReportRepository>(), qid)..load(),
            child: const ReportsListScreen(),
          );
        },
      ),
      GoRoute(
        path: '/quarries/:qid/passports',
        builder: (context, state) {
          final qid = state.pathParameters['qid']!;
          return BlocProvider(
            create: (ctx) =>
                PassportListCubit(ctx.read<PassportRepository>(), qid)..load(),
            child: PassportListScreen(quarryId: qid),
          );
        },
      ),
      GoRoute(
        path: '/quarries/:qid/passports/new',
        builder: (context, state) {
          final qid = state.pathParameters['qid']!;
          return BlocProvider(
            create: (ctx) =>
                PassportListCubit(ctx.read<PassportRepository>(), qid),
            child: PassportCreateScreen(quarryId: qid),
          );
        },
      ),
      GoRoute(
        path: '/quarries/:qid/passports/:pid',
        builder: (context, state) {
          final qid = state.pathParameters['qid']!;
          final pid = state.pathParameters['pid']!;
          return BlocProvider(
            create: (ctx) => PassportDetailCubit(
                ctx.read<PassportRepository>(), qid, pid)
              ..load(),
            child: PassportDetailScreen(quarryId: qid),
          );
        },
      ),
      GoRoute(
        path: '/quarries/:qid/passports/:pid/captures',
        builder: (context, state) {
          final qid = state.pathParameters['qid']!;
          final pid = state.pathParameters['pid']!;
          return BlocProvider(
            create: (ctx) => CaptureCubit(
              ctx.read<CaptureRepository>(),
              ctx.read<DeviceRepository>(),
              qid,
              pid,
            )..load(),
            child: CaptureScreen(quarryId: qid),
          );
        },
      ),
      GoRoute(
        path: '/reports/:rid',
        builder: (context, state) {
          final rid = state.pathParameters['rid']!;
          return BlocProvider(
            create: (ctx) =>
                ReportCubit(ctx.read<ReportRepository>(), rid)..load(),
            child: const ReportScreen(),
          );
        },
      ),
    ],
  );
}
