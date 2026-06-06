# Handoff: M1 backend+mobile complete — pending commit & rebuild

**Date:** 2026-06-06
**Session goal:** Close all M1 backend gaps (use-case coverage, mobile↔backend integration, per-quarry role exposure) and wire Flutter mobile to the live backend.
**Status:** completed — all features working, code NOT yet committed to git

---

## What was done

### Backend (backend/)

1. **Keycloak issuer decoupled** (`config.py`, `docker-compose.yml`)
   - Split `keycloak_url` into `kc_internal_url` (JWKS fetch) + `kc_public_url` (token issuer validation)
   - Keycloak `KC_HOSTNAME_URL=http://localhost:8080` pinned so every token carries the same `iss`

2. **Full Quarry + SiteSection CRUD** (`routers/quarries.py`, `schemas/quarry.py`)
   - Paginated list (`{items,total,page,page_size}` envelope — fixed on all list endpoints)
   - `POST /quarries` requires `require_any_admin`

3. **Passport complete state machine** (`routers/passports.py`)
   - `POST /{id}/complete` (ACTIVE → COMPLETED) added
   - AuditLog writes confirmed for all transitions

4. **Admin user management** (`routers/admin.py`, `schemas/user.py`)
   - `PATCH /admin/users/{id}` — update `full_name` / `is_active`; AuditLog
   - `DELETE /admin/users/{id}` — soft deactivation; blocks self-delete (400)

5. **`GET /api/v1/me/access`** (`routers/me.py`, `main.py`)
   - Returns `[{quarry_id, quarry_name, role_name, role_level}]` for the caller
   - Used by mobile `AccessCubit` for precise per-quarry UI gating

6. **`GET /reports/{id}/export`** (`routers/reports.py`)
   - JSON download (PDF is M2+); labelled `"⚠ Mock pipeline"`; BLASTER+ required

7. **Worker auto-creates Report + Recommendation** (`worker/app/db_models.py`, `worker/app/tasks/pipeline.py`)
   - After successful pipeline `_create_report_and_recommendation()` fires
   - `Recommendation.status = REQUIRES_HUMAN_REVIEW` invariant enforced

8. **Dev seed endpoint** (`routers/admin.py`)
   - `POST /api/v1/admin/dev-seed` → `{quarry_id, section_id, passport_id, report_id, recommendation_id}`

9. **Role-gating on analysis/reports** (`routers/analysis.py`, `routers/reports.py`)
   - Was `get_current_user` only (AUD-004); now `require_quarry_role(SURVEYOR+)`

10. **New router files** (untracked):
    - `routers/blast_events.py`, `routers/capture_sessions.py`, `routers/devices.py`, `routers/me.py`
    - `schemas/blast.py`
    - `migrations/versions/04dd1eabaa39_initial_schema.py`, `0002_seed_roles.py`
    - `tests/test_auth.py` (10 tests), `tests/test_blast_capture.py`

### Mobile (mobile/)

Full Flutter app with real backend integration:
- `core/auth/` — `AuthCubit`, `AuthRepository`, `AccessCubit`, `AccessRepository`, `AuthUser.freezed`, `QuarryAccess.freezed`, `jwt_decode`, `role_level`, `dev_password_auth_repository`
- `features/` — quarries, passport, capture, report screens
- `core/di.dart` — dependency injection
- `core/router.dart` — GoRouter with auth guard
- `lib/app.dart` — BlocProvider tree, `ZM_USE_MOCKS` dart-define switch
- Offline sync expanded: `sync_cubit.dart`, `sync_processor.dart`, `pending_upload.dart`

**Run mobile (web dev mode, backend=live):**
```powershell
cd mobile
flutter run -d web-server --web-port 5173 --dart-define=ZM_USE_MOCKS=false
```

---

## Files changed (since initial commit d7a1983)

28 modified files (+1252 −165 lines) + ~50 new untracked files. See `git diff --stat HEAD` for full list.

---

