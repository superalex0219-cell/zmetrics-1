import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '../../../shared/bloc/data_state.dart';
import '../../../shared/widgets/async_view.dart';
import '../../../shared/widgets/z_scaffold.dart';
import '../application/capture_cubit.dart';
import '../domain/capture_session.dart';

/// Capture sessions for a blast event.
///
/// ZED 2 USB capture is an M2+ milestone; this screen records a placeholder
/// session (frame_count) that is enqueued offline-first via SyncManager
/// (rules/05-mobile.md).
class CaptureScreen extends StatelessWidget {
  const CaptureScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ZScaffold(
      title: 'Capture sessions',
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _createSession(context),
        icon: const Icon(Icons.add_a_photo),
        label: const Text('New session'),
      ),
      body: BlocBuilder<CaptureCubit, DataState<CaptureView>>(
        builder: (context, state) => AsyncView<CaptureView>(
          state: state,
          onRetry: () => context.read<CaptureCubit>().load(),
          onData: (context, view) {
            return ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(
                    color: Colors.grey.shade200,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text(
                    'ZED 2 stereo capture is a later milestone (M2+). '
                    'Sessions created here are placeholders and are queued '
                    'offline-first.',
                    style: TextStyle(fontSize: 12),
                  ),
                ),
                if (view.sessions.isEmpty)
                  const Padding(
                    padding: EdgeInsets.all(24),
                    child: Center(child: Text('No capture sessions yet.')),
                  ),
                for (final s in view.sessions)
                  _SessionTile(session: s),
              ],
            );
          },
        ),
      ),
    );
  }

  Future<void> _createSession(BuildContext context) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await context.read<CaptureCubit>().createSession(frameCount: 0);
      messenger.showSnackBar(
        const SnackBar(content: Text('Session queued (offline-first)')),
      );
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Failed: $e')));
    }
  }
}

class _SessionTile extends StatelessWidget {
  const _SessionTile({required this.session});
  final CaptureSession session;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        leading: Icon(
          session.synced ? Icons.cloud_done : Icons.cloud_upload,
          color: session.synced ? Colors.green : Colors.orange,
        ),
        title: Text('Session ${session.id.substring(0, 8)}…'),
        subtitle: Text(session.synced ? 'Synced' : 'Pending sync'),
        trailing: TextButton(
          onPressed: () => _trigger(context),
          child: const Text('Analyze'),
        ),
      ),
    );
  }

  Future<void> _trigger(BuildContext context) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      final job = await context.read<CaptureCubit>().triggerAnalysis(session.id);
      messenger.showSnackBar(
        SnackBar(content: Text('Analysis job ${job.status.label}')),
      );
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Failed: $e')));
    }
  }
}
