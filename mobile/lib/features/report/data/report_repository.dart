import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';

import '../../../core/network/api_exception.dart';
import '../../../core/network/json_list.dart';
import '../domain/analysis_result.dart';
import '../domain/comment.dart';
import '../domain/recommendation.dart';
import '../domain/report.dart';

/// Data access for reports, recommendations and comments.
abstract class ReportRepository {
  Future<List<Report>> listReports(String quarryId);
  Future<Report> getReport(String reportId);
  Future<List<Recommendation>> listRecommendations(String reportId);

  /// SAFETY: [decision] is one of REVIEWED / ACCEPTED / REJECTED — the only
  /// human-driven transitions out of REQUIRES_HUMAN_REVIEW. The caller must
  /// pass an explicit decision; nothing here advances status automatically
  /// (rules/product-safety.md).
  Future<Recommendation> reviewRecommendation(
    String reportId,
    String recommendationId,
    RecommendationStatus decision,
  );

  Future<Comment> addComment(
    String reportId,
    String recommendationId,
    String body,
  );

  /// Fetches the granulometry result for a report.
  /// Returns null if the result is not yet available (job still running).
  Future<AnalysisResult?> getAnalysisResult(String analysisResultId);
}

/// In-memory stub. The seeded report is explicitly a MOCK-pipeline result
/// (AnalysisMethod.mock) so the synthetic-data warning is exercised end-to-end
/// (rules/product-safety.md AI/ML labelling).
class MockReportRepository implements ReportRepository {
  static const _uuid = Uuid();

  final Map<String, Report> _reports = {
    'r-1': const Report(
      id: 'r-1',
      analysisMethod: AnalysisMethod.mock,
      summary: '⚠ Mock pipeline — results are synthetic. '
          'Гранулометрический состав рассчитан по синтетическим данным.',
      analysisResult: AnalysisResult(
        id: 'ar-1',
        p10Mm: 42.137,
        p50Mm: 187.502,
        p80Mm: 318.964,
        rosinRammlerN: 1.243210,
        rosinRammlerXc: 210.55,
        oversizePercent: 6.482,
        finesPercent: 11.205,
        confidenceScore: 0.71,
        sizeDistribution: [
          SizeBin(sizeMm: 25, cumulativePassingPct: 11.205),
          SizeBin(sizeMm: 50, cumulativePassingPct: 21.4),
          SizeBin(sizeMm: 100, cumulativePassingPct: 38.7),
          SizeBin(sizeMm: 200, cumulativePassingPct: 60.9),
          SizeBin(sizeMm: 300, cumulativePassingPct: 77.1),
          SizeBin(sizeMm: 500, cumulativePassingPct: 93.518),
        ],
      ),
      recommendations: [
        Recommendation(
          id: 'rec-1',
          reportId: 'r-1',
          status: RecommendationStatus.requiresHumanReview,
          recommendationText:
              'P80 (319 мм) превышает целевое значение (300 мм). Возможное '
              'направление: уменьшить сетку бурения. Все значения ниже — '
              'справочные, требуют проверки взрывником.',
          confidenceNotes:
              'confidence_score = 0.71 (< 0.8): интерпретировать с осторожностью.',
          parameterSuggestions: {
            'burden_m': 3.0,
            'spacing_m': 3.5,
          },
          comments: [],
        ),
      ],
    ),
  };

  Report _require(String reportId) {
    final r = _reports[reportId];
    if (r == null) throw ApiException('Report not found', statusCode: 404);
    return r;
  }

  @override
  Future<List<Report>> listReports(String quarryId) async =>
      List.unmodifiable(_reports.values);

  @override
  Future<Report> getReport(String reportId) async => _require(reportId);

  @override
  Future<List<Recommendation>> listRecommendations(String reportId) async =>
      List.unmodifiable(_require(reportId).recommendations);

  @override
  Future<Recommendation> reviewRecommendation(
    String reportId,
    String recommendationId,
    RecommendationStatus decision,
  ) async {
    final report = _require(reportId);
    final recs = [...report.recommendations];
    final idx = recs.indexWhere((r) => r.id == recommendationId);
    if (idx == -1) {
      throw ApiException('Recommendation not found', statusCode: 404);
    }
    final updated = recs[idx].copyWith(status: decision);
    recs[idx] = updated;
    _reports[reportId] = report.copyWith(recommendations: recs);
    return updated;
  }

  @override
  Future<Comment> addComment(
    String reportId,
    String recommendationId,
    String body,
  ) async {
    final report = _require(reportId);
    final recs = [...report.recommendations];
    final idx = recs.indexWhere((r) => r.id == recommendationId);
    if (idx == -1) {
      throw ApiException('Recommendation not found', statusCode: 404);
    }
    final comment = Comment(
      id: _uuid.v4(),
      recommendationId: recommendationId,
      authorName: 'You',
      body: body,
      createdAt: DateTime.now(),
    );
    recs[idx] = recs[idx].copyWith(comments: [...recs[idx].comments, comment]);
    _reports[reportId] = report.copyWith(recommendations: recs);
    return comment;
  }

  @override
  Future<AnalysisResult?> getAnalysisResult(String analysisResultId) async {
    for (final r in _reports.values) {
      if (r.analysisResult?.id == analysisResultId) return r.analysisResult;
    }
    return null;
  }
}

/// Live implementation against the FastAPI backend.
class RemoteReportRepository implements ReportRepository {
  RemoteReportRepository(this._dio);

  final Dio _dio;

  @override
  Future<List<Report>> listReports(String quarryId) async {
    try {
      final res = await _dio.get('/api/v1/quarries/$quarryId/reports');
      return parseJsonList(res.data, Report.fromJson);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<Report> getReport(String reportId) async {
    try {
      final res = await _dio.get('/api/v1/reports/$reportId');
      return Report.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<List<Recommendation>> listRecommendations(String reportId) async {
    try {
      final res = await _dio.get('/api/v1/reports/$reportId/recommendations');
      final data = res.data;
      final items = data is Map<String, dynamic>
          ? (data['items'] as List<dynamic>? ?? const [])
          : (data as List<dynamic>);
      return items
          .map((e) => Recommendation.fromJson(e as Map<String, dynamic>))
          .toList(growable: false);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<Recommendation> reviewRecommendation(
    String reportId,
    String recommendationId,
    RecommendationStatus decision,
  ) async {
    try {
      final res = await _dio.post(
        '/api/v1/reports/$reportId/recommendations/$recommendationId/review',
        data: {'status': _statusJson(decision)},
      );
      return Recommendation.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<Comment> addComment(
    String reportId,
    String recommendationId,
    String body,
  ) async {
    try {
      final res = await _dio.post(
        '/api/v1/reports/$reportId/recommendations/$recommendationId/comments',
        data: {'body': body},
      );
      return Comment.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiException.fromDio(e);
    }
  }

  @override
  Future<AnalysisResult?> getAnalysisResult(String analysisResultId) async {
    try {
      final res = await _dio.get('/api/v1/analysis-results/$analysisResultId');
      return AnalysisResult.fromJson(res.data as Map<String, dynamic>);
    } on DioException catch (e) {
      final ex = ApiException.fromDio(e);
      if (ex.statusCode == 404) return null;
      throw ex;
    }
  }

  static String _statusJson(RecommendationStatus s) => switch (s) {
        RecommendationStatus.requiresHumanReview => 'requires_human_review',
        RecommendationStatus.reviewed => 'reviewed',
        RecommendationStatus.accepted => 'accepted',
        RecommendationStatus.rejected => 'rejected',
      };
}
