from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    backend_url: str = Field(
        default="http://fastapi.agentic-app.svc.cluster.local:8000",
        alias="BACKEND_URL",
    )
    backend_timeout_seconds: float = Field(default=60.0, alias="BACKEND_TIMEOUT_SECONDS")
    internal_tool_api_token: str | None = Field(default=None, alias="INTERNAL_TOOL_API_TOKEN")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
