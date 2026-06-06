import '../network/token_provider.dart';
import 'auth_user.dart';
import 'oidc_service.dart';

/// Sign-in / sign-out, independent of the concrete auth mechanism.
abstract class AuthRepository {
  /// Returns the user if a valid session can be restored, else `null`.
  Future<AuthUser?> restore();

  /// Interactive sign-in. [username]/[password] are used by credential-based
  /// flows (dev ROPC); redirect-based flows (OIDC) ignore them. Throws on failure.
  Future<AuthUser> signIn({String? username, String? password});

  Future<void> signOut();
}

/// Mock auth used while Keycloak is not connected (config.useMockServices).
/// Provides a one-tap fake sign-in and a constant bearer token.
class MockAuthRepository implements AuthRepository, TokenProvider {
  AuthUser? _user;

  static const _mockUser = AuthUser(
    id: 'mock-sub-0001',
    displayName: 'Mock Admin',
    email: 'admin@example.test',
    realmRoles: ['zmetrics-admin'],
  );

  @override
  Future<AuthUser?> restore() async => _user;

  @override
  Future<AuthUser> signIn({String? username, String? password}) async {
    _user = _mockUser;
    return _mockUser;
  }

  @override
  Future<void> signOut() async => _user = null;

  @override
  Future<String?> currentAccessToken() async =>
      _user == null ? null : 'mock-access-token';

  @override
  Future<String?> refreshAccessToken() async =>
      _user == null ? null : 'mock-access-token';
}

/// Real auth via Keycloak OIDC.
class OidcAuthRepository implements AuthRepository {
  OidcAuthRepository(this._oidc);

  final OidcService _oidc;

  @override
  Future<AuthUser?> restore() async {
    final token = await _oidc.currentAccessToken();
    if (token == null || token.isEmpty) return null;
    // A token exists; a full implementation would decode the persisted ID
    // token for display claims. Kept minimal here.
    return const AuthUser(id: 'restored', displayName: 'Signed-in user');
  }

  @override
  Future<AuthUser> signIn({String? username, String? password}) async {
    final result = await _oidc.signIn();
    if (result == null) {
      throw Exception('Sign-in was cancelled or failed.');
    }
    return AuthUser(
      id: result.sub,
      displayName: result.name ?? result.email ?? result.sub,
      email: result.email,
    );
  }

  @override
  Future<void> signOut() => _oidc.signOut();
}
