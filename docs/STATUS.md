# ZMetrics — STATUS

**Last updated:** 2026-06-06 (curating chat)
**Git HEAD:** pending commit for BACK-SEC-2 — push pending

---

## TL;DR for the next session

1. **Commit BACK-SEC-2** — `capture_sessions.py`, `blast_events.py`, `analysis.py`, `admin.py`, `test_blast_capture.py`
2. `git push origin main` — all local commits, none pushed yet.
3. **Rebuild containers** — image is stale:
   ```powershell
   docker compose -f infra\docker-compose.yml build backend
   docker compose -f infra\docker-compose.yml up -d --force-recreate backend
   ```
4. **Next task:** MOB-2 (OIDC PKCE via flutter_appauth) or MOB-3 (CaptureScreen — now unblocked).

---

## Layer status

| Layer | State | Notes |
|-------|-------|-------|
| **backend** | M1 + SEC-1 + BACK-SEC-2 complete | 53 tests. All IDOR gaps closed. AuditLog complete for role_assigned. Magic-byte validation on artifact upload. |
| **worker** | M1 mock pipeline | 7 mock steps; auto-creates Report + Recommendation (`REQUIRES_HUMAN_REVIEW`). `db_models.py` hand-synced — SYNC risk (M6+). |
| **mobile** | M1 + MOB-1 complete | 41 tests. Granulometry wired to live backend (`9dc2b4a`). Dead `_withDerivedMethod` removed. PKCE/capture flow not yet built. |
| **infra** | stale image | Needs `docker compose build backend` to pick up SEC-1 batch + GAP-1/2 changes. |

---

## Completed work (this session)

| Commit | What |
|--------|------|
| `d162899` | M1: backend MVP + Flutter mobile + per-quarry RBAC |
| `8a200b6` | GAP-1: `GET /api/v1/analysis-results/{id}`; GAP-2: `ReportRead.analysis_method` |
| `1d9ad72` | SEC-1 IDOR (`add_comment`), SEC-2 (`keycloak_sub` removed), SEC-3 (dev-seed flag), DB-1 (index + migration) |
| `9dc2b4a` | MOB-1: mobile wires analysis-result endpoint; removes dead `_withDerivedMethod` workaround |
| pending | BACK-SEC-2: IDOR on capture_sessions/blast_events/analysis; AuditLog dev_seed; magic-byte validation; 53 tests |

---

## Priority queue (next tasks)

| Pri | ID | Item | Layer | Spec |
|-----|----|------|-------|------|
| **P1** | MOB-2 | OIDC PKCE via `flutter_appauth` (replace ROPC) | mobile | not yet written |
| P1 | MOB-3 | CaptureScreen + SyncProcessor drain + job status polling | mobile | not yet written; BACK-SEC-2 now complete |
| P3 | MOB-4 | Report export: save JSON to device / share sheet | mobile | not yet written |
| P3 | M5-a | Rule-based recommendation engine in worker (P80 vs passport target) | worker | not yet written |
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
| `2026-06-06-TASK-backend-sec2-idor-capture.md` | BACK-SEC-2 IDORs | **done — pending commit** |
