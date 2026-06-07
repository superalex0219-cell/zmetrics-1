# ZMetrics — Roadmap

Last sync: 2026-06-07 | HEAD: `4435f28`

---

## DONE

### M0 — Foundation (`d7a1983`)
- [x] Monorepo structure (backend / worker / mobile / infra / docs)
- [x] Docker Compose: Postgres 16, Redis 7, MinIO, Keycloak 24, backend, worker
- [x] SQLAlchemy 2.0 async models for all domain entities
- [x] Alembic migrations with async env
- [x] FastAPI skeleton: JWT auth, CRUD endpoints, health
- [x] Mock CV pipeline: 7 steps via `PipelineStep` interface
- [x] `AnalysisResult` computed from synthetic data (Rosin-Rammler)
- [x] Pytest smoke tests

### M1 — Backend MVP + Security (`d162899` → `aa4c42f`)
- [x] Keycloak JWT validation (RS256, JWKS fetch at runtime, issuer check)
- [x] Per-quarry RBAC (`QuarryUserAccess`, `RoleLevel` USER/SURVEYOR/BLASTER/ADMIN)
- [x] Full CRUD: quarries, site_sections, blast_passports (7-state machine)
- [x] BlastEvent creation + CaptureSession + Artifact upload (MinIO presigned)
- [x] AnalysisJob enqueue → Celery → AnalysisResult → Report → Recommendation
- [x] AuditLog written on passport/recommendation/role/access state changes
- [x] `GET /api/v1/analysis-results/{id}` (GAP-1)
- [x] `ReportRead.analysis_method` derived from `ModelVersion.model_type` (GAP-2)
- [x] Integration test suite: 53 tests against real Postgres
- [x] SEC-1: IDOR in `add_comment` fixed
- [x] SEC-2: `keycloak_sub` removed from API responses
- [x] SEC-3: `dev-seed` gated behind `ENABLE_DEV_SEED` flag
- [x] DB-1: `AnalysisJob.model_version_id` index + migration
- [x] BACK-SEC-2: IDOR batch — `capture_sessions`, `blast_events`, `analysis` + magic-byte validation + AuditLog in dev_seed

### M4 — Flutter Mobile (`796823a` → `ebb28e5`)
- [x] Per-quarry RBAC: `AccessCubit`, `RoleLevel`, role-gated UI actions
- [x] Quarry / section / passport list + create screens
- [x] Passport state-machine UI (all 5 transitions, human-driven only)
- [x] Offline queue: `SyncManager` (SQLite backend), idempotency keys, retry ×5
- [x] Report screen: P10/P50/P80, Rosin-Rammler, cumulative passing table, mock badge
- [x] Recommendation review (ACCEPT / REJECT / REVIEWED) + inline comments
- [x] MOB-1: `getAnalysisResult` wired to live backend
- [x] MOB-2: OIDC PKCE via `flutter_appauth` (Keycloak `zmetrics-mobile` client)
- [x] MOB-3: Capture flow — device/calibration picker, SyncProcessor, job polling, navigate to reports
- [x] MOB-4: Report JSON export via Android share sheet (`share_plus`)
- [x] MOB-DESIGN: Teal theme `0xFF0F766E`, dark AppBar `0xFF17202A`, Russian labels, `StatCard` widget
- [x] 63 tests total

### WEB-1 — React Web Frontend (`09ca465`)
- [x] React + Vite + TypeScript + Lucide + plain CSS (matches reference design)
- [x] Keycloak OIDC browser redirect (check-sso + PKCE, `zmetrics-web` Keycloak client)
- [x] Auth screen: Keycloak redirect, display name in topbar, logout
- [x] Dashboard: live quarry/section/report counts, latest analysis P80, fraction histogram
- [x] Карьеры: real quarry cards from `GET /api/v1/quarries`
- [x] Участки: quarry selector → `GET /api/v1/quarries/{id}/sections`
- [x] Паспорта БВР: list + create form → `POST /api/v1/quarries/{id}/passports`
- [x] Отчёты: list + JSON export (Bearer auth download), `⚠ Синтетические данные` mock badge
- [x] Рекомендации: list + review (принять/отклонить/ознакомлен); `parameter_suggestions` read-only
- [x] `frontend` service in docker-compose, nginx proxy, Dockerfile
- [x] `tsc --noEmit` passes

