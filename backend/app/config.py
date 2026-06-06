from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://zmetrics:changeme@localhost:5432/zmetrics"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme"
    minio_use_ssl: bool = False
    minio_bucket_frames: str = "zmetrics-frames"
    minio_bucket_artifacts: str = "zmetrics-artifacts"

    # Keycloak OIDC
    # kc_internal_url: backchannel URL the backend uses to fetch JWKS (docker-internal)
    # kc_public_url: frontend-facing URL embedded in token iss claims (host-reachable)
    kc_internal_url: str = "http://localhost:8080"
    kc_public_url: str = "http://localhost:8080"
    kc_realm: str = "zmetrics"
    kc_client_id: str = "zmetrics-backend"

    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Dev/bootstrap: gates POST /api/v1/admin/dev-seed. MUST stay False outside
    # local/dev stacks — the seed endpoint grants the caller admin on a quarry.
    # Set ENABLE_DEV_SEED=true only via compose env (never baked into the image).
    enable_dev_seed: bool = False

    @computed_field
    @property
    def jwks_url(self) -> str:
        return f"{self.kc_internal_url}/realms/{self.kc_realm}/protocol/openid-connect/certs"

    @computed_field
    @property
    def token_issuer(self) -> str:
        return f"{self.kc_public_url}/realms/{self.kc_realm}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
