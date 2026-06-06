# TASK (mobile): wire analysis-result endpoint + clean dead workarounds

**Date:** 2026-06-06
**From:** curating chat (post SEC-1/2/3/DB-1 security batch)
**Layer:** `mobile/` ONLY — `features/report/` (data, domain, application, presentation)
**Review agent:** `mobile-reviewer`
**Priority:** P1 — without this, granulometry (P10/P50/P80) is invisible in live mode

> **Precondition:** HEAD must be `1d9ad72` or newer.
> Backend `GET /api/v1/analysis-results/{id}` is live since `8a200b6`. Verify:
> `git log --oneline -5 | grep analysis-results`

---

## Context

Backend GAP-1 was closed (`8a200b6`): `GET /api/v1/analysis-results/{result_id}` now exists and
returns full granulometry (P10/P50/P80, Rosin-Rammler, size_distribution).

Backend GAP-2 was also closed: `ReportRead` now always includes `analysis_method: "mock"|"real"`.

Mobile hasn't been updated yet. Two workarounds were added at the time and are now dead:

1. `_withDerivedMethod()` in `RemoteReportRepository` — derives method from title text. Backend sends
   the field directly, so this heuristic is no longer needed and must be removed.
2. `@Default(AnalysisMethod.real)` in `report.dart` comment says "backend doesn't expose field yet".
   Backend now always sends it; the default should be changed to `.mock` (fail-safe: shows warning
   badge if field is absent vs silently hiding it).

Additionally, `Report` never mapped `analysis_result_id` from JSON, so `ReportCubit` had no UUID
to pass to the new endpoint — the report screen shows a placeholder for granulometry in live mode.

---

## Deliverable 1 — Add `analysisResultId` to `Report` domain model

**File:** `mobile/lib/features/report/domain/report.dart`

Add the field:
```dart
@JsonKey(name: 'analysis_result_id') String? analysisResultId,
```

Change the default for `analysisMethod`:
```dart
@JsonKey(name: 'analysis_method')
@Default(AnalysisMethod.mock)   // was .real — .mock is fail-safe (shows warning badge)
AnalysisMethod analysisMethod,
```

Update the comment on the field — backend now always sends `analysis_method`.

After editing `report.dart`, regenerate freezed/json files:
```powershell
cd mobile
dart run build_runner build --delete-conflicting-outputs
```

This will regenerate `report.freezed.dart` and `report.g.dart`. Commit both generated files.

---

## Deliverable 2 — Add `getAnalysisResult` to repository

**File:** `mobile/lib/features/report/data/report_repository.dart`

Add to the abstract interface:
```dart
/// Fetches the granulometry result for a report.
/// Returns null if the result is not yet available (job still running).
Future<AnalysisResult?> getAnalysisResult(String analysisResultId);
```

**`MockReportRepository`** — already has `analysisResult` embedded in the seeded report.
Implement by scanning `_reports` for a matching result id:
```dart
@override
Future<AnalysisResult?> getAnalysisResult(String analysisResultId) async {
  for (final r in _reports.values) {
    if (r.analysisResult?.id == analysisResultId) return r.analysisResult;
  }
  return null;
}
```

**`RemoteReportRepository`** — remove `_withDerivedMethod()` entirely (dead workaround).
Remove all three call sites (in `listReports` and `getReport`).

Add `getAnalysisResult`:
```dart
@override
Future<AnalysisResult?> getAnalysisResult(String analysisResultId) async {
  try {
    final res = await _dio.get('/api/v1/analysis-results/$analysisResultId');
    return AnalysisResult.fromJson(res.data as Map<String, dynamic>);
  } on DioException catch (e) {
    final ex = ApiException.fromDio(e);
    if (ex.statusCode == 404) return null;
    throw ex;
  }
}
```

---

## Deliverable 3 — Wire in `ReportCubit.load()`

**File:** `mobile/lib/features/report/application/report_cubit.dart`

After fetching the report and recs, fetch the analysis result if `analysisResultId` is non-null:
```dart
Future<void> load() async {
  emit(const DataLoading());
  try {
    final report = await _repo.getReport(reportId);
    final recs = await _repo.listRecommendations(reportId);
    AnalysisResult? result;
    if (report.analysisResultId != null) {
      result = await _repo.getAnalysisResult(report.analysisResultId!);
    }
    emit(DataLoaded(report.copyWith(
      recommendations: recs,
      analysisResult: result,
    )));
  } on ApiException catch (e) {
    emit(DataFailure(e.message));
  } catch (e) {
    emit(DataFailure('$e'));
  }
}
```

---

## Deliverable 4 — Update `ReportScreen` placeholder

**File:** `mobile/lib/features/report/presentation/report_screen.dart`

The current placeholder at line 57–69 says "pending an analysis-result endpoint". Remove that
comment and replace the fallback text with something honest:
```dart
else
  const Padding(
    padding: EdgeInsets.symmetric(vertical: 12),
    child: Text(
      'Analysis result not yet available — job may still be running.',
      style: TextStyle(color: Colors.grey),
    ),
  ),
```

This case will now only appear if the job is running or failed (not if backend is missing the
endpoint), so the message should reflect that.

---

## Boundaries / guardrails

- Touch `mobile/lib/features/report/` only. No core/, no other features.
- Do NOT add OIDC / flutter_appauth wiring — that's a separate M2 task.
- Do NOT implement SyncProcessor handlers for capture — that's M2.
- The `_withDerivedMethod` workaround MUST be removed entirely — do not keep it as a fallback.
  The backend contract is stable. A title-text heuristic in live code is a maintenance hazard.
- `analysisResult` in `Report` stays `AnalysisResult?` — null is a valid state when job is still running.
- Safety: `MockPipelineBadge` must still show when `analysisMethod.isMock` — do not break this path.

## Acceptance

```powershell
# In the mobile directory:
cd mobile
dart run build_runner build --delete-conflicting-outputs
# No errors

flutter test
# All tests pass (was 41, no regressions expected)

# Manual smoke (Android emulator or device):
# 1. Mock mode: report screen shows MockPipelineBadge + granulometry values ✅
# 2. Live mode (ENABLE_DEV_SEED=true backend running):
#    - Login → quarry → report → granulometry values visible (not "not available" placeholder) ✅
#    - analysis_method: "mock" from backend → MockPipelineBadge visible ✅
```

## When done

Report back: files changed, test count, confirmation that `_withDerivedMethod` is gone and
granulometry renders from live backend.
