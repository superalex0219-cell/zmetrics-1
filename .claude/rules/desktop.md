---
paths:
  - "desktop/**/*.py"
---

# Desktop Client Rules (Python + PySide6)

The desktop client is the **single** ZMetrics client (replaces the former React web and
Flutter mobile apps). Primary target: Windows. It is a thin REST client of the FastAPI
backend plus local capture and an offline queue. CV currently runs server-side.

## Stack
- Python 3.x (match backend/worker version), packaged with `PyInstaller`
- UI: **PySide6** (Qt for Python, LGPL) — desktop layout, side-menu navigation
- HTTP: `httpx` (sync) executed off the UI thread via `QThreadPool` workers
  (never block the Qt event loop). `qasync` is optional if full async is needed.
- Auth: OIDC Authorization Code + PKCE via loopback redirect (see below)
- Token storage: `keyring` (Windows Credential Manager) — never plaintext, never logged
- Offline queue: stdlib `sqlite3`
- Camera/CV-on-client: OpenCV (`cv2`); `pyzed` only if/when ZED SDK depth runs locally
- Config: `pydantic-settings` (backend URL, realm, client id) — never hardcode the backend URL

## Architecture (feature/layer folders)
```
desktop/zmetrics_desktop/
  config.py     # settings
  api/          # REST client; groups mirror the backend routers
  auth/         # OIDC PKCE loopback + keyring token store + 401 refresh
  models/       # Pydantic DTOs mirroring backend/app/schemas (no ORM imports)
  offline/      # SyncManager over sqlite3 (pending_uploads)
  capture/      # OpenCV UVC capture + side-by-side split
  ui/           # PySide6 views — one module per screen + main window
  app.py        # QApplication entry point
```
- No business logic in widgets — keep views dumb; call `api/`/`offline/` services.
- `models/` are DTOs only; do not import backend ORM models.

## Auth (OIDC PKCE loopback)
1. Start a local HTTP server on `http://localhost:<port>/callback`
2. Open the system browser to the Keycloak authorize endpoint (PKCE challenge)
3. Capture the `code` on the loopback, exchange it for tokens at the token endpoint
4. Store access/refresh tokens in `keyring`
5. On 401, refresh once and retry (wrap all API calls)
- Use the public Keycloak client `zmetrics-desktop`. Never embed a client secret.

## Offline-first (parity with the former mobile SyncManager)
- All write operations (create capture_session, upload frames, create passport) go
  through `SyncManager`
- `SyncManager` stores pending operations in the SQLite table `pending_uploads`
- Each queued item has a client-generated `idempotency_key` (UUID v4) to prevent
  duplicate server-side records
- Process the queue when connectivity is available (ping `/health`); max retry 5, then
  surface an error state to the user

## Capture (ZED 2 as UVC)
- ZED 2 enumerates as a UVC camera emitting a side-by-side (left|right) frame; the ZED SDK
  is NOT required while CV is server-side
- Enumerate devices (e.g. `pygrabber` / Media Foundation); capture via
  `cv2.VideoCapture(index, cv2.CAP_MSMF)` at full SBS resolution
- If `width/height > 1.8`, treat as side-by-side: split at `width/2` into left/right,
  encode each with `cv2.imencode('.jpg', ...)`, upload as separate `left_frame`/`right_frame`
  artifacts (the server's `cv_rectification` expects two separate frames)
- Calibration: store factory ZED calibration once as a `Calibration` record per serial

## Safety (same as the rest of the system)
- `parameter_suggestions` are displayed **read-only** — never write them back to a passport
- Recommendation status changes are explicit user actions only
- Reports must show the analysis method and the mock badge `"⚠ Синтетические данные"`
- Never log tokens or PII

## Tests
- `pytest` for `api/`, `offline/`, and `capture/` (SBS split is testable on a synthetic
  concatenated image — no camera required)
- UI smoke tests optional via `pytest-qt`
