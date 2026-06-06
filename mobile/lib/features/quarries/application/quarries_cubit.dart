import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../data/quarry_repository.dart';
import '../domain/quarry.dart';

class QuarriesCubit extends Cubit<DataState<List<Quarry>>> {
  QuarriesCubit(this._repo) : super(const DataLoading());

  final QuarryRepository _repo;

  Future<void> load() async {
    emit(const DataLoading());
    try {
      emit(DataLoaded(await _repo.listQuarries()));
    } on ApiException catch (e) {
      emit(DataFailure(e.message));
    } catch (e) {
      emit(DataFailure('$e'));
    }
  }

  /// Creates a quarry then reloads. Throws [ApiException] to the caller so the
  /// form can surface the error without discarding the current list.
  Future<void> createQuarry({required String name}) async {
    await _repo.createQuarry(name: name);
    await load();
  }
}
