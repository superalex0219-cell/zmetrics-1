# ZMetrics — STATUS

**Last updated:** 2026-06-06 (curating chat)
**Milestone:** M1 — **COMPLETE** (all features committed, GAP-1/GAP-2 closed, security batch done, 49 tests)
**Git HEAD:** `9dc2b4a` (feat(mobile): MOB-1 analysis-result wiring) — **4 commits ahead of origin/main** (push pending)

---

## TL;DR for the next session

1. `git push` — 3 local commits (`8a200b6`, `ad137d6`, `1d9ad72`) ahead of origin.
2. **Rebuild containers** to bake in all changes:
   `docker compose -f infra\docker-compose.yml build backend && docker compose -f infra\docker-compose.yml up -d --force-recreate backend`
3. **Next coding task:** Mobile — wire analysis-result endpoint + remove dead workarounds.
   Spec: `docs/handoffs/2026-06-06-TASK-mobile-report-wire-analysis-result.md`.
   Granulometry (P10/P50/P80) invisible in live mode until this is done.

---

## Layer status

| Layer | State | Notes |
|-------|-------|-------|
| **backend** | M1 + security batch complete | 49 tests. SEC-1 IDOR fixed, SEC-2 keycloak_sub removed, SEC-3 dev-seed guarded, DB-1 index added. |
| **worker** | M1 mock pipeline | 7 mock steps; auto-creates Report + Recommendation (REQUIRES_HUMAN_REVIEW). `db_models.py` hand-synced — SYNC risk. |
| **mobile** | M1 + MOB-1 complete | 41 tests. Granulometry wired to live backend (`9dc2b4a`). Dead workaround `_withDerivedMethod` removed. |
| **infra** | stale image | Needs `docker compose build backend` to get SEC-1/2/3/DB-1 + GAP-1/2 changes. |

---

## Open gaps & priority queue

| Pri | ID | Item | Layer | Why |
|-----|----|------|-------|-----|
| ✅0 | — | M1 committed & pushed (`d162899`→`8a200b6` ahead) | ops | Done; push pending |
| ✅1 | GAP-2 | `analysis_method` on `ReportRead` (`8a200b6`) | backend | CLOSED — `from_report()` single source of truth |
| ✅1 | GAP-1 | `GET /api/v1/analysis-results/{id}` (`8a200b6`) | backend | CLOSED — mobile report screen unblocked |
| ✅2 | — | 5 missing endpoint tests (suite 31→44) | backend | CLOSED |
| ✅P1 | SEC-1 | `add_comment` IDOR fixed (`1d9ad72`) | backend | CLOSED — rec ownership validated |
| ✅P2 | SEC-2 | `keycloak_sub` removed from `UserProfileRead` (`1d9ad72`) | backend | CLOSED |
| ✅P2 | SEC-3 | `dev-seed` guarded by `enable_dev_seed` flag (`1d9ad72`) | backend | CLOSED |
| ✅P3 | DB-1 | `AnalysisJob.model_version_id` index added (`1d9ad72`) | backend + migration | CLOSED — migration `6929bdaa526b` applied |
| ✅P1 | MOB-1 | Granulometry wired to live backend (`9dc2b4a`) | mobile | CLOSED — `analysisResultId` mapped, `getAnalysisResult` wired |
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

- `2026-06-06-TASK-mobile-report-wire-analysis-result.md` — MOB-1 spec (completed `9dc2b4a`)
- `2026-06-06-TASK-backend-security-hardening.md` — SEC-1/2/3 + DB-1 (completed `1d9ad72`)
- `2026-06-06-TASK-backend-report-metrics.md` — GAP-1/GAP-2 spec (completed `8a200b6`)
- `2026-06-06-m1-complete-uncommitted.md` — M1 done, committed `d162899`
- `2026-06-06-mobile-web-backend-rbac.md` — Flutter app + per-quarry gating
- `2026-06-06-use-case-gaps-and-me-access.md` — use-case gap closure + `/me/access`
