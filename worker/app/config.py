from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://zmetrics:changeme@localhost:5432/zmetrics"

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "changeme"
    minio_use_ssl: bool = False
    minio_bucket_frames: str = "zmetrics-frames"
    minio_bucket_artifacts: str = "zmetrics-artifacts"

    worker_concurrency: int = 2


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
