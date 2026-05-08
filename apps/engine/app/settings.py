from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    db_url: str | None = Field(default=None, alias="DB_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    @property
    def postgres_dsn(self) -> str:
        if not self.db_url:
            raise RuntimeError("DB_URL is not set")
        return self.db_url.replace("+asyncpg", "")

    @property
    def redis_dsn(self) -> str:
        if not self.redis_url:
            raise RuntimeError("REDIS_URL is not set")
        return self.redis_url


@lru_cache
def get_settings() -> Settings:
    return Settings()

