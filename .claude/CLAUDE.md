# ZMetrics — Quarry Blast Fragmentation Analysis

## Product Goal
Platform for managing blast work passports (паспорт БВР), capturing stereo images of blast muck piles (развал) via ZED 2, running asynchronous CV/ML analysis, calculating particle size distribution, and generating reports with AI-assisted BVR recommendations.

## Domain Glossary
- **BVR / БВР** — Буровзрывные работы (Blast Work)
- **Паспорт БВР** — Blast Work Passport (blast design document)
- **Развал** — Blast muck pile (fragmented rock after explosion)
- **Грансостав / гранулометрический состав** — Granulometric distribution (particle size distribution)
- **P10/P50/P80** — % passing sizes in mm (10/50/80% of material passes this size)
- **Rosin-Rammler** — Empirical distribution fit for fragmentation: `R = exp(-(x/xc)^n)`
- **Карьер** — Quarry
- **Участок / блок** — Site section / blast block within a quarry

## Architecture
- **Infra**: Docker Compose (postgres:16, redis:7, minio, keycloak:24, backend, worker)
- **Auth**: Keycloak OIDC. FastAPI validates JWT RS256 from Keycloak JWKS. Roles are per-quarry (not global): `user < surveyor < blaster < admin`.
- **Storage**: PostgreSQL 16 for structured data. MinIO (S3-compatible) for stereo frames, point clouds, masks, report files.
- **Async**: Celery + Redis. Analysis jobs run in the worker container.
- **Backend**: FastAPI + Pydantic v2 + SQLAlchemy 2.0 (async) + Alembic
- **Worker**: Celery + mock CV pipeline. Real CV (OpenCV/Open3D/YOLO-seg) is a later milestone.
- **Mobile**: Flutter Android-first, offline store-and-forward.

## Entity Hierarchy (process flow)
```
Quarry → SiteSection → BlastPassport → BlastEvent
                                           ↓
                                   CaptureSession (Device + Calibration)
                                           ↓
                                       Artifact (left/right/depth/pointcloud/mask)
                                           ↓
                                      AnalysisJob (Celery, status: queued→running→completed|failed)
                                           ↓
                                     AnalysisResult (P10/P50/P80, Rosin-Rammler params)
                                           ↓
                                         Report
                                           ↓
                             Recommendation (always starts: requires_human_review)
```

## Safety Constraints (NON-NEGOTIABLE)
- **NEVER** write code that auto-approves or auto-applies blast parameters.
- All `Recommendation` records MUST be created with `status = requires_human_review`.
- `BlastPassport` state transitions require explicit human action at each step.
- Keep `AuditLog` entries for: passport state changes, role assignments, recommendation reviews.

## Monorepo Layout
- `backend/` — FastAPI app, SQLAlchemy models, Alembic migrations, Pydantic schemas, tests
- `worker/` — Celery tasks, pipeline interface + mock implementations
- `mobile/` — Flutter Android-first app
- `infra/` — Docker Compose, Keycloak realm config, MinIO init script
- `docs/` — Architecture docs, domain model, API contract, pipeline spec, roadmap
- `scripts/` — PowerShell bootstrap and migration helpers
- `.claude/rules/` — Claude coding rules per layer

## Key Commands (PowerShell)

Start all services:
```powershell
docker compose -f infra\docker-compose.yml up -d
```

Run migrations:
```powershell
docker compose -f infra\docker-compose.yml exec backend alembic upgrade head
```

Create new migration:
```powershell
docker compose -f infra\docker-compose.yml exec backend alembic revision --autogenerate -m "description"
```

Run backend tests:
```powershell
docker compose -f infra\docker-compose.yml exec backend pytest -v
```

View logs:
```powershell
docker compose -f infra\docker-compose.yml logs -f backend worker
```
