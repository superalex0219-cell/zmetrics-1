# Architecture Rules

These rules apply to all files. They define the system's structural invariants.

## Process Flow (non-negotiable)

Every change must respect this entity hierarchy:
```
Quarry → SiteSection → BlastPassport → BlastEvent
                                           ↓
                                   CaptureSession (Device + Calibration)
                                           ↓
                                       Artifact
                                           ↓
                                      AnalysisJob → AnalysisResult → Report → Recommendation
```

No shortcut paths. A `Report` cannot exist without an `AnalysisResult`. An `AnalysisResult` cannot exist without a completed `AnalysisJob`. An `AnalysisJob` cannot exist without a `CaptureSession`.

## Layer Boundaries

| Layer | Owns | Must NOT |
|-------|------|----------|
| `backend/app/routers/` | HTTP input/output | Contain business logic |
| `backend/app/services/` | Domain logic, DB mutations | Call external HTTP APIs |
| `backend/app/db/models/` | Table schema + relationships | Contain business logic |
| `backend/app/schemas/` | API contracts | Import ORM models directly |
| `worker/app/pipeline/` | CV/ML computation | Call FastAPI endpoints |
| `worker/app/tasks/` | Celery orchestration | Contain CV math |

## Async All the Way

- Backend: always `async def` endpoints, `AsyncSession`, `await db.execute()`
- Worker: use `asyncio.run()` at Celery task boundary; keep async pipeline internally
- Never mix sync and async SQLAlchemy in the same session

## Storage Split

| Data type | Store in |
|-----------|----------|
| Structured metadata | PostgreSQL |
| Stereo frames (.jpg) | MinIO `zmetrics-frames` bucket |
| Pipeline artifacts (.npy, .ply, .json) | MinIO `zmetrics-artifacts` bucket |
| Report files (.pdf, .html) | MinIO `zmetrics-artifacts` bucket |
| ML model weights | MinIO (separate bucket, M3+) |
| Secrets, tokens | Never stored; environment variables only |

## Versioning Conventions

- `BlastPassport`: `revision_number` increments on each revision; old record gets `status=SUPERSEDED`
- `ModelVersion`: ML models tracked in DB with `version_tag`; `is_active` flag marks the current default
- API: versioned at `/api/v1/`; breaking changes require `/api/v2/`
