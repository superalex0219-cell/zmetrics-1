# TASK (backend): BACK-SEC-2 — IDOR fixes on capture/blast/analysis + audit trail

**Date:** 2026-06-06
**From:** curating chat (post MOB-1)
**Layer:** `backend/` ONLY — routers: `capture_sessions.py`, `blast_events.py`, `analysis.py`, `admin.py`
**Review agent:** `security-reviewer` (primary), then `backend-reviewer`
**Priority:** P1 — before MOB-3 (mobile capture flow) is built on top of these endpoints

> **Precondition:** HEAD must be `c09cb89` or newer.

---

## Context

The security-reviewer flagged these during the SEC-1 batch and explicitly deferred them as out-of-scope.
All four items are pre-existing IDOR/audit-trail gaps, not regressions.

---

## Deliverable 1 — `capture_sessions.py`: add quarry-level access control

**Bug:** All three endpoints (`list_artifacts`, `upload_artifact`, `get_artifact_url`) call only
`Depends(get_current_user)`. There is no quarry chain-walk and no `check_quarry_access` call.
Any authenticated user can list/upload/download artifacts for any capture session by UUID.

**Pattern to follow:** `analysis.py` already has `_quarry_id_for_session` — copy it verbatim
or import it (if you move it to a shared location; that is acceptable but not required).

**Fix:** Add the helper and call it in every endpoint:

```python
async def _quarry_id_for_session(session_id: UUID, db: AsyncSession) -> UUID:
    from app.db.models.blast import BlastEvent
    from app.db.models.passport import BlastPassport
    from app.db.models.quarry import SiteSection
    result = await db.execute(
        select(SiteSection.quarry_id)
        .join(BlastPassport, BlastPassport.site_section_id == SiteSection.id)
        .join(BlastEvent, BlastEvent.passport_id == BlastPassport.id)
        .join(CaptureSession, CaptureSession.blast_event_id == BlastEvent.id)
        .where(CaptureSession.id == session_id)
    )
    quarry_id = result.scalar_one_or_none()
    if quarry_id is None:
        raise HTTPException(status_code=404, detail="Capture session not found")
    return quarry_id
```

Endpoint-level minimums (mirror `analysis.py`):
- `list_artifacts` → `RoleLevel.USER`
- `upload_artifact` → `RoleLevel.SURVEYOR`
- `get_artifact_url` → `RoleLevel.USER`

In `upload_artifact`, replace the existing bare session existence check with the helper (the 404
path is already handled by the helper; keep content-type validation as-is).

**Note on magic-bytes check:** `security.md` says "validate content-type header AND magic bytes
(not just extension)". The current code validates content-type header only. Add a minimal magic-byte
check for JPEG/PNG before the MinIO upload. JPEG magic: `content[:3] == b'\xff\xd8\xff'`.
PNG magic: `content[:8] == b'\x89PNG\r\n\x1a\n'`. Raise 415 if neither matches for frame types.

---

## Deliverable 2 — `blast_events.py`: validate passport belongs to quarry

**Bug:** All four endpoints accept `quarry_id` in the path and `passport_id` separately, but never
verify that `passport.site_section.quarry_id == quarry_id`. A user with access to quarry A can
pass `quarry_id=A&passport_id=<uuid-from-quarry-B>` and see or modify quarry B's blast events.

Additionally, `get_blast_event` and `list_capture_sessions` use only `Depends(get_current_user)`
with no role check at all — add `check_quarry_access(db, current_user.id, quarry_id, RoleLevel.USER)`.

**Fix:** Add a helper that validates ownership and returns the passport in one query:

```python
async def _get_passport_in_quarry(passport_id: UUID, quarry_id: UUID, db: AsyncSession) -> BlastPassport:
    from app.db.models.quarry import SiteSection
    passport = (await db.execute(
        select(BlastPassport)
        .join(SiteSection, SiteSection.id == BlastPassport.site_section_id)
        .where(BlastPassport.id == passport_id, SiteSection.quarry_id == quarry_id)
    )).scalar_one_or_none()
    if passport is None:
        raise HTTPException(status_code=404, detail="Passport not found")
    return passport
```

