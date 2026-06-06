import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/network/json_list.dart';
import '../domain/quarry.dart';
import '../domain/site_section.dart';

/// Data access for quarries and their sections.
abstract class QuarryRepository {
  Future<List<Quarry>> listQuarries();
  Future<Quarry> createQuarry({required String name, double? latitude, double? longitude});
  Future<List<SiteSection>> listSections(String quarryId);
  Future<SiteSection> createSection(
    String quarryId, {
    required String name,
    String? blockNumber,
  });
}

/// In-memory stub used until the backend is connected (config.useMockServices).
/// Seed IDs (`q-granite`, `sec-a1`, …) are referenced by the other mock repos
/// so the whole quarry → … → report flow is navigable offline.
class MockQuarryRepository implements QuarryRepository {
  MockQuarryRepository();

  static const _uuid = Uuid();

  final List<Quarry> _quarries = [
    const Quarry(id: 'q-granite', name: 'Гранитный карьер «Северный»', latitude: 55.75, longitude: 37.61),
    const Quarry(id: 'q-dolomite', name: 'Доломитовый карьер «Восток»'),
  ];

  final List<SiteSection> _sections = [
    const SiteSection(id: 'sec-a1', quarryId: 'q-granite', name: 'Уступ 320', blockNumber: 'A1'),
    const SiteSection(id: 'sec-a2', quarryId: 'q-granite', name: 'Уступ 305', blockNumber: 'A2'),
    const SiteSection(id: 'sec-b1', quarryId: 'q-dolomite', name: 'Блок Б1', blockNumber: 'B1'),
  ];

  @override
  Future<List<Quarry>> listQuarries() async => List.unmodifiable(_quarries);

  @override
  Future<Quarry> createQuarry({required String name, double? latitude, double? longitude}) async {
    final q = Quarry(id: _uuid.v4(), name: name, latitude: latitude, longitude: longitude);
    _quarries.add(q);
    return q;
  }

  @override
  Future<List<SiteSection>> listSections(String quarryId) async =>
      _sections.where((s) => s.quarryId == quarryId).toList(growable: false);

  @override
  Future<SiteSection> createSection(String quarryId, {required String name, String? blockNumber}) async {
    final s = SiteSection(id: _uuid.v4(), quarryId: quarryId, name: name, blockNumber: blockNumber);
    _sections.add(s);
    return s;
  }
}

/// Live implementation against the FastAPI backend (docs/api_contract.md).
/// Wired but unused while config.useMockServices is true.
class RemoteQuarryRepository implements QuarryRepository {
  RemoteQuarryRepository(this._dio);

  final Dio _dio;

  @override
  Future<List<Quarry>> listQuarries() async {
    try {
      final res = await _dio.get('/api/v1/quarries');
      return parseJsonList(res.data, Quarry.fromJson);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<Quarry> createQuarry({required String name, double? latitude, double? longitude}) async {
    try {
      final res = await _dio.post('/api/v1/quarries', data: {
        'name': name,
        if (latitude != null) 'latitude': latitude,
        if (longitude != null) 'longitude': longitude,
      });
      return Quarry.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<List<SiteSection>> listSections(String quarryId) async {
    try {
      final res = await _dio.get('/api/v1/quarries/$quarryId/sections');
      return parseJsonList(res.data, SiteSection.fromJson);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<SiteSection> createSection(String quarryId, {required String name, String? blockNumber}) async {
    try {
      // SiteSectionCreate requires quarry_id in the body (also in the path).
      final res = await _dio.post('/api/v1/quarries/$quarryId/sections', data: {
        'quarry_id': quarryId,
        'name': name,
        if (blockNumber != null) 'block_number': blockNumber,
      });
      return SiteSection.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }
}
