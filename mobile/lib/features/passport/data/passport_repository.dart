import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/network/json_list.dart';
import '../domain/blast_passport.dart';
import '../domain/passport_status.dart';

/// Data access for blast passports.
///
/// SAFETY: state-transition methods map 1:1 to explicit backend HTTP actions
/// (submit/approve/revise). There is no bulk-approve and no auto-transition
/// (rules/product-safety.md).
abstract class PassportRepository {
  Future<List<BlastPassport>> listPassports(String quarryId);
  Future<BlastPassport> getPassport(String quarryId, String passportId);
  Future<BlastPassport> createPassport(String quarryId, NewBlastPassport draft);
  Future<BlastPassport> submit(String quarryId, String passportId);
  Future<BlastPassport> approve(String quarryId, String passportId);
  Future<BlastPassport> complete(String quarryId, String passportId);
  Future<BlastPassport> revise(String quarryId, String passportId);
}

/// In-memory stub. Passports are keyed by quarry for the mock list endpoint.
class MockPassportRepository implements PassportRepository {
  static const _uuid = Uuid();

  final Map<String, List<BlastPassport>> _byQuarry = {
    'q-granite': [
      const BlastPassport(
        id: 'p-1',
        siteSectionId: 'sec-a1',
        status: PassportStatus.draft,
        revisionNumber: 1,
        explosiveType: 'ANFO',
        totalExplosiveKg: 1850.5,
        holeDiameterMm: 115,
        holeDepthM: 12.5,
        burdenM: 3.2,
        spacingM: 3.8,
        stemmingM: 2.5,
        targetP80Mm: 350,
      ),
      const BlastPassport(
        id: 'p-2',
        siteSectionId: 'sec-a2',
        status: PassportStatus.approved,
        revisionNumber: 2,
        explosiveType: 'Emulite',
        totalExplosiveKg: 2100,
        holeDiameterMm: 127,
        holeDepthM: 14,
        burdenM: 3.5,
        spacingM: 4.0,
        stemmingM: 2.8,
        targetP80Mm: 300,
      ),
    ],
  };

  List<BlastPassport> _list(String quarryId) =>
      _byQuarry.putIfAbsent(quarryId, () => []);

  BlastPassport _transition(String quarryId, String passportId, PassportStatus to) {
    final list = _list(quarryId);
    final idx = list.indexWhere((p) => p.id == passportId);
    if (idx == -1) {
      throw ApiException('Passport not found', statusCode: 404);
    }
    final updated = list[idx].copyWith(status: to);
    list[idx] = updated;
    return updated;
  }

  @override
  Future<List<BlastPassport>> listPassports(String quarryId) async =>
      List.unmodifiable(_list(quarryId));

  @override
  Future<BlastPassport> getPassport(String quarryId, String passportId) async {
    final list = _list(quarryId);
    final idx = list.indexWhere((p) => p.id == passportId);
    if (idx == -1) throw ApiException('Passport not found', statusCode: 404);
    return list[idx];
  }

  @override
  Future<BlastPassport> createPassport(String quarryId, NewBlastPassport draft) async {
    final p = BlastPassport(
      id: _uuid.v4(),
      siteSectionId: draft.siteSectionId,
      status: PassportStatus.draft,
      revisionNumber: 1,
      explosiveType: draft.explosiveType,
      totalExplosiveKg: draft.totalExplosiveKg,
      holeDiameterMm: draft.holeDiameterMm,
      holeDepthM: draft.holeDepthM,
      burdenM: draft.burdenM,
      spacingM: draft.spacingM,
      stemmingM: draft.stemmingM,
      targetP80Mm: draft.targetP80Mm,
    );
    _list(quarryId).add(p);
    return p;
  }

  @override
  Future<BlastPassport> submit(String quarryId, String passportId) =>
      Future.value(_transition(quarryId, passportId, PassportStatus.submitted));

  @override
  Future<BlastPassport> approve(String quarryId, String passportId) =>
      Future.value(_transition(quarryId, passportId, PassportStatus.approved));

  @override
  Future<BlastPassport> complete(String quarryId, String passportId) =>
      Future.value(_transition(quarryId, passportId, PassportStatus.completed));

  @override
  Future<BlastPassport> revise(String quarryId, String passportId) async {
    // Mock: mark current SUPERSEDED, append a new DRAFT revision.
    final list = _list(quarryId);
    final idx = list.indexWhere((p) => p.id == passportId);
    if (idx == -1) throw ApiException('Passport not found', statusCode: 404);
    final old = list[idx];
    final next = old.copyWith(
      id: _uuid.v4(),
      status: PassportStatus.draft,
      revisionNumber: old.revisionNumber + 1,
      supersededById: null,
    );
    list[idx] = old.copyWith(status: PassportStatus.superseded, supersededById: next.id);
    list.add(next);
    return next;
  }
}

/// Live implementation against the FastAPI backend.
class RemotePassportRepository implements PassportRepository {
  RemotePassportRepository(this._dio);

  final Dio _dio;
  String _base(String quarryId) => '/api/v1/quarries/$quarryId/passports';

  @override
  Future<List<BlastPassport>> listPassports(String quarryId) async {
    try {
      final res = await _dio.get(_base(quarryId));
      return parseJsonList(res.data, BlastPassport.fromJson);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<BlastPassport> getPassport(String quarryId, String passportId) async {
    try {
      final res = await _dio.get('${_base(quarryId)}/$passportId');
      return BlastPassport.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<BlastPassport> createPassport(String quarryId, NewBlastPassport draft) async {
    try {
      final res = await _dio.post(_base(quarryId), data: draft.toJson());
      return BlastPassport.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  Future<BlastPassport> _action(
    String quarryId,
    String passportId,
    String action, {
    Object? data,
  }) async {
    try {
      final res =
          await _dio.post('${_base(quarryId)}/$passportId/$action', data: data);
      return BlastPassport.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<BlastPassport> submit(String quarryId, String passportId) =>
      _action(quarryId, passportId, 'submit');

  @override
  Future<BlastPassport> approve(String quarryId, String passportId) =>
      _action(quarryId, passportId, 'approve');

  @override
  Future<BlastPassport> complete(String quarryId, String passportId) =>
      _action(quarryId, passportId, 'complete');

  @override
  // revise expects a JSON body (BlastPassportUpdate, all fields optional).
  Future<BlastPassport> revise(String quarryId, String passportId) =>
      _action(quarryId, passportId, 'revise', data: const <String, dynamic>{});
}
