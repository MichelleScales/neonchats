from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_env: Literal["development", "staging", "production"] = "development"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    cors_origins: list[str] = ["http://localhost:3000"]

    # Database
    database_url: str = "postgresql+asyncpg://emp:emp@localhost:5432/emp"
    database_sync_url: str = "postgresql://emp:emp@localhost:5432/emp"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "changeme"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # AI providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    moonshot_api_key: str = ""
    moonshot_base_url: str = "https://api.moonshot.cn/v1"
    default_model_provider: Literal["anthropic", "openai", "moonshot"] = "moonshot"
    default_external_model: str = "moonshot-v1-8k"

    # Integrations
    sendgrid_api_key: str = ""
    sendgrid_from_email: str = "noreply@example.com"
    hubspot_access_token: str = ""

    # Object storage
    storage_endpoint: str = "http://localhost:9000"
    storage_access_key: str = "minioadmin"
    storage_secret_key: str = "minioadmin"
    storage_bucket: str = "emp-assets"


@lru_cache
def get_settings() -> Settings:
    return Settings()
