import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../config.dart';
import '../network/token_provider.dart';
import 'auth_repository.dart';
import 'auth_user.dart';
import 'jwt_decode.dart';

const _kAccessKey = 'access_token';
const _kRefreshKey = 'refresh_token';

/// Dev/web auth via Keycloak Resource-Owner-Password-Credentials (ROPC) against
/// the **public** `zmetrics-mobile` client (no client secret, CORS allowed).
///
/// This is the dev/web path; production native uses OIDC PKCE ([OidcService]).
/// Tokens live only in [FlutterSecureStorage] and are never logged (security.md).
class DevPasswordAuthRepository implements AuthRepository, TokenProvider {
  DevPasswordAuthRepository(this._config, {Dio? dio, FlutterSecureStorage? storage})
      : _dio = dio ?? Dio(),
        _storage = storage ?? const FlutterSecureStorage();

  final AppConfig _config;
  final Dio _dio;
  final FlutterSecureStorage _storage;

  String get _tokenEndpoint =>
      '${_config.keycloakIssuer}/protocol/openid-connect/token';

  @override
  Future<AuthUser?> restore() async {
    final token = await _storage.read(key: _kAccessKey);
    if (token == null || token.isEmpty) return null;
    return _userFromToken(token);
  }

  @override
  Future<AuthUser> signIn({String? username, String? password}) async {
    if (username == null || password == null || username.isEmpty) {
      throw Exception('Username and password are required.');
    }
    try {
      final res = await _dio.post(
        _tokenEndpoint,
        data: {
          'grant_type': 'password',
          'client_id': _config.keycloakClientId,
          'username': username,
          'password': password,
          'scope': 'openid profile email',
        },
        options: Options(contentType: Headers.formUrlEncodedContentType),
      );
      final access = res.data['access_token'] as String?;
      if (access == null) throw Exception('No access_token in response.');
      await _storage.write(key: _kAccessKey, value: access);
      await _storage.write(
          key: _kRefreshKey, value: res.data['refresh_token'] as String?);
      return _userFromToken(access);
    } on DioException catch (e) {
      final detail = e.response?.data is Map
          ? (e.response?.data['error_description'] ?? e.response?.data['error'])
          : null;
      throw Exception('Sign-in failed: ${detail ?? e.message}');
    }
  }

  @override
  Future<void> signOut() async {
    await _storage.delete(key: _kAccessKey);
    await _storage.delete(key: _kRefreshKey);
  }

  @override
  Future<String?> currentAccessToken() => _storage.read(key: _kAccessKey);

  @override
  Future<String?> refreshAccessToken() async {
    final refresh = await _storage.read(key: _kRefreshKey);
    if (refresh == null) return null;
    try {
      final res = await _dio.post(
        _tokenEndpoint,
        data: {
          'grant_type': 'refresh_token',
          'client_id': _config.keycloakClientId,
          'refresh_token': refresh,
        },
        options: Options(contentType: Headers.formUrlEncodedContentType),
      );
      final access = res.data['access_token'] as String?;
      if (access == null) return null;
      await _storage.write(key: _kAccessKey, value: access);
      final newRefresh = res.data['refresh_token'] as String?;
      if (newRefresh != null) {
        await _storage.write(key: _kRefreshKey, value: newRefresh);
      }
      return access;
    } catch (_) {
      return null;
    }
  }

  AuthUser _userFromToken(String token) {
    final claims = decodeJwtClaims(token);
    final realmAccess = claims['realm_access'];
    final roles = realmAccess is Map && realmAccess['roles'] is List
        ? (realmAccess['roles'] as List).whereType<String>().toList()
        : <String>[];
    return AuthUser(
      id: (claims['sub'] as String?) ?? 'unknown',
      displayName: (claims['name'] ??
              claims['preferred_username'] ??
              claims['email'] ??
              'User') as String,
      email: claims['email'] as String?,
      realmRoles: roles,
    );
  }
}
