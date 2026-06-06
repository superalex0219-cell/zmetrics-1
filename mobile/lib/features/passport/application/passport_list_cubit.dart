import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../data/passport_repository.dart';
import '../domain/blast_passport.dart';

class PassportListCubit extends Cubit<DataState<List<BlastPassport>>> {
  PassportListCubit(this._repo, this.quarryId) : super(const DataLoading());

  final PassportRepository _repo;
  final String quarryId;

  Future<void> load() async {
    emit(const DataLoading());
    try {
      emit(DataLoaded(await _repo.listPassports(quarryId)));
    } on ApiException catch (e) {
      emit(DataFailure(e.message));
    } catch (e) {
      emit(DataFailure('$e'));
    }
  }

  /// SAFETY: [draft] fields are entered manually by the blaster and are never
  /// prefilled from AI recommendations (rules/product-safety.md). New
  /// passports are always created in DRAFT by the backend default.
  Future<BlastPassport> create(NewBlastPassport draft) async {
    final created = await _repo.createPassport(quarryId, draft);
    await load();
    return created;
  }
}
