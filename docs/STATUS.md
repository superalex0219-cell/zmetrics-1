# ZMetrics - STATUS

**Last updated:** 2026-06-09 (rev 8 — ADMIN-USERS-1 backend DONE (working tree); ADMIN-USERS-2 frontend next)
**Git HEAD:** `4aa677b`
**Working tree:** active development changes are not committed yet.

> ⚠ **Backend image NOT rebuilt** for ADMIN-USERS-1 — running container still serves pre-task code (`pytest` in container = 57). ADMIN-USERS-1 verified by executor's local run (78 passed) + curator code inspection. Rebuild `backend` to activate.

---

## TL;DR для следующей сессии

1. **Infra is up.** Docker Desktop data was reset/moved to `G:\DockerDesktop\wsl`; current stack is running from `X:\zmetrics\zmetrics`.
2. **Worker/SAM3 is no longer pending rebuild.** Worker image is rebuilt and running with CUDA:
   - `torch 2.11.0+cu128`
   - `torchvision 0.26.0+cu128`
   - `transformers 5.10.2`
   - GPU: `NVIDIA GeForce RTX 5080`
   - model mount: `/models/sam3` from `models/sam3/`
3. **SAM3 smoke tests passed.**
   - Local GPU smoke: 77 masks on `frontend/public/assets/rock-sample.png`.
   - Container GPU smoke: 77 masks, ~5.9s, peak VRAM ~3.9 GB.
4. **Web UI can bootstrap an empty DB.**
   - `POST /api/v1/quarries` now allows the first authenticated user to create the first quarry.
   - Creator receives admin access on the created quarry.
   - Multiple existing admin accesses no longer crash quarry creation.
5. **Frontend has a visible redesign pass.**
   - Responsive shell with fixed topbar, desktop sidebar, mobile drawer, breadcrumbs, toast, loading banner.
   - Dashboard rebuilt as an operational screen with command block, workflow progress, quick actions, latest reports.
   - Quarries/Sites rebuilt as management layouts with form + working area.
6. **Next practical task:** add a UI/API smoke path for SAM3 job launch, then run Rule Engine E2E (P80 vs target and recommendation text in UI).

---

## Current runtime

| Service | State | Notes |
|---|---:|---|
| frontend | running | `http://localhost:5173`, latest build assets: `index-C-ksp_ND.js`, `index-H1In1gsc.css` |
| backend | healthy | `http://localhost:8000/health` |
| worker | running | Celery worker responds to ping; SAM3 loads on CUDA |
| keycloak | running | `http://localhost:8080` |
| minio | healthy | `http://localhost:9001` |
| postgres | healthy | compose volume under Docker Desktop data on `G:` |
| redis | healthy | compose volume under Docker Desktop data on `G:` |

---

## Layer status

| Layer | State | Notes |
|---|---|---|
| **backend** | M1 + SEC-1 + BACK-SEC-2 + ARCH-1 + web bootstrap fix | Full suite last run: 56 passed. New quarry bootstrap tests: 4 passed. |
| **worker** | M1 + M5-a + M5-b + SAM3 GPU segmentation | SAM3 path default `/models/sam3`; CUDA runtime validated before Transformers import. Worker tests: 32 passed in container (23 + 9 LLM). LLM layer dormant until image rebuilt with `anthropic` + flag/key set. |
| **frontend** | WEB-1 + WEB-2 + responsive redesign | Docker build passes. Runtime nginx serves redesigned UI at `localhost:5173`. |
| **mobile** | M1 + MOB-1/2/3/4 + MOB-DESIGN | 63 tests from previous milestone. Not touched in this session. |
| **infra** | running | Worker image rebuilt with CUDA PyTorch cu128. Frontend image rebuilt after redesign. |

---

## Completed in current working tree

