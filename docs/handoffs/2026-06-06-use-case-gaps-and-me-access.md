# Handoff: Use-case gap closure + GET /me/access

**Date:** 2026-06-06  
**Session goal:** Close all ❌/⚠️ use-case gaps identified by comparing the PlantUML diagram against the backend, then add `GET /api/v1/me/access` for accurate per-quarry role gating on mobile.  
**Status:** completed

---

## What was done

### Backend

1. **`POST /quarries` → ADMIN-only** (`backend/app/auth/roles.py`, `backend/app/routers/quarries.py`, `backend/app/routers/admin.py`)
   - Extracted `require_any_admin` dependency into `auth/roles.py` (shared); removed the duplicate private `_require_any_admin` from `admin.py`.
   - `create_quarry` now requires admin on at least one quarry.

2. **Worker auto-creates `Report` + `Recommendation`** (`worker/app/db_models.py`, `worker/app/tasks/pipeline.py`)
   - Added `CaptureSession`, `Report`, `Recommendation`, `RecommendationStatus` stubs to `worker/app/db_models.py`.
   - After successful pipeline: `_create_report_and_recommendation(db, job_id, capture_session_id)` is called before `db.commit()`.
   - `Recommendation` is always created with `status = REQUIRES_HUMAN_REVIEW` — safety invariant enforced.
   - `Report.generated_by_id` is set from `CaptureSession.captured_by_id`.

3. **`GET /reports/{id}/export`** (`backend/app/routers/reports.py`)
   - Returns a downloadable JSON file (`Content-Disposition: attachment`).
   - Requires BLASTER+. Includes full `AnalysisResult`, `Report`, and all `Recommendation` records.
   - Labelled `"⚠ Mock pipeline"`. PDF generation is M2+.

4. **`PATCH /admin/users/{id}` + `DELETE /admin/users/{id}`** (`backend/app/routers/admin.py`, `backend/app/schemas/user.py`)
   - `PATCH` — updates `full_name` and/or `is_active`; writes `AuditLog`.
   - `DELETE` — sets `is_active = false` (soft deactivation); prevents self-deactivation (400); writes `AuditLog`.

5. **`GET /api/v1/me/access`** (`backend/app/routers/me.py`, `backend/app/main.py`)
   - New router registered at `/api/v1/me`.
   - Single SQL JOIN: `QuarryUserAccess → Role → Quarry`, filtered to active non-revoked entries.
   - Response: `[{quarry_id, quarry_name, role_name, role_level}]`
   - Closes MOB-005: mobile no longer approximates role from JWT realm roles.

### Documentation

- `docs/handoffs/mobile-auth-notes.md` — progressive record; pунктs 5–9 added this session.

---

## Files changed

```
backend/app/auth/roles.py           +26   require_any_admin extracted here
backend/app/routers/admin.py        +55   PATCH/DELETE users; removed _require_any_admin
backend/app/routers/quarries.py     +3    POST /quarries → require_any_admin
backend/app/routers/reports.py      +65   GET /{id}/export endpoint
backend/app/routers/me.py           NEW   GET /me/access
backend/app/main.py                 +2    register me.router
backend/app/schemas/user.py         +5    UserProfileUpdate schema
worker/app/db_models.py             +51   CaptureSession/Report/Recommendation stubs
worker/app/tasks/pipeline.py        +70   _create_report_and_recommendation
docs/handoffs/mobile-auth-notes.md  +160  пункты 5–9
```

---

## What was NOT done / is blocked

| Item | Reason |
|------|--------|
| `добавление пользователя к участку` (per-section, not per-quarry) | Domain model uses per-quarry RBAC; per-section would require schema change. Deferred to M2. |
| PDF report generation | Requires wkhtmltopdf/weasyprint integration. M2+. Currently JSON export placeholder. |
| Keycloak user deactivation sync | `DELETE /admin/users/{id}` deactivates in our DB only; Keycloak session remains live until token expires. True revocation needs Keycloak Admin API call. M2. |
| `AuditLog.ip_address` | Still always NULL. Needs request-context middleware. M2. |
| `verify_aud: False` in JWT decode | Intentional; documented in `docs/handoffs/backend-auth.md` §AUD-002. |

---

## Known issues / tech debt introduced

- `require_any_admin` allows an admin of quarry A to create quarry B and then manage users on both. For a single-operator deployment this is fine; multi-tenant M2 should scope admin creation rights.
- `_create_report_and_recommendation` uses `CaptureSession.captured_by_id` as `Report.generated_by_id`. Semantically this is "the surveyor who captured", not "the system". Acceptable for M1; M2 may introduce a `system_user` sentinel.
- Worker `db_models.py` model stubs are hand-synced with backend models. If `Report` or `Recommendation` schema changes in backend, `worker/app/db_models.py` must be updated too. Mark with `# SYNC: backend/app/db/models/report.py`.

---

## Test state

```
31/31 tests pass (backend)
New auth tests: 10 (test_auth.py)
```

No new tests were written for this session's endpoints. Next session should add:
- `test_me_access.py` — GET /me/access returns correct roles; empty for no access
- `test_report_export.py` — export returns JSON with correct structure; 403 for USER role
- `test_user_management.py` — PATCH updates name; DELETE sets is_active=false; self-delete blocked

---

## Next session: start here

1. **Read:** `@CLAUDE.md`, `@docs/handoffs/mobile-auth-notes.md`, `@docs/handoffs/backend-auth.md`
2. **First task:** Write the missing tests listed above (`test_me_access`, `test_report_export`, `test_user_management`)
3. **Then:** Rebuild Docker image to bake all changes in:
   ```powershell
   docker compose -f infra\docker-compose.yml build backend worker
   docker compose -f infra\docker-compose.yml up -d --force-recreate backend worker
   docker compose -f infra\docker-compose.yml exec backend pytest -v
   ```
4. **Then:** Review `mobile/` — there are many untracked Flutter files; understand what's already built and what remains for the mobile MVP.

---

## Commands to verify current state

```powershell
# Start services
docker compose -f infra\docker-compose.yml up -d

# Run tests
docker compose -f infra\docker-compose.yml exec backend pytest -v

# Check migration state
docker compose -f infra\docker-compose.yml exec backend alembic current
# Expected: 0002 (head)

# Smoke-test GET /me/access
$token = (Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8080/realms/zmetrics/protocol/openid-connect/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "grant_type=password&client_id=zmetrics-mobile&username=admin-user&password=changeme"
).access_token

Invoke-RestMethod "http://localhost:8000/api/v1/me/access" `
  -Headers @{Authorization="Bearer $token"}
# Expected: [{quarry_id, quarry_name:"Demo Quarry", role_name:"admin", role_level:4}]

# Smoke-test export
$reports = Invoke-RestMethod "http://localhost:8000/api/v1/quarries/<quarry_id>/reports" `
  -Headers @{Authorization="Bearer $token"}
$reportId = $reports.items[0].id
Invoke-RestMethod "http://localhost:8000/api/v1/reports/$reportId/export" `
  -Headers @{Authorization="Bearer $token"}
# Expected: JSON with analysis_result.p80_mm etc.
```
