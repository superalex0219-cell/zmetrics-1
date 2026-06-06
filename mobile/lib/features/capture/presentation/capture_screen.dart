import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/bloc/data_state.dart';
import '../../../shared/widgets/async_view.dart';
import '../../../shared/widgets/z_scaffold.dart';
import '../application/capture_cubit.dart';
import '../domain/analysis_job.dart';
import '../domain/capture_session.dart';
import '../domain/device.dart';

/// Capture sessions for a blast event.
///
/// Shows a device + calibration picker, then lets the user create offline-first
/// sessions and trigger CV/ML analysis jobs. ZED 2 USB capture is M2+; this
/// screen records placeholder sessions that are queued via SyncManager.
class CaptureScreen extends StatefulWidget {
  const CaptureScreen({super.key, required this.quarryId});

  final String quarryId;

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends State<CaptureScreen> {
  /// Tracks the last non-null pollingJob so we can detect the transition to
  /// null (terminal) in the BlocConsumer listener.
  AnalysisJob? _prevPollingJob;

  @override
  Widget build(BuildContext context) {
    return BlocConsumer<CaptureCubit, DataState<CaptureView>>(
      listener: (context, state) {
        if (state is! DataLoaded<CaptureView>) return;
        final view = state.value;
        if (_prevPollingJob != null && view.pollingJob == null) {
          final prevId = _prevPollingJob!.id;
          final job = view.jobs.firstWhere(
            (j) => j.id == prevId,
            orElse: () => AnalysisJob(
              id: prevId,
              captureSessionId: '',
              status: AnalysisJobStatus.failed,
            ),
          );
          if (job.status == AnalysisJobStatus.completed) {
            context.go('/quarries/${widget.quarryId}/reports');
          } else if (job.status == AnalysisJobStatus.failed) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(
                    'Analysis failed: ${job.errorMessage ?? 'unknown error'}'),
              ),
            );
          }
        }
        _prevPollingJob = view.pollingJob;
      },
      builder: (context, state) {
        final cubit = context.read<CaptureCubit>();
        final view =
            state is DataLoaded<CaptureView> ? state.value : const CaptureView();
        final canCreate =
            state is DataLoaded<CaptureView> && view.canCreateSession;

        return ZScaffold(
          title: 'Capture sessions',
          floatingActionButton: FloatingActionButton.extended(
            onPressed: canCreate ? () => _startSession(context) : null,
            icon: const Icon(Icons.add_a_photo),
            label: const Text('Start session'),
          ),
          body: AsyncView<CaptureView>(
            state: state,
            onRetry: cubit.load,
            onData: (context, view) => _Body(
              quarryId: widget.quarryId,
              view: view,
              onSelectDevice: cubit.selectDevice,
              onSelectCalibration: cubit.selectCalibration,
              onTriggerAnalysis: (sessionId) => _analyse(context, sessionId),
            ),
          ),
        );
      },
    );
  }

  Future<void> _startSession(BuildContext context) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await context.read<CaptureCubit>().createSession();
      messenger.showSnackBar(
        const SnackBar(content: Text('Session queued (offline-first)')),
      );
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Failed: $e')));
    }
  }

  Future<void> _analyse(BuildContext context, String sessionId) async {
    final messenger = ScaffoldMessenger.of(context);
    final cubit = context.read<CaptureCubit>();
    try {
      final job = await cubit.triggerAnalysis(sessionId);
      unawaited(cubit.pollJobUntilTerminal(sessionId, job.id));
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Failed: $e')));
    }
  }
}

class _Body extends StatelessWidget {
  const _Body({
    required this.quarryId,
    required this.view,
    required this.onSelectDevice,
    required this.onSelectCalibration,
    required this.onTriggerAnalysis,
  });

  final String quarryId;
  final CaptureView view;
  final Future<void> Function(String deviceId) onSelectDevice;
  final void Function(String calibrationId) onSelectCalibration;
  final void Function(String sessionId) onTriggerAnalysis;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (view.devices.isEmpty)
          Container(
            padding: const EdgeInsets.all(12),
            margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(
              color: Colors.grey.shade200,
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Text(
              'No devices registered. Run dev seed from the quarries screen.',
              style: TextStyle(fontSize: 13),
            ),
          ),

        // Device dropdown
        if (view.devices.isNotEmpty) ...[
          DropdownButtonFormField<String>(
            decoration: const InputDecoration(
              labelText: 'Device',
              border: OutlineInputBorder(),
            ),
            value: view.selectedDeviceId,
            items: view.devices
                .map((d) => DropdownMenuItem(
                      value: d.id,
                      child: Text('${d.model} — ${d.serialNumber}'),
                    ))
                .toList(),
            onChanged: (id) {
              if (id != null) onSelectDevice(id);
            },
          ),
          const SizedBox(height: 12),

          // Calibration dropdown — enabled only after a device is selected
          DropdownButtonFormField<String>(
            decoration: const InputDecoration(
              labelText: 'Calibration',
              border: OutlineInputBorder(),
            ),
            value: view.selectedCalibrationId,
            disabledHint: const Text('Select a device first'),
            items: view.selectedDeviceId == null
                ? null
                : view.calibrations
                    .map((c) => DropdownMenuItem(
                          value: c.id,
                          child: Text(
                              '${c.baselineMm} mm baseline · ${c.imageWidthPx}×${c.imageHeightPx}'),
                        ))
                    .toList(),
            onChanged: view.selectedDeviceId == null
                ? null
                : (id) {
                    if (id != null) onSelectCalibration(id);
                  },
          ),
          const SizedBox(height: 16),
        ],

        // Polling indicator
        if (view.pollingJob != null) ...[
          const LinearProgressIndicator(),
          const SizedBox(height: 8),
          Chip(
            avatar: const Icon(Icons.memory, size: 16),
            label:
                Text('Analyzing… (${view.pollingJob!.status.label.toLowerCase()})'),
          ),
          const SizedBox(height: 12),
        ],

        // Session list
        if (view.sessions.isEmpty && view.devices.isNotEmpty)
          const Padding(
            padding: EdgeInsets.all(24),
            child: Center(child: Text('No capture sessions yet.')),
          ),
        for (final s in view.sessions) _SessionTile(session: s, onAnalyse: onTriggerAnalysis),
      ],
    );
  }
}

class _SessionTile extends StatelessWidget {
  const _SessionTile({required this.session, required this.onAnalyse});

  final CaptureSession session;
  final void Function(String sessionId) onAnalyse;

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
          onPressed: () => onAnalyse(session.id),
          child: const Text('Analyse'),
        ),
      ),
    );
  }
}

// Suppresses unawaited future warning for the fire-and-forget poll.
void unawaited(Future<void> future) {}
