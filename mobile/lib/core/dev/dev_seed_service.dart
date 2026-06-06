import 'package:dio/dio.dart';

import '../network/api_exception.dart';

/// Result of the backend dev-seed (or the mock equivalent): the ids needed to
/// navigate the demo flow.
class DevSeedResult {
  const DevSeedResult({required this.quarryId, required this.reportId});
  final String quarryId;
  final String reportId;
}

/// Triggers demo data creation so a fresh `admin-user` sees something.
abstract class DevSeedService {
  Future<DevSeedResult> seed();
}

/// Calls `POST /api/v1/admin/dev-seed` (idempotent on the backend).
class RemoteDevSeedService implements DevSeedService {
  RemoteDevSeedService(this._dio);
  final Dio _dio;

  @override
  Future<DevSeedResult> seed() async {
    try {
      final res = await _dio.post('/api/v1/admin/dev-seed');
      final data = res.data as Map<String, dynamic>;
      return DevSeedResult(
        quarryId: data['quarry_id'] as String,
        reportId: data['report_id'] as String,
      );
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }
}

/// Mock seed: the in-memory repositories are already seeded, so just return the
/// well-known ids.
class MockDevSeedService implements DevSeedService {
  @override
  Future<DevSeedResult> seed() async =>
      const DevSeedResult(quarryId: 'q-granite', reportId: 'r-1');
}
