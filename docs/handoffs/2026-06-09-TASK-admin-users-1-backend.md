# ADMIN-USERS-1 — Admin user management via Keycloak Admin API (Backend + Infra)

**Layer:** `backend/` + `infra/keycloak/` (realm config) + `infra/docker-compose.yml`
**Depends on:** M1 admin endpoints (list/update/deactivate users, grant/revoke access) ✅ already exist
**Frontend:** none here — UI is ADMIN-USERS-2 (separate handoff, depends on this)
**New migrations:** none (no schema change — `UserProfile`/`QuarryUserAccess` already sufficient)
**Review agent:** backend security reviewer (focus: admin-gating, secret handling, partial-failure rollback, no `keycloak_sub` leakage)
**Target test count:** backend +~10 (Keycloak admin client fully mocked — no real Keycloak calls)

---

## Goal

Admins can **create** users and **edit** them (profile/email, per-quarry roles, activate/deactivate, reset password) from the app — backed by the **Keycloak Admin REST API** so the created accounts can actually log in. The app DB `UserProfile` mirrors the Keycloak identity (`keycloak_sub` link).

### What already exists (do NOT rebuild — only extend)
In `backend/app/routers/admin.py`, all `require_any_admin`-gated:
- `GET /admin/users` — list
- `PATCH /admin/users/{id}` — update `full_name`/`is_active` (local only today)
- `DELETE /admin/users/{id}` — deactivate (local `is_active=False`)
- `POST /admin/quarries/{qid}/access` — grant role + AuditLog
- `DELETE /admin/quarries/{qid}/access/{aid}` — revoke role + AuditLog
- `GET /admin/audit-logs`

### What this task adds
1. **Keycloak Admin API client** (`services/keycloak_admin.py`) — service-account token + user CRUD/password ops
2. `POST /admin/users` — create in Keycloak → mirror local `UserProfile`
3. Extend `PATCH /admin/users/{id}` — sync `email`/`full_name`/`enabled` to Keycloak
4. `POST /admin/users/{id}/reset-password` — Keycloak temporary-password reset
5. Extend `DELETE /admin/users/{id}` — also disable the Keycloak account
6. `GET /admin/users/{id}/access` — list a user's active per-quarry roles (for the admin UI)
7. Infra: grant the `zmetrics-backend` service account the `realm-management` roles + wire the client secret into the backend

**Safety/security invariants (non-negotiable):**
- All new endpoints gated by `Depends(require_any_admin)`.
- `keycloak_sub` is **never** returned by the API (keep `UserProfileRead` as-is).
- Temporary passwords are returned **once** in the response body, **never** persisted in the app DB, **never** logged.
- `AuditLog` written for: `user_created`, `user_updated` (already), `user_deactivated` (already), `user_password_reset`. Append-only.
- The Keycloak client secret comes from env/config only — never hardcoded in Python, never logged.
- No auto-approve / no blast-domain changes — this is pure identity/RBAC.

---

## 1. Config — `backend/app/config.py`

`kc_internal_url`, `kc_public_url`, `kc_realm`, `kc_client_id` already exist. Add the service-account secret + an admin toggle:

```python
# Keycloak service-account credentials for the Admin REST API (user management).
# The existing `zmetrics-backend` client already has serviceAccountsEnabled=true.
kc_client_secret: str = "changeme-replace-in-production"   # alias KC_CLIENT_SECRET
enable_admin_user_management: bool = False                  # alias ENABLE_ADMIN_USER_MGMT
```

Add `@computed_field` helpers if convenient:
```python
@computed_field
@property
def kc_token_url(self) -> str:
    return f"{self.kc_internal_url}/realms/{self.kc_realm}/protocol/openid-connect/token"

@computed_field
@property
def kc_admin_users_url(self) -> str:
    return f"{self.kc_internal_url}/admin/realms/{self.kc_realm}/users"
```

When `enable_admin_user_management is False`, the **create / reset-password / Keycloak-sync** paths return `503 Service Unavailable` (`detail="User management is not enabled"`). This lets the feature ship dark and be turned on only where the service account is configured. (Local edit of `full_name`/`is_active` may stay working without the flag — but email/enabled sync and create require it.)

---

## 2. `backend/app/services/keycloak_admin.py` (new)

Async `httpx` client (`httpx>=0.27` already a dependency). One class, constructed per request via a small dependency (or a module-level singleton with an `httpx.AsyncClient`). Keep it isolated and mockable.

