# ZMetrics — Roadmap

Last sync: 2026-06-06 | HEAD: `3be7873`

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

### M1 — Backend MVP (`d162899` → `1d9ad72`)
- [x] Keycloak JWT validation (RS256, JWKS fetch at runtime, issuer check)
- [x] Per-quarry RBAC (`QuarryUserAccess`, `RoleLevel` USER/SURVEYOR/BLASTER/ADMIN)
- [x] Full CRUD: quarries, site_sections, blast_passports (7-state machine)
- [x] BlastEvent creation + CaptureSession + Artifact upload (MinIO presigned)
- [x] AnalysisJob enqueue → Celery → AnalysisResult → Report → Recommendation
- [x] AuditLog written on passport/recommendation/role/access state changes
- [x] `GET /api/v1/analysis-results/{id}` (GAP-1, `8a200b6`)
- [x] `ReportRead.analysis_method` derived from `ModelVersion.model_type` (GAP-2, `8a200b6`)
- [x] Integration test suite: 49 tests against real Postgres
- [x] SEC-1: IDOR in `add_comment` fixed (`1d9ad72`)
- [x] SEC-2: `keycloak_sub` removed from API responses (`1d9ad72`)
- [x] SEC-3: `dev-seed` gated behind `ENABLE_DEV_SEED` flag (`1d9ad72`)
- [x] DB-1: `AnalysisJob.model_version_id` index + migration `6929bdaa526b` (`1d9ad72`)

### M4 (partial) — Flutter Mobile (parallel, started ahead of M2/M3)
- [x] Per-quarry RBAC: `AccessCubit`, `RoleLevel`, role-gated UI actions
- [x] Quarry / section / passport list + create screens
- [x] Passport state-machine UI (all 5 transitions, human-driven only)
- [x] Offline queue: `SyncManager` (SQLite backend), idempotency keys, retry ×5
- [x] Report screen: P10/P50/P80, Rosin-Rammler, cumulative passing table, mock badge
- [x] Recommendation review (ACCEPT / REJECT / REVIEWED) + inline comments
- [x] MOB-1: `analysisResultId` mapped, `getAnalysisResult` wired to live backend (`9dc2b4a`)
- [x] Dead `_withDerivedMethod` heuristic removed (`9dc2b4a`)

---

## IN PROGRESS / NEXT

### BACK-SEC-2 — Backend IDOR batch #2 · `backend/` only
Spec: `docs/handoffs/2026-06-06-TASK-backend-sec2-idor-capture.md`

- [ ] `capture_sessions.py`: add quarry chain-walk + `check_quarry_access` to all 3 endpoints; add JPEG/PNG magic-byte validation
- [ ] `blast_events.py`: validate `passport_id` belongs to `quarry_id` via `_get_passport_in_quarry`; add missing `check_quarry_access` to `get_blast_event` and `list_capture_sessions`
- [ ] `analysis.py::get_job_result`: join through `AnalysisJob` to enforce `capture_session_id` ownership
- [ ] `admin.py::dev_seed`: write `AuditLog(action="role_assigned")`
- [ ] 4 new tests (≥53 total)

### MOB-2 — OIDC PKCE · `mobile/` only
*Unblocks production deployment. Currently ROPC (password grant) — will break if Keycloak disables it.*

- [ ] Wire `flutter_appauth` (already in pubspec.yaml) for authorization-code + PKCE flow
- [ ] Replace `DevPasswordAuthRepository` with `OidcAuthRepository` for live mode
- [ ] Redirect URI registered in `zmetrics-mobile` Keycloak client
- [ ] Keep ROPC path behind `config.useMockServices` for local dev convenience

### MOB-3 — Capture Flow · `mobile/` only
*Depends on BACK-SEC-2 being merged first (clean endpoints).*

- [ ] `CaptureScreen`: replace stub UI with form (device/calibration selection, start capture)
- [ ] Enqueue `kOpCreateCaptureSession` → SyncProcessor actually POSTs to backend
- [ ] Frame upload via `SyncProcessor` (multipart, idempotency key per frame)
- [ ] Job status polling: `GET /capture-sessions/{id}/jobs/{job_id}` → show progress indicator
- [ ] Navigate to report screen when job status = `completed`

---

## BACKLOG (no hardware or deferred)

### MOB-4 — Report export · `mobile/`
- [ ] Save `/reports/{id}/export` JSON to device Downloads folder
- [ ] Share sheet integration (Android `ACTION_SEND`)

### M5-a — Rule-based recommendations · `worker/`
*No hardware needed. High value: engine currently writes a static placeholder text.*

- [ ] Compare `AnalysisResult.p80_mm` vs `BlastPassport.target_fragment_size_mm`
- [ ] Flag oversize (p80 > target × 1.1) and excessive fines (fines_percent > threshold)
- [ ] Write structured `Recommendation.parameter_suggestions` JSONB with basis text
- [ ] `confidence_notes` when `confidence_score < 0.8`
- [ ] Unit tests for rule logic (no DB needed)

### M5-b — LLM explanation layer · `worker/` or `backend/`
*Depends on M5-a rules being stable.*

- [ ] Claude API call with structured output for `recommendation_text` (rules/product-safety.md: `requires_human_review` enforced, no auto-apply)
- [ ] `confidence_notes` auto-generated from model output
- [ ] Fallback to rule-text if LLM unavailable

### M5-c — Historical trends · `backend/` + `mobile/`
- [ ] `GET /quarries/{id}/sections/{sid}/trend` — P80 over time per section
- [ ] Mobile chart widget (sparkline, last 10 blasts)

---

## BLOCKED (requires ZED 2 hardware)

### M2 — Real CV Stereo (8 weeks)
- [ ] OpenCV stereo calibration step (replace mock `StereoCalibrationStep`)
- [ ] Stereo rectification (replace mock)
- [ ] StereoSGBM depth estimation (replace mock)
- [ ] Open3D point cloud generation (replace mock)
- [ ] Calibration import from ZED SDK `.conf` file

### M3 — Segmentation + Particle Volumes (12 weeks, requires training data)
- [ ] YOLO-seg adapter (`SegmentationAdapter` interface)
- [ ] Training data collection and labeling pipeline
- [ ] Particle mask → 3D volume projection
- [ ] Granulometry from real particle measurements
- [ ] Report PDF generation (WeasyPrint)
- [ ] Ground truth validation (sieve analysis comparison)

---

## M6+ — Production & Scale

- [ ] ZED SDK direct USB integration (replace Camera2 placeholder)
- [ ] Multi-quarry SaaS deployment (tenant isolation, billing)
- [ ] PostGIS for quarry/section geospatial boundaries
- [ ] MLOps: model versioning, retraining pipeline, dataset management
- [ ] DVC / Git LFS for training datasets and model weights
- [ ] Replace worker `db_models.py` hand-sync with shared package import
- [ ] Keycloak user deactivation sync (currently revoked access not propagated on JWT refresh)
- [ ] PDF report generation for export (M3 dependency)
