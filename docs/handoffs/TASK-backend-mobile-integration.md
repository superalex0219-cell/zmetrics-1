# TASK (backend/infra): make the Flutter web app able to authenticate & call the API

**From:** mobile
**To:** backend/infra owner
**Date:** 2026-06-05
**Priority:** blocks mobile↔backend integration (web)

The Flutter app (web + Android) is being switched from mock mode to the live
backend. The mobile-side API alignment is being handled on our end. The items
below are **backend/infra changes only** — they are required before web login
can work end-to-end. Everything was reproduced against the currently running
stack (`infra-backend-1`, `infra-keycloak-1` healthy).

---

## 1. BLOCKER — Keycloak issuer mismatch (causes 401 on every API call)

### Evidence
A valid token obtained from Keycloak via the browser/host carries
`iss = http://127.0.0.1:8080/realms/zmetrics` (or `http://localhost:8080/...`).
The backend validates `iss` against `token_issuer`, which is derived from
`KEYCLOAK_URL=http://keycloak:8080` (docker-compose). Result:

```bash
# Token issued via host:
curl -s -X POST http://127.0.0.1:8080/realms/zmetrics/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'grant_type=password&client_id=zmetrics-backend&client_secret=changeme-replace-in-production&username=admin-user&password=changeme&scope=openid'
# → 200, token.iss = http://127.0.0.1:8080/realms/zmetrics

curl -s http://127.0.0.1:8000/api/v1/quarries -H "Authorization: Bearer <token>"
# → 401 {"detail":"Invalid token: Invalid issuer"}
```

Root cause: `app/config.py` couples **both** `jwks_url` and `token_issuer` to the
single `keycloak_url`. A browser cannot resolve the internal docker host
`keycloak:8080`, so any browser-issued token has a different `iss` than the
backend expects.

### Requested fix (recommended — decouple issuer from JWKS host)
1. **`backend/app/config.py`** — split the single setting into two:
   - `kc_internal_url` (backchannel, JWKS fetch) — default `http://keycloak:8080`
   - `kc_public_url` (frontend/issuer) — default `http://localhost:8080`
   - `jwks_url` → `{kc_internal_url}/realms/{realm}/protocol/openid-connect/certs`
   - `token_issuer` → `{kc_public_url}/realms/{realm}`
2. **`infra/docker-compose.yml`** — Keycloak service: pin the public issuer so
   every token (regardless of request host) uses the same `iss`:
   ```yaml
   environment:
     KC_HOSTNAME_URL: http://localhost:8080   # forces iss = http://localhost:8080/realms/zmetrics
   ```
   Backend service env:
   ```yaml
     KC_INTERNAL_URL: http://keycloak:8080
     KC_PUBLIC_URL: http://localhost:8080
   ```
3. Restart `keycloak` and `backend`.

**Acceptance:** the token from the curl above is accepted →
`GET /api/v1/quarries` returns `200` (not 401).

> Fallback if a backend code change is undesirable: keep them coupled, set
> `KEYCLOAK_URL=http://localhost:8080` + `KC_HOSTNAME_URL=http://localhost:8080`,
> and add `extra_hosts: ["localhost:host-gateway"]` to the backend service so the
> in-container JWKS fetch to `localhost:8080` reaches the host-published Keycloak.
> Works, but hacky — the config split above is cleaner.

---

## 2. Web login path — ROPC/CORS on the public client

For **production** the web app should use the OIDC **PKCE** redirect flow against
`zmetrics-mobile` (public, `standardFlowEnabled: true`, `webOrigins: ["*"]`,
redirect `http://localhost:*`). That works as-is.

For **dev convenience** we'd like a password (ROPC) login from the browser. Today
neither client allows it from a browser:
- `zmetrics-mobile`: `directAccessGrantsEnabled: false` → ROPC rejected.
- `zmetrics-backend`: ROPC works but is **confidential** (secret would be exposed
  in frontend) and has **no `webOrigins`** → browser CORS blocks the token call.

### Requested (pick one)
- **(A, preferred)** Confirm PKCE is the intended web auth; no change needed.
  We'll implement web PKCE on the mobile side.
