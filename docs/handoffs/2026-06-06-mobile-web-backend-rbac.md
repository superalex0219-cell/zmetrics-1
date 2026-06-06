# Handoff: mobile web + backend integration & per-quarry RBAC

**Date:** 2026-06-06
**Session goal:** Build the Flutter web/mobile app, wire it to the live backend, and add per-quarry role-based UI gating.
**Status:** partial (mobile feature-complete for M1 scope; one backend ops step pending)
**Scope guard:** worked in `mobile/` only; backend/infra changes were delegated to the backend colleague via `docs/handoffs/TASK-backend-mobile-integration.md`.

## What was done (mobile/)

- **Full Flutter app** (web + Android), feature-first: `core/` (config, DI, network, auth, router), `features/{quarries,passport,capture,report}/{domain,data,application,presentation}`, `shared/{offline,widgets,bloc}`.
- **Backend integration** (`--dart-define=ZM_USE_MOCKS=false`): Remote repos aligned to the implemented API; `parseJsonList` tolerates both bare-array and `{items}` pagination; dev ROPC login via public `zmetrics-mobile` client; `mock ↔ backend` switch; "Seed demo data" button → [dev_seed_service.dart](mobile/lib/core/dev/dev_seed_service.dart).
- **Auth**: [dev_password_auth_repository.dart](mobile/lib/core/auth/dev_password_auth_repository.dart), tokens in secure storage; Dio [auth_interceptor.dart](mobile/lib/core/network/auth_interceptor.dart) adds bearer + refresh-on-401; failed refresh / `403 Account is inactive` → forced logout via [auth_event_bus.dart](mobile/lib/core/auth/auth_event_bus.dart).
- **Per-quarry RBAC (GAP-4)**: consumes `GET /api/v1/me/access` via [access_repository.dart](mobile/lib/core/auth/access_repository.dart) + [access_cubit.dart](mobile/lib/core/auth/access_cubit.dart); UI gating in [auth_context.dart](mobile/lib/core/auth/auth_context.dart) (`canManageBlastingOn`/`canApproveOn`/`isAdminAnywhere`). **Falls back to JWT realm role if the endpoint is unavailable.**
- **Passport lifecycle**: list/detail/create + submit/approve/**complete**/revise, role- and status-gated ([passport_detail_screen.dart](mobile/lib/features/passport/presentation/passport_detail_screen.dart)).
- **Reports**: per-quarry list ([reports_list_screen.dart](mobile/lib/features/report/presentation/reports_list_screen.dart)) + detail with recommendation review; mock-pipeline safety badge derived from report title; explicit "metrics unavailable" placeholder (backend GAP-1).
- **Offline-first**: `SyncManager` (sqflite on device / in-memory on web) + `SyncProcessor` + `SyncCubit` + offline banner.
- **Quality**: `flutter analyze` clean; **41/41 tests** pass; web build OK. Flutter SDK installed at `C:\flutter` (3.44.1 / Dart 3.12.1).

## Files changed

```
28 tracked files changed, 1252 insertions(+), 165 deletions(-)
(mobile tracked: app.dart, core/router.dart, main.dart, core/auth/oidc_service.dart,
 shared/offline/sync_manager.dart, pubspec.yaml)
+ ~80 new untracked mobile files under mobile/lib, mobile/test, mobile/android, mobile/web
+ docs/handoffs/*  (this file, TASK-backend-mobile-integration.md, mobile-app.md)
```
Note: backend/worker/infra files also appear modified in `git status` but were authored by the backend colleague, NOT this mobile session.

## What was NOT done / is blocked

- **Capture / analysis happy-path from the app** — stubbed (mock). Needs blast-event + device + calibration chain + frame upload (MinIO). M2+.
- **Granulometry metrics (P10/P50/P80) in backend mode** — blocked on backend **GAP-1** (no `GET /analysis-results/{id}`); screen shows a placeholder.
- **Report export download** — backend endpoint exists (`GET /reports/{id}/export`, blaster+); mobile web/file-save plumbing not built yet.
- **Web OIDC PKCE** (production auth) and an actual **Android run** — dev uses ROPC; not yet done.

## Known issues / tech debt

- ⚠ **Running `infra-backend-1` returns 404 for `/api/v1/me/access`** — endpoint is in source but the container image is stale; needs `docker compose build backend && up -d backend`. Until then the app uses the realm-role fallback. (Backend/ops task — see TASK doc "UPDATE 2026-06-06 — GAP-4".)
- Report **review** buttons are not per-quarry gated (the `/reports/:id` route lacks quarry context) — rely on backend 403 + friendly message. Acceptable.
- Lists read **page 1 only** — server-side pagination UI (load-more) deferred.
- Cubit states use native Dart 3 `sealed class` instead of freezed unions (MOB-001) — intentional, codegen-free.

## Next session: start here

1. Read: @CLAUDE.md, @docs/handoffs/mobile-app.md, @docs/handoffs/TASK-backend-mobile-integration.md, @.claude/rules/mobile.md
2. First task: confirm backend image rebuilt → verify `GET /api/v1/me/access` returns 200 and the app switches from realm-role fallback to precise per-quarry gating (log out / back in).
3. Then: implement **report export** download (web `dart:html` anchor / device `path_provider`), gated to blaster+.
4. Then: when backend GAP-1 lands, render real P10/P50/P80 in the report screen.

## Commands to verify current state

```powershell
# Mobile: deps + codegen + checks
cd mobile
C:\flutter\bin\flutter pub get
C:\flutter\bin\dart run build_runner build --delete-conflicting-outputs
C:\flutter\bin\flutter analyze
C:\flutter\bin\flutter test                 # expect 41/41

# Run web against the backend (CORS-allowed origin)
C:\flutter\bin\flutter run -d web-server --web-port 5173 --dart-define=ZM_USE_MOCKS=false
#   login: admin-user / changeme   →  http://localhost:5173

# Backend stack + the pending rebuild for /me/access
docker compose -f infra\docker-compose.yml ps
docker compose -f infra\docker-compose.yml build backend
docker compose -f infra\docker-compose.yml up -d backend
```
