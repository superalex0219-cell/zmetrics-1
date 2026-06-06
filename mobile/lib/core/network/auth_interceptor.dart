import 'package:dio/dio.dart';

import 'token_provider.dart';

/// Adds `Authorization: Bearer <token>` to every request and transparently
/// refreshes the token once on a 401 before retrying the original request.
///
/// Tokens are never logged (security rule 05-mobile / security.md).
class AuthInterceptor extends QueuedInterceptor {
  AuthInterceptor(this._tokens, this._dio, {this.onAuthFailure});

  final TokenProvider _tokens;
  final Dio _dio;

  /// Called when a 401 could not be recovered by refreshing the token, so the
  /// app can sign out and route to login.
  final void Function()? onAuthFailure;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _tokens.currentAccessToken();
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    // A deactivated account returns 403 "Account is inactive" — force logout
    // (mobile-auth-notes §8), distinct from a per-quarry permission 403.
    if (err.response?.statusCode == 403) {
      final data = err.response?.data;
      final detail = data is Map ? data['detail'] : null;
      if (detail == 'Account is inactive') {
        onAuthFailure?.call();
      }
      return handler.next(err);
    }

    final isAuthError = err.response?.statusCode == 401;
    final alreadyRetried = err.requestOptions.extra['__auth_retried'] == true;

    if (!isAuthError || alreadyRetried) {
      return handler.next(err);
    }

    final newToken = await _tokens.refreshAccessToken();
    if (newToken == null || newToken.isEmpty) {
      // Refresh failed → notify the app to sign out, then propagate the 401.
      onAuthFailure?.call();
      return handler.next(err);
    }

    final options = err.requestOptions
      ..extra['__auth_retried'] = true
      ..headers['Authorization'] = 'Bearer $newToken';

    try {
      final response = await _dio.fetch(options);
      handler.resolve(response);
    } on DioException catch (e) {
      handler.next(e);
    }
  }
}
