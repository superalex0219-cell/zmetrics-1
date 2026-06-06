# TASK (backend): security hardening batch — SEC-1/2/3 + DB-1

**Date:** 2026-06-06
**From:** curating chat (post GAP-1/GAP-2 review)
**Layer:** `backend/` ONLY (routers, schemas, models, one Alembic migration for DB-1).
**Review agent:** `security-reviewer` (primary), then `backend-reviewer`.
**Priority:** P1 (SEC-1 is an IDOR correctness bug), P2 (SEC-2/3), P3 (DB-1).

> **Precondition:** HEAD must be `8a200b6` or newer (not `d7a1983`/`d162899`).
> Check: `git rev-parse --short HEAD`. If stale, stop and report back.

---

## Context

Four issues flagged during the GAP-1/GAP-2 security review. All are pre-existing (not introduced by
the last diff), but SEC-1 is a real correctness/IDOR bug and SEC-2 violates `security.md` directly.

Relevant files to read before editing:
- `backend/app/routers/reports.py` — `add_comment` at line ~219
- `backend/app/schemas/user.py` — `UserProfileRead`
- `backend/app/routers/admin.py` — `dev_seed` at line ~150
- `backend/app/db/models/analysis.py` — `AnalysisJob.model_version_id` at line ~57

---

## Deliverable 1 — SEC-1 (P1): fix IDOR in `add_comment`

**Bug:** `POST /reports/{report_id}/recommendations/{rec_id}/comments`
The router calls `_quarry_id_for_report(report_id, db)` to get the quarry and check access — but
then creates the comment with `recommendation_id = rec_id` **without validating that `rec_id`
actually belongs to `report_id`**. An authenticated USER who has access to report Y and knows the
UUID of recommendation X (in report Z) can successfully post a comment on X.

**Fix:** after `check_quarry_access`, fetch `Recommendation` with both conditions:
```python
rec = (await db.execute(
    select(Recommendation).where(
        Recommendation.id == rec_id,
        Recommendation.report_id == report_id,
    )
)).scalar_one_or_none()
if rec is None:
    raise HTTPException(status_code=404, detail="Recommendation not found")
```
Then create `Comment(recommendation_id=rec.id, ...)`.

Note: `review_recommendation` in the same file already does this correctly — match the pattern.

**Test to add:** `test_add_comment_wrong_report_rejected` — create two reports, try to add comment
on rec from report-B while claiming report-A in the path. Expect 404.

---

## Deliverable 2 — SEC-2 (P2): remove `keycloak_sub` from `UserProfileRead`

**Issue:** `security.md` §Output security: *"Never expose `keycloak_sub`…"*
`UserProfileRead` in `schemas/user.py` exposes it. It's returned by `GET /admin/users` and
`PATCH/DELETE /admin/users/{id}` (admin-only endpoints) and indirectly by audit logs.

**Fix:** remove the `keycloak_sub: str` field from `UserProfileRead`. The admin endpoints don't
need it for any client operation. If a caller genuinely needs to map sub → profile, that's a
separate internal concern.

Check all callers of `UserProfileRead` to confirm nothing else depended on the field being present.

**Test:** existing `test_user_management.py` — ensure response JSON no longer contains `keycloak_sub`.

---

## Deliverable 3 — SEC-3 (P2): dev-seed guard

**Issue:** `POST /api/v1/admin/dev-seed` uses `Depends(get_current_user)` — any authenticated user
can call it and become admin on the Demo Quarry. This is intentional for bootstrap purposes
(chicken-and-egg: no admin yet → can't require admin), but it needs an **explicit dev-only guard**
so it can be disabled in production.

**Fix:** gate behind a settings flag. In `config.py` add:
```python
enable_dev_seed: bool = Field(default=False)
```
In the endpoint, check early:
```python
if not settings.enable_dev_seed:
    raise HTTPException(status_code=404)  # 404, not 403, to avoid discoverability
```
Set `ENABLE_DEV_SEED=true` in `infra/docker-compose.yml` backend service env (dev stack only).
Update `backend/Dockerfile` — do NOT bake this env var into the image; it must come from compose.

This keeps the bootstrap flow working in dev (`ENABLE_DEV_SEED=true`) while the endpoint is
invisible in any stack that doesn't set the flag.

**Test:** `test_dev_seed_disabled` — override settings to `enable_dev_seed=False`, call the
endpoint, expect 404. Add alongside existing seed tests or in `test_admin.py`.

---

## Deliverable 4 — DB-1 (P3): `AnalysisJob.model_version_id` index

**Issue:** `AnalysisJob.model_version_id` has no `index=True`. The `_report_read()` helper and
`list_quarry_reports` both `outerjoin(ModelVersion, ModelVersion.id == AnalysisJob.model_version_id)`.
Without an index, this is a sequential scan on `analysis_job` for every report page.

**Fix:**
1. In `backend/app/db/models/analysis.py` add `index=True` to the `model_version_id` column:
   ```python
   model_version_id: Mapped[uuid.UUID | None] = mapped_column(
       UUID(as_uuid=True), ForeignKey("model_version.id"), nullable=True, index=True
   )
   ```
2. Run `alembic revision --autogenerate -m "add_index_analysis_job_model_version_id"` inside the
   backend container and commit the generated migration file.
3. Apply: `alembic upgrade head`.

**No schema change** — this is a structural index only; no data migration, no column type change.

---

## Boundaries / guardrails

- Touch `backend/` only. No mobile, worker, or infra code changes (except `docker-compose.yml`
  env for `ENABLE_DEV_SEED`, which is infra config — keep that change minimal: one env var line).
- Do NOT create a `services/` layer for these fixes — they are small, router-level corrections.
- The IDOR fix (SEC-1) MUST keep the existing `_quarry_id_for_report` call so quarry-level RBAC
  still runs first. The rec ownership check is an *additional* guard, not a replacement.
- All mutating endpoints still require `get_current_user` + quarry access check.
- `AuditLog` is append-only — no changes there.

## Acceptance

```powershell
docker compose -f infra\docker-compose.yml exec backend pytest -v
# expect: all existing 44 tests pass + new ones (≥47)

# SEC-1 smoke (after rebuild)
# Call add_comment with rec_id from a different report → expect 404

# SEC-2 smoke
# GET /api/v1/admin/users → response items must NOT contain "keycloak_sub"

# SEC-3 smoke
# Without ENABLE_DEV_SEED=true: POST /api/v1/admin/dev-seed → 404
# With ENABLE_DEV_SEED=true: POST /api/v1/admin/dev-seed → 201

# DB-1
docker compose -f infra\docker-compose.yml exec backend alembic current
# expect: new migration hash / head
```

## When done

Report back to curating chat: files changed, test count, and confirm:
- SEC-1: `add_comment` now validates `rec_id.report_id == report_id`
- SEC-2: `keycloak_sub` absent from `UserProfileRead` response
- SEC-3: `enable_dev_seed=False` (default) causes 404; compose sets `True` for dev
- DB-1: Alembic migration generated and applied
