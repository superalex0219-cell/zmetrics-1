# TASK: MOB-3 — Capture flow: device picker, session create, job polling

**Date:** 2026-06-06
**From:** curating chat (post MOB-2)
**Layer:** `mobile/` primary; one small addendum in `backend/app/schemas/blast.py`
**Review agent:** `mobile-reviewer`
**Priority:** P1 — completes the end-to-end blast → capture → report flow

---

## Context

The `CaptureScreen` is currently a stub: "New session" creates a local-only unsynced session with no device/calibration, the `SyncProcessor` handler for `kOpCreateCaptureSession` is a no-op (`(_) async {}`), and there is no job polling. This task wires everything end-to-end:

```
User picks device → picks calibration → creates session (queued offline-first)
→ SyncProcessor POSTs to backend → user taps "Analyse" → job polling
→ completed → navigate to quarry reports list
```

---

## Backend addendum (one line change only)

**File:** `backend/app/schemas/blast.py`

`CaptureSessionCreate` requires `capture_datetime` but the mobile doesn't send it today, and `frame_count` has no default in the DB (the column is `NOT NULL`). Add defaults so a session can be created before frames are uploaded:

```python
class CaptureSessionCreate(BaseModel):
    device_id: UUID
    calibration_id: UUID
    capture_datetime: datetime | None = None   # defaults to now() server-side if omitted
    notes: str | None = None
```

And in `blast_events.py::create_capture_session`, set a server-side default if missing:

```python
from datetime import datetime, timezone
...
session = CaptureSession(
    blast_event_id=event.id,
    captured_by_id=current_user.id,
    device_id=body.device_id,
    calibration_id=body.calibration_id,
    capture_datetime=body.capture_datetime or datetime.now(tz=timezone.utc),
    frame_count=0,
    notes=body.notes,
)
```

No migration needed (`frame_count` model default needs to be added — set `default=0` in `CaptureSession.frame_count` mapped_column). Check `backend/app/db/models/capture.py` and add `default=0` if missing.

---

## Deliverable 1 — `NewCaptureSession` domain model extended

**File:** `mobile/lib/features/capture/domain/capture_session.dart`

Add `quarry_id`, `passport_id`, and `capture_datetime` to `NewCaptureSession` so the `SyncProcessor` has everything it needs to call the correct backend URL:

```dart
@freezed
class NewCaptureSession with _$NewCaptureSession {
  const factory NewCaptureSession({
    @JsonKey(name: 'blast_event_id') required String blastEventId,
    @JsonKey(name: 'quarry_id') required String quarryId,
    @JsonKey(name: 'passport_id') required String passportId,
    @JsonKey(name: 'device_id') required String deviceId,
    @JsonKey(name: 'calibration_id') required String calibrationId,
    @JsonKey(name: 'capture_datetime') required String captureDateTime,
    @JsonKey(name: 'frame_count') @Default(0) int frameCount,
  }) = _NewCaptureSession;

  factory NewCaptureSession.fromJson(Map<String, dynamic> json) =>
      _$NewCaptureSessionFromJson(json);
}
```

Run `flutter pub run build_runner build --delete-conflicting-outputs` after any freezed change.

---

## Deliverable 2 — `Device` + `Calibration` domain models and `DeviceRepository`

**New files:**
- `mobile/lib/features/capture/domain/device.dart`
- `mobile/lib/features/capture/data/device_repository.dart`

### `device.dart`

Minimal freezed models for the picker UI:

```dart
@freezed
class Device with _$Device {
  const factory Device({
    required String id,
    @JsonKey(name: 'serial_number') required String serialNumber,
    required String model,
  }) = _Device;
  factory Device.fromJson(Map<String, dynamic> json) => _$DeviceFromJson(json);
}

@freezed
class DeviceCalibration with _$DeviceCalibration {
  const factory DeviceCalibration({
    required String id,
    @JsonKey(name: 'device_id') required String deviceId,
    @JsonKey(name: 'baseline_mm') required double baselineMm,
    @JsonKey(name: 'image_width_px') required int imageWidthPx,
    @JsonKey(name: 'image_height_px') required int imageHeightPx,
  }) = _DeviceCalibration;
  factory DeviceCalibration.fromJson(Map<String, dynamic> json) =>
      _$DeviceCalibrationFromJson(json);
}
```

