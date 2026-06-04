import 'package:flutter_appauth/flutter_appauth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _kIssuer = 'http://localhost:8080/realms/zmetrics';
const _kClientId = 'zmetrics-mobile';
const _kRedirectUri = 'zmetrics://callback';
const _kScopes = ['openid', 'profile', 'email'];

const _kTokenKey = 'access_token';
const _kRefreshTokenKey = 'refresh_token';

class OidcService {
  final FlutterAppAuth _appAuth = const FlutterAppAuth();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Future<String?> signIn() async {
    final result = await _appAuth.authorizeAndExchangeCode(
      AuthorizationTokenRequest(
        _kClientId,
        _kRedirectUri,
        issuer: _kIssuer,
        scopes: _kScopes,
      ),
    );
    if (result?.accessToken != null) {
      await _storage.write(key: _kTokenKey, value: result!.accessToken);
      await _storage.write(key: _kRefreshTokenKey, value: result.refreshToken);
      return result.accessToken;
    }
    return null;
  }

  Future<String?> getAccessToken() => _storage.read(key: _kTokenKey);

  Future<void> signOut() async {
    await _storage.delete(key: _kTokenKey);
    await _storage.delete(key: _kRefreshTokenKey);
  }
}
