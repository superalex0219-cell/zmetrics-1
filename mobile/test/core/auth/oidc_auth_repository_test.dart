import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_appauth/flutter_appauth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:zmetrics_mobile/core/auth/auth_repository.dart';
import 'package:zmetrics_mobile/core/auth/oidc_service.dart';
import 'package:zmetrics_mobile/core/config.dart';

// ---------------------------------------------------------------------------
// Minimal stub — replaces flutter_secure_storage so there are no platform
// channels in unit tests.
// ---------------------------------------------------------------------------
class _FakeStorage implements FlutterSecureStorage {
  final Map<String, String> _data = {};

  @override
  Future<String?> read({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _data[key];

  @override
  Future<void> write({
    required String key,
    required String? value,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async {
    if (value == null) {
      _data.remove(key);
    } else {
      _data[key] = value;
    }
  }

  @override
  Future<void> delete({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _data.remove(key);

  @override
  Future<bool> containsKey({
    required String key,
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _data.containsKey(key);

  @override
  Future<Map<String, String>> readAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      Map.unmodifiable(_data);

  @override
  Future<void> deleteAll({
    IOSOptions? iOptions,
    AndroidOptions? aOptions,
    LinuxOptions? lOptions,
    WebOptions? webOptions,
    MacOsOptions? mOptions,
    WindowsOptions? wOptions,
  }) async =>
      _data.clear();

  // Unused platform members — satisfy the interface.
  @override
  AndroidOptions get aOptions => const AndroidOptions();
  @override
  IOSOptions get iOptions => const IOSOptions();
  @override
  LinuxOptions get lOptions => const LinuxOptions();
  @override
  MacOsOptions get mOptions => const MacOsOptions();
  @override
  WebOptions get webOptions => const WebOptions();
  @override
  WindowsOptions get wOptions => const WindowsOptions();

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const _testConfig = AppConfig(
  apiBaseUrl: 'http://localhost:8000',
  useMockServices: false,
  keycloakIssuer: 'http://localhost:8080/realms/zmetrics',
  keycloakClientId: 'zmetrics-mobile',
  keycloakRedirectUri: 'zmetrics://callback',
);

/// Encodes a minimal JWT with the given payload (no real signature — tests
/// only verify the payload decoding path).
String _makeJwt(Map<String, dynamic> payload) {
  final header = base64Url.encode(utf8.encode('{"alg":"RS256","typ":"JWT"}'));
  final body = base64Url.encode(utf8.encode(jsonEncode(payload)));
  return '$header.$body.fakesig';
}

OidcService _makeOidcService(_FakeStorage storage) =>
    OidcService(_testConfig, appAuth: const FlutterAppAuth(), storage: storage);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------
void main() {
  group('OidcAuthRepository.restore()', () {
    test('returns null when no token is stored', () async {
      final storage = _FakeStorage();
      final repo = OidcAuthRepository(_makeOidcService(storage));

      expect(await repo.restore(), isNull);
    });

    test('decodes claims from stored access token', () async {
      final storage = _FakeStorage();
      final jwt = _makeJwt({
        'sub': 'user-sub-abc123',
        'name': 'Alexei Smirnov',
        'email': 'alexei@example.com',
      });
      await storage.write(key: 'access_token', value: jwt);

      final repo = OidcAuthRepository(_makeOidcService(storage));
      final user = await repo.restore();

      expect(user, isNotNull);
      expect(user!.id, 'user-sub-abc123');
      expect(user.displayName, 'Alexei Smirnov');
      expect(user.email, 'alexei@example.com');
    });
  });
}
