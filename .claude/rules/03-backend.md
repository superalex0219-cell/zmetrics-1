---
paths:
  - "backend/**/*.py"
---

# Backend Coding Rules

## Stack
- FastAPI + Pydantic v2 + SQLAlchemy 2.0 (async) + Alembic
- Use `AsyncSession` everywhere; never use sync SQLAlchemy sessions in the API

## Models
- All PKs are `UUID`, generated via `uuid.uuid4` (Python-side default)
- All models inherit `TimestampMixin` for `created_at` / `updated_at`
- Use `mapped_column()` and `Mapped[T]` annotations (SQLAlchemy 2.0 style)
- Enum columns use `SQLAlchemyEnum(MyEnum)` type; define the Python enum separately
- Store camera matrices and JSON blobs as `JSONB` (PostgreSQL-native)

## Schemas
- Response schemas use `model_config = ConfigDict(from_attributes=True)`
- Keep request schemas (Create/Update) separate from response schemas (Read)
- Do not expose internal IDs of soft-deleted records in list endpoints

## Routers
- Routers are thin — they validate input, call a service, return a response
- Business logic lives in `app/services/`
- Every mutating endpoint must: (1) verify JWT, (2) check quarry role ≥ required level, (3) write AuditLog for state-changing ops

## Auth
- Use `Depends(get_current_user)` on all protected endpoints
- Use `Depends(require_quarry_role(RoleLevel.BLASTER))` for write operations
- Role level hierarchy: USER=1, SURVEYOR=2, BLASTER=3, ADMIN=4
- Admin-only operations use `require_quarry_role(RoleLevel.ADMIN)`

## FastAPI Patterns
- Use `lifespan` context manager (not deprecated `@app.on_event`)
- Use `APIRouter` with `prefix` and `tags` for all routers
- Return HTTP 404 (not 500) for missing resources; use `raise HTTPException(status_code=404)`
- Pagination: `?page=1&page_size=20`, return `{"items": [...], "total": N, "page": 1, "page_size": 20}`

## Alembic
- Run `alembic revision --autogenerate` after model changes
- Never edit generated migration files except for: ordering, data migrations, adding indexes
- Migration `env.py` uses the async pattern (`asyncio.run(run_async_migrations())`)
