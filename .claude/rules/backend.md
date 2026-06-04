---
paths:
  - "backend/**/*.py"
---

# Backend Rules

## Framework conventions

- FastAPI `lifespan` context manager (not `@app.on_event`)
- All routers use `APIRouter(prefix=..., tags=[...])`
- Route functions are thin: validate input → call service → return response
- Business logic lives in `backend/app/services/`, never in routers

## SQLAlchemy 2.0

- Always `Mapped[T]` + `mapped_column()` annotation style
- Always `AsyncSession`; never import `Session` (sync)
- Queries: `await session.execute(select(Model).where(...))`
- Flush before reading back generated IDs: `await session.flush()`
- `expire_on_commit=False` on session factory (already configured)

## Pydantic v2

- Request schemas: no `from_attributes`; validate input only
- Response schemas: `model_config = ConfigDict(from_attributes=True)`
- Use `model_dump(exclude_unset=True)` on update payloads to patch only provided fields
- Never expose internal FK IDs of soft-deleted records

## Auth pattern

```python
# Read endpoint
async def get_thing(current_user: UserProfile = Depends(get_current_user)):

# Write endpoint requiring blaster on a quarry
async def create_thing(
    quarry_id: UUID,
    current_user: UserProfile = Depends(require_quarry_role(RoleLevel.BLASTER)),
):
```

Role check is skipped only for `/health` endpoints.

## Error conventions

- Missing resource: `raise HTTPException(status_code=404, detail="X not found")`
- Wrong state transition: `raise HTTPException(status_code=409, detail="Cannot X in status Y")`
- Auth failure: `raise HTTPException(status_code=403, detail="...")`
- Never return 500 for domain errors; catch and raise 4xx

## Pagination

```python
# Endpoint signature
async def list_things(page: int = 1, page_size: int = 20):
    offset = (page - 1) * page_size
    ...
```
Return `PaginatedResponse` from `app/schemas/common.py`.

## Audit logs

Write `AuditLog` for every state-mutating operation on:
- `BlastPassport` status changes
- `Recommendation` status changes
- `QuarryUserAccess` grants/revocations

Use `db.add(AuditLog(...))` — never bulk-insert audit logs.