## What was NOT done / is blocked

| Item | Reason |
|------|--------|
| **All M1 work uncommitted** | Git is still at d7a1983 (M0 scaffold). Everything since is local only. |
| **Container image stale** | Running `infra-backend-1` doesn't have `GET /me/access` or paginated lists. Needs rebuild. |
| Per-section RBAC | Domain uses per-quarry roles; per-section would need schema change. Deferred M2. |
| PDF report generation | WeasyPrint/wkhtmltopdf integration. M2+. |
| Keycloak user deactivation sync | DB deactivation only; Keycloak session lives until token expiry. M2. |
| `AuditLog.ip_address` | Always NULL — needs request-context middleware. M2. |
| `GET /api/v1/analysis-results/{id}` | GAP-1: ReportRead has `analysis_result_id` but no standalone result endpoint. Mobile report screen can't show P10/P50/P80 in backend mode. |
| `analysis_method` on ReportRead | GAP-2: product-safety.md requires mock-vs-real label in reports. |

---

## Known issues / tech debt

- `worker/app/db_models.py` stubs hand-synced with backend models — must update if `Report`/`Recommendation` schema changes in backend. Marked `# SYNC: backend/app/db/models/report.py`.
- `verify_aud: False` in JWT decode — intentional (see `docs/handoffs/backend-auth.md` §AUD-002).
- `require_any_admin` allows admin of quarry A to create quarry B. Fine for single-operator; multi-tenant scoping is M2.

---

## Test state

- 31/31 backend tests pass (`pytest -v`, confirmed)
- `test_auth.py` — 10 auth tests
- **Missing tests (write next session):**
  - `test_me_access.py` — GET /me/access returns correct roles; empty for no access
  - `test_report_export.py` — export returns JSON; 403 for USER role
  - `test_user_management.py` — PATCH updates name; DELETE sets `is_active=false`; self-delete blocked

---

## Next session: start here

1. **Read:** `@CLAUDE.md`, `@docs/handoffs/mobile-auth-notes.md`, `@docs/handoffs/backend-auth.md`
2. **First task — commit all M1 work:**
   ```powershell
   git add backend infra mobile worker docs
   git commit -m "feat(m1): backend MVP + Flutter mobile integration"
   git push
   ```
3. **Rebuild containers** to bake in all changes:
   ```powershell
   docker compose -f infra\docker-compose.yml build backend worker
   docker compose -f infra\docker-compose.yml up -d --force-recreate backend worker
   ```
4. **Run tests** to confirm clean state:
   ```powershell
   docker compose -f infra\docker-compose.yml exec backend pytest -v
   ```
5. **Write missing tests** (`test_me_access`, `test_report_export`, `test_user_management`)
6. **Close GAP-1**: add `GET /api/v1/analysis-results/{id}` so mobile report screen shows P10/P50/P80

---

## Commands to verify current state

```powershell
# Start services
docker compose -f infra\docker-compose.yml up -d

# Rebuild + restart backend after code changes
docker compose -f infra\docker-compose.yml build backend worker
docker compose -f infra\docker-compose.yml up -d --force-recreate backend worker

# Run tests
docker compose -f infra\docker-compose.yml exec backend pytest -v

# Migration state (expect: 0002)
docker compose -f infra\docker-compose.yml exec backend alembic current

# Smoke-test auth + me/access
$token = (Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8080/realms/zmetrics/protocol/openid-connect/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "grant_type=password&client_id=zmetrics-mobile&username=admin-user&password=changeme&scope=openid"
).access_token

Invoke-RestMethod "http://localhost:8000/api/v1/me/access" -Headers @{Authorization="Bearer $token"}
# Expected: [{quarry_name:"Demo Quarry", role_name:"admin", role_level:4}]

Invoke-RestMethod "http://localhost:8000/api/v1/quarries" -Headers @{Authorization="Bearer $token"}
# Expected: {items:[{name:"Demo Quarry",...}], total:1, page:1, page_size:20}
```
