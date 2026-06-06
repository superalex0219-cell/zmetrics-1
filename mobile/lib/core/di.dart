import 'package:flutter/foundation.dart';

import '../features/capture/data/capture_repository.dart';
import '../features/passport/data/passport_repository.dart';
import '../features/quarries/data/quarry_repository.dart';
import '../features/report/data/report_repository.dart';
import '../shared/offline/sync_manager.dart';
import '../shared/offline/sync_processor.dart';
import 'auth/access_repository.dart';
import 'auth/auth_event_bus.dart';
import 'auth/auth_repository.dart';
import 'auth/dev_password_auth_repository.dart';
import 'config.dart';
import 'dev/dev_seed_service.dart';
import 'network/api_client.dart';
import 'network/token_provider.dart';

/// Composition root. Wires either mock stubs (config.useMockServices) or the
/// live backend-backed implementations. Constructed once in main() and exposed
/// to the widget tree via RepositoryProvider.
///
/// NOTE: the Capture feature stays on the mock stub even in backend mode — the
/// real capture-session flow needs a blast-event + device + calibration chain
/// that has no client UI yet (see docs/handoffs/TASK-backend-mobile-integration.md §6).
class AppDependencies {
  AppDependencies._({
    required this.config,
    required this.authRepository,
    required this.syncManager,
    required this.quarryRepository,
    required this.passportRepository,
    required this.reportRepository,
    required this.captureRepository,
    required this.syncProcessor,
    required this.devSeedService,
    required this.authEventBus,
    required this.accessRepository,
  });

  final AppConfig config;
  final AuthRepository authRepository;
  final AccessRepository accessRepository;
  final SyncManager syncManager;
  final QuarryRepository quarryRepository;
  final PassportRepository passportRepository;
  final ReportRepository reportRepository;
  final CaptureRepository captureRepository;
  final SyncProcessor syncProcessor;
  final DevSeedService devSeedService;

  /// Fires when a session expires (failed token refresh on a 401).
  final AuthEventBus authEventBus;

  factory AppDependencies.create([AppConfig? configOverride]) {
    final config = configOverride ?? AppConfig.fromEnvironment();
    final authEventBus = AuthEventBus();

    // sqflite has no web backend → use the in-memory queue on web.
    final SyncManager syncManager =
        kIsWeb ? InMemorySyncManager() : SqfliteSyncManager();

    // Capture is always the mock stub for now (see class note).
    final capture = MockCaptureRepository(syncManager);
    final processor = SyncProcessor(syncManager, {
      kOpCreateCaptureSession: (_) async {},
    });

    if (config.useMockServices) {
      return AppDependencies._(
        config: config,
        authRepository: MockAuthRepository(),
        syncManager: syncManager,
        quarryRepository: MockQuarryRepository(),
        passportRepository: MockPassportRepository(),
        reportRepository: MockReportRepository(),
        captureRepository: capture,
        syncProcessor: processor,
        devSeedService: MockDevSeedService(),
        authEventBus: authEventBus,
        accessRepository: MockAccessRepository(),
      );
    }

    // Live backend wiring. Auth is dev ROPC (web-friendly, public client) and
    // also serves as the bearer-token provider for the Dio interceptor.
    final auth = DevPasswordAuthRepository(config);
    final TokenProvider tokens = auth;
    final dio = ApiClient(
      config,
      tokens,
      onAuthFailure: authEventBus.notifySessionExpired,
    ).dio;
    return AppDependencies._(
      config: config,
      authRepository: auth,
      syncManager: syncManager,
      quarryRepository: RemoteQuarryRepository(dio),
      passportRepository: RemotePassportRepository(dio),
      reportRepository: RemoteReportRepository(dio),
      captureRepository: capture,
      syncProcessor: processor,
      devSeedService: RemoteDevSeedService(dio),
      authEventBus: authEventBus,
      accessRepository: RemoteAccessRepository(dio),
    );
  }
}
