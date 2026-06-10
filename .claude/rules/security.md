# Security Rules

These rules apply to all code in the project.

## Authentication and authorization

- All `/api/v1/` endpoints MUST call `Depends(get_current_user)` or a role-requiring dependency
- JWT validation MUST check: signature (RS256), expiry, issuer URL
- JWKS MUST be fetched from Keycloak at runtime — never hardcode public keys
- Role checks MUST be per-quarry (via `QuarryUserAccess`), not global
- Revoked access (`revoked_at IS NOT NULL`) MUST be treated as no access

## Desktop client auth

- **Primary flow (product decision 2026-06-11): in-app login form → direct access
  grant** (`grant_type=password`) against the public Keycloak client `zmetrics-desktop`
  (`directAccessGrantsEnabled=true`). No browser. The password goes only to the
  Keycloak token endpoint and is NEVER stored, logged, or kept beyond the request.
- The PKCE-loopback browser flow (`AuthManager.login`) remains in the codebase as an
  alternative for environments where ROPC is disabled — do not delete it.
- Never embed a client secret in the desktop app (public client)
- Tokens stored in the OS keyring (Windows Credential Manager) — never plaintext, never logged
- Refresh on 401, retry once

## Secrets management

- Secrets come from environment variables only
- `.env` files are gitignored; never commit one
- Docker Compose reads secrets from `infra/.env` (not committed)
- Use `pydantic-settings` with `env_file=".env"` for local dev only
- Production: inject env vars from a secrets manager (Vault, AWS Secrets Manager)

## Input validation

- All API inputs validated by Pydantic v2 schemas before reaching services
- File uploads: validate content-type header AND magic bytes (not just extension)
- MinIO keys: constructed server-side only, never passed directly from user input
- UUIDs from path params: FastAPI auto-validates via `UUID` type annotation

## Output security

- Never expose `keycloak_sub`, raw passwords, or internal system errors in API responses
- Presigned MinIO URLs: max 1 hour (`expires_in=3600`); never permanent public URLs
- `AuditLog` endpoint: admin-only; paginated; no sensitive field values in response

## Injection prevention

- SQLAlchemy ORM queries prevent SQL injection by design — never use `text()` with f-strings
- If raw SQL is needed, use `text("... :param")` with bound parameters
- MinIO object keys are constructed from validated UUIDs — no path traversal possible
- Celery task args: only pass UUIDs (strings) — never serialize full objects

## CORS

- The native desktop client does not require CORS (no browser origin). The web frontend
  has been removed, so `BACKEND_CORS_ORIGINS` is no longer needed for normal operation.
- If a browser-based tool ever calls the API, keep `BACKEND_CORS_ORIGINS` an explicit
  allowlist in `.env` — never `allow_origins=["*"]` in production, and credentials mode
  requires an explicit origin (not wildcard).

## Rate limiting

Not yet implemented (M1+). When added:
- Auth endpoints: stricter limits (Keycloak handles this)
- File upload endpoints: per-user quota enforced in `StorageService`
