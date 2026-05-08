import structlog
from fastapi import APIRouter, Query

from app.api.schemas.inventory import LLMProvider, LLMModel, LLMStatus
from app.services.k8s_secret_store import get_secret

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/llm")

PROVIDERS = {
    "gemini": {
        "id": "gemini",
        "name": "Google Gemini",
        "enabled": True,
        "models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
    },
    "claude": {
        "id": "claude",
        "name": "Anthropic Claude",
        "enabled": True,
        "models": ["claude-sonnet-4-20250514", "claude-3-opus", "claude-3-haiku"],
    },
    "openai": {
        "id": "openai",
        "name": "OpenAI",
        "enabled": True,
        "models": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
    },
    "grok": {
        "id": "grok",
        "name": "xAI Grok",
        "enabled": True,
        "models": ["grok-3", "grok-3-mini"],
    },
    "kimi": {
        "id": "kimi",
        "name": "Kimi / Moonshot",
        "enabled": True,
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
    },
}


@router.get("/providers")
async def list_providers():
    return {"providers": [LLMProvider(**p).model_dump() for p in PROVIDERS.values()]}


@router.get("/models")
async def list_models(provider: str = Query(...)):
    p = PROVIDERS.get(provider)
    if not p:
        return {"models": []}
    return {"models": [LLMModel(id=m, name=m) for m in p["models"]]}


@router.get("/status")
async def llm_status() -> LLMStatus:
    try:
        s = get_secret("agentic-llm-provider-default") if get_secret else None
    except Exception:
        s = None

    if not s:
        return LLMStatus(configured=False)

    provider = s.get("LLM_PROVIDER", "")
    model = s.get("LLM_MODEL", "")
    api_key_set = bool(s.get("LLM_API_KEY", ""))
    ready = bool(provider and model and api_key_set)

    return LLMStatus(configured=True, provider=provider, model=model, ready=ready)