### `device_repository.dart`

```dart
abstract class DeviceRepository {
  Future<List<Device>> listDevices();
  Future<List<DeviceCalibration>> listCalibrations(String deviceId);
}

class MockDeviceRepository implements DeviceRepository {
  static final _device = Device(id: 'mock-device-001', serialNumber: 'DEMO-ZED2-0001', model: 'ZED 2');
  static final _cal = DeviceCalibration(id: 'mock-cal-001', deviceId: 'mock-device-001', baselineMm: 120, imageWidthPx: 1280, imageHeightPx: 720);

  @override Future<List<Device>> listDevices() async => [_device];
  @override Future<List<DeviceCalibration>> listCalibrations(String deviceId) async => [_cal];
}

class RemoteDeviceRepository implements DeviceRepository {
  RemoteDeviceRepository(this._dio);
  final Dio _dio;

  @override
  Future<List<Device>> listDevices() async {
    final res = await _dio.get('/api/v1/devices');
    return Paginated<Device>.fromJson(res.data, Device.fromJson).items;
  }

  @override
  Future<List<DeviceCalibration>> listCalibrations(String deviceId) async {
    final res = await _dio.get('/api/v1/devices/$deviceId/calibrations');
    return Paginated<DeviceCalibration>.fromJson(res.data, DeviceCalibration.fromJson).items;
  }
}
```

---

## Deliverable 3 — `CaptureRepository`: fix URLs + wire live mode

**File:** `mobile/lib/features/capture/data/capture_repository.dart`

### Interface change

```dart
abstract class CaptureRepository {
  // quarryId + passportId replace blastEventId for correct URL routing
  Future<CaptureSession> createCaptureSession(NewCaptureSession draft);
  Future<List<CaptureSession>> listSessions(String quarryId, String passportId);
  Future<AnalysisJob> triggerAnalysis(String captureSessionId);
  Future<List<AnalysisJob>> listJobs(String captureSessionId);
  Future<AnalysisJob> getJob(String captureSessionId, String jobId);
}
```

### `RemoteCaptureRepository` fixes

`listSessions` — fix URL:
```dart
@override
Future<List<CaptureSession>> listSessions(String quarryId, String passportId) async {
  final res = await _dio.get(
    '/api/v1/quarries/$quarryId/passports/$passportId/blast-event/capture-sessions',
  );
  return Paginated<CaptureSession>.fromJson(res.data, CaptureSession.fromJson).items;
}
```

`postQueuedCaptureSession` — fix URL and body:
```dart
Future<void> postQueuedCaptureSession(
  String idempotencyKey,
  Map<String, dynamic> payload,
) async {
  final quarryId = payload['quarry_id'] as String;
  final passportId = payload['passport_id'] as String;
  await _dio.post(
    '/api/v1/quarries/$quarryId/passports/$passportId/blast-event/capture-sessions',
    data: {
      'device_id': payload['device_id'],
      'calibration_id': payload['calibration_id'],
      'capture_datetime': payload['capture_datetime'],
    },
    options: Options(headers: {'Idempotency-Key': idempotencyKey}),
  );
}
```

`triggerAnalysis` URL is already correct: `POST /api/v1/captures/$captureSessionId/jobs` ✅

`MockCaptureRepository.listSessions` — update signature to `(String quarryId, String passportId)`.

---

## Deliverable 4 — `CaptureCubit` refactor

**File:** `mobile/lib/features/capture/application/capture_cubit.dart`

### Extended `CaptureView`

```dart
class CaptureView {
  const CaptureView({
    this.sessions = const [],
    this.jobs = const [],
    this.devices = const [],
    this.calibrations = const [],
    this.selectedDeviceId,
    this.selectedCalibrationId,
    this.pollingJob,
  });

  final List<CaptureSession> sessions;
  final List<AnalysisJob> jobs;
  final List<Device> devices;
  final List<DeviceCalibration> calibrations;
  final String? selectedDeviceId;
  final String? selectedCalibrationId;

  /// Non-null while a job is being polled (status queued or running).
  final AnalysisJob? pollingJob;

  bool get canCreateSession =>
      selectedDeviceId != null && selectedCalibrationId != null;

  CaptureView copyWith({...}) => ...;
}
```

### Constructor change

