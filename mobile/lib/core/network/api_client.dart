import 'package:dio/dio.dart';

import '../config.dart';
import 'auth_interceptor.dart';
import 'retry_interceptor.dart';
import 'token_provider.dart';

/// Builds the shared [Dio] instance with auth + retry interceptors.
///
/// Base URL comes from [AppConfig] (never hardcoded — mobile.md HTTP rule).
class ApiClient {
  ApiClient(this._config, this._tokens, {void Function()? onAuthFailure})
      : _onAuthFailure = onAuthFailure {
    dio = Dio(
      BaseOptions(
        baseUrl: _config.apiBaseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 30),
        contentType: Headers.jsonContentType,
        // Keep Dio's default validateStatus (2xx only). Non-2xx responses
        // throw DioException, which drives the auth (401) and retry (503)
        // interceptors and is normalised by ApiException.fromDio.
      ),
    );
    dio.interceptors
        .add(AuthInterceptor(_tokens, dio, onAuthFailure: _onAuthFailure));
    dio.interceptors.add(RetryInterceptor(dio));
  }

  final AppConfig _config;
  final TokenProvider _tokens;
  final void Function()? _onAuthFailure;
  late final Dio dio;
}
