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
| `desktop/zmetrics_desktop/api/` | REST calls to the backend | Contain UI or business logic |
| `desktop/zmetrics_desktop/ui/` | PySide6 views | Contain network or business logic |

## Client

- The single client is a **Python + PySide6 desktop app** (`desktop/`), Windows-first.
  It replaces the former React web and Flutter mobile apps.
- The client is a thin consumer of the `/api/v1/` REST API plus local stereo capture
  (ZED 2 as UVC) and an offline SQLite queue. See `desktop.md`.
- **CV runs server-side** (in the worker). The client only captures side-by-side frames,
  splits them into left/right, and uploads. If part of the CV is later moved to the
  client, share it via an importable package derived from `worker/app/pipeline/` — do not
  duplicate the math.

## Async All the Way

- Backend: always `async def` endpoints, `AsyncSession`, `await db.execute()`
- Worker: use `asyncio.run()` at Celery task boundary; keep async pipeline internally
- Never mix sync and async SQLAlchemy in the same session
- Desktop client: keep network/camera off the Qt UI thread (`QThreadPool` workers)

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