```dart
class CaptureCubit extends Cubit<DataState<CaptureView>> {
  CaptureCubit(this._captureRepo, this._deviceRepo, this.quarryId, this.passportId)
      : super(const DataLoading());

  final String quarryId;
  final String passportId;
```

### `load()` — also loads devices

```dart
Future<void> load() async {
  emit(const DataLoading());
  try {
    final sessions = await _captureRepo.listSessions(quarryId, passportId);
    final devices = await _deviceRepo.listDevices();
    emit(DataLoaded(CaptureView(sessions: sessions, devices: devices)));
  } on ApiException catch (e) {
    emit(DataFailure(e.message));
  }
}
```

### `selectDevice(deviceId)` — loads calibrations for that device

```dart
Future<void> selectDevice(String deviceId) async {
  final cur = state;
  if (cur is! DataLoaded<CaptureView>) return;
  final cals = await _deviceRepo.listCalibrations(deviceId);
  emit(DataLoaded(cur.value.copyWith(
    selectedDeviceId: deviceId,
    calibrations: cals,
    selectedCalibrationId: null,
  )));
}

void selectCalibration(String calibrationId) {
  final cur = state;
  if (cur is! DataLoaded<CaptureView>) return;
  emit(DataLoaded(cur.value.copyWith(selectedCalibrationId: calibrationId)));
}
```

### `createSession()` — uses selected device/calibration

```dart
Future<CaptureSession> createSession() async {
  final cur = state;
  if (cur is! DataLoaded<CaptureView>) throw StateError('Not loaded');
  final view = cur.value;
  if (!view.canCreateSession) throw StateError('Device and calibration required');

  final session = await _captureRepo.createCaptureSession(NewCaptureSession(
    blastEventId: '',       // not used for routing; quarryId+passportId are
    quarryId: quarryId,
    passportId: passportId,
    deviceId: view.selectedDeviceId!,
    calibrationId: view.selectedCalibrationId!,
    captureDateTime: DateTime.now().toUtc().toIso8601String(),
  ));
  await load();
  return session;
}
```

### `pollJobUntilTerminal(sessionId, jobId)` — polls every 3 s, stops on terminal

```dart
Future<void> pollJobUntilTerminal(String sessionId, String jobId) async {
  while (true) {
    await Future.delayed(const Duration(seconds: 3));
    if (isClosed) return;

    AnalysisJob job;
    try {
      job = await _captureRepo.getJob(sessionId, jobId);
    } catch (_) {
      return; // network error — stop polling, let user retry
    }

    final cur = state;
    if (cur is DataLoaded<CaptureView>) {
      emit(DataLoaded(cur.value.copyWith(
        pollingJob: job.status.isTerminal ? null : job,
        jobs: [
          ...cur.value.jobs.where((j) => j.id != job.id),
          job,
        ],
      )));
    }
    if (job.status.isTerminal) return;
  }
}
```

---

## Deliverable 5 — `CaptureScreen` rewrite

**File:** `mobile/lib/features/capture/presentation/capture_screen.dart`

Replace the stub. New screen structure:

```
ZScaffold("Capture sessions")
  ├── [if no devices] → grey box: "No devices registered. Run dev seed from the quarries screen."
  ├── [device dropdown]     ← DropdownButton<Device>
  ├── [calibration dropdown] ← enabled only after device selected
  ├── [FAB: "Start session"] ← enabled only when canCreateSession; grayed out otherwise
  ├── [if pollingJob != null] → LinearProgressIndicator + "Analyzing…" chip
  └── [session list]
        └── each session: icon (synced/pending), id prefix, "Analyse" button
              └── "Analyse" triggers analysis + calls cubit.pollJobUntilTerminal
```

**Navigation after job terminal:**
```dart
// in BlocListener on CaptureView state change:
if (prevPolling != null && currentView.pollingJob == null) {
  final job = currentView.jobs.firstWhere((j) => j.id == prevPolling.id);
  if (job.status == AnalysisJobStatus.completed) {
    context.go('/quarries/$quarryId/reports');
  } else if (job.status == AnalysisJobStatus.failed) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Analysis failed: ${job.errorMessage ?? 'unknown error'}')),
    );
  }
}
```

Use `BlocConsumer` (both `builder` + `listener`) or split `BlocBuilder` + `BlocListener`.

---

