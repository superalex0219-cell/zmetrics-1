# ZMetrics — Roadmap

## M0 — Current: Foundation (done)
- [x] Monorepo structure
- [x] Docker Compose: Postgres, Redis, MinIO, Keycloak, backend, worker
- [x] SQLAlchemy models for all domain entities
- [x] Alembic migrations setup
- [x] FastAPI skeleton: auth, CRUD endpoints, health
- [x] Mock CV pipeline: all 7 steps via `PipelineStep` interface
- [x] `AnalysisResult` computed from synthetic data
- [x] Pytest smoke tests

## M1 — Backend MVP (4 weeks)
- [ ] Keycloak JWT integration (real token validation in dev)
- [ ] Full CRUD for quarries, sections, passports
- [ ] Capture session + artifact upload API (MinIO multipart)
- [ ] `BlastEvent` creation
- [ ] `Report` and `Recommendation` generation from `AnalysisResult`
- [ ] `AuditLog` populated for all state changes
- [ ] OpenAPI docs verified, Postman collection exported
- [ ] Integration test suite with real Postgres

## M2 — Real CV Stereo (8 weeks)
- [ ] OpenCV stereo calibration step (replace mock)
- [ ] Stereo rectification (replace mock)
- [ ] StereoSGBM depth estimation (replace mock)
- [ ] Open3D point cloud generation (replace mock)
- [ ] Calibration import from ZED SDK calibration file

## M3 — Segmentation + Particle Volumes (12 weeks)
- [ ] YOLO-seg adapter (`SegmentationAdapter` interface)
- [ ] Training data collection and labeling pipeline
- [ ] Particle mask → 3D volume projection
- [ ] Granulometry from real particle data
- [ ] Report PDF generation (WeasyPrint or equivalent)
- [ ] Ground truth validation (sieve analysis comparison)

## M4 — Flutter Mobile Capture (12 weeks, parallel to M2/M3)
- [ ] Flutter auth via Keycloak PKCE (flutter_appauth)
- [ ] Quarry / section / passport list screens
- [ ] Offline queue (SyncManager + SQLite)
- [ ] Camera capture screen (Camera2 API)
- [ ] Frame upload with idempotency keys
- [ ] Job status polling and result display

## M5 — AI Recommendations (16 weeks)
- [ ] Rule-based recommendation engine (P80 vs target, oversize thresholds)
- [ ] LLM-assisted explanation layer (Claude API with structured output)
- [ ] Recommendation review workflow improvements
- [ ] Historical trend analysis (P80 vs passport target per section)

## M6+ — Production & Scale
- [ ] ZED SDK direct integration (replace Camera2)
- [ ] Multi-quarry SaaS deployment
- [ ] Geospatial data (PostGIS for quarry/section boundaries)
- [ ] MLOps: model versioning, retraining pipeline, dataset management
- [ ] DVC / Git LFS for training datasets and model weights
