# ZMetrics — Roadmap

## M0 — Foundation (DONE `d7a1983`)
- [x] Monorepo structure
- [x] Docker Compose: Postgres, Redis, MinIO, Keycloak, backend, worker
- [x] SQLAlchemy models for all domain entities
- [x] Alembic migrations setup
- [x] FastAPI skeleton: auth, CRUD endpoints, health
- [x] Mock CV pipeline: all 7 steps via `PipelineStep` interface
- [x] `AnalysisResult` computed from synthetic data
- [x] Pytest smoke tests

## M1 — Backend MVP (DONE `d162899`–`1d9ad72`)
- [x] Keycloak JWT integration (RS256, JWKS from Keycloak, issuer check)
- [x] Full CRUD for quarries, sections, passports
- [x] Capture session + artifact API (MinIO presigned upload/download)
- [x] `BlastEvent` creation
- [x] `Report` and `Recommendation` generation from `AnalysisResult`
- [x] `AuditLog` populated for passport/recommendation/role/access changes
- [x] Integration test suite with real Postgres (49 tests)
- [x] Per-quarry RBAC (`QuarryUserAccess`, `RoleLevel` USER/SURVEYOR/BLASTER/ADMIN)
- [x] Security hardening: IDOR fix, keycloak_sub removed, dev-seed guard, DB index
- [ ] OpenAPI docs exported / Postman collection — deferred (auto-docs via `/docs` sufficient for M1)

## M4 — Flutter Mobile (MOSTLY DONE — parallel milestone, started ahead of M2/M3)
- [x] Per-quarry RBAC in mobile (AccessCubit, role-gated UI)
- [x] Quarry / section / passport list + create screens
- [x] Passport state-machine UI (DRAFT→SUBMITTED→APPROVED→ACTIVE→COMPLETED)
- [x] Offline queue (SyncManager + SQLite, idempotency keys, retry×5)
- [x] Report screen: P10/P50/P80, Rosin-Rammler, cumulative passing table (`9dc2b4a`)
- [x] Recommendation review (ACCEPT/REJECT/REVIEWED) + inline comments
- [x] Mock pipeline safety badge (`MockPipelineBadge`)
- [ ] **MOB-2:** Flutter auth via Keycloak PKCE (flutter_appauth) — currently ROPC; needed for production
- [ ] **MOB-3:** Camera capture screen (Camera2 API placeholder → queue → job polling)
- [ ] **MOB-3:** Frame upload via SyncProcessor (SyncProcessor handler is a no-op today)
- [ ] Report export: save JSON to device / share sheet

## BACK-SEC-2 — Backend security batch #2 (pre-existing IDORs)
Flagged by security-reviewer during SEC-1 batch; deferred as out-of-scope then.

- [ ] `capture_sessions.py`: artifact upload/URL endpoints missing `check_quarry_access`
- [ ] `blast_events.py`: `passport_id` not validated against `quarry_id` in path
- [ ] `analysis.py`: `get_job_result` — `job_id` not validated against `capture_session_id`
- [ ] `dev_seed`: no `AuditLog(action="role_assigned")` written for the grant

## M2 — Real CV Stereo (requires ZED 2 hardware — 8 weeks)
- [ ] OpenCV stereo calibration step (replace mock)
- [ ] Stereo rectification (replace mock)
- [ ] StereoSGBM depth estimation (replace mock)
- [ ] Open3D point cloud generation (replace mock)
- [ ] Calibration import from ZED SDK calibration file

## M3 — Segmentation + Particle Volumes (requires training data — 12 weeks)
- [ ] YOLO-seg adapter (`SegmentationAdapter` interface)
- [ ] Training data collection and labeling pipeline
- [ ] Particle mask → 3D volume projection
- [ ] Granulometry from real particle data
- [ ] Report PDF generation (WeasyPrint or equivalent)
- [ ] Ground truth validation (sieve analysis comparison)

## M5 — AI Recommendations (no hardware needed)
- [ ] Rule-based recommendation engine (P80 vs passport target, oversize thresholds)
- [ ] LLM-assisted explanation layer (Claude API with structured output, `requires_human_review` enforced)
- [ ] Historical trend analysis (P80 vs passport target per section over time)
- [ ] Recommendation review workflow improvements (bulk view, filters)

## M6+ — Production & Scale
- [ ] ZED SDK direct integration (replace Camera2)
- [ ] Multi-quarry SaaS deployment
- [ ] Geospatial data (PostGIS for quarry/section boundaries)
- [ ] MLOps: model versioning, retraining pipeline, dataset management
- [ ] DVC / Git LFS for training datasets and model weights
- [ ] worker `db_models.py` replaced by shared package import (currently hand-synced — SYNC risk)