Replace every `select(BlastPassport).where(BlastPassport.id == passport_id)` with a call to this
helper (passing the `quarry_id` from the path). Remove the separate "passport not found" check
after the old query — the helper handles it.

`create_blast_event` already uses `require_quarry_role(RoleLevel.BLASTER)` which validates quarry
membership. But it fetches the passport without verifying ownership — replace with the helper.
The status check (`APPROVED` or `ACTIVE`) comes after, unchanged.

Summary of role changes:
- `get_blast_event` → add `check_quarry_access(db, user.id, quarry_id, RoleLevel.USER)` (missing entirely)
- `list_capture_sessions` → add `check_quarry_access(db, user.id, quarry_id, RoleLevel.USER)` (missing entirely)
- `create_blast_event` → already has `require_quarry_role` (correct); just fix the passport fetch
- `create_capture_session` → already has `require_quarry_role` (correct); just fix the passport fetch

---

## Deliverable 3 — `analysis.py`: fix `get_job_result` cross-session IDOR

**Bug:** `get_job_result` validates that the user has access to the quarry of `capture_session_id`,
but then fetches the `AnalysisResult` with only `AnalysisResult.job_id == job_id` — without
confirming `job_id` belongs to `capture_session_id`. An attacker can pass a valid
`capture_session_id` and a `job_id` from a completely different session to read that result.

`get_job` (just above it) already does this correctly: it checks both conditions.

**Fix:** Join through `AnalysisJob` to enforce ownership:

```python
result = await db.execute(
    select(AnalysisResult)
    .join(AnalysisJob, AnalysisJob.id == AnalysisResult.job_id)
    .where(
        AnalysisResult.job_id == job_id,
        AnalysisJob.capture_session_id == capture_session_id,
    )
)
```

No other changes to `analysis.py`.

---

## Deliverable 4 — `admin.py`: add AuditLog for role_assigned in dev_seed

**Bug:** `dev_seed` creates a `QuarryUserAccess` but does not write an `AuditLog`.
`product-safety.md` requires `AuditLog(action="role_assigned")` for all role grants.

**Fix:** After the `QuarryUserAccess` is added (or confirmed existing), add:

```python
db.add(AuditLog(
    actor_id=current_user.id,
    entity_type="quarry_user_access",
    entity_id=access.id,
    action="role_assigned",
    new_value={"role": access.role.value, "quarry_id": str(quarry.id)},
))
```

Write the log entry even if the access record already existed (idempotent re-seed case).
Use a conditional: if existing access was found, the `action` may be `"role_assigned"` again
(duplicate audit entries are acceptable; the log is append-only).

---

## Tests to add

1. **`test_capture_session_upload_no_access`** — POST artifact to a session the user has no quarry
   access to → 403 (not 200).
2. **`test_capture_session_artifact_wrong_quarry`** — user has access to quarry A; tries to upload
   to a session in quarry B → 403.
3. **`test_blast_event_passport_wrong_quarry`** — user has access to quarry A; GET blast-event
   with `quarry_id=A&passport_id=<from quarry B>` → 404.
4. **`test_analysis_job_result_wrong_session`** — user has access to the session; passes
   a `job_id` from a different session → 404.

Add to `test_blast_capture.py` (existing file) or new `test_capture_security.py`.

---

## Boundaries / guardrails

- Touch `backend/` routers only. No model changes, no migration needed.
- Do NOT add `check_quarry_access` to `/health` or `/admin/dev-seed` (dev-seed already gated by `enable_dev_seed`).
- Keep the SURVEYOR minimum for `upload_artifact` — matching `create_capture_session`.
- `AuditLog` is append-only — no DELETE or UPDATE.
- Do NOT create a `services/` layer for these fixes — they are small, router-level corrections.

## Acceptance

```powershell
docker compose -f infra\docker-compose.yml exec backend pytest -v
# expect: all 49 existing tests pass + 4 new security tests ≥ 53 total

# Smoke checks (after rebuild):
# 1. Unauthed user cannot GET /capture-sessions/{id}/artifacts → 401/403
# 2. User from quarry A cannot POST artifact to session in quarry B → 403
# 3. GET blast-event with passport from wrong quarry → 404
# 4. get_job_result with job from different session → 404
```

## When done

Report: files changed, test count, confirm each deliverable.