```python
class KeycloakAdminError(Exception):
    """Raised on non-2xx from Keycloak; carries status_code + message."""
    def __init__(self, status_code: int, message: str): ...

class KeycloakAdminClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None): ...

    async def _admin_token(self) -> str:
        """client_credentials grant against kc_token_url using kc_client_id + kc_client_secret.
        Cache the token in-memory until ~30s before expiry."""

    async def create_user(self, *, email: str, full_name: str, temp_password: str) -> str:
        """POST {kc_admin_users_url}. Body:
          { username: email, email, firstName: full_name, enabled: true,
            emailVerified: false,
            credentials: [{ type: 'password', value: temp_password, temporary: true }] }
        On 201: parse the new user id (sub) from the Location header and return it.
        On 409: raise KeycloakAdminError(409, 'user exists')."""

    async def update_user(self, *, sub: str, email: str | None = None,
                          full_name: str | None = None, enabled: bool | None = None) -> None:
        """PUT {kc_admin_users_url}/{sub} with only the provided fields
        (firstName=full_name when given)."""

    async def reset_password(self, *, sub: str, temp_password: str) -> None:
        """PUT {kc_admin_users_url}/{sub}/reset-password
          body { type: 'password', value: temp_password, temporary: true }."""
```

Notes:
- **Token caching**: store `(token, expires_at)`; refresh on demand. Never log the token or secret.
- **Timeouts**: pass an `httpx` timeout (e.g. 10s). On `httpx` transport errors → raise `KeycloakAdminError(502, ...)`.
- **full_name → Keycloak**: set `firstName = full_name`, leave `lastName` empty. The app's `UserProfile.full_name` remains the display source of truth; Keycloak just needs a value.
- Provide a tiny helper `generate_temp_password() -> str` (e.g. `secrets.token_urlsafe(12)` + ensure it meets a basic policy: at least one digit/letter — token_urlsafe already mixes). Put it in this module.

---

## 3. Schemas — `backend/app/schemas/user.py`

Add:
```python
class UserProfileCreate(BaseModel):
    email: EmailStr
    full_name: str
    # No password field — a temporary one is generated server-side and returned once.

class UserCreateResult(BaseModel):
    user: UserProfileRead
    temporary_password: str   # shown ONCE; never stored, never logged

class PasswordResetResult(BaseModel):
    temporary_password: str   # shown ONCE

class UserQuarryAccessRead(BaseModel):
    access_id: UUID
    quarry_id: UUID
    quarry_name: str
    role_name: str
    role_level: int
```

Extend `UserProfileUpdate` to allow email:
```python
class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None      # NEW — synced to Keycloak
    is_active: bool | None = None      # synced to Keycloak `enabled`
```
(`EmailStr` requires `pydantic[email]`/`email-validator`. If not already installed, add `email-validator` to backend deps; otherwise use `str` and validate format minimally. Check `backend/pyproject.toml` first.)

`UserProfileRead` stays unchanged — **do not add `keycloak_sub`**.

---

## 4. Endpoints — extend `backend/app/routers/admin.py`

### 4a. `POST /admin/users` → `UserCreateResult` (201)
```
require_any_admin; if not settings.enable_admin_user_management → 503
1. temp = generate_temp_password()
2. sub = await kc.create_user(email, full_name, temp)         # KeycloakAdminError(409) → HTTP 409
3. try: create local UserProfile(keycloak_sub=sub, email, full_name, is_active=True); flush
   except IntegrityError (email/sub dup):
       best-effort: await kc.update_user(sub=sub, enabled=False)  # neutralize orphan
       raise HTTPException(409, "Email already registered")
4. AuditLog(actor=current_user, entity_type="user_profile", entity_id=new.id, action="user_created",
            new_value={"email": email})   # NEVER include the password
5. return UserCreateResult(user=new, temporary_password=temp)
```
Map `KeycloakAdminError.status_code`: 409→409, 502/503→502, others→500 with generic detail (never echo raw Keycloak internals).

