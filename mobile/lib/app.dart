import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import 'core/auth/access_cubit.dart';
import 'core/auth/auth_cubit.dart';
import 'core/config.dart';
import 'core/di.dart';
import 'core/dev/dev_seed_service.dart';
import 'core/router.dart';
import 'features/capture/data/capture_repository.dart';
import 'features/capture/data/device_repository.dart';
import 'features/passport/data/passport_repository.dart';
import 'features/quarries/data/quarry_repository.dart';
import 'features/report/data/report_repository.dart';
import 'shared/offline/sync_cubit.dart';

class ZMetricsApp extends StatefulWidget {
  const ZMetricsApp({super.key, required this.deps});

  final AppDependencies deps;

  @override
  State<ZMetricsApp> createState() => _ZMetricsAppState();
}

class _ZMetricsAppState extends State<ZMetricsApp> {
  late final AuthCubit _authCubit;
  late final AccessCubit _accessCubit;
  late final SyncCubit _syncCubit;
  late final GoRouter _router;
  StreamSubscription<void>? _sessionExpirySub;
  StreamSubscription<AuthState>? _authStateSub;

  @override
  void initState() {
    super.initState();
    _authCubit = AuthCubit(widget.deps.authRepository);
    _accessCubit = AccessCubit(widget.deps.accessRepository);
    _syncCubit = SyncCubit(
      syncManager: widget.deps.syncManager,
      processor: widget.deps.syncProcessor,
    )..start();
    // Load per-quarry roles on sign-in; clear them on sign-out.
    _authStateSub = _authCubit.stream.listen((s) {
      if (s is Authenticated) {
        _accessCubit.load(s.user);
      } else if (s is Unauthenticated) {
        _accessCubit.clear();
      }
    });
    // A failed token refresh (401) signs the user out → router sends to /login.
    _sessionExpirySub = widget.deps.authEventBus.onSessionExpired
        .listen((_) => _authCubit.handleSessionExpired());
    _authCubit.restore();
    _router = buildRouter(_authCubit);
  }

  @override
  void dispose() {
    _authStateSub?.cancel();
    _sessionExpirySub?.cancel();
    _accessCubit.close();
    _authCubit.close();
    _syncCubit.close();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final deps = widget.deps;
    return MultiRepositoryProvider(
      providers: [
        RepositoryProvider<AppConfig>.value(value: deps.config),
        RepositoryProvider<QuarryRepository>.value(value: deps.quarryRepository),
        RepositoryProvider<PassportRepository>.value(value: deps.passportRepository),
        RepositoryProvider<ReportRepository>.value(value: deps.reportRepository),
        RepositoryProvider<CaptureRepository>.value(value: deps.captureRepository),
        RepositoryProvider<DeviceRepository>.value(value: deps.deviceRepository),
        RepositoryProvider<DevSeedService>.value(value: deps.devSeedService),
      ],
      child: MultiBlocProvider(
        providers: [
          BlocProvider<AuthCubit>.value(value: _authCubit),
          BlocProvider<AccessCubit>.value(value: _accessCubit),
          BlocProvider<SyncCubit>.value(value: _syncCubit),
        ],
        child: MaterialApp.router(
          title: 'ZMetrics',
          theme: ThemeData(
            colorScheme: ColorScheme.fromSeed(
              seedColor: const Color(0xFF0F766E),
            ),
            useMaterial3: true,
            appBarTheme: const AppBarTheme(
              backgroundColor: Color(0xFF17202A),
              foregroundColor: Colors.white,
              iconTheme: IconThemeData(color: Colors.white),
              actionsIconTheme: IconThemeData(color: Colors.white),
            ),
          ),
          routerConfig: _router,
        ),
      ),
    );
  }
}
