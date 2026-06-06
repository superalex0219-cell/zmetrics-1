# Handoff: backend/auth

**Date:** 2026-06-05  
**Scope:** `backend/app/auth/`, `backend/app/dependencies.py`, `backend/app/db/models/user.py`

---

## Status: implemented and tested

### What was already built (M0)
| Component | File | Notes |
|-----------|------|-------|
| Keycloak JWKS fetch + cache | `app/auth/jwt.py` | RS256, 5-min TTL, 5-retry with backoff |
| JWT decode | `app/auth/jwt.py` | `decode_token()` — raises `ValueError` on expiry/bad sig |
| Per-quarry RBAC dependency | `app/auth/roles.py` | `require_quarry_role(RoleLevel.X)` → FastAPI `Depends` |
| User auto-provision | `app/dependencies.py` | `get_current_user()` creates `UserProfile` on first login |
| User/Role/QuarryUserAccess models | `app/db/models/user.py` | Role is per-quarry, revocation via `revoked_at` |

### What was fixed in this session (M1)

#### 1. JWT issuer validation (`app/auth/jwt.py:52`)
`jwt.decode()` now passes `issuer=settings.token_issuer`. Without this, a JWT issued by
any Keycloak realm would be accepted. The `token_issuer` field already existed in
`app/config.py` but was unused.

#### 2. `QuarryUserAccess` re-grant bug (`app/db/models/user.py:60`)
Replaced `UniqueConstraint("user_id", "quarry_id")` with a partial unique index:
```
UNIQUE (user_id, quarry_id) WHERE revoked_at IS NULL
```
The old constraint prevented re-granting access after revocation (INSERT would raise
`UniqueViolationError`). The new partial index only enforces uniqueness on active rows.

#### 3. Test infrastructure: SQLite JSONB compatibility (`tests/conftest.py`)
Added `@compiles(JSONB, "sqlite")` to render JSONB columns as `TEXT` during SQLite schema
creation. Without this, `create_tables` failed on any model with a JSONB column, breaking
all tests.

#### 4. Auth test suite (`tests/test_auth.py` — new, 10 tests)
Covers:
- JWT decode: expired token → ValueError, invalid signature → ValueError
- `get_current_user`: auto-provision, existing user, disabled user → 403, missing sub → 401
- `require_quarry_role` via HTTP: no access → 403, revoked → 403, low role → 403, sufficient → 201

#### 5. Roles seed migration (`migrations/versions/0002_seed_roles.py`)
Inserts the four standard `Role` rows (`user/1`, `surveyor/2`, `blaster/3`, `admin/4`).
`require_quarry_role` does a DB join against this table — without it, all role checks return
403 even for correctly granted users.

**Before applying:** replace `down_revision = "0001"` with the actual revision hash produced
by `alembic revision --autogenerate -m "initial_schema"`.

#### 6. Recommendation Python-side default (`app/db/models/report.py`)
SQLAlchemy 2.0's `mapped_column(default=X)` is INSERT-time only — Python object attributes
are `None` until flush. Added `__init__` override to `Recommendation` so that
`rec.status` is `REQUIRES_HUMAN_REVIEW` immediately on construction, satisfying the safety
invariant at the Python layer as well as the DB layer.

#### 7. Test infrastructure: mock patch target corrected (`tests/conftest.py`, `tests/test_auth.py`)
`dependencies.py` does `from app.auth.jwt import decode_token` (direct import binding).
Mocking `app.auth.jwt.decode_token` had no effect on the dependency; corrected to
`app.dependencies.decode_token` throughout.

---

## How to deploy

```powershell
# 0. Start Docker Desktop, then start the stack (requires infra/.env)
docker compose -f infra\docker-compose.yml up -d

# 1. Generate initial schema migration (run once, review output)
docker compose -f infra\docker-compose.yml exec backend `
  alembic revision --autogenerate -m "initial_schema"
# Review the generated file: ensure enums are created before tables in upgrade()

# 2. Update 0002_seed_roles.py: set down_revision to the revision hash from step 1

# 3. Apply all migrations
docker compose -f infra\docker-compose.yml exec backend alembic upgrade head

# 4. Run tests (also passes locally via: cd backend && python -m pytest tests/ -v)
docker compose -f infra\docker-compose.yml exec backend pytest -v

# 5. Manual smoke test
$token = (Invoke-RestMethod -Method Post `
  -Uri "http://localhost:8080/realms/zmetrics/protocol/openid-connect/token" `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "grant_type=password&client_id=zmetrics-backend&client_secret=changeme&username=admin-user&password=changeme"
).access_token

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/quarries" `
  -Headers @{ Authorization = "Bearer $token" }
# Expected: {"items":[],"total":0,"page":1,"page_size":20}
```

---

## Architectural issues (logged, not in scope)

### AUD-001: IP address never captured in AuditLog
`AuditLog.ip_address` exists but is always `NULL`. To populate it, add a
`RequestContextMiddleware` that stores `request.client.host` in a `contextvars.ContextVar`
and read it inside audit log writes. Medium complexity; deferred to M1 hardening.

### AUD-002: `verify_aud: False` in JWT decode
Audience validation is intentionally disabled. Keycloak realm-level access tokens do not
always include the backend client ID in the `aud` claim. If the project switches to
client-scoped tokens, re-enable with `audience=settings.kc_client_id`.

### AUD-003: `_require_any_admin` is cross-quarry
The admin router's `_require_any_admin` helper grants access if the user is admin on *any*
quarry. The audit log endpoint therefore exposes logs across *all* quarries to any admin.
Consider per-quarry scoping in M2 (filter by quarries the admin has access to).

### AUD-004: Analysis router skips quarry role check
`app/routers/analysis.py` uses only `get_current_user` — no `require_quarry_role` call.
Any authenticated user can submit/read analysis jobs regardless of quarry access. Add
`require_quarry_role(RoleLevel.SURVEYOR)` check before M1 ships.
