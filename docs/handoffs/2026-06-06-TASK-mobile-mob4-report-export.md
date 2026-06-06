# MOB-4 — Report Export (share sheet + JSON download)

**Layer:** `mobile/` only  
**Depends on:** MOB-3 done ✅  
**Backend pre-condition:** `GET /api/v1/reports/{id}/export` already exists (returns `application/json`, role = BLASTER)  
**Target test count:** 55 → ~63

---

## Goal

Add an **Export** button to `ReportScreen`. Tapping it:

1. Calls `GET /api/v1/reports/{id}/export` (auth-gated, BLASTER role on the quarry)
2. Writes the response bytes to `{tempDir}/report_{reportId}_{yyyyMMdd}.json`
3. Opens the Android share sheet (`share_plus`), so the user can save to Downloads, send via email, Drive, etc.

Mock path: serialise the in-memory `Report` object to JSON bytes, then follow the same write → share flow.

---

## New packages (`pubspec.yaml`)

```yaml
# File sharing / Downloads
share_plus: ^7.2.1
path_provider: ^2.1.3
```

No new Android permissions needed: `getTemporaryDirectory()` is app-private (no `WRITE_EXTERNAL_STORAGE`). `share_plus` 7.x bundles its own `FileProvider` via manifest merge — no manual `AndroidManifest.xml` change is required. If the build fails with a FileProvider conflict, add the following to `android/app/src/main/AndroidManifest.xml`:

```xml
<provider
    android:name="androidx.core.content.FileProvider"
    android:authorities="${applicationId}.fileprovider"
    android:exported="false"
    android:grantUriPermissions="true">
  <meta-data
      android:name="android.support.FILE_PROVIDER_PATHS"
      android:resource="@xml/file_paths"/>
</provider>
```
and create `android/app/src/main/res/xml/file_paths.xml`:
```xml
<?xml version="1.0" encoding="utf-8"?>
<paths>
  <cache-path name="cache" path="."/>
</paths>
```

---

## Files to change

### 1. `mobile/lib/features/report/data/report_repository.dart`

Add to the abstract interface:

```dart
/// Returns raw JSON bytes of the export payload.
/// Requires BLASTER role on the quarry (enforced server-side).
Future<Uint8List> exportReport(String reportId);
```

**`MockReportRepository.exportReport`** — serialise the current in-memory report:

```dart
@override
Future<Uint8List> exportReport(String reportId) async {
  final report = _require(reportId);
  final json = jsonEncode({
    'export_format': 'json_placeholder',
    'note': '⚠ Mock pipeline — results are synthetic.',
    'report': {'id': report.id, 'summary': report.summary},
    'analysis_result': report.analysisResult == null
        ? null
        : {
            'p10_mm': report.analysisResult!.p10Mm,
            'p50_mm': report.analysisResult!.p50Mm,
            'p80_mm': report.analysisResult!.p80Mm,
          },
  });
  return Uint8List.fromList(utf8.encode(json));
}
```

**`RemoteReportRepository.exportReport`** — download as raw bytes:

```dart
@override
Future<Uint8List> exportReport(String reportId) async {
  try {
    final res = await _dio.get<List<int>>(
      '/api/v1/reports/$reportId/export',
      options: Options(responseType: ResponseType.bytes),
    );
    return Uint8List.fromList(res.data ?? []);
  } on DioException catch (e) {
    throw ApiException.fromDio(e);
  }
}
```

---

### 2. `mobile/lib/features/report/application/report_cubit.dart`

Add `export()` method. The cubit writes the file and opens the share sheet directly — no extra service class.

```dart
import 'dart:io';
import 'package:intl/intl.dart';          // for date formatting
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

/// Fetches the export JSON, writes to temp, opens the share sheet.
/// Throws [ApiException] on network error; caller shows snackbar.
Future<void> export() async {
  final bytes = await _repo.exportReport(reportId);
  final dir = await getTemporaryDirectory();
  final date = DateFormat('yyyyMMdd').format(DateTime.now().toUtc());
  final file = File('${dir.path}/report_${reportId}_$date.json');
  await file.writeAsBytes(bytes, flush: true);
  await Share.shareXFiles(
    [XFile(file.path, mimeType: 'application/json')],
    subject: 'ZMetrics report $reportId',
  );
}
```

