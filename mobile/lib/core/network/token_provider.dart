/// Abstraction the network layer uses to obtain and refresh access tokens,
/// without depending on the concrete auth implementation (OIDC vs mock).
abstract class TokenProvider {
  /// Current access token, or `null` if not authenticated.
  Future<String?> currentAccessToken();

  /// Attempts to refresh the access token. Returns the new token, or `null`
  /// if refresh failed (caller should treat this as logged-out).
  Future<String?> refreshAccessToken();
}
