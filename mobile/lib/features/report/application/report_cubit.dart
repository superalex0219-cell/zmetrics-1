import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../data/report_repository.dart';
import '../domain/analysis_result.dart';
import '../domain/recommendation.dart';
import '../domain/report.dart';

class ReportCubit extends Cubit<DataState<Report>> {
  ReportCubit(this._repo, this.reportId) : super(const DataLoading());

  final ReportRepository _repo;
  final String reportId;

  Future<void> load() async {
    emit(const DataLoading());
    try {
      final report = await _repo.getReport(reportId);
      final recs = await _repo.listRecommendations(reportId);
      AnalysisResult? result;
      if (report.analysisResultId != null) {
        result = await _repo.getAnalysisResult(report.analysisResultId!);
      }
      emit(DataLoaded(report.copyWith(
        recommendations: recs,
        analysisResult: result,
      )));
    } on ApiException catch (e) {
      emit(DataFailure(e.message));
    } catch (e) {
      emit(DataFailure('$e'));
    }
  }

  /// SAFETY: [decision] must be an explicit human choice
  /// (reviewed/accepted/rejected). The system never advances a recommendation
  /// automatically (rules/product-safety.md).
  Future<void> review(String recommendationId, RecommendationStatus decision) async {
    await _repo.reviewRecommendation(reportId, recommendationId, decision);
    await load();
  }

  Future<void> addComment(String recommendationId, String body) async {
    await _repo.addComment(reportId, recommendationId, body);
    await load();
  }

  /// Fetches the export JSON, writes to temp dir, opens the share sheet.
  /// Optional [getDir] and [doShare] allow test-time injection without
  /// platform channels.
  Future<void> export({
    Future<Directory> Function()? getDir,
    Future<void> Function(List<XFile>, {String? subject})? doShare,
  }) async {
    final bytes = await _repo.exportReport(reportId);
    final dir = await (getDir ?? getTemporaryDirectory)();
    final now = DateTime.now().toUtc();
    final date =
        '${now.year}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}';
    final file = File('${dir.path}/report_${reportId}_$date.json');
    await file.writeAsBytes(bytes, flush: true);
    await (doShare ?? _share)(
      [XFile(file.path, mimeType: 'application/json')],
      subject: 'ZMetrics report $reportId',
    );
  }

  static Future<void> _share(List<XFile> files, {String? subject}) =>
      Share.shareXFiles(files, subject: subject);
}
