import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:share_plus/share_plus.dart';
import 'package:zmetrics_mobile/core/network/api_exception.dart';
import 'package:zmetrics_mobile/features/report/application/report_cubit.dart';
import 'package:zmetrics_mobile/features/report/data/report_repository.dart';
import 'package:zmetrics_mobile/features/report/domain/analysis_result.dart';
import 'package:zmetrics_mobile/features/report/domain/comment.dart';
import 'package:zmetrics_mobile/features/report/domain/recommendation.dart';
import 'package:zmetrics_mobile/features/report/domain/report.dart';
import 'package:zmetrics_mobile/features/report/presentation/report_screen.dart';
import 'package:zmetrics_mobile/shared/bloc/data_state.dart';
import 'package:zmetrics_mobile/shared/offline/sync_cubit.dart';
import 'package:zmetrics_mobile/shared/offline/sync_manager.dart';
import 'package:zmetrics_mobile/shared/offline/sync_processor.dart';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Builds a Dio that intercepts every request, calls [onRequest], and
/// resolves/rejects based on [statusCode].
Dio _buildDio({
  required int statusCode,
  dynamic responseData,
  void Function(RequestOptions)? onRequest,
}) {
  final dio = Dio(BaseOptions(baseUrl: 'http://test'));
  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) {
      onRequest?.call(options);
      if (statusCode >= 200 && statusCode < 300) {
        handler.resolve(Response(
          requestOptions: options,
          statusCode: statusCode,
          data: responseData,
        ));
      } else {
        handler.reject(DioException(
          requestOptions: options,
          response: Response(
            requestOptions: options,
            statusCode: statusCode,
            data: {'detail': 'HTTP $statusCode'},
          ),
          type: DioExceptionType.badResponse,
        ));
      }
    },
  ));
  return dio;
}

/// Repo that succeeds for load methods but throws [ApiException] on export.
class _ExportThrowingRepo implements ReportRepository {
  @override
  Future<Uint8List> exportReport(String reportId) async =>
      throw ApiException('Forbidden', statusCode: 403);

  @override
  Future<List<Report>> listReports(String quarryId) async => [];

  @override
  Future<Report> getReport(String reportId) async => const Report(
        id: 'r-x',
        analysisMethod: AnalysisMethod.mock,
        recommendations: [],
      );

  @override
  Future<List<Recommendation>> listRecommendations(String reportId) async => [];

  @override
  Future<Recommendation> reviewRecommendation(
    String reportId,
    String recommendationId,
    RecommendationStatus decision,
  ) async =>
      throw UnimplementedError();

  @override
  Future<Comment> addComment(
    String reportId,
    String recommendationId,
    String body,
  ) async =>
      throw UnimplementedError();

  @override
  Future<AnalysisResult?> getAnalysisResult(String analysisResultId) async =>
      null;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

void main() {
  // ---- 1 & 2: MockReportRepository.exportReport ----

  group('MockReportRepository.exportReport', () {
    test('returns valid JSON bytes with export_format and p80_mm', () async {
      final repo = MockReportRepository();
      final bytes = await repo.exportReport('r-1');

      expect(bytes, isNotEmpty);
      final decoded = jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>;
      expect(decoded['export_format'], 'json_placeholder');
      expect(decoded['note'], contains('Mock pipeline'));
      final result = decoded['analysis_result'] as Map<String, dynamic>;
      expect(result.containsKey('p80_mm'), isTrue);
      expect(result['p80_mm'], isNotNull);
    });

    test('throws ApiException(404) for unknown reportId', () async {
      final repo = MockReportRepository();
      await expectLater(
        repo.exportReport('does-not-exist'),
        throwsA(isA<ApiException>()
            .having((e) => e.statusCode, 'statusCode', 404)),
      );
    });
  });

  // ---- 3, 4, 5: RemoteReportRepository.exportReport ----

  group('RemoteReportRepository.exportReport', () {
    test('200 success: returns Uint8List from response bytes', () async {
      final expectedBytes = [1, 2, 3, 4, 5];
      final dio = _buildDio(
        statusCode: 200,
        responseData: expectedBytes,
      );

      final repo = RemoteReportRepository(dio);
      final result = await repo.exportReport('r-abc');

      expect(result, equals(Uint8List.fromList(expectedBytes)));
    });

    test('403 → ApiException with statusCode 403', () async {
      final dio = _buildDio(statusCode: 403);
      final repo = RemoteReportRepository(dio);

      await expectLater(
        repo.exportReport('r-abc'),
        throwsA(isA<ApiException>()
            .having((e) => e.statusCode, 'statusCode', 403)),
      );
    });

    test('404 → ApiException with statusCode 404', () async {
      final dio = _buildDio(statusCode: 404);
      final repo = RemoteReportRepository(dio);

      await expectLater(
        repo.exportReport('r-xyz'),
        throwsA(isA<ApiException>()
            .having((e) => e.statusCode, 'statusCode', 404)),
      );
    });
  });

  // ---- 6: ReportCubit.export — writes file and calls share ----

  group('ReportCubit.export', () {
    test('writes JSON file to dir and calls share with correct args', () async {
      final cubit = ReportCubit(MockReportRepository(), 'r-1');
      final tmpDir = await Directory.systemTemp.createTemp('zmreport_test_');

      List<XFile>? capturedFiles;
      String? capturedSubject;

      try {
        await cubit.export(
          getDir: () async => tmpDir,
          doShare: (files, {subject}) async {
            capturedFiles = files;
            capturedSubject = subject;
          },
        );

        expect(capturedFiles, hasLength(1));
        expect(capturedFiles!.first.path, contains('report_r-1_'));
        expect(capturedFiles!.first.path, endsWith('.json'));
        expect(capturedSubject, 'ZMetrics report r-1');
        expect(File(capturedFiles!.first.path).existsSync(), isTrue);
      } finally {
        await tmpDir.delete(recursive: true);
        await cubit.close();
      }
    });

    // ---- 7: ReportCubit.export — ApiException propagates ----

    test('rethrows ApiException(403) when repo.exportReport throws', () async {
      final cubit = ReportCubit(_ExportThrowingRepo(), 'r-1');

      await expectLater(
        cubit.export(),
        throwsA(isA<ApiException>()
            .having((e) => e.statusCode, 'statusCode', 403)),
      );
      await cubit.close();
    });
  });

  // ---- 8: Widget — export button disabled in loading state ----

  group('ReportScreen export button', () {
    testWidgets('export button is disabled while cubit is in DataLoading',
        (tester) async {
      final reportCubit = ReportCubit(MockReportRepository(), 'r-1');
      // Do NOT call reportCubit.load() — stays in DataLoading.

      // SyncCubit must be in the tree for OfflineBanner (inside ZScaffold).
      // We do NOT call start() so no platform channels are hit.
      final syncManager = InMemorySyncManager();
      final syncCubit = SyncCubit(
        syncManager: syncManager,
        processor: SyncProcessor(syncManager, {}),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: MultiBlocProvider(
            providers: [
              BlocProvider<ReportCubit>.value(value: reportCubit),
              BlocProvider<SyncCubit>.value(value: syncCubit),
            ],
            child: const ReportScreen(),
          ),
        ),
      );

      final exportBtn = tester.widget<IconButton>(
        find.byWidgetPredicate(
          (w) => w is IconButton && w.tooltip == 'Export JSON',
        ),
      );
      expect(exportBtn.onPressed, isNull,
          reason: 'Button must be disabled when state is DataLoading');

      await reportCubit.close();
      await syncCubit.close();
    });
  });
}