> **Note on `intl`:** already pulled transitively. Use `intl` for date if available;
> otherwise just inline `DateTime.now().toUtc()` formatted with string interpolation.

---

### 3. `mobile/lib/features/report/presentation/report_screen.dart`

- Add an `IconButton(icon: Icon(Icons.ios_share))` to `ZScaffold`'s actions (or an `OutlinedButton` at the bottom of `_ReportBody`).
- The button must be disabled while loading (`state is DataLoading`) and while export is in progress.
- Use a local `bool _exporting` (wrap `_ReportBody` as `StatefulWidget` or use `ValueNotifier`) to track export-in-progress.
- On tap: call `cubit.export()`, show a `CircularProgressIndicator.small` while waiting, show error snackbar on failure.

Minimal UI sketch:

```dart
// In ZScaffold actions
IconButton(
  icon: _exporting
      ? const SizedBox(
          width: 18, height: 18,
          child: CircularProgressIndicator(strokeWidth: 2))
      : const Icon(Icons.ios_share),
  tooltip: 'Export JSON',
  onPressed: state is DataLoaded && !_exporting ? _export : null,
)

Future<void> _export(BuildContext context) async {
  setState(() => _exporting = true);
  try {
    await context.read<ReportCubit>().export();
  } catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(friendlyError(e))));
    }
  } finally {
    if (mounted) setState(() => _exporting = false);
  }
}
```

Because `ReportScreen` is currently a `StatelessWidget`, convert it to a `StatefulWidget` — or convert only the inner scaffold part. Prefer converting `ReportScreen` itself (minimal change).

---

## Tests (`mobile/test/features/report/`)

Add `report_export_test.dart` with ~8 tests:

1. **Mock export returns valid JSON bytes** — calls `MockReportRepository.exportReport('r-1')`, decodes, checks `export_format == 'json_placeholder'` and `p80_mm` present.
2. **Remote export: success path** — mock Dio returns 200 with bytes; `exportReport` returns matching `Uint8List`.
3. **Remote export: 403 → ApiException with statusCode 403** — Dio throws 403; wrapped correctly.
4. **Remote export: 404 → ApiException with statusCode 404**.
5. **Cubit.export: writes file and calls Share** — inject a fake `ReportRepository` returning known bytes; stub `getTemporaryDirectory`; verify `Share.shareXFiles` called with correct path. *(Use `mockito` or manual fake — no platform calls in unit test; see note.)*
6. **Cubit.export: ApiException propagates** — repo throws `ApiException('403')`, cubit's `export()` rethrows it.

> **Testing note on path_provider + share_plus:** both need platform channels which aren't available in pure unit tests. The standard pattern is to set up path_provider's mock path with `setUpAll(() => PathProviderPlatform.instance = FakePathProvider())` and to verify `Share.shareXFiles` via a method channel mock or by injecting the share call behind a thin interface. If this adds excessive complexity, it's acceptable to test only the repository layer (items 1-4) and do a widget test for the button's loading state (items 5-6 as widget test with mocked cubit).

---

## Acceptance criteria

- [ ] "Export" button visible on `ReportScreen`; disabled while loading/exporting
- [ ] Tapping it shows spinner; then Android share sheet appears (or error snackbar on 403)
- [ ] Mock path works without a backend connection (`config.useMockServices = true`)
- [ ] BLASTER role enforcement is server-side only — no client-side role gate (403 shows snackbar)
- [ ] `flutter test` passes: ~63 tests (8 new)
- [ ] `flutter analyze` shows no new warnings

---

## What NOT to change

- Do not add a "Save to Downloads" button that bypasses the share sheet — `MediaStore` API requires `MethodChannel` native code and is out of scope.
- Do not prefill any passport field from the exported data (product-safety.md).
- Do not auto-trigger export after polling completes — export is always an explicit user action.