- **(B, dev shortcut)** In `infra/keycloak/realm-export.json` set
  `directAccessGrantsEnabled: true` on the **`zmetrics-mobile`** public client.
  Then the browser can do ROPC with no secret and CORS is allowed (`webOrigins: ["*"]`).
  Re-import note: `start-dev --import-realm` uses `IGNORE_EXISTING` and will **not**
  update an already-imported realm — apply the change at runtime via the admin REST
  API (or recreate the realm) so it takes effect now, and keep the file edit for
  fresh environments.

---

## 3. CORS — allow the web dev origin

The Flutter web dev server will run on **`http://localhost:5173`** (already in the
`backend_cors_origins` default). Please confirm `BACKEND_CORS_ORIGINS` in
`infra/.env` actually contains `http://localhost:5173` (and `http://localhost:8080`
is **not** needed there). If we end up on a different port we'll let you know.

---

## 4. Seed data so the app shows something for `admin-user`

`GET /api/v1/quarries` returns only quarries the current user has a non-revoked
`QuarryUserAccess` for (see `routers/quarries.py`). A freshly auto-provisioned
`admin-user` will therefore see an **empty list**. Please seed (or expose an admin
action for):
1. One `Quarry` + one `SiteSection`.
2. A `QuarryUserAccess(user=admin-user, quarry=#1, role=admin, revoked_at=NULL)`.
3. *(for the report screen)* one completed chain: `AnalysisJob(completed)` →
   `AnalysisResult` → `Report` → `Recommendation(status=requires_human_review)`.
   Give us a **report id** to open, or an endpoint to list reports for a quarry
   (there is currently no "list reports" route — only `GET /reports/{id}`).

**Acceptance:** with the dev token, `admin-user` sees ≥1 quarry, and the seeded
report id returns `200` from `GET /api/v1/reports/{id}`.

---

## 5. Contract clarifications (please confirm; we'll follow the actual behaviour)

These are **discrepancies between `docs/api_contract.md` and the implemented
routers**. We've aligned the mobile client to the *implemented* behaviour; please
confirm which is canonical and update the contract doc:

| Topic | `api_contract.md` says | Implemented router | Mobile follows |
|------|------------------------|--------------------|----------------|
| List responses | `{items,total,page,page_size}` envelope | bare JSON array (`response_model=list[...]`) | bare array |
| Create section | — | `SiteSectionCreate` requires `quarry_id` in **body** (also in path) | sends `quarry_id` in body |
| Passport revise | `POST .../revise` | requires a JSON body (`BlastPassportUpdate`) | sends `{}` |
| Capture sessions | `POST /captures/{id}/jobs` only | create/list live at `POST/GET /api/v1/quarries/{qid}/passports/{pid}/blast-event/capture-sessions` | n/a (capture stays mock for now) |

---

## 6. Out of scope for this integration (FYI)

Per product decision, the **Capture** feature stays on the mock stub for now. The
real flow requires a dependency chain we are **not** wiring yet:
`passport APPROVED/ACTIVE → POST .../blast-event → Device + Calibration must exist →
POST .../blast-event/capture-sessions (SURVEYOR role, body: device_id + calibration_id)`.
If/when capture goes live we'll need: a way to register a `Device`, create a
`Calibration`, and create a `BlastEvent` — none of which have client UIs yet.

Also note backend handoff **AUD-004**: `routers/analysis.py` uses only
`get_current_user` (no `require_quarry_role`) — any authenticated user can
submit/read analysis jobs. Worth closing before the surveyor flow ships.

---

## Quick verification script (run after the fixes)

```bash
TOKEN=$(curl -s -X POST http://localhost:8080/realms/zmetrics/protocol/openid-connect/token \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'grant_type=password&client_id=zmetrics-mobile&username=admin-user&password=changeme&scope=openid' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/api/v1/quarries -H "Authorization: Bearer $TOKEN"
# expect: 200, and a non-empty list for admin-user
```
(uses the public `zmetrics-mobile` client per item 2B; swap to `zmetrics-backend`
+ secret if you keep ROPC on the confidential client.)

---

## UPDATE 2026-06-05 — integrated ✅

Backend delivered items 1–4 (issuer fix, ROPC on the public client, CORS, and a
`POST /api/v1/admin/dev-seed` endpoint). Verified end-to-end at the HTTP layer:

