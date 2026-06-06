import 'dart:async';

import 'package:dio/dio.dart';

/// Retries transient `503 Service Unavailable` responses up to [maxRetries]
/// times with exponential backoff (mobile.md HTTP rule).
class RetryInterceptor extends Interceptor {
  RetryInterceptor(
    this._dio, {
    this.maxRetries = 3,
    this.baseDelay = const Duration(milliseconds: 300),
  });

  final Dio _dio;
  final int maxRetries;
  final Duration baseDelay;

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (err.response?.statusCode != 503) {
      return handler.next(err);
    }

    final attempt = (err.requestOptions.extra['__retry_attempt'] as int?) ?? 0;
    if (attempt >= maxRetries) {
      return handler.next(err);
    }

    final delay = baseDelay * (1 << attempt); // 300ms, 600ms, 1200ms
    await Future<void>.delayed(delay);

    final options = err.requestOptions
      ..extra['__retry_attempt'] = attempt + 1;

    try {
      final response = await _dio.fetch(options);
      handler.resolve(response);
    } on DioException catch (e) {
      handler.next(e);
    }
  }
}
