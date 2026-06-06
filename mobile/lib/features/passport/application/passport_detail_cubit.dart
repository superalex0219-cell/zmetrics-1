import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../core/network/api_exception.dart';
import '../../../shared/bloc/data_state.dart';
import '../data/passport_repository.dart';
import '../domain/blast_passport.dart';

/// Loads a single passport and drives its human-initiated state transitions.
///
/// SAFETY: each method maps to one explicit backend action (submit/approve/
/// revise). There is no auto-advance and no bulk action
/// (rules/product-safety.md).
class PassportDetailCubit extends Cubit<DataState<BlastPassport>> {
  PassportDetailCubit(this._repo, this.quarryId, this.passportId)
      : super(const DataLoading());

  final PassportRepository _repo;
  final String quarryId;
  final String passportId;

  Future<void> load() async {
    emit(const DataLoading());
    try {
      emit(DataLoaded(await _repo.getPassport(quarryId, passportId)));
    } on ApiException catch (e) {
      emit(DataFailure(e.message));
    } catch (e) {
      emit(DataFailure('$e'));
    }
  }

  Future<void> submit() async {
    emit(DataLoaded(await _repo.submit(quarryId, passportId)));
  }

  Future<void> approve() async {
    emit(DataLoaded(await _repo.approve(quarryId, passportId)));
  }

  Future<void> complete() async {
    emit(DataLoaded(await _repo.complete(quarryId, passportId)));
  }

  Future<BlastPassport> revise() async {
    final next = await _repo.revise(quarryId, passportId);
    // After a revision the current record is superseded; reload to reflect it.
    await load();
    return next;
  }
}
