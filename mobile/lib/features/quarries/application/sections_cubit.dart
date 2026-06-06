import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../data/quarry_repository.dart';
import '../domain/site_section.dart';

class SectionsCubit extends Cubit<DataState<List<SiteSection>>> {
  SectionsCubit(this._repo, this.quarryId) : super(const DataLoading());

  final QuarryRepository _repo;
  final String quarryId;

  Future<void> load() async {
    emit(const DataLoading());
    try {
      emit(DataLoaded(await _repo.listSections(quarryId)));
    } on ApiException catch (e) {
      emit(DataFailure(e.message));
    } catch (e) {
      emit(DataFailure('$e'));
    }
  }

  Future<void> createSection({required String name, String? blockNumber}) async {
    await _repo.createSection(quarryId, name: name, blockNumber: blockNumber);
    await load();
  }
}