- ROPC against `zmetrics-mobile` (no secret) → token with `iss=http://localhost:8080/realms/zmetrics`.
- `POST /api/v1/admin/dev-seed` → `{quarry_id, section_id, passport_id, report_id, recommendation_id}`.
- `GET /api/v1/quarries` with that token → `200` + `[{"name":"Demo Quarry",...}]`.
- CORS preflight from `http://localhost:5173` allowed on both the API and the Keycloak token endpoint.

Mobile side done: Remote repos aligned to the real shapes, dev ROPC login
(username/password), `mock ↔ backend` switch via `--dart-define=ZM_USE_MOCKS=false`,
and a "Seed demo data" button. Run: `flutter run -d web-server --web-port 5173 --dart-define=ZM_USE_MOCKS=false`.

### New follow-ups discovered during integration (low priority)

- **GAP-1: no way to fetch an `AnalysisResult` by id.** `ReportRead` exposes
  `analysis_result_id`, but the only result endpoint is
  `GET /captures/{capture_session_id}/jobs/{job_id}/result`. The mobile report
  screen therefore cannot show P10/P50/P80 in backend mode. Please add
  `GET /api/v1/analysis-results/{id}` (or embed the result in `ReportRead`).
- **GAP-2: `ReportRead` has no analysis-method / mock-vs-real field.**
  rules/product-safety.md requires reports to show the method prominently and
  label synthetic results. The client defaults to "real" (no badge) because the
  field is absent. Please add `analysis_method` (and ideally `model_version`,
  `confidence_score`) to `ReportRead`.
- **GAP-3 (contract):** list endpoints still return bare arrays while
  `api_contract.md` documents the `{items,...}` envelope — please update the doc
  (the client tolerates both).

## UPDATE 2026-06-05 (b) — after `backend-mvp-fixes.md`

Reviewed the backend MVP fixes. Mobile reaction:

- ✅ **Pagination restored** (`{items,total,page,page_size}` on all lists) — GAP-3
  effectively resolved. The client's `parseJsonList` already accepts both the
  envelope and a bare array, so no breakage. We currently read `items` and
  ignore `total`/paging (single page) — **server-side pagination UI (load-more)
  is a future mobile task**, not a backend ask.
- ✅ **AUD-004 closed** (analysis/reports now role-checked). Good — our report
  screen relies on the seeded admin having quarry access.
- ✅ **`POST /{passport_id}/complete`** — now wired in the mobile passport detail
  screen (ACTIVE → COMPLETED, shown to admins only).

### GAP-4 (NEW ask): expose the caller's per-quarry role

For accurate UI gating we currently approximate the user's role from the JWT
`realm_access.roles` (global realm roles), which may not match the real
**per-quarry** `QuarryUserAccess`. Please expose the caller's effective role per
quarry, either:
- add `my_role` (e.g. `"blaster"`) to each item of `GET /api/v1/quarries`, **or**
- add `GET /api/v1/me/access` → `[{quarry_id, role}]`.

Until then the client hides obviously-forbidden actions by realm role and relies
on the backend's 403 as the real guard (MOB-005).

## UPDATE 2026-06-06 — GAP-4 delivered & consumed ✅ (one ops note)

Backend added `GET /api/v1/me/access` → `[{quarry_id, quarry_name, role_name,
role_level}]` (mobile-auth-notes §9). **Mobile now consumes it** for precise
per-quarry UI gating (`AccessCubit` + `AuthContext.canManageBlastingOn/
canApproveOn/isAdminAnywhere`), replacing the realm-role heuristic.

**Resilience:** if `/me/access` is unreachable the client transparently falls
back to the JWT realm role, so gating keeps working either way.

⚠ **OPS:** the **running `infra-backend-1` container returns 404 for
`/api/v1/me/access`** — the endpoint exists in source (`app/routers/me.py`,
registered in `main.py`) but the deployed image is stale. Please
`docker compose -f infra/docker-compose.yml build backend && up -d backend`
(same root cause as backend-mvp-fixes §4). Until then the app runs on the
realm-role fallback. Verified once rebuilt:
`curl /api/v1/me/access -H "Authorization: Bearer <token>"` → 200 + role list.
