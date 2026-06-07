# ZMetrics — STATUS

**Last updated:** 2026-06-07 (curating chat)
**Git HEAD:** `4435f28` — M5-a rule engine done

---

## TL;DR for the next session

1. `git push origin main` — 19 commits ahead of origin/main, never pushed.
2. **Rebuild containers** after WEB-1 + MOB-DESIGN:
   ```powershell
   docker compose -f infra\docker-compose.yml build backend frontend
   docker compose -f infra\docker-compose.yml up -d --force-recreate
   ```
   Web UI available at http://localhost:5173 after rebuild.
3. **Next task:** M5-a (rule engine in worker — P80 vs passport target → structured Recommendation).

---

## Layer status

| Layer | State | Notes |
|-------|-------|-------|
| **backend** | M1 + SEC-1 + BACK-SEC-2 complete | 53 tests. All IDOR gaps closed. AuditLog complete for role_assigned. Magic-byte validation on artifact upload. |
| **worker** | M1 + M5-a rule engine | 7 mock steps + rule engine. `evaluate_fragmentation` flags oversize/fines vs passport target_p80_mm. `parameter_suggestions` JSONB populated. `db_models.py` hand-synced — SYNC risk (M6+). |
| **frontend** | WEB-1 complete | React + Vite + Keycloak OIDC. 7 screens wired to real API. Mock badge, read-only parameter_suggestions, review buttons. Dockerised. |
| **mobile** | M1 + MOB-1/2/3/4 + MOB-DESIGN | 63 tests. Teal theme + dark AppBar. Russian labels. StatCard widget. |
| **infra** | stale image | Needs `docker compose build backend` to pick up SEC-1 batch + GAP-1/2 changes. |

---

## Completed work (this session)

| Commit | What |
|--------|------|
| `d162899` | M1: backend MVP + Flutter mobile + per-quarry RBAC |
| `8a200b6` | GAP-1: `GET /api/v1/analysis-results/{id}`; GAP-2: `ReportRead.analysis_method` |
| `1d9ad72` | SEC-1 IDOR (`add_comment`), SEC-2 (`keycloak_sub` removed), SEC-3 (dev-seed flag), DB-1 (index + migration) |
| `9dc2b4a` | MOB-1: mobile wires analysis-result endpoint; removes dead `_withDerivedMethod` workaround |
| `aa4c42f` | BACK-SEC-2: IDOR on capture_sessions/blast_events/analysis; AuditLog dev_seed; magic-byte validation; 53 tests |
| `796823a` | MOB-2: OIDC PKCE (flutter_appauth), restore() fix, login screen; 45 tests |
| `760dbb5` | MOB-3: device picker, SyncProcessor wired, job polling, navigate to reports; 55 tests |
| `f734b97` | MOB-4: report export (share_plus + path_provider); 63 tests |
| `09ca465` | WEB-1: React frontend wired to backend; Keycloak OIDC; 7 screens live |
| `ebb28e5` | MOB-DESIGN: teal theme + dark AppBar + Russian labels + StatCard |
| `4435f28` | M5-a: rule engine — evaluate_fragmentation; BlastEvent/BlastPassport stubs; 15 new tests |

---

## Priority queue (next tasks)

| Pri | ID | Item | Layer | Spec |
|-----|----|------|-------|------|
| **P2** | WEB-2 | Passport workflow in web: detail view, state transitions, blast event form | frontend | not yet written |
| P3 | M5-b | LLM explanation layer for recommendations (Claude API) | worker | depends M5-a |
| later | — | OIDC deactivation sync, PDF reports, per-section RBAC | multi | M2+ |

---

## Safety invariants (must stay true)

- `Recommendation` always created `status = requires_human_review`. ✅
- No auto-approve / bulk-approve endpoints. ✅
- Passport transitions are explicit human HTTP actions. ✅
- AuditLog append-only; written on state changes. ✅ (dev_seed gap closed in BACK-SEC-2)
- Reports label mock-vs-real prominently. ✅ (`ReportRead.analysis_method` from `ModelVersion.model_type`)

---

## How to verify current state

```powershell
git log --oneline -5
# 3be7873 docs(handoff): BACK-SEC-2 task spec
# 86add37 docs(roadmap): sync with actual state
# c09cb89 docs(status): close MOB-1
# 9dc2b4a feat(mobile): MOB-1 analysis-result wiring
# fcb7a4c docs(status): close SEC-1/2/3/DB-1

docker compose -f infra\docker-compose.yml exec backend pytest -v
# expect: 49 passing (after rebuild)

docker compose -f infra\docker-compose.yml exec backend alembic current
# expect: 6929bdaa526b (head)

cd mobile && flutter test
# expect: 41 passing
```

---

## Active handoffs

| File | Task | Status |
|------|------|--------|
| `2026-06-07-TASK-web2-passport-workflow.md` | WEB-2 passport workflow | **in progress** |
| `2026-06-07-TASK-worker-m5a-rule-engine.md` | M5-a rule engine | **done** (`4435f28`) |
| `2026-06-06-TASK-backend-sec2-idor-capture.md` | BACK-SEC-2 IDORs | **done** (`aa4c42f`) |
| `2026-06-06-TASK-mobile-mob2-pkce.md` | MOB-2 OIDC PKCE | **done** (`796823a`) |
| `2026-06-06-TASK-mobile-mob3-capture-flow.md` | MOB-3 capture flow | **done** (`760dbb5`) |
| `2026-06-06-TASK-mobile-mob4-report-export.md` | MOB-4 report export | **done** (`f734b97`) |
