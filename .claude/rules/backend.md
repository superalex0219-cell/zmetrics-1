---
paths:
  - "backend/**/*.py"
---

# Backend Coding Rules

## Stack
- FastAPI + Pydantic v2 + SQLAlchemy 2.0 (async) + Alembic
- Always `async def` endpoints, always `AsyncSession`; never use sync SQLAlchemy in the API

## Framework conventions
- Use the `lifespan` context manager (not the deprecated `@app.on_event`)
- All routers use `APIRouter(prefix=..., tags=[...])`
- Routers are thin: validate input → call a service → return a response
- Business logic lives in `backend/app/services/`, never in routers
- API is versioned at `/api/v1/`; breaking changes require `/api/v2/`

## Models
- All PKs are `UUID`, generated Python-side via `default=uuid.uuid4` (not server-side)
- All mutable models inherit `TimestampMixin` (`created_at` / `updated_at`)
- Soft-deletable models (quarry, site_section) inherit `SoftDeleteMixin` (`deleted_at`)
- Use `Mapped[T]` + `mapped_column()` (SQLAlchemy 2.0 style)
- Enum columns: define the Python `str, enum.Enum` separately; use `SAEnum(MyEnum, name="...")`
- Store camera matrices and JSON blobs as `JSONB`
- See `database.md` for full schema/migration conventions

## SQLAlchemy 2.0 usage
- Queries: `await session.execute(select(Model).where(...))`
- Flush before reading back generated IDs: `await session.flush()`
- `expire_on_commit=False` on the session factory (already configured)

## Schemas
- Keep request schemas (Create/Update) separate from response schemas (Read)
- Response schemas: `model_config = ConfigDict(from_attributes=True)`
- Request schemas: validate input only — no `from_attributes`
- Use `model_dump(exclude_unset=True)` on update payloads to patch only provided fields
- Schemas must NOT import ORM models directly
- Never expose internal FK IDs of soft-deleted records, nor `keycloak_sub`

## Auth
- Use `Depends(get_current_user)` on all protected endpoints (skip only `/health`)
- Use `Depends(require_quarry_role(RoleLevel.BLASTER))` for write operations
- Role hierarchy: `USER=1, SURVEYOR=2, BLASTER=3, ADMIN=4`; admin ops use `RoleLevel.ADMIN`
- Every mutating endpoint must: (1) verify JWT, (2) check quarry role ≥ required level,
  (3) write `AuditLog` for state-changing ops (see `safety.md`)

```python
# Read endpoint
async def get_thing(current_user: UserProfile = Depends(get_current_user)): ...

# Write endpoint requiring blaster on a quarry
async def create_thing(
    quarry_id: UUID,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
): ...
```

## Error conventions
- Missing resource: `raise HTTPException(status_code=404, detail="X not found")`
- Wrong state transition: `raise HTTPException(status_code=409, detail="Cannot X in status Y")`
- Auth failure: `raise HTTPException(status_code=403, detail="...")`
- Never return 500 for domain errors — catch and raise the appropriate 4xx

## Pagination
- `?page=1&page_size=20`; `offset = (page - 1) * page_size`
- Return `PaginatedResponse` from `app/schemas/common.py`:
  `{"items": [...], "total": N, "page": 1, "page_size": 20}`

## Audit logs
Write `AuditLog` for every state-mutating operation (passport/recommendation status,
quarry access grants/revocations) via `db.add(AuditLog(...))` — never bulk-insert.

## Alembic
- Run `alembic revision --autogenerate` after model changes
- Never hand-write migrations from scratch; never edit applied migrations
- Edit generated migrations only for: ordering, data migrations, adding indexes
- `env.py` uses the async pattern (`asyncio.run(run_async_migrations())`)
