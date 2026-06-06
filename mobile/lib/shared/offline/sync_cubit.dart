import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import 'sync_manager.dart';
import 'sync_processor.dart';

/// Connectivity + pending-upload state for the offline banner.
class SyncState {
  const SyncState({
    this.online = true,
    this.pendingCount = 0,
    this.exhaustedCount = 0,
  });

  final bool online;
  final int pendingCount;

  /// Items that exceeded the retry limit and need user attention.
  final int exhaustedCount;

  SyncState copyWith({bool? online, int? pendingCount, int? exhaustedCount}) =>
      SyncState(
        online: online ?? this.online,
        pendingCount: pendingCount ?? this.pendingCount,
        exhaustedCount: exhaustedCount ?? this.exhaustedCount,
      );
}

/// Watches connectivity and drains the offline queue when the network returns
/// (mobile.md: queue processed on a `mobile`/`wifi` connectivity event).
class SyncCubit extends Cubit<SyncState> {
  SyncCubit({
    required SyncManager syncManager,
    required SyncProcessor processor,
    Connectivity? connectivity,
  })  : _sync = syncManager,
        _processor = processor,
        _connectivity = connectivity ?? Connectivity(),
        super(const SyncState());

  final SyncManager _sync;
  final SyncProcessor _processor;
  final Connectivity _connectivity;
  StreamSubscription<List<ConnectivityResult>>? _sub;

  Future<void> start() async {
    await refreshPending();
    final initial = await _connectivity.checkConnectivity();
    await _onConnectivity(initial);
    _sub = _connectivity.onConnectivityChanged.listen(_onConnectivity);
  }

  Future<void> _onConnectivity(List<ConnectivityResult> results) async {
    final online = results.any((r) =>
        r == ConnectivityResult.wifi ||
        r == ConnectivityResult.mobile ||
        r == ConnectivityResult.ethernet);
    emit(state.copyWith(online: online));
    if (online) {
      await drain();
    }
  }

  /// Drains the queue once and refreshes the pending count.
  Future<void> drain() async {
    final outcome = await _processor.process();
    final pending = await _sync.pendingCount();
    emit(state.copyWith(
      pendingCount: pending,
      exhaustedCount: outcome.exhausted,
    ));
  }

  Future<void> refreshPending() async {
    emit(state.copyWith(pendingCount: await _sync.pendingCount()));
  }

  @override
  Future<void> close() {
    _sub?.cancel();
    return super.close();
  }
}
