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
    llm_enabled: bool = Field(default=False, alias="LLM_ENABLED")
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    llm_model: str = Field(default="gpt-5.4-mini", alias="LLM_MODEL")
    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS")
    llm_temperature: float = Field(default=0.2, alias="LLM_TEMPERATURE")
    llm_report_writer_enabled: bool = Field(default=True, alias="LLM_REPORT_WRITER_ENABLED")
    llm_reviewer_enabled: bool = Field(default=True, alias="LLM_REVIEWER_ENABLED")
    llm_max_input_chars: int = Field(default=60000, alias="LLM_MAX_INPUT_CHARS")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    web_search_enabled: bool = Field(default=False, alias="WEB_SEARCH_ENABLED")
    web_search_provider: str = Field(default="tavily", alias="WEB_SEARCH_PROVIDER")
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")
    web_search_max_results: int = Field(default=5, alias="WEB_SEARCH_MAX_RESULTS")
    web_search_timeout_seconds: float = Field(default=20.0, alias="WEB_SEARCH_TIMEOUT_SECONDS")
    web_search_official_first: bool = Field(default=True, alias="WEB_SEARCH_OFFICIAL_FIRST")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
