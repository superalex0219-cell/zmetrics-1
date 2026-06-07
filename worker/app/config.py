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

    # SAM3 segmentation model
    sam3_model_path: str = "bodhicitta/sam3"  # HuggingFace ID or absolute path to local weights
    sam3_text_prompt: str = "rock fragment"  # open-vocab prompt for quarry blast muck
    sam3_confidence_threshold: float = 0.5   # post_process_instance_segmentation threshold


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
