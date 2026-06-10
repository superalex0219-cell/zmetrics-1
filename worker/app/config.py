from functools import lru_cache

from pydantic import Field
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

    # SAM3 segmentation model. In Docker this is mounted from SAM3_WEIGHTS_DIR.
    # Off by default: real inference needs a GPU; without it the mock segmentation
    # step runs instead (same artifact contract).
    enable_sam3: bool = Field(default=False, alias="ENABLE_SAM3")
    sam3_model_path: str = "/models/sam3"  # local path, or set to a HuggingFace ID
    sam3_text_prompt: str = "rock fragment"  # open-vocab prompt for quarry blast muck
    sam3_confidence_threshold: float = 0.5   # post_process_instance_segmentation threshold

    enable_real_stereo: bool = Field(default=False, alias="ENABLE_REAL_STEREO")

    # --- LLM explanation layer (M5-b) ---
    enable_llm_recommendations: bool = Field(default=False, alias="ENABLE_LLM_RECOMMENDATIONS")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    llm_model: str = Field(default="claude-sonnet-4-6", alias="LLM_MODEL")
    llm_timeout_s: float = Field(default=20.0, alias="LLM_TIMEOUT_S")
    llm_max_tokens: int = Field(default=512, alias="LLM_MAX_TOKENS")


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
