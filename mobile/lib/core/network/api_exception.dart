import 'package:dio/dio.dart';

/// Normalised error surfaced by the data layer to cubits.
///
/// The backend error contract (see docs/api_contract.md) is:
///   {"detail": "Human-readable message", "error_code": "OPTIONAL_CODE"}
class ApiException implements Exception {
  ApiException(this.message, {this.statusCode, this.errorCode});

  final String message;
  final int? statusCode;
  final String? errorCode;

  /// Maps a Dio failure onto a user-presentable [ApiException].
  factory ApiException.fromDio(DioException e) {
    final response = e.response;
    if (response != null) {
      final data = response.data;
      String message = 'Request failed (${response.statusCode}).';
      String? code;
      if (data is Map) {
        if (data['detail'] is String) message = data['detail'] as String;
        if (data['error_code'] is String) code = data['error_code'] as String;
      }
      return ApiException(
        message,
        statusCode: response.statusCode,
        errorCode: code,
      );
    }
    // No response → connectivity / timeout class of error.
    return ApiException(
      switch (e.type) {
        DioExceptionType.connectionTimeout ||
        DioExceptionType.sendTimeout ||
        DioExceptionType.receiveTimeout =>
          'Connection timed out. Check your network and try again.',
        DioExceptionType.connectionError =>
          'Cannot reach the server. You may be offline.',
        _ => 'Network error: ${e.message ?? 'unknown'}.',
      },
    );
  }

  @override
  String toString() => 'ApiException($statusCode, $errorCode): $message';
}

/// User-presentable message for any thrown error. For a 403 it clarifies that
/// this is a permissions issue (roles are per-quarry; backend is authoritative).
String friendlyError(Object error) {
  if (error is ApiException) {
    if (error.statusCode == 403) {
      return error.message.isEmpty
          ? 'You do not have permission for this action on this quarry.'
          : error.message;
    }
    return error.message;
  }
  return '$error';
}
