# Config: Load and validate environment variables using Pydantic Settings

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: str

    # Groq
    groq_api_key: str
    groq_whisper_model: str = "whisper-large-v3"
    groq_llm_model: str = "llama-3.1-8b-instant"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    tenant_id: str = "default"

    # Auth — generate secret with: openssl rand -hex 32
    jwt_secret: str = "in-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
