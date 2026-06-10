import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:go_router/go_router.dart';

import '../../../shared/bloc/data_state.dart';
import '../../../shared/widgets/async_view.dart';
import '../../../shared/widgets/z_scaffold.dart';
import '../application/capture_cubit.dart';
import '../data/otg_stereo_camera.dart';
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
                    'Ошибка анализа: ${job.errorMessage ?? 'неизвестная ошибка'}'),
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
          title: 'Сессии съемки',
          floatingActionButton: FloatingActionButton.extended(
            onPressed: canCreate ? () => _startSession(context) : null,
            icon: const Icon(Icons.add_a_photo),
            label: const Text('Начать сессию'),
          ),
          body: AsyncView<CaptureView>(
            state: state,
            onRetry: cubit.load,
            onData: (context, view) => _Body(
              quarryId: widget.quarryId,
              view: view,
              onSelectDevice: cubit.selectDevice,
              onSelectCalibration: cubit.selectCalibration,
              onCaptureOtg: () => _captureOtgAndAnalyse(context),
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
        const SnackBar(content: Text('Сессия добавлена в очередь')),
      );
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Ошибка: $e')));
    }
  }

  Future<void> _analyse(BuildContext context, String sessionId) async {
    final messenger = ScaffoldMessenger.of(context);
    final cubit = context.read<CaptureCubit>();
    try {
      final job = await cubit.triggerAnalysis(sessionId);
      unawaited(cubit.pollJobUntilTerminal(sessionId, job.id));
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('Ошибка: $e')));
    }
  }

  Future<void> _captureOtgAndAnalyse(BuildContext context) async {
    final messenger = ScaffoldMessenger.of(context);
    final cubit = context.read<CaptureCubit>();
    try {
      messenger.showSnackBar(
        const SnackBar(content: Text('Снимаем кадр с OTG-стереокамеры...')),
      );
      final frame = await const OtgStereoCamera().captureFrame();
      final job = await cubit.uploadStereoFramesAndTrigger(
        leftJpeg: frame.leftJpeg,
        rightJpeg: frame.rightJpeg,
      );
      final stereoText = frame.hasRightFrame ? 'left/right' : 'left';
      messenger.showSnackBar(
        SnackBar(content: Text('Кадры $stereoText загружены, анализ запущен')),
      );
      unawaited(cubit.pollJobUntilTerminal(job.captureSessionId, job.id));
    } catch (e) {
      messenger.showSnackBar(SnackBar(content: Text('OTG ошибка: $e')));
    }
  }
}

class _Body extends StatelessWidget {
  const _Body({
    required this.quarryId,
    required this.view,
    required this.onSelectDevice,
    required this.onSelectCalibration,
    required this.onCaptureOtg,
    required this.onTriggerAnalysis,
  });

  final String quarryId;
  final CaptureView view;
  final Future<void> Function(String deviceId) onSelectDevice;
  final void Function(String calibrationId) onSelectCalibration;
  final Future<void> Function() onCaptureOtg;
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
              'Нет устройств. Загрузите демо-данные на экране «Карьеры».',
              style: TextStyle(fontSize: 13),
            ),
          ),

        // Device dropdown
        if (view.devices.isNotEmpty) ...[
          DropdownButtonFormField<String>(
            decoration: const InputDecoration(
              labelText: 'Устройство',
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
              labelText: 'Калибровка',
              border: OutlineInputBorder(),
            ),
            value: view.selectedCalibrationId,
            disabledHint: const Text('Сначала выберите устройство'),
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

        _OtgCapturePanel(
          enabled: view.canCreateSession && view.pollingJob == null,
          onCapture: onCaptureOtg,
        ),
        const SizedBox(height: 12),

        // Polling indicator
        if (view.pollingJob != null) ...[
          const LinearProgressIndicator(),
          const SizedBox(height: 8),
          Chip(
            avatar: const Icon(Icons.memory, size: 16),
            label:
                Text('Анализ… (${view.pollingJob!.status.label.toLowerCase()})'),
          ),
          const SizedBox(height: 12),
        ],

        // Session list
        if (view.sessions.isEmpty && view.devices.isNotEmpty)
          const Padding(
            padding: EdgeInsets.all(24),
            child: Center(child: Text('Нет сессий съемки.')),
          ),
        for (final s in view.sessions) _SessionTile(session: s, onAnalyse: onTriggerAnalysis),
      ],
    );
  }
}

class _OtgCapturePanel extends StatefulWidget {
  const _OtgCapturePanel({
    required this.enabled,
    required this.onCapture,
  });

  final bool enabled;
  final Future<void> Function() onCapture;

  @override
  State<_OtgCapturePanel> createState() => _OtgCapturePanelState();
}

class _OtgCapturePanelState extends State<_OtgCapturePanel> {
  late Future<List<OtgUsbCamera>> _devices;

  @override
  void initState() {
    super.initState();
    _devices = const OtgStereoCamera().listUsbCameras();
  }

  void _refresh() {
    setState(() {
      _devices = const OtgStereoCamera().listUsbCameras();
    });
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.usb, color: Color(0xFF0F766E)),
                const SizedBox(width: 8),
                const Expanded(
                  child: Text(
                    'OTG-стереокамера',
                    style: TextStyle(fontWeight: FontWeight.w700),
                  ),
                ),
                IconButton(
                  tooltip: 'Обновить список USB',
                  onPressed: _refresh,
                  icon: const Icon(Icons.refresh),
                ),
              ],
            ),
            const SizedBox(height: 8),
            const Text(
              'Подключите камеру через OTG. Если Android видит ее как external Camera2/UVC поток, приложение снимет JPEG; side-by-side кадр будет разделен на left/right автоматически.',
              style: TextStyle(fontSize: 13),
            ),
            const SizedBox(height: 10),
            FutureBuilder<List<OtgUsbCamera>>(
              future: _devices,
              builder: (context, snap) {
                if (snap.connectionState == ConnectionState.waiting) {
                  return const LinearProgressIndicator();
                }
                final devices = snap.data ?? const [];
                if (devices.isEmpty) {
                  return const Text(
                    'USB-камера не найдена. Проверьте OTG-переходник и питание камеры.',
                    style: TextStyle(fontSize: 13, color: Colors.orange),
                  );
                }
                return Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: devices
                      .map(
                        (d) => Chip(
                          avatar: Icon(
                            d.hasPermission ? Icons.check_circle : Icons.usb,
                            size: 16,
                          ),
                          label: Text(
                            '${d.label} (${d.vendorId}:${d.productId})',
                          ),
                        ),
                      )
                      .toList(),
                );
              },
            ),
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: widget.enabled ? widget.onCapture : null,
                icon: const Icon(Icons.camera),
                label: const Text('Снять OTG-кадр и анализировать'),
              ),
            ),
            if (!widget.enabled)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  'Сначала выберите устройство и калибровку ZED 2.',
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                ),
              ),
          ],
        ),
      ),
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
        title: Text('Сессия ${session.id.substring(0, 8)}…'),
        subtitle: Text(session.synced ? 'Синхронизировано' : 'Ожидает синхронизации'),
        trailing: TextButton(
          onPressed: () => onAnalyse(session.id),
          child: const Text('Анализировать'),
        ),
      ),
    );
  }
}

// Suppresses unawaited future warning for the fire-and-forget poll.
void unawaited(Future<void> future) {}
