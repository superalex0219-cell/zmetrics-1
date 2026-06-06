# ZMetrics — STATUS

**Last updated:** 2026-06-06 (curating chat)
**Milestone:** M1 — **COMPLETE** (all features committed, GAP-1/GAP-2 closed, 44 tests)
**Git HEAD:** `8a200b6` (feat(backend): GAP-1/GAP-2) — **1 commit ahead of origin/main** (push pending)

---

## TL;DR for the next session

1. `git push` — local commit `8a200b6` waiting for origin.
2. **Rebuild containers** to bake in GAP-1/GAP-2:
   `docker compose -f infra\docker-compose.yml build backend && docker compose -f infra\docker-compose.yml up -d --force-recreate backend`
3. **Next coding task:** Backend security hardening batch (P1/P2).
   Spec: `docs/handoffs/2026-06-06-TASK-backend-security-hardening.md`.
   Two real bugs + two cleanup items, all in `backend/` only.

---

## Layer status

| Layer | State | Notes |
|-------|-------|-------|
| **backend** | M1 + GAP-1/2 complete | 44 tests. `analysis_results` router + `ReportRead.analysis_method`. Security hardening batch queued. |
| **worker** | M1 mock pipeline | 7 mock steps; auto-creates Report + Recommendation (REQUIRES_HUMAN_REVIEW). `db_models.py` hand-synced — SYNC risk. |
| **mobile** | M1 complete (web+Android) | 41 tests. `report.dart` has `@Default(AnalysisMethod.real)` — dead default now that backend always sends the field; clean up in next mobile task. |
| **infra** | stale image | Needs `docker compose build backend` to get GAP-1/2 + all M1 changes. |

---

## Open gaps & priority queue

| Pri | ID | Item | Layer | Why |
|-----|----|------|-------|-----|
| ✅0 | — | M1 committed & pushed (`d162899`→`8a200b6` ahead) | ops | Done; push pending |
| ✅1 | GAP-2 | `analysis_method` on `ReportRead` (`8a200b6`) | backend | CLOSED — `from_report()` single source of truth |
| ✅1 | GAP-1 | `GET /api/v1/analysis-results/{id}` (`8a200b6`) | backend | CLOSED — mobile report screen unblocked |
| ✅2 | — | 5 missing endpoint tests (suite 31→44) | backend | CLOSED |
| **P1** | SEC-1 | `add_comment`: `rec_id` not validated against `report_id` (IDOR) | backend | Any USER can comment on any recommendation by UUID — correctness bug |
| **P2** | SEC-2 | `UserProfileRead` exposes `keycloak_sub` | backend | Violates security.md; internal identifier leak to admin callers |
| **P2** | SEC-3 | `POST /admin/dev-seed` under `get_current_user` (not `require_any_admin`) | backend | Bootstrap necessity; needs explicit dev-only guard so it's documented |
| **P3** | DB-1 | `AnalysisJob.model_version_id` missing `index=True` | backend + migration | outerjoin in `_report_read` + `list_quarry_reports` seq-scans without it |
| 3 | — | Report export file-save (web/device) | mobile | Backend `GET /reports/{id}/export` exists; client plumbing not built |
| M2 | AUD-001/003 | `ip_address` NULL; `GET /quarries/{id}` no per-quarry check | backend | Known pre-existing; deferred |
| M2 | — | Per-section RBAC; Keycloak deactivation sync; PDF reports; capture flow | multi | Deferred by design |

---

## Safety invariants (must stay true — see .claude/rules/product-safety.md)

- `Recommendation` always created `status = requires_human_review`. ✅ (model `__init__` + DB default + worker).
- No auto-approve / bulk-approve endpoints. ✅
- Passport transitions are explicit human HTTP actions. ✅ (DRAFT→SUBMITTED→APPROVED→ACTIVE→COMPLETED).
- AuditLog append-only; written on passport/recommendation/role/access changes. ✅
- Reports label mock-vs-real prominently. ✅ GAP-2 closed — `ReportRead.analysis_method` derived from `ModelVersion.model_type`.

---

## How to verify current state

```powershell
git log --oneline -3
# expect: 8a200b6 feat(backend): analysis-results endpoint + report safety label
#         668d2ec docs(status)...
#         d162899 feat(m1)...

docker compose -f infra\docker-compose.yml exec backend pytest -v
# expect: 44/44 (after rebuild)

docker compose -f infra\docker-compose.yml exec backend alembic current
# expect: 0002 / head
```

## Recent handoffs (newest first)

- `2026-06-06-TASK-backend-security-hardening.md` — next task spec (SEC-1/2/3 + DB-1)
- `2026-06-06-TASK-backend-report-metrics.md` — GAP-1/GAP-2 spec (completed `8a200b6`)
- `2026-06-06-m1-complete-uncommitted.md` — M1 done, committed `d162899`
- `2026-06-06-mobile-web-backend-rbac.md` — Flutter app + per-quarry gating
- `2026-06-06-use-case-gaps-and-me-access.md` — use-case gap closure + `/me/access`
