# ZMetrics — STATUS

**Last updated:** 2026-06-06 (curating chat)
**Milestone:** M1 — Backend MVP (feature-complete in source, see risks below)
**Git HEAD:** `d7a1983` (M0 scaffold) — ⚠ **all M1 work is uncommitted**

---

## TL;DR for the next session

1. **PRIORITY-0 (blocker, not a coding task):** Commit + push M1, then rebuild containers.
   Weeks of work (28 modified + ~42 untracked) live only in the working tree.
2. **Next coding task:** Backend — close GAP-1 (`GET /analysis-results/{id}`) and GAP-2
   (`analysis_method` on `ReportRead`) + write the 3 missing endpoint tests.
   Spec: `docs/handoffs/2026-06-06-TASK-backend-report-metrics.md`.

---

## Layer status

| Layer | State | Notes |
|-------|-------|-------|
| **backend** | M1 feature-complete | Auth (Keycloak JWT, per-quarry RBAC), full CRUD, passport state machine, capture/blast/device routers, dev-seed, me/access, report export. 31/31 tests pass. |
| **worker** | M1 mock pipeline | 7 mock steps; auto-creates Report + Recommendation (REQUIRES_HUMAN_REVIEW) after success. `db_models.py` hand-synced stubs — `# SYNC` risk. |
| **mobile** | M1 feature-complete (web+Android) | Flutter, offline-first, per-quarry RBAC via `/me/access` w/ realm-role fallback. 41/41 tests, analyze clean. |
| **infra** | running but **stale image** | `infra-backend-1` predates `/me/access` + pagination — returns 404/old shapes until rebuilt. |

---

## Open gaps & priority queue

| Pri | ID | Item | Layer | Why |
|-----|----|------|-------|-----|
| 0 | — | Commit + push M1; rebuild backend/worker images | ops | Single point of catastrophic loss; running stack ≠ source |
| 1 | GAP-2 | `analysis_method` (+ model_version/confidence) on `ReportRead` | backend | **Safety**: product-safety.md requires mock-vs-real label on reports |
| 1 | GAP-1 | `GET /api/v1/analysis-results/{id}` | backend | Unblocks mobile report screen showing P10/P50/P80 in backend mode |
| 2 | — | Tests: `test_me_access`, `test_report_export`, `test_user_management` | backend | Endpoints shipped without tests |
| 3 | — | Report export download plumbing (web/device) | mobile | Backend endpoint exists; client save not built |
| 3 | GAP-3 | `docs/api_contract.md` documents bare arrays; impl uses `{items}` envelope | docs | Drift; client tolerates both |
| M2 | AUD-001 | `AuditLog.ip_address` always NULL | backend | Needs request-context middleware |
| M2 | — | Per-section RBAC; Keycloak deactivation sync; PDF report gen; capture happy-path from app | multi | Deferred by design |

---

## Safety invariants (must stay true — see .claude/rules/product-safety.md)

- `Recommendation` always created `status = requires_human_review`. ✅ enforced (model `__init__` + DB default + worker).
- No auto-approve / bulk-approve endpoints. ✅
- Passport transitions are explicit human HTTP actions. ✅ (DRAFT→SUBMITTED→APPROVED→ACTIVE→COMPLETED).
- AuditLog append-only; written on passport/recommendation/role/access changes. ✅
- Reports must label mock-vs-real prominently. ⚠ **GAP-2 open** — `ReportRead` has no `analysis_method`.

---

## How to verify current state

```powershell
git log --oneline -1                  # expect d7a1983 until M1 is committed
docker compose -f infra\docker-compose.yml ps
docker compose -f infra\docker-compose.yml exec backend pytest -v   # expect 31/31
docker compose -f infra\docker-compose.yml exec backend alembic current  # expect 0002 / head
```

## Recent handoffs (newest first)

- `2026-06-06-TASK-backend-report-metrics.md` — next task spec (GAP-1/GAP-2 + tests)
- `2026-06-06-m1-complete-uncommitted.md` — M1 done, pending commit & rebuild
- `2026-06-06-mobile-web-backend-rbac.md` — Flutter app + per-quarry gating
- `2026-06-06-use-case-gaps-and-me-access.md` — use-case gap closure + `/me/access`
