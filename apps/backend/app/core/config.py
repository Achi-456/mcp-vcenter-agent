from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    db_url: str | None = Field(default=None, alias="DB_URL")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")
    agent_engine_url: str = Field(
        default="http://agent-engine.agentic-agents.svc.cluster.local:8080",
        alias="AGENT_ENGINE_URL",
    )
    mcp_server_url: str = Field(
        default="http://mcp-server.agentic-app.svc.cluster.local:8001",
        alias="MCP_SERVER_URL",
    )
    internal_tool_api_token: str | None = Field(default=None, alias="INTERNAL_TOOL_API_TOKEN")
    vcenter_secret_name: str = Field(default="agentic-vcenter-default", alias="VCENTER_SECRET_NAME")
    k8s_namespace: str = Field(default="agentic-app", alias="POD_NAMESPACE")
    llm_enabled: bool = Field(default=False, alias="LLM_ENABLED")
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    llm_model: str | None = Field(default=None, alias="LLM_MODEL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    llm_timeout_seconds: float = Field(default=30.0, alias="LLM_TIMEOUT_SECONDS")
    llm_secret_name: str = Field(default="agentic-llm-provider", alias="LLM_SECRET_NAME")
    llm_runtime_namespace: str = Field(default="agentic-agents", alias="LLM_RUNTIME_NAMESPACE")
    llm_engine_deployment_name: str = Field(default="agent-engine", alias="LLM_ENGINE_DEPLOYMENT_NAME")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