| Area | What changed |
|---|---|
| Docker | Docker data reset/moved to `G:\DockerDesktop\wsl`; stack started again. |
| Worker | Dockerfile now installs CUDA PyTorch/torchvision cu128 before `.[sam3]`. |
| Worker | SAM3 runtime guard added for too-old PyTorch (`float8_e8m0fnu`). |
| Worker | Default `SAM3_MODEL_PATH` changed to `/models/sam3`. |
| Worker | Added lightweight SAM3 runtime tests. |
| Backend | First quarry bootstrap path added; creator gets admin role. |
| Backend | Quarry creation fixed for users with more than one existing admin access. |
| Backend | Added `backend/tests/test_quarries.py`. |
| Frontend | Added quarry and site-section creation APIs and UI forms. |
| Frontend | Added `.dockerignore` to avoid copying local `node_modules` into Docker builds. |
| Frontend | Redesign pass: responsive shell, mobile drawer, breadcrumbs, toasts, loading/empty states. |
| Frontend | Dashboard rebuilt into operational workflow screen. |
| Frontend | Quarries/Sites rebuilt into management layouts. |
| Frontend | Reports now have search/sort and clearer empty/error states. |
| Backend | `POST /devices` returns 409 (not 500) on duplicate serial_number (`IntegrityError` → rollback + HTTPException). |
| Backend | **Fixed E2E 422 on `POST /captures/{id}/jobs`**: `AnalysisJobCreate.capture_session_id` was a required body field but is redundant with the URL path. Removed it; body is now optional (`AnalysisJobCreate \| None = None`). |
| Frontend | Analyses page: device/calibration creation moved out of fragile mount-time state into self-healing `handleLaunch` (auto-creates default ZED 2 + calibration if none). Removed `deviceList` state, the separate "Register ZED 2" UI section, and the `deviceList.length > 0` gate on the launch button. |
| Worker | M5-b: `app/llm.py` enhances `recommendation_text` via Anthropic API (flag `ENABLE_LLM_RECOMMENDATIONS`). Lazy SDK import; always falls back to deterministic M5-a rule text; `MOCK_BADGE`/`REVIEW_FOOTER` enforced in code; `parameter_suggestions`/`status` untouched; `max_retries=0`. |
| Backend | ADMIN-USERS-1: `services/keycloak_admin.py` (service-account token cache, create/update/reset-password), `POST /admin/users`, `POST /admin/users/{id}/reset-password`, `GET /admin/users/{id}/access`; PATCH/DELETE sync identity to Keycloak. Behind `ENABLE_ADMIN_USER_MGMT`. Temp pw returned once (never stored/logged/audited); savepoint rollback neutralizes orphan KC account; no `keycloak_sub` in responses. |
| Infra | `zmetrics-backend` service account granted `realm-management: manage-users/view-users/query-users` in realm-export.json; `KC_CLIENT_SECRET` + `ENABLE_ADMIN_USER_MGMT` wired into backend compose env + `.env.example`. |

---

## Verification log

| Check | Result |
|---|---|
| `docker compose ... exec backend pytest tests` | 56 passed |
| `docker compose ... exec backend pytest tests/test_quarries.py` | 4 passed |
| `worker\.venv ... pytest worker/tests` | 23 passed |
| Worker Celery ping | OK / pong |
| Local SAM3 GPU smoke | 77 masks |
| Container SAM3 GPU smoke | 77 masks, CUDA |
| `docker compose ... build frontend` | passed |
| `http://localhost:5173/` | 200 |
| latest frontend JS/CSS assets | 200 |
| `docker compose ... build backend` (rev 6) | passed |
| `pytest tests/test_analysis.py tests/test_blast_capture.py` (rev 6) | 20 passed |
| `http://localhost:8000/health` (rev 6) | 200 |
| `worker exec pytest tests/` (rev 7) | 32 passed |
| `worker exec import app.llm` without `anthropic` (rev 7) | OK (lazy import verified in running container) |

Note: automated headless browser check did not run because the bundled local runtime missed `playwright-core`; use manual browser QA for visual checks.

---

## Deploy notes — activating ADMIN-USERS (Keycloak Admin API)

The feature ships **dark** (`ENABLE_ADMIN_USER_MGMT=false`). To turn it on:

1. **Rebuild backend image** — code is in the working tree but not in the running container:
   `docker compose -f infra\docker-compose.yml up -d --build backend`
