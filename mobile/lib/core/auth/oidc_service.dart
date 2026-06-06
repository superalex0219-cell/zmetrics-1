import 'dart:convert';

import 'package:flutter_appauth/flutter_appauth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config.dart';
import '../network/token_provider.dart';

const _kTokenKey = 'access_token';
const _kRefreshTokenKey = 'refresh_token';

/// Result of a successful sign-in: the OIDC subject + token already persisted.
class OidcSignInResult {
  const OidcSignInResult({required this.sub, this.email, this.name});
  final String sub;
  final String? email;
  final String? name;
}

/// Keycloak OIDC (PKCE) integration. Tokens are stored in secure storage only
/// and are never logged (security.md).
///
/// Implements [TokenProvider] so the Dio [AuthInterceptor] can read/refresh
/// tokens without depending on this class directly.
class OidcService implements TokenProvider {
  OidcService(this._config, {FlutterAppAuth? appAuth, FlutterSecureStorage? storage})
      : _appAuth = appAuth ?? const FlutterAppAuth(),
        _storage = storage ?? const FlutterSecureStorage();

  final AppConfig _config;
  final FlutterAppAuth _appAuth;
  final FlutterSecureStorage _storage;

  Future<OidcSignInResult?> signIn() async {
    final result = await _appAuth.authorizeAndExchangeCode(
      AuthorizationTokenRequest(
        _config.keycloakClientId,
        _config.keycloakRedirectUri,
        issuer: _config.keycloakIssuer,
        scopes: const ['openid', 'profile', 'email'],
      ),
    );
    final accessToken = result?.accessToken;
    if (accessToken == null) return null;

    await _storage.write(key: _kTokenKey, value: accessToken);
    await _storage.write(key: _kRefreshTokenKey, value: result!.refreshToken);

    final claims = result.idToken == null
        ? const <String, dynamic>{}
        : _decodeIdTokenClaims(result.idToken!);
    return OidcSignInResult(
      sub: (claims['sub'] as String?) ?? 'unknown',
      email: claims['email'] as String?,
      name: (claims['name'] ?? claims['preferred_username']) as String?,
    );
  }

  @override
  Future<String?> currentAccessToken() => _storage.read(key: _kTokenKey);

  @override
  Future<String?> refreshAccessToken() async {
    final refreshToken = await _storage.read(key: _kRefreshTokenKey);
    if (refreshToken == null) return null;
    try {
      final result = await _appAuth.token(
        TokenRequest(
          _config.keycloakClientId,
          _config.keycloakRedirectUri,
          issuer: _config.keycloakIssuer,
          refreshToken: refreshToken,
          scopes: const ['openid', 'profile', 'email'],
        ),
      );
      if (result?.accessToken == null) return null;
      await _storage.write(key: _kTokenKey, value: result!.accessToken);
      if (result.refreshToken != null) {
        await _storage.write(key: _kRefreshTokenKey, value: result.refreshToken);
      }
      return result.accessToken;
    } catch (_) {
      // Refresh failed → treat as logged out; do not log token material.
      return null;
    }
  }

  Future<void> signOut() async {
    await _storage.delete(key: _kTokenKey);
    await _storage.delete(key: _kRefreshTokenKey);
  }

  /// Decodes (without verifying) the ID token payload for display claims only.
  /// Signature verification is the backend's responsibility on each API call.
  Map<String, dynamic> _decodeIdTokenClaims(String idToken) {
    try {
      final parts = idToken.split('.');
      if (parts.length != 3) return const {};
      final payload = parts[1];
      final normalized = base64Url.normalize(payload);
      final decoded = utf8.decode(base64Url.decode(normalized));
      return jsonDecode(decoded) as Map<String, dynamic>;
    } catch (_) {
      return const {};
    }
  }
}
