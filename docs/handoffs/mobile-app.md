# Handoff: mobile (Flutter web + Android)

**Date:** 2026-06-05
**Scope:** `mobile/` only. No changes to `backend/`, `worker/`, or `infra/`.

---

## Status: implemented, analyzes clean, 26 tests passing

Single Flutter codebase targeting **web and Android** (mobile-first, offline-first).
Runs **standalone with mock services** — no backend, Keycloak, MinIO, or worker
required. External services are stubbed behind interfaces and switched on via one
flag when they come online.

Verified locally with Flutter 3.44.1 / Dart 3.12.1:
- `dart run build_runner build --delete-conflicting-outputs` → 30 generated files
- `flutter analyze` → **No issues found**
- `flutter test` → **26/26 passed**
- `flutter build web` → succeeds (web platform scaffolding added)

### How to run

```powershell
cd mobile
C:\flutter\bin\flutter pub get
C:\flutter\bin\dart run build_runner build --delete-conflicting-outputs   # generates *.freezed.dart / *.g.dart
C:\flutter\bin\flutter run -d chrome          # web
C:\flutter\bin\flutter run -d <android-device># Android
C:\flutter\bin\flutter test
```

Default boot is **mock mode**. To point at a real backend later:

```powershell
flutter run --dart-define=ZM_USE_MOCKS=false --dart-define=ZM_API_BASE_URL=http://10.0.2.2:8000
```

---

## What was built

### Architecture (feature-first, per rules/mobile.md)
```
lib/
  core/           config, DI composition root, network (dio + interceptors), auth, router
  features/<f>/   domain/ (freezed models) · data/ (repositories) · application/ (cubits) · presentation/ (screens)
  shared/         offline/ (SyncManager, SyncProcessor, SyncCubit) · widgets/ · bloc/ (DataState)
```

### Layers
| Layer | Implementation |
|-------|----------------|
| Domain models | `freezed` + `json_serializable`, snake_case `@JsonKey`, enum `@JsonValue` matching backend |
| State mgmt | `flutter_bloc` Cubits; states are native Dart 3 `sealed class` (exhaustive `switch`) |
| Data access | Repository interface + `Mock*` (in-memory stub) + `Remote*` (Dio) per feature |
| HTTP | `dio` with `AuthInterceptor` (bearer + 401-refresh-retry-once) and `RetryInterceptor` (503 backoff) |
| Auth | OIDC PKCE via `flutter_appauth`; tokens in `flutter_secure_storage` only; `MockAuthRepository` for dev |
| Offline | `SyncManager` interface → `SqfliteSyncManager` (device) / `InMemorySyncManager` (web/tests); `SyncProcessor` drains queue; `SyncCubit` triggers on connectivity |
| Routing | `go_router` with auth-guard redirect to `/login` |

### Feature flow implemented (full domain vertical)
`Quarries → Sections → Passports (list/detail/create) → Capture sessions → Analysis report → Recommendation review`

### Service stubs (per "ML / MinIO etc. not connected yet — make stubs")
- **Backend REST**: `Remote*Repository` classes are written against `docs/api_contract.md` but unused while `useMockServices=true`. `Mock*Repository` serve seeded in-memory data.
- **Keycloak**: real `OidcService` present; `MockAuthRepository` gives one-tap fake login + constant bearer token in mock mode.
- **MinIO / file upload**: not implemented. Capture sessions record a placeholder `frame_count`; frame/artifact upload is out of scope (M2+, ZED 2). No MinIO client added.
- **Worker / CV pipeline**: not contacted. The seeded report is explicitly `AnalysisMethod.mock` and carries the mandated synthetic-data label.

---

## Safety constraints honoured (rules/product-safety.md)

- **No auto-apply of blast parameters.** `parameter_suggestions` render read-only; there is no code path writing them into a passport.
- **Manual passport entry.** `PassportCreateScreen` starts every field empty with an explicit on-screen notice — never prefilled from AI.
- **Recommendations require human review.** Seed/mock recommendations are `requires_human_review`; the UI offers only explicit human transitions (accept/reject/mark-reviewed). Asserted in tests.
- **State transitions are explicit & single-action.** Passport submit/approve/revise map 1:1 to backend actions; no bulk action, no time/AI auto-advance.
- **Mock pipeline labelled.** `MockPipelineBadge` shows the exact required string `⚠ Mock pipeline — results are synthetic`; widget test asserts it.
- **Scientific precision preserved.** P10/P50/P80 displayed at full precision; test guards round-tripping.
- **Confidence warnings.** Report shows a warning when `confidence_score < 0.5` and a softer note for `< 0.8`.
- **No secrets / tokens logged.** Tokens live only in secure storage; interceptor never logs them.

---

