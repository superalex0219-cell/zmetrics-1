/// Application-wide configuration.
///
/// Values are compile-time overridable via `--dart-define`, e.g.:
///   flutter run --dart-define=ZM_API_BASE_URL=http://10.0.2.2:8000 \
///               --dart-define=ZM_USE_MOCKS=false
///
/// Defaults are tuned for local development with the backend stack NOT yet
/// wired up: [useMockServices] is `true`, so every repository resolves to its
/// in-memory mock implementation and the app runs standalone (no backend,
/// Keycloak, MinIO or worker required).
class AppConfig {
  const AppConfig({
    required this.apiBaseUrl,
    required this.useMockServices,
    required this.keycloakIssuer,
    required this.keycloakClientId,
    required this.keycloakRedirectUri,
  });

  /// Base URL of the FastAPI backend (no trailing slash).
  final String apiBaseUrl;

  /// When `true`, the DI container binds mock repositories and a mock auth
  /// flow. This is the default until the backend / Keycloak are connected.
  final bool useMockServices;

  final String keycloakIssuer;
  final String keycloakClientId;
  final String keycloakRedirectUri;

  factory AppConfig.fromEnvironment() {
    return const AppConfig(
      apiBaseUrl: String.fromEnvironment(
        'ZM_API_BASE_URL',
        defaultValue: 'http://localhost:8000',
      ),
      useMockServices: bool.fromEnvironment(
        'ZM_USE_MOCKS',
        defaultValue: true,
      ),
      keycloakIssuer: String.fromEnvironment(
        'ZM_KC_ISSUER',
        defaultValue: 'http://localhost:8080/realms/zmetrics',
      ),
      keycloakClientId: String.fromEnvironment(
        'ZM_KC_CLIENT_ID',
        defaultValue: 'zmetrics-mobile',
      ),
      keycloakRedirectUri: String.fromEnvironment(
        'ZM_KC_REDIRECT_URI',
        defaultValue: 'zmetrics://callback',
      ),
    );
  }
}