2. **Fix `infra/.env`** (currently misconfigured for the admin grant):
   - `KC_CLIENT_ID=zmetrics-backend` ← currently `zmetrics-frontend` (a client that isn't even in the realm; harmless for JWT validation today, but the `client_credentials` grant needs the service-account client)
   - `KC_CLIENT_SECRET=<zmetrics-backend client secret>` (must match realm)
   - `ENABLE_ADMIN_USER_MGMT=true`
3. **Service-account roles** — realm-export.json now grants them, but the realm is imported only on first boot. For the **existing** stack either re-import the realm or assign `realm-management: manage-users/view-users` to the `zmetrics-backend` service account once via Keycloak Admin Console (8080).
4. Smoke: `POST /api/v1/admin/users` → use returned temp password in a password-grant token request.

**Unrelated security note (not yet fixed):** `infra/docker-compose.yml` hardcodes `ENABLE_DEV_SEED: "true"`. `dev-seed` grants the caller admin on a quarry — for shared stands change to `${ENABLE_DEV_SEED:-false}`.

---

## Priority queue

| Pri | ID | Item | Layer | Notes |
|---|---|---|---|---|
| ~~P1~~ | ~~WORKER-FIX-1~~ | ~~Fix worker db_models.py: Artifact.minio_key→storage_key, add calibration_id~~ | ~~worker~~ | **DONE 2026-06-09** — storage_bucket/storage_key, calibration_id, Calibration stub, sam3 fixed |
| ~~P1~~ | ~~WEB-ANALYSIS-1~~ | ~~Capture panel: browser getUserMedia + photo gallery + passport selector + job poll~~ | ~~frontend~~ | **DONE 2026-06-09** — types.ts, api.ts, App.tsx; SBS auto-split; passport filter; state machine. E2E live-test fixes (rev 6): device self-heal, 409 on dup serial, enqueue 422 fixed. |
| ~~P1~~ | ~~M2-STEREO~~ | ~~Real OpenCV StereoSGBM pipeline in worker (cv_*.py files)~~ | ~~worker~~ | **DONE 2026-06-09** — cv_calibration/rectification/depth/pointcloud, ENABLE_REAL_STEREO flag. ⚠ Calibration JSON format needs verify before enabling. |
| ~~P2~~ | ~~ADMIN-USERS-1~~ | ~~Admin user mgmt via Keycloak Admin API~~ | ~~backend+infra~~ | **DONE 2026-06-09 (working tree)** — keycloak_admin client, create/reset-pw/access endpoints, realm service-account roles. 78 tests (executor-local) + code review. ⚠ Rebuild backend + fix `.env` to activate (see Deploy notes). |
| **P2** | ADMIN-USERS-2 | Admin user mgmt UI (rewrite AdminPage placeholder) | frontend | **SPECCED, UNBLOCKED** → `docs/handoffs/2026-06-09-TASK-admin-users-2-frontend.md`. Ready for executor. |
| **P2** | WEB-QA-1 | Manual responsive QA at 1920/1366/768/390 widths | frontend | Verify no horizontal scroll, mobile drawer, tables-as-cards, forms. |
| **P2** | UT-2 | Rule engine E2E: P80 vs target, recommendation text in UI | backend/worker/frontend | Unblocked by WEB-ANALYSIS-1. |
| ~~P3~~ | ~~M5-b~~ | ~~LLM explanation layer~~ | ~~worker~~ | **DONE 2026-06-09** — `app/llm.py`, lazy SDK, fallback-safe, badge/footer enforced, 32 worker tests. ⚠ Rebuild worker image (`anthropic`) + set flag/key to activate. |
| later | UT-3 | Mobile smoke test | Android | Needs Android Studio + AVD/device. |

---

## Dev credentials

- Keycloak admin UI: `http://localhost:8080` -> `admin` / see `infra/.env`
- App login: `admin-user` / `changeme`
- Password token flow for dev/API smoke:
  `POST http://localhost:8080/realms/zmetrics/protocol/openid-connect/token`
  with `client_id=zmetrics-mobile`, `grant_type=password`, `username=admin-user`, `password=changeme`
- Dev seed: `POST /api/v1/admin/dev-seed` requires `ENABLE_DEV_SEED=true` and Bearer token.

---

## Safety invariants

- `Recommendation` always starts with `status = requires_human_review`.
- No auto-approve / bulk-approve endpoints.
- Passport transitions are explicit human HTTP actions.
- AuditLog is append-only and records state changes.
- Mock/synthetic reports remain labeled in UI.
- `parameter_suggestions` are read-only in UI; no write-back path to passports.

---

## Active handoffs

| File | Task | Status |
|---|---|---|
| `2026-06-09-TASK-admin-users-1-backend.md` | ADMIN-USERS-1 Keycloak Admin API user mgmt | done (working tree) — pending backend rebuild |
| `2026-06-09-TASK-admin-users-2-frontend.md` | ADMIN-USERS-2 admin user mgmt UI | specced — unblocked, ready for executor |
| `2026-06-09-TASK-worker-m5b-llm-explanation.md` | M5-b LLM explanation layer | done (working tree) |
| `2026-06-08-TASK-m2-stereo-cv.md` | M2-STEREO real OpenCV stereo pipeline | done (working tree) |
| `2026-06-08-TASK-worker-fix-1.md` | WORKER-FIX-1 db_models + sam3 fix | done (working tree) |
| `2026-06-09-TASK-web-analysis-1.md` | WEB-ANALYSIS-1 camera capture panel | done (working tree) |
| `2026-06-07-TASK-web2-passport-workflow.md` | WEB-2 passport workflow | done (`849e1f9`) |
| `2026-06-07-TASK-worker-m5a-rule-engine.md` | M5-a rule engine | done (`4435f28`) |
| `2026-06-06-TASK-backend-sec2-idor-capture.md` | BACK-SEC-2 IDORs | done (`aa4c42f`) |
| `2026-06-06-TASK-mobile-mob2-pkce.md` | MOB-2 OIDC PKCE | done (`796823a`) |
| `2026-06-06-TASK-mobile-mob3-capture-flow.md` | MOB-3 capture flow | done (`760dbb5`) |
| `2026-06-06-TASK-mobile-mob4-report-export.md` | MOB-4 report export | done (`f734b97`) |
