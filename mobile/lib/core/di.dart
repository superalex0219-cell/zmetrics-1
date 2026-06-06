import 'package:flutter/foundation.dart';

import '../features/capture/data/capture_repository.dart';
import '../features/capture/data/device_repository.dart';
import '../features/passport/data/passport_repository.dart';
import '../features/quarries/data/quarry_repository.dart';
import '../features/report/data/report_repository.dart';
import '../shared/offline/sync_manager.dart';
import '../shared/offline/sync_processor.dart';
import 'auth/access_repository.dart';
import 'auth/auth_event_bus.dart';
import 'auth/auth_repository.dart';
import 'auth/dev_password_auth_repository.dart';
import 'auth/oidc_service.dart';
import 'config.dart';
import 'dev/dev_seed_service.dart';
import 'network/api_client.dart';
import 'network/token_provider.dart';

/// Composition root. Wires either mock stubs (config.useMockServices) or the
/// live backend-backed implementations. Constructed once in main() and exposed
/// to the widget tree via RepositoryProvider.
class AppDependencies {
  AppDependencies._({
    required this.config,
    required this.authRepository,
    required this.syncManager,
    required this.quarryRepository,
    required this.passportRepository,
    required this.reportRepository,
    required this.captureRepository,
    required this.deviceRepository,
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
  final DeviceRepository deviceRepository;
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

    if (config.useMockServices) {
      final capture = MockCaptureRepository(syncManager);
      final processor = SyncProcessor(syncManager, {
        kOpCreateCaptureSession: (_) async {},
      });
      return AppDependencies._(
        config: config,
        authRepository: MockAuthRepository(),
        syncManager: syncManager,
        quarryRepository: MockQuarryRepository(),
        passportRepository: MockPassportRepository(),
        reportRepository: MockReportRepository(),
        captureRepository: capture,
        deviceRepository: MockDeviceRepository(),
        syncProcessor: processor,
        devSeedService: MockDevSeedService(),
        authEventBus: authEventBus,
        accessRepository: MockAccessRepository(),
      );
    }

    // Live backend wiring — OIDC PKCE via flutter_appauth.
    // OidcService implements TokenProvider; OidcAuthRepository implements AuthRepository.
    final oidcService = OidcService(config);
    final auth = OidcAuthRepository(oidcService);
    final TokenProvider tokens = oidcService;
    final dio = ApiClient(
      config,
      tokens,
      onAuthFailure: authEventBus.notifySessionExpired,
    ).dio;

    final remoteCapture = RemoteCaptureRepository(dio, syncManager);
    final processor = SyncProcessor(syncManager, {
      kOpCreateCaptureSession: (upload) =>
          remoteCapture.postQueuedCaptureSession(
              upload.idempotencyKey, upload.payload),
    });

    return AppDependencies._(
      config: config,
      authRepository: auth,
      syncManager: syncManager,
      quarryRepository: RemoteQuarryRepository(dio),
      passportRepository: RemotePassportRepository(dio),
      reportRepository: RemoteReportRepository(dio),
      captureRepository: remoteCapture,
      deviceRepository: RemoteDeviceRepository(dio),
      syncProcessor: processor,
      devSeedService: RemoteDevSeedService(dio),
      authEventBus: authEventBus,
      accessRepository: RemoteAccessRepository(dio),
    );
  }
}
