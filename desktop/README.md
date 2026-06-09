# ZMetrics Desktop Client

Single ZMetrics client — Python + PySide6, Windows-first. Replaces the former React web
and Flutter mobile apps. Thin REST consumer of the FastAPI backend plus local stereo
capture (ZED 2 as a UVC camera) and an offline SQLite queue. **CV runs server-side.**

## Layout
```
zmetrics_desktop/
  config.py     # settings (backend URL, Keycloak) via pydantic-settings
  api/          # httpx REST client
  auth/         # OIDC PKCE loopback + keyring token store
  models/       # Pydantic DTOs mirroring backend/app/schemas
  offline/      # SyncManager (sqlite pending_uploads queue)
  capture/      # OpenCV UVC capture + side-by-side split
  ui/           # PySide6 views + main window
  app.py        # QApplication entry point
```

## Develop (Windows host)
Requires Python 3.11+ (and, for `pyinstaller`/camera, the usual Windows build tooling).

```powershell
cd desktop
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Run:
```powershell
python -m zmetrics_desktop
```

Test (no camera / GUI needed for the core):
```powershell
pytest
```

Configuration is read from env vars prefixed `ZMETRICS_` or a local `.env`, e.g.
`ZMETRICS_BACKEND_BASE_URL=http://localhost:8000`.

## Status
Scaffold + auth + capture (plan steps 3–5). Implemented: config, offline queue,
side-by-side split, REST client with 401-refresh-retry, OIDC PKCE loopback login (system
browser + ephemeral-port callback, tokens in keyring), navigation shell with login/logout
toolbar, UVC camera enumeration + ZED 2 SBS capture (`capture/camera.py`, hardware E2E
pending). Next: wire the offline queue to the API client, then screen porting.
See `C:\Users\Nikita\.claude\plans\quizzical-spinning-backus.md`.
