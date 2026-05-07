import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.schemas.connections import (
    VCenterConnectionRequest, VCenterTestResponse, VCenterConnectionStatus,
    VCenterSaveResponse, LLMConnectionRequest, LLMTestResponse,
    LLMConnectionStatus, LLMSaveResponse, ConnectionDeleteResponse,
)
from app.services.k8s_secret_store import (
    VCENTER_SECRET_NAME, LLM_SECRET_NAME,
    create_or_update_secret, get_secret, delete_secret, secret_exists,
    _now, mask_username,
)
from app.services.vcenter_connection_service import test_vcenter_connection
from app.services.llm_connection_service import test_llm_connection

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/connections")

# ── vCenter ──────────────────────────────────────────────

@router.post("/vcenter/test")
async def vcenter_test(req: VCenterConnectionRequest) -> JSONResponse:
    ok, msg, err = test_vcenter_connection(
        vcenter_url=req.vcenter_url,
        username=req.username,
        password=req.password,
        verify_ssl=req.verify_ssl,
    )
    resp = VCenterTestResponse(ok=ok, status="success" if ok else "failed", message=msg, error_code=err)
    return JSONResponse(resp.model_dump(), status_code=200 if ok else 400)


@router.post("/vcenter")
async def vcenter_save(req: VCenterConnectionRequest) -> JSONResponse:
    ok, msg, err = test_vcenter_connection(
        vcenter_url=req.vcenter_url,
        username=req.username,
        password=req.password,
        verify_ssl=req.verify_ssl,
    )
    if not ok:
        resp = VCenterSaveResponse(ok=False, status="failed", message=f"Test failed before save: {msg}")
        return JSONResponse(resp.model_dump(), status_code=400)

    now = _now()
    data = {
        "VCENTER_NAME": req.name,
        "VCENTER_URL": req.vcenter_url,
        "VCENTER_USERNAME": req.username,
        "VCENTER_PASSWORD": req.password,
        "VCENTER_VERIFY_SSL": str(req.verify_ssl).lower(),
        "VCENTER_CREATED_AT": now,
        "VCENTER_UPDATED_AT": now,
        "VCENTER_LAST_TEST_STATUS": "success",
        "VCENTER_LAST_TESTED_AT": now,
    }
    create_or_update_secret(VCENTER_SECRET_NAME, data, {
        "agentic.io/managed-by": "fastapi",
        "agentic.io/secret-type": "vcenter",
    })

    status = VCenterConnectionStatus(
        configured=True, name=req.name, vcenter_url=req.vcenter_url,
        username_hint=mask_username(req.username), verify_ssl=req.verify_ssl,
        password_set=True, last_test_status="success", last_tested_at=now,
    )
    return JSONResponse(VCenterSaveResponse(
        ok=True, status="saved", message="vCenter credentials saved securely.", connection=status,
    ).model_dump())


@router.get("/vcenter/status")
async def vcenter_status() -> JSONResponse:
    s = get_secret(VCENTER_SECRET_NAME)
    if not s:
        return JSONResponse(VCenterConnectionStatus(configured=False).model_dump())

    return JSONResponse(VCenterConnectionStatus(
        configured=True,
        name=s.get("VCENTER_NAME"),
        vcenter_url=s.get("VCENTER_URL"),
        username_hint=mask_username(s.get("VCENTER_USERNAME", "")),
        verify_ssl=s.get("VCENTER_VERIFY_SSL") == "true",
        password_set=bool(s.get("VCENTER_PASSWORD")),
        last_test_status=s.get("VCENTER_LAST_TEST_STATUS"),
        last_tested_at=s.get("VCENTER_LAST_TESTED_AT"),
    ).model_dump())


@router.delete("/vcenter")
async def vcenter_delete() -> JSONResponse:
    delete_secret(VCENTER_SECRET_NAME)
    return JSONResponse(ConnectionDeleteResponse(ok=True, status="deleted", message="vCenter credentials deleted.").model_dump())


# ── LLM ──────────────────────────────────────────────────

@router.post("/llm/test")
async def llm_test(req: LLMConnectionRequest) -> JSONResponse:
    ok, msg, err = await test_llm_connection(req.provider, req.base_url, req.model, req.api_key)
    resp = LLMTestResponse(ok=ok, status="success" if ok else "failed", message=msg, error_code=err)
    return JSONResponse(resp.model_dump(), status_code=200 if ok else 400)


@router.post("/llm")
async def llm_save(req: LLMConnectionRequest) -> JSONResponse:
    ok, msg, err = await test_llm_connection(req.provider, req.base_url, req.model, req.api_key)
    if not ok:
        resp = LLMSaveResponse(ok=False, status="failed", message=f"Test failed before save: {msg}")
        return JSONResponse(resp.model_dump(), status_code=400)

    now = _now()
    data = {
        "LLM_PROVIDER": req.provider,
        "LLM_BASE_URL": req.base_url,
        "LLM_MODEL": req.model,
        "LLM_API_KEY": req.api_key,
        "LLM_CREATED_AT": now,
        "LLM_UPDATED_AT": now,
        "LLM_LAST_TEST_STATUS": "success",
        "LLM_LAST_TESTED_AT": now,
    }
    create_or_update_secret(LLM_SECRET_NAME, data, {
        "agentic.io/managed-by": "fastapi",
        "agentic.io/secret-type": "llm",
    })

    status = LLMConnectionStatus(
        configured=True, provider=req.provider, base_url=req.base_url,
        model=req.model, api_key_set=True, last_test_status="success", last_tested_at=now,
    )
    return JSONResponse(LLMSaveResponse(
        ok=True, status="saved", message="LLM credentials saved securely.", connection=status,
    ).model_dump())


@router.get("/llm/status")
async def llm_status() -> JSONResponse:
    s = get_secret(LLM_SECRET_NAME)
    if not s:
        return JSONResponse(LLMConnectionStatus(configured=False).model_dump())

    return JSONResponse(LLMConnectionStatus(
        configured=True,
        provider=s.get("LLM_PROVIDER"),
        base_url=s.get("LLM_BASE_URL"),
        model=s.get("LLM_MODEL"),
        api_key_set=bool(s.get("LLM_API_KEY")),
        last_test_status=s.get("LLM_LAST_TEST_STATUS"),
        last_tested_at=s.get("LLM_LAST_TESTED_AT"),
    ).model_dump())


@router.delete("/llm")
async def llm_delete() -> JSONResponse:
    delete_secret(LLM_SECRET_NAME)
    return JSONResponse(ConnectionDeleteResponse(ok=True, status="deleted", message="LLM credentials deleted.").model_dump())
