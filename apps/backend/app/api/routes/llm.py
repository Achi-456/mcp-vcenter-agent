from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import llm_model_dep
from app.core.responses import success_response
from app.services.llm_model_service import LLMModelService

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])


@router.get("/providers")
async def providers(service: LLMModelService = Depends(llm_model_dep)) -> dict[str, Any]:
    return success_response(await service.providers(), source="llm_provider_discovery")


@router.get("/models")
async def models(
    provider: str = Query(default="gemini"),
    service: LLMModelService = Depends(llm_model_dep),
) -> dict[str, Any]:
    return success_response(await service.list_models(provider), source="llm_model_discovery")


@router.get("/status")
async def status(service: LLMModelService = Depends(llm_model_dep)) -> dict[str, Any]:
    return success_response(await service.status(), source="llm_configuration")


class ConfigureProviderSchema(BaseModel):
    provider: str
    api_key: str


@router.post("/configure")
async def configure(
    data: ConfigureProviderSchema,
    service: LLMModelService = Depends(llm_model_dep),
) -> dict[str, Any]:
    result = await service.configure_provider(data.provider, data.api_key)
    return success_response(result, source="llm_configuration_update")
