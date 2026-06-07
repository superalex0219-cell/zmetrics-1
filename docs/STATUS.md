# ZMetrics — STATUS

**Last updated:** 2026-06-07
**Git HEAD:** `5316cad` — BUG-HUNT-1 frontend fixes

---

## TL;DR для следующей сессии

1. `git push origin main` — commits ahead of origin/main, never pushed.
2. **Rebuild containers** after backend fix (audit-logs endpoint):
   ```powershell
   docker compose -f infra\docker-compose.yml build backend worker
   docker compose -f infra\docker-compose.yml up -d --force-recreate
   ```
   Web UI доступен на http://localhost:5173.
3. **Next task:** UT-1 — user smoke test (checklist в roadmap).

---

## Layer status

| Layer | State | Notes |
|-------|-------|-------|
| **backend** | M1 + SEC-1 + BACK-SEC-2 + ARCH-1 | 53 tests. `audit-logs` теперь принимает `entity_id` query-param. |
| **worker** | M1 + M5-a rule engine + ARCH-2 | `p10`/`p50` корректно `None` вместо `0.0` в pipeline. |
| **frontend** | WEB-1 + WEB-2 + ARCH-1/3 + BUG-HUNT-1 | `downloadWithAuth` защищён. Все concurrent fetch через `Promise.allSettled`. `handleLoadRecommendations` имеет try/catch. |
| **mobile** | M1 + MOB-1/2/3/4 + MOB-DESIGN | 63 tests. Teal theme + dark AppBar. Russian labels. |
| **infra** | stale image | Нужен `docker compose build backend worker` для ARCH-1/2 изменений. |

---

## Completed work (all sessions)

| Commit | What |
|--------|------|
| `d162899` | M1: backend MVP + Flutter mobile + per-quarry RBAC |
| `8a200b6` | GAP-1: `GET /api/v1/analysis-results/{id}`; GAP-2: `ReportRead.analysis_method` |
| `1d9ad72` | SEC-1 IDOR (`add_comment`), SEC-2 (`keycloak_sub` removed), SEC-3 (dev-seed flag), DB-1 (index + migration) |
| `9dc2b4a` | MOB-1: mobile wires analysis-result endpoint |
| `aa4c42f` | BACK-SEC-2: IDOR on capture_sessions/blast_events/analysis; AuditLog dev_seed; magic-byte validation |
| `796823a` | MOB-2: OIDC PKCE (flutter_appauth), login screen; 45 tests |
| `760dbb5` | MOB-3: device picker, SyncProcessor wired, job polling, navigate to reports; 55 tests |
| `f734b97` | MOB-4: report export (share_plus + path_provider); 63 tests |
| `09ca465` | WEB-1: React frontend wired to backend; Keycloak OIDC; 7 screens live |
| `ebb28e5` | MOB-DESIGN: teal theme + dark AppBar + Russian labels + StatCard |
| `4435f28` | M5-a: rule engine — evaluate_fragmentation; BlastEvent/BlastPassport stubs; 15 tests |
| `849e1f9` | WEB-2: passport detail panel, status transitions, blast event form, audit log |
| `7fa824d` | docs: roadmap UT/BUG-HUNT sections added |
| `c077029` | ARCH fixes: downloadWithAuth origin check; p10/p50 None; audit-logs entity_id filter |
| `5316cad` | BUG-HUNT-1: Promise.allSettled для concurrent fetch; try/catch в handleLoadRecommendations |

---

## Priority queue (next tasks)

| Pri | ID | Item | Layer | Notes |
|-----|----|------|-------|-------|
| **P1** | UT-1 | User smoke test: web UI — паспорта, взрыв, рекомендации | browser | checklist в roadmap; rebuild контейнеров сначала |
| P2 | UT-2 | Rule engine E2E: P80 vs target, текст рекомендации в UI | browser | depends UT-1 |
| ~~P3~~ | ~~BUG-HUNT-1~~ | ~~Frontend error states & edge cases~~ | ~~done~~ | 5/7 ✅; 2 баги исправлены |
| P3 | M5-b | LLM explanation layer (Claude API) | worker | depends M5-a stable |
| later | UT-3 | Mobile smoke test | Android | нужен Android Studio + AVD |

---

## Dev credentials (temporary — seed only)

- Keycloak admin UI: http://localhost:8080 → `admin` / см. `infra/.env`
- App login: `admin-user` / `changeme` (Keycloak попросит сменить при первом browser-логине)
- Dev seed: `POST /api/v1/admin/dev-seed` (нужен `ENABLE_DEV_SEED=true` и Bearer токен)
- Токен для seed: `POST http://localhost:8080/realms/zmetrics/protocol/openid-connect/token` с `client_id=zmetrics-mobile`, `grant_type=password`, `username=admin-user`, `password=changeme`

---

## Safety invariants (must stay true)

- `Recommendation` always created `status = requires_human_review`. ✅
- No auto-approve / bulk-approve endpoints. ✅
- Passport transitions are explicit human HTTP actions. ✅
- AuditLog append-only; written on state changes. ✅
- Reports label mock-vs-real prominently. ✅
- `parameter_suggestions` shown read-only only — no write-back path. ✅

---

## Active handoffs

| File | Task | Status |
|------|------|--------|
| `2026-06-07-TASK-web2-passport-workflow.md` | WEB-2 passport workflow | **done** (`849e1f9`) |
| `2026-06-07-TASK-worker-m5a-rule-engine.md` | M5-a rule engine | **done** (`4435f28`) |
| `2026-06-06-TASK-backend-sec2-idor-capture.md` | BACK-SEC-2 IDORs | **done** (`aa4c42f`) |
| `2026-06-06-TASK-mobile-mob2-pkce.md` | MOB-2 OIDC PKCE | **done** (`796823a`) |
| `2026-06-06-TASK-mobile-mob3-capture-flow.md` | MOB-3 capture flow | **done** (`760dbb5`) |
| `2026-06-06-TASK-mobile-mob4-report-export.md` | MOB-4 report export | **done** (`f734b97`) |
