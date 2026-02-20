# Config: Load and validate environment variables using Pydantic Settings

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str

    # OpenClaw
    openclaw_api_url: str
    openclaw_webhook_token: str
    openclaw_outbound_token: str
    openclaw_phone_number_id: str

    # Groq
    groq_api_key: str
    groq_whisper_model: str = "whisper-large-v3"
    groq_llm_model: str = "llama-3.1-8b-instant"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    tenant_id: str = "default"

    # Digest
    digest_hour: int = 8
    digest_timezone: str = "America/New_York"

    # Storage
    artifacts_path: str = "/var/data/personal-crm/artifacts"

    # Worker
    worker_poll_interval: int = 2
    worker_max_retries: int = 3

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
