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


def _app_support_env() -> Path:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "ZMetrics" / ".env"
    return Path.home() / ".zmetrics" / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ZMETRICS_",
        env_file=(".env", _app_support_env()),
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
