import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../offline/sync_cubit.dart';

/// Thin status strip shown under the app bar when the device is offline or
/// there are queued uploads waiting to sync (mobile.md offline-first).
class OfflineBanner extends StatelessWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<SyncCubit, SyncState>(
      builder: (context, state) {
        if (state.online && state.pendingCount == 0 && state.exhaustedCount == 0) {
          return const SizedBox.shrink();
        }
        final (color, icon, text) = !state.online
            ? (Colors.orange.shade800, Icons.cloud_off, _offlineText(state))
            : state.exhaustedCount > 0
                ? (Colors.red.shade700, Icons.sync_problem,
                    '${state.exhaustedCount} upload(s) failed — tap to retry')
                : (Colors.blueGrey, Icons.cloud_upload,
                    '${state.pendingCount} pending upload(s)…');
        return Material(
          color: color,
          child: InkWell(
            onTap: () => context.read<SyncCubit>().drain(),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
              child: Row(
                children: [
                  Icon(icon, size: 16, color: Colors.white),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(text,
                        style: const TextStyle(color: Colors.white, fontSize: 12)),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  String _offlineText(SyncState state) => state.pendingCount > 0
      ? 'Offline — ${state.pendingCount} change(s) will sync when reconnected'
      : 'Offline';
}