## Deliverable 6 — Router + `PassportDetailScreen`

**File:** `mobile/lib/core/router.dart`

Change route path:
```dart
// OLD:
GoRoute(path: '/blast-events/:eid/captures', ...)

// NEW:
GoRoute(
  path: '/quarries/:qid/passports/:pid/captures',
  builder: (context, state) {
    final qid = state.pathParameters['qid']!;
    final pid = state.pathParameters['pid']!;
    return BlocProvider(
      create: (ctx) => CaptureCubit(
        ctx.read<CaptureRepository>(),
        ctx.read<DeviceRepository>(),
        qid,
        pid,
      )..load(),
      child: CaptureScreen(quarryId: qid),
    );
  },
),
```

**File:** `mobile/lib/features/passport/presentation/passport_detail_screen.dart`

Add a "Captures" button alongside the existing "Reports" button:

```dart
OutlinedButton.icon(
  icon: const Icon(Icons.camera_alt_outlined),
  label: const Text('Captures'),
  onPressed: () => context.go('/quarries/$quarryId/passports/${passport.id}/captures'),
),
```

---

## Deliverable 7 — `di.dart`: wire live capture + SyncProcessor handler

**File:** `mobile/lib/core/di.dart`

In the live branch, replace:
```dart
// BEFORE
final capture = MockCaptureRepository(syncManager);
final processor = SyncProcessor(syncManager, {
  kOpCreateCaptureSession: (_) async {},
});
```

With:
```dart
// AFTER
final remoteCapture = RemoteCaptureRepository(dio, syncManager);
final capture = remoteCapture;
final processor = SyncProcessor(syncManager, {
  kOpCreateCaptureSession: (upload) =>
      remoteCapture.postQueuedCaptureSession(upload.idempotencyKey, upload.payload),
});
```

Also add `DeviceRepository` to both branches:
```dart
// mock branch
final deviceRepo = MockDeviceRepository();

// live branch
final deviceRepo = RemoteDeviceRepository(dio);
```

Add `DeviceRepository` to `AppDependencies` fields and `RepositoryProvider` in `app.dart`.

Mock path: `MockCaptureRepository` + no-op handler stays as-is.

---

## Tests to add

1. **`test/features/capture/data/remote_capture_repository_test.dart`** — verify `listSessions` URL and `postQueuedCaptureSession` builds correct path + body from payload.
2. **`test/features/capture/application/capture_cubit_test.dart`** — `selectDevice` loads calibrations; `createSession` fails if no device selected; `pollJobUntilTerminal` emits `pollingJob: null` when job is terminal.
3. **`test/features/capture/data/device_repository_test.dart`** — `MockDeviceRepository` returns 1 device and 1 calibration.

---

## Boundaries / guardrails

- Frame upload (multipart artifact POST) is NOT in scope — ZED 2 is M2+.
- Navigation on job complete goes to `/quarries/{qid}/reports` (the list), NOT auto-opening a specific report. Report auto-open requires `report_id` in `AnalysisJobRead` — separate backend task (GAP-3).
- Do NOT hardcode device ID or calibration ID — always fetch from backend.
- `isClosed` check in `pollJobUntilTerminal` prevents emitting on a disposed cubit.
- Mock path stays fully functional with `MockCaptureRepository` — no regression on `ZM_USE_MOCKS=true`.

---

## Acceptance

```bash
cd mobile
flutter test                     # ≥ 48 tests, all passing
flutter build apk --debug \
  --dart-define=ZM_USE_MOCKS=false \
  --dart-define=ZM_API_BASE_URL=http://10.0.2.2:8000 \
  --dart-define=ZM_KC_ISSUER=http://10.0.2.2:8080/realms/zmetrics
# Must compile without errors

# Manual smoke (with running backend + dev seed):
# 1. Open passport detail → tap "Captures"
# 2. Device dropdown shows DEMO-ZED2-0001
# 3. Select device → calibration dropdown appears
# 4. Select calibration → "Start session" FAB activates
# 5. Tap "Start session" → session appears with orange cloud icon
# 6. Wait for sync → cloud icon turns green
# 7. Tap "Analyse" → progress bar appears
# 8. Wait ~5s (mock pipeline) → navigates to quarry reports list
# 9. New report visible in list
```

## When done

Report: files changed, test count, confirm each deliverable.
