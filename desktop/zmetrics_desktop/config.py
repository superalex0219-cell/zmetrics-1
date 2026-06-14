"""Client configuration via pydantic-settings.

The backend URL is never hardcoded in call sites — read it from here. Values can be
overridden by environment variables prefixed ``ZMETRICS_`` or a local ``.env`` file.
"""
from __future__ import annotations

import platform
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _default_offline_db() -> Path:
    return Path.home() / ".zmetrics" / "offline.db"


def user_env_path() -> Path:
    """Per-user env file edited by the desktop app."""
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "ZMetrics" / ".env"
    return Path.home() / ".zmetrics" / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ZMETRICS_",
        env_file=(".env", user_env_path()),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Backend REST API
    backend_base_url: str = "http://localhost:8000"
    api_prefix: str = "/api/v1"
    request_timeout_s: float = 30.0

    # Keycloak (OIDC PKCE, public desktop client)
    keycloak_base_url: str = "http://localhost:8080"
    keycloak_realm: str = "zmetrics"
    keycloak_client_id: str = "zmetrics-desktop"

    # Offline queue
    offline_db_path: Path = Field(default_factory=_default_offline_db)

    @property
    def api_base(self) -> str:
        """Full base URL for ``/api/v1`` calls."""
        return f"{self.backend_base_url.rstrip('/')}{self.api_prefix}"

    @property
    def oidc_issuer(self) -> str:
        return f"{self.keycloak_base_url.rstrip('/')}/realms/{self.keycloak_realm}"


def load_settings() -> Settings:
    return Settings()


SERVER_ENV_KEYS = {
    "backend_base_url": "ZMETRICS_BACKEND_BASE_URL",
    "keycloak_base_url": "ZMETRICS_KEYCLOAK_BASE_URL",
    "keycloak_realm": "ZMETRICS_KEYCLOAK_REALM",
    "keycloak_client_id": "ZMETRICS_KEYCLOAK_CLIENT_ID",
    "request_timeout_s": "ZMETRICS_REQUEST_TIMEOUT_S",
}


def save_user_server_settings(values: dict[str, str | float]) -> Path:
    """Write server-related settings to the per-user env file.

    Unknown lines are preserved, so future settings or hand-written comments survive
    edits from the app.
    """
    path = user_env_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    updates = {
        env_key: str(values[field]).strip()
        for field, env_key in SERVER_ENV_KEYS.items()
        if field in values and str(values[field]).strip()
    }
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    lines: list[str] = []
    seen: set[str] = set()
    for line in existing:
        key = line.split("=", 1)[0].strip()
        if key in updates:
            lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            lines.append(f"{key}={value}")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
