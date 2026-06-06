# TASK (backend): report metrics endpoint + analysis-method safety label + missing tests

**Date:** 2026-06-06
**From:** curating chat
**Layer:** `backend/` ONLY (routers + schemas + tests). No worker, mobile, infra, or DB-migration changes expected.
**Review agent:** `backend-reviewer` (and re-check `security-reviewer` because this touches RBAC on a new read endpoint and a safety-labelling requirement).
**Priority:** P1 — GAP-2 is a product-safety compliance gap; GAP-1 unblocks the mobile report screen.

> ⚠ **Precondition (do this first, outside the code task):** M1 is uncommitted at `d7a1983`.
> Commit + push M1 and rebuild containers BEFORE starting, so your diff is clean and reviewable.
> See `docs/STATUS.md` PRIORITY-0.

---

## Context

The mobile report screen cannot show granulometry (P10/P50/P80) in backend mode, and reports
carry no mock-vs-real label. Both are gaps recorded in
`docs/handoffs/TASK-backend-mobile-integration.md` (GAP-1, GAP-2).

Relevant current code (read before editing):
- `backend/app/routers/reports.py` — `_quarry_id_for_report()` already walks the chain to `quarry_id`; reuse it.
- `backend/app/routers/analysis.py` — existing `GET /{capture_session_id}/jobs/{job_id}/result` returns `AnalysisResultRead`; mirror its access pattern.
- `backend/app/schemas/report.py` — `ReportRead`.
- `backend/app/schemas/analysis.py` — `AnalysisResultRead` (already complete).
- `backend/app/db/models/analysis.py` — `AnalysisResult`, `AnalysisJob`, `ModelVersion` (has `model_type`: "mock"/"yolo_seg"/...).
- `backend/app/db/models/report.py` — `Report` (FK `analysis_result_id`).

---

## Deliverable 1 — GAP-1: `GET /api/v1/analysis-results/{result_id}`

- New route returning `AnalysisResultRead` for a single result by its own id.
- Decide where it lives: a new thin router `routers/analysis_results.py` registered in `main.py`,
  OR add to `reports.py`. Prefer a small dedicated router (cleaner prefix `/api/v1/analysis-results`).
- **RBAC:** resolve `quarry_id` by walking `AnalysisResult → AnalysisJob → CaptureSession → BlastEvent → BlastPassport → SiteSection.quarry_id`, then `check_quarry_access(db, user.id, quarry_id, RoleLevel.USER)`. Factor a `_quarry_id_for_result(result_id, db)` helper mirroring the existing ones.
- 404 if result not found; 403 enforced by `check_quarry_access`.
- Do NOT widen access: USER+ on that quarry only.

## Deliverable 2 — GAP-2: analysis-method safety label on `ReportRead`

product-safety.md: *"PDF/HTML reports MUST display the analysis method (mock vs real) prominently"*
and *"label synthetic results."* The API must expose this so clients can render the badge.

- Add to `ReportRead`: `analysis_method: str` ("mock" | "real"), and (nice-to-have, include if cheap)
  `model_version_tag: str | None`, `confidence_score: float | None`.
- **Source of truth:** derive from the linked `AnalysisJob.model_version → ModelVersion.model_type`.
  - `model_version is None` OR `model_type == "mock"` ⇒ `analysis_method = "mock"`.
  - otherwise `"real"`.
  - `confidence_score` from the `AnalysisResult`.
- Since `ReportRead` uses `from_attributes`, derived fields need a deliberate assembly step in the
  router (build the dict / use a computed value) rather than relying on ORM attribute mapping.
  Update **both** `GET /reports/{id}` and any place `ReportRead` is returned.
- **No DB migration** — this is derived, not stored. If you find you need a stored column, STOP and
  flag it back to the curating chat (that changes scope to database layer + Alembic).

## Deliverable 3 — Tests (pytest, SQLite in-memory per existing `conftest.py`)

Write the three missing endpoint tests noted across handoffs, plus cover the new work:
- `tests/test_analysis_results.py` — `GET /analysis-results/{id}` returns metrics for a user with
  quarry access; 403 for a user without access; 404 for unknown id.
- `tests/test_report_metrics.py` — `ReportRead.analysis_method == "mock"` for the mock pipeline chain.
- `tests/test_me_access.py` — `/me/access` returns correct roles; empty list for no access.
- `tests/test_report_export.py` — export returns JSON; 403 for USER role (export is BLASTER+).
- `tests/test_user_management.py` — `PATCH` updates name; `DELETE` sets `is_active=false`; self-delete blocked (400).

Target: full suite stays green (was 31/31; expect ~40+).

---

## Boundaries / guardrails

- Routers stay thin (rules/backend.md). Chain-walk helpers are acceptable in the router as the
  existing code already does (`_quarry_id_for_*`); don't invent a service layer just for reads unless
  it's trivial.
- Every read endpoint: `Depends(get_current_user)` + per-quarry `check_quarry_access`. No global access.
- Do NOT expose `keycloak_sub` or internal errors.
- Do NOT touch the worker, mobile, or infra. Do NOT add a DB migration.
- Keep `analysis_method` derivation in one helper so it can't drift.

## Acceptance

```powershell
docker compose -f infra\docker-compose.yml build backend; `
docker compose -f infra\docker-compose.yml up -d --force-recreate backend
docker compose -f infra\docker-compose.yml exec backend pytest -v   # all green

# manual
$token = (Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8080/realms/zmetrics/protocol/openid-connect/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "grant_type=password&client_id=zmetrics-mobile&username=admin-user&password=changeme&scope=openid").access_token
$seed = Invoke-RestMethod -Method Post "http://localhost:8000/api/v1/admin/dev-seed" -Headers @{Authorization="Bearer $token"}
$report = Invoke-RestMethod "http://localhost:8000/api/v1/reports/$($seed.report_id)" -Headers @{Authorization="Bearer $token"}
$report.analysis_method   # expect "mock"
Invoke-RestMethod "http://localhost:8000/api/v1/analysis-results/$($report.analysis_result_id)" -Headers @{Authorization="Bearer $token"}
# expect P10/P50/P80 etc.
```

## When done

Report back to the curating chat with: files changed, test count, and confirmation that
`analysis_method` derives from `ModelVersion.model_type` (not hardcoded). The curating chat will
review the diff for layer/integration correctness and update `docs/STATUS.md`.
