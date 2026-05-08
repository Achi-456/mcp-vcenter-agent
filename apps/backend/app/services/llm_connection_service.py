import structlog

import httpx

from app.services.k8s_secret_store import _now

logger = structlog.get_logger()


async def test_llm_connection(
    provider: str,
    base_url: str,
    model: str,
    api_key: str,
) -> tuple[bool, str, str | None]:
    logger.info("llm_test_started", provider=provider, model=model)

    try:
        if provider in ("openai", "openrouter"):
            ok, msg = await _test_openai_compatible(base_url, model, api_key)
        else:
            ok, msg = False, f"Unsupported provider: {provider}"
    except Exception as exc:
        error_code = _classify_llm_error(str(exc))
        ok, msg = False, _llm_friendly(error_code)
        logger.warning("llm_test_failed", provider=provider, error_code=error_code)
        return ok, msg, error_code

    if ok:
        logger.info("llm_test_success", provider=provider, model=model)
        return True, "LLM connection successful.", None
    return False, msg, _classify_llm_error(msg)


async def _test_openai_compatible(base_url: str, model: str, api_key: str) -> tuple[bool, str]:
    url = f"{base_url.rstrip('/')}/chat/completions"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": [{"role": "user", "content": "Reply with: ok"}], "max_tokens": 5},
        )
        if resp.status_code == 200:
            return True, "ok"
        err = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"error": resp.text}
        return False, err.get("error", {}).get("message", str(err))


def _classify_llm_error(msg: str) -> str:
    m = msg.lower()
    if "401" in m or "403" in m or "auth" in m or "key" in m:
        return "LLM_AUTH_FAILED"
    if "model" in m or "not found" in m:
        return "LLM_MODEL_NOT_FOUND"
    if "timeout" in m or "refused" in m or "unreachable" in m:
        return "LLM_UNREACHABLE"
    return "LLM_UNKNOWN_ERROR"


def _llm_friendly(code: str) -> str:
    return {
        "LLM_AUTH_FAILED": "Invalid API key. Check your credentials.",
        "LLM_MODEL_NOT_FOUND": "Model not found or not available with this API key.",
        "LLM_UNREACHABLE": "Could not reach the LLM provider. Check the Base URL.",
        "LLM_UNKNOWN_ERROR": "An unknown error occurred testing the LLM connection.",
    }.get(code, "LLM test failed.")
