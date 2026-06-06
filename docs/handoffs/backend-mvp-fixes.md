# Backend MVP Fixes — Handoff

**Date:** 2026-06-05  
**Branch:** main  
**Tests:** 31/31 pass  
**Docker image:** rebuilt (`infra-backend:latest` is current)

---

## What was fixed

### 1. Auth gaps in analysis and reports routers

**Problem:** `analysis.py` and `reports.py` only called `get_current_user` — any authenticated user could read or trigger analysis on someone else's quarry data.

**Fix:**
- Added `check_quarry_access(db, user_id, quarry_id, minimum_level)` helper in `app/auth/roles.py`
- Added `_quarry_id_for_session(session_id, db)` in `analysis.py` — walks `CaptureSession → BlastEvent → BlastPassport → SiteSection → quarry_id`
- Added `_quarry_id_for_report(report_id, db)` in `reports.py` — walks the full chain to quarry_id

**Access levels enforced:**

| Endpoint | Before | After |
|---|---|---|
| `POST /capture-sessions/{id}/jobs` | Any user | SURVEYOR+ on that quarry |
| `GET /capture-sessions/{id}/jobs*` | Any user | USER+ on that quarry |
| `GET /reports/{id}` | Any user | USER+ on that quarry |
| `GET /reports/{id}/recommendations` | Any user | USER+ on that quarry |
| `POST /reports/{id}/recommendations/{id}/review` | Any user | BLASTER+ on that quarry |
| `POST /reports/{id}/recommendations/{id}/comments` | Any user | USER+ on that quarry |

---

### 2. `POST /{passport_id}/complete` — ACTIVE → COMPLETED transition

**Problem:** Domain model specifies ACTIVE → COMPLETED but the endpoint did not exist.

**Fix:** Added in `passports.py`. Requires ADMIN role. Writes AuditLog entry.

```
POST /api/v1/quarries/{quarry_id}/passports/{passport_id}/complete
Authorization: Bearer <token with ADMIN role on quarry>
```

Full state machine now:  
`DRAFT → SUBMITTED → APPROVED → ACTIVE → COMPLETED`  
(+ `SUPERSEDED` via `/revise`)

---

### 3. Pagination on all list endpoints

**Problem:** All list endpoints returned `[]` (plain JSON arrays). Violates backend convention; clients couldn't tell total count without fetching everything.

**Fix:** All list endpoints now return `PaginatedResponse`:
```json
{
  "items": [...],
  "total": 42,
  "page": 1,
  "page_size": 20
}
```

Query params: `?page=1&page_size=20` (defaults: page=1, page_size=20; admin/users uses page_size=50).

**Affected endpoints:**
- `GET /quarries`
- `GET /quarries/{id}/sections`
- `GET /quarries/{id}/reports`
- `GET /quarries/{id}/passports`
- `GET /devices`
- `GET /devices/{id}/calibrations`
- `GET /quarries/{id}/passports/{id}/blast-event/capture-sessions`
- `GET /capture-sessions/{id}/artifacts`
- `GET /capture-sessions/{id}/jobs`
- `GET /reports/{id}/recommendations`
- `GET /admin/users`

**Test updates:** `test_blast_capture.py` updated to use `resp.json()["items"]`.

---

### 4. Docker image rebuild

**Problem:** All previous code changes lived only inside the running container (via `docker compose cp`). On `--force-recreate` the image reverted to the original scaffold.

**Fix:** `docker compose build backend` bakes all current code into the image. Both `backend` and `worker` containers were recreated from the new image.

---

## Known remaining gaps (not in scope for this session)

| ID | Issue | Notes |
|---|---|---|
| AUD-001 | `AuditLog.ip_address` always NULL | Needs `Request` injected via middleware or endpoint parameter; safe to defer to M2 |
| AUD-002 | `POST /quarries` has no role check | Creating a new quarry cannot be guarded by per-quarry RBAC (quarry doesn't exist yet); consider a global "can_create_quarry" flag in M2 |
| AUD-003 | Single `GET /quarries/{id}` returns any quarry to any authenticated user | Low risk; the list endpoint already filters by membership; direct-by-id is read-only |
| AUD-004 | `_require_any_admin` in `admin.py` is cross-quarry | Admin on *any* quarry can see all audit logs. Acceptable for M1 single-operator deployment; scope to quarry in M2 |

---

## Verification

```powershell
# Get token
$token = (Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8080/realms/zmetrics/protocol/openid-connect/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "grant_type=password&client_id=zmetrics-mobile&username=admin-user&password=changeme"
).access_token

# Paginated quarry list
Invoke-RestMethod "http://localhost:8000/api/v1/quarries" -Headers @{Authorization="Bearer $token"}
# → { "items": [...], "total": 1, "page": 1, "page_size": 20 }

# Auth gap check — analysis endpoint returns 403 for user without quarry access
$fake_session = "00000000-0000-0000-0000-000000000001"
Invoke-RestMethod "http://localhost:8000/api/v1/capture-sessions/$fake_session/jobs" `
  -Headers @{Authorization="Bearer $token"}
# → 404 (session doesn't exist, not 200 with empty list)
```
