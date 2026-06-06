import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../data/report_repository.dart';
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
      // ReportRead does not nest recommendations — fetch them separately and
      // merge. (For the mock repo this returns the same embedded list.)
      final recs = await _repo.listRecommendations(reportId);
      emit(DataLoaded(report.copyWith(recommendations: recs)));
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
}