## Tests (26, pure-Dart — no device/emulator needed)
- `test/models/json_round_trip_test.dart` — freezed JSON parsing, enum mapping, precision, local-only `synced` field.
- `test/repositories/mock_repositories_test.dart` — quarry/section CRUD, passport state machine, **safety invariants**, offline enqueue.
- `test/offline/sync_test.dart` — queue dedupe, retry, exhaustion surfacing, `SyncProcessor` drain.
- `test/bloc/cubits_test.dart` — quarries/passport/report/auth cubits.
- `test/widget/mock_pipeline_badge_test.dart` — mandated synthetic-data label renders.

---

## Architectural issues (logged, NOT in scope — per instructions)

### MOB-001: Cubit states use native `sealed class`, not freezed unions
`rules/mobile.md` says "states are freezed sealed classes". I used Dart 3 native
`sealed class` (codegen-free, exhaustive). Functionally equivalent; the rule predates
Dart 3 sealed classes. If strict freezed unions are required, migration is mechanical.
Domain models DO use freezed + json_serializable as mandated.

### MOB-002: `Decimal` JSON encoding assumption
`Remote*Repository` parse numeric blast/granulometry fields as JSON `num` (Dart `double`).
If the backend serialises SQLAlchemy `Numeric`/`Decimal` as JSON **strings**, parsing
will throw. Confirm the backend's Pydantic serialization mode and add a string→double
`JsonConverter` if needed. Mock mode is unaffected.

### MOB-003: Capture / BlastEvent endpoints are assumed
`docs/api_contract.md` documents `POST /captures/{id}/jobs` and analysis reads, but does
**not** define create-capture-session or list-by-blast-event routes. `RemoteCaptureRepository`
assumes `POST /api/v1/capture-sessions` (with `Idempotency-Key` header) and
`GET /api/v1/blast-events/{id}/captures`. These need to be reconciled with the backend
contract before `useMockServices=false`. The offline queue already sends an idempotency key.

### MOB-004: Token refresh on web
`flutter_appauth` web support differs from mobile; the OIDC redirect/refresh flow has only
been reasoned about, not exercised on web (mock mode bypasses it). Validate the PKCE flow on
web when Keycloak is wired.

### MOB-005: Per-quarry RBAC not reflected in UI
The app shows all action buttons (submit/approve/revise) based on passport status, relying on
the backend to enforce per-quarry roles (`QuarryUserAccess`). The mock has no role model.
When auth is live, hide/disable actions by the user's role on the current quarry to avoid
dead-end 403s. (Backend handoff AUD-004 also notes the analysis router currently skips the
role check.)

---

## Session 2 (2026-06-06) — backend integration + RBAC + reports

Added on top of the initial scaffold, after the backend MVP/auth fixes
(`backend-mvp-fixes.md`, `mobile-auth-notes.md`):

- **Live backend mode** (`--dart-define=ZM_USE_MOCKS=false`): Remote repos aligned
  to the implemented API (tolerant list parsing for both bare-array and `{items}`
  pagination via `parseJsonList`), dev ROPC login (public `zmetrics-mobile`
  client), `mock ↔ backend` switch, "Seed demo data" button.
- **Role-aware UI gating** from JWT `realm_access.roles` (coarse hint;
  backend per-quarry RBAC is authoritative): create-quarry → admin; section /
  passport create + submit + revise → blaster+; approve + complete → admin.
- **Passport COMPLETE** action (ACTIVE→COMPLETED, admin) — new backend endpoint.
- **Reports list per quarry** (`GET /quarries/{id}/reports`) + screen + nav from
  sections/passport. Mock-pipeline **safety badge** restored in backend mode by
  deriving method from the report title ("⚠ Mock pipeline").
- **Graceful auth errors**: failed token refresh on 401 → sign out → /login;
  403 "Account is inactive" → forced logout; other 403 → clear "no permission"
  message (not a logout). `friendlyError()` helper.
- Tests: **39/39 pass**, `flutter analyze` clean.

### Remaining mobile backlog (next)
- **Report export** download — backend `GET /reports/{id}/export` exists (blaster+,
  JSON); needs web/file-save plumbing (`dart:html` anchor on web / path_provider on device).
- **Analysis happy-path from app**: capture-session create + frame upload (MinIO) +
  `POST /captures/{id}/jobs` + poll job until completed. Blocked on the capture flow
  (blast-event/device/calibration chain) — still stubbed.
- **Per-quarry role gating** once backend exposes it (TASK GAP-4); current gating is
  a realm-role heuristic.
- **Server-side pagination UI** (load-more) — lists currently read page 1 only.
- **Web OIDC PKCE** for production (dev uses ROPC); **Android PKCE** run.
- **Granulometry metrics in backend mode** — blocked on TASK GAP-1 (no
  GET-analysis-result-by-id endpoint); screen shows an explicit placeholder.

### MOB-006: No real frame capture / MinIO upload
Capture is a metadata placeholder only. ZED 2 stereo capture (Camera2/ZED SDK) and MinIO
presigned-URL upload are M2+ and intentionally stubbed.
