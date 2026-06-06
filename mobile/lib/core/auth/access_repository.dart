import 'package:dio/dio.dart';

import '../network/api_exception.dart';
import '../network/json_list.dart';
import 'quarry_access.dart';

/// Fetches the caller's per-quarry roles (`GET /api/v1/me/access`, GAP-4 /
/// mobile-auth-notes §9).
abstract class AccessRepository {
  Future<List<QuarryAccess>> myAccess();
}

class RemoteAccessRepository implements AccessRepository {
  RemoteAccessRepository(this._dio);
  final Dio _dio;

  @override
  Future<List<QuarryAccess>> myAccess() async {
    try {
      final res = await _dio.get('/api/v1/me/access');
      return parseJsonList(res.data, QuarryAccess.fromJson);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }
}

/// Mock: admin on the seeded quarry so the mock UI shows all actions.
class MockAccessRepository implements AccessRepository {
  @override
  Future<List<QuarryAccess>> myAccess() async => const [
        QuarryAccess(
          quarryId: 'q-granite',
          quarryName: 'Гранитный карьер «Северный»',
          roleName: 'admin',
          roleLevel: 4,
        ),
      ];
}