### M5-a — Rule-based recommendations · `worker/` (`4435f28`)
- [x] `evaluate_fragmentation()` pure function — oversize (`p80 > target × 1.1`), excessive fines (`> 15%`), on_target
- [x] `parameter_suggestions` JSONB: `observed_p80_mm`, `target_p80_mm`, `deviation_pct`, `basis`; `None` when target unknown
- [x] `BlastEvent` + `BlastPassport` read-only stubs in `worker/app/db_models.py`
- [x] Join chain `CaptureSession → BlastEvent → BlastPassport` in `_create_report_and_recommendation`
- [x] `confidence_notes` auto-populated when `confidence_score < 0.8`
- [x] 15 unit tests for rule logic

---

## BACKLOG

### WEB-2 — Passport workflow in web · `frontend/`
*Web currently has passport list + basic create. Missing the full workflow.*

- [ ] Passport detail view (all fields, status chip, revision history)
- [ ] State transitions: DRAFT → SUBMITTED → APPROVED (human buttons, same safety rules as mobile)
- [ ] Blast event creation form under passport detail
- [ ] AuditLog display on passport detail (admin/blaster only)

### M5-b — LLM explanation layer · `worker/` or `backend/`
*Depends on M5-a rules being stable. Adds human-readable text to structured suggestions.*

- [ ] Claude API call with structured output for `recommendation_text`
- [ ] `confidence_notes` auto-generated from model output
- [ ] Fallback to rule-text if LLM unavailable
- [ ] Safety: `requires_human_review` enforced, no auto-apply

### M5-c — Historical P80 trends · `backend/` + `frontend/` + `mobile/`
- [ ] `GET /api/v1/quarries/{id}/sections/{sid}/trend` — P80 over last N blasts per section
- [ ] Web dashboard: sparkline chart in section/passport context
- [ ] Mobile: sparkline widget on reports list screen

### WEB-3 — Admin panel + audit log · `frontend/`
*Low urgency — admin ops currently via direct API calls or dev-seed endpoint.*

- [ ] Wire Admin screen: real user list from `GET /api/v1/quarry-users`
- [ ] Audit log table: `GET /api/v1/audit-log` (paginated, admin only)
- [ ] Role assignment UI (admin only — calls `POST /api/v1/quarries/{id}/users`)

---

## BLOCKED (requires ZED 2 hardware)

### M2 — Real CV Stereo (≈8 weeks after hardware)
- [ ] OpenCV stereo calibration step (replace mock `StereoCalibrationStep`)
- [ ] Stereo rectification (replace mock)
- [ ] StereoSGBM depth estimation (replace mock)
- [ ] Open3D point cloud generation (replace mock)
- [ ] Calibration import from ZED SDK `.conf` file

### M3 — Segmentation + Particle Volumes (≈12 weeks, requires training data)
- [ ] YOLO-seg adapter (`SegmentationAdapter` interface)
- [ ] Training data collection and labeling pipeline
- [ ] Particle mask → 3D volume projection
- [ ] Granulometry from real particle measurements
- [ ] Report PDF generation (WeasyPrint) — web download button already wired to export endpoint
- [ ] Ground truth validation (sieve analysis comparison)

---

## M6+ — Production & Scale

- [ ] ZED SDK direct USB integration (replace Camera2 placeholder)
- [ ] Multi-quarry SaaS deployment (tenant isolation, billing)
- [ ] PostGIS for quarry/section geospatial boundaries
- [ ] MLOps: model versioning, retraining pipeline, dataset management
- [ ] DVC / Git LFS for training datasets and model weights
- [ ] Replace worker `db_models.py` hand-sync with shared package import
- [ ] Keycloak user deactivation sync (revoked access not propagated on JWT refresh)
- [ ] Web: real-time job status via WebSocket (currently no live updates in web)
- [ ] Mobile: push notifications for completed analysis jobs