### 4b. Extend `PATCH /admin/users/{id}`
Keep the existing local update + AuditLog. **Add** Keycloak sync when any of `email`/`full_name`/`is_active` changed:
```
if settings.enable_admin_user_management:
    await kc.update_user(sub=user.keycloak_sub,
                         email=body.email, full_name=body.full_name,
                         enabled=body.is_active)
```
If `enable_admin_user_management is False` and the body touches `email`, return 503 (can't sync identity); `full_name`/`is_active` local-only edits may proceed. Keep the AuditLog `new_value` as today (no secrets).

### 4c. `POST /admin/users/{id}/reset-password` → `PasswordResetResult`
```
require_any_admin; flag off → 503
load user (404 if missing)
temp = generate_temp_password()
await kc.reset_password(sub=user.keycloak_sub, temp_password=temp)
AuditLog(action="user_password_reset", entity_type="user_profile", entity_id=user.id)  # no password in log
return PasswordResetResult(temporary_password=temp)
```

### 4d. Extend `DELETE /admin/users/{id}` (deactivate)
Keep local `is_active=False` + self-deactivation guard + AuditLog. Add:
```
if settings.enable_admin_user_management:
    await kc.update_user(sub=user.keycloak_sub, enabled=False)
```

### 4e. `GET /admin/users/{id}/access` → `list[UserQuarryAccessRead]`
Join `QuarryUserAccess → Quarry → Role` for `user_id == id`, `revoked_at IS NULL`, `Quarry.deleted_at IS NULL`. Mirrors the `/me/access` query but for an arbitrary user (admin only). Powers the role-management UI.

> Grant/revoke already exist (`POST/DELETE /admin/quarries/{qid}/access...`). Do **not** duplicate them.

---

## 5. Infra

### 5a. `infra/keycloak/realm-export.json` — service account roles
The `zmetrics-backend` client already has `serviceAccountsEnabled: true` + a `secret`. Grant its service account the realm-management user-management roles so it can call the Admin API. Add a service-account user entry (or extend the realm `users` list):

```json
{
  "username": "service-account-zmetrics-backend",
  "enabled": true,
  "serviceAccountClientId": "zmetrics-backend",
  "clientRoles": {
    "realm-management": ["manage-users", "view-users", "query-users"]
  }
}
```
Verify against the running Keycloak version's export format. If the realm is only imported on first boot, document that the dev stack needs a realm re-import (or set the roles via Admin Console once) — note this in the task report.

### 5b. `infra/docker-compose.yml` — backend env
Add under `backend.environment:`:
```yaml
      KC_CLIENT_SECRET: ${KC_CLIENT_SECRET:-changeme-replace-in-production}
      ENABLE_ADMIN_USER_MGMT: ${ENABLE_ADMIN_USER_MGMT:-false}
```

### 5c. `infra/.env.example`
Document both (secret blank/placeholder, flag false). Note that `KC_CLIENT_SECRET` must match the `zmetrics-backend` client secret in the realm.

---

## 6. Tests — extend `backend/tests/test_user_management.py` (and/or `test_admin.py`)

**Mock the Keycloak client** — no network. Patch `KeycloakAdminClient` (or inject a fake via the dependency). Run with the flag enabled in tests.

| # | Test | Assert |
|---|------|--------|
| 1 | create user as admin | 201; response has `temporary_password`; local `UserProfile` row exists with returned `keycloak_sub` (fake) |
| 2 | create user response never contains `keycloak_sub` | `"keycloak_sub" not in resp.json()["user"]` |
| 3 | create with duplicate email (KC 409) | HTTP 409; no local row created |
| 4 | local insert fails after KC create | KC `update_user(enabled=False)` called (rollback); 409 |
| 5 | create as non-admin | 403 |
| 6 | create with flag off | 503 |
| 7 | PATCH email syncs to KC | `kc.update_user` called with that email; AuditLog `user_updated` written |
| 8 | reset-password | 200; `temporary_password` present; `kc.reset_password` called; AuditLog `user_password_reset`; password NOT in audit `new_value` |
| 9 | deactivate also disables in KC | `kc.update_user(enabled=False)` called; cannot deactivate self (400) |
| 10 | `GET /admin/users/{id}/access` | returns user's active roles with quarry name; excludes revoked + soft-deleted quarries |
| 11 | temp password never logged | (optional) capture logs, assert password string absent |

Keycloak client unit tests (mock `httpx`): token caching reused within expiry; `create_user` parses `sub` from `Location` header; non-2xx → `KeycloakAdminError`.

---

## Safety checklist for the executor

- [ ] Every new endpoint has `Depends(require_any_admin)`
- [ ] `UserProfileRead` still omits `keycloak_sub`; create/reset responses never include it
- [ ] Temp passwords: returned once, never written to DB, never in `AuditLog`, never logged
- [ ] `KC_CLIENT_SECRET` read from settings only; not logged; not in any response
- [ ] Partial-failure path (KC ok, local insert fails) neutralizes the orphan KC account
- [ ] `AuditLog` entries added for create + password reset (append-only; no secrets)
- [ ] Flag off → create/reset/email-sync return 503, no Keycloak calls
- [ ] No blast-domain code touched; no auto-approve paths

---

## Acceptance criteria

1. `pytest backend/tests/test_user_management.py backend/tests/test_admin.py -v` — all green (existing + ~10 new)
2. `pytest backend/tests/` — full suite green (no regressions)
3. With the flag on and a configured service account, `POST /api/v1/admin/users` creates a Keycloak account that can obtain a token via the password grant using the returned temporary password (manual smoke — document the curl in the report)
4. `keycloak_sub` appears in **no** API response (grep the response models)
5. Non-admin callers get 403 on every new endpoint

---

## Explicitly out of scope

- Frontend UI (→ ADMIN-USERS-2)
- Self-service registration / email delivery of passwords (admin reads the temp password and conveys it out-of-band)
- Keycloak group/realm-role management (only per-quarry app roles via existing grant/revoke)
- Hard-deleting users (we deactivate, preserving audit trail)
- No new Alembic migration
