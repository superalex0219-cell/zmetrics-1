import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../data/report_repository.dart';
import '../domain/report.dart';

/// Lists reports for a quarry (`GET /api/v1/quarries/{id}/reports`).
class ReportsListCubit extends Cubit<DataState<List<Report>>> {
  ReportsListCubit(this._repo, this.quarryId) : super(const DataLoading());

  final ReportRepository _repo;
  final String quarryId;

  Future<void> load() async {
    emit(const DataLoading());
    try {
      emit(DataLoaded(await _repo.listReports(quarryId)));
    } on ApiException catch (e) {
      emit(DataFailure(e.message));
    } catch (e) {
      emit(DataFailure('$e'));
    }
  }
}
