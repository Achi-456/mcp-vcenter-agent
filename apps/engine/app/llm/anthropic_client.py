import httpx
import structlog

from app.llm.base import LLMClient

logger = structlog.get_logger()

ANTHROPIC_API = "https://api.anthropic.com/v1/messages"


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str):
        self._api_key = api_key

    async def generate(self, system_prompt: str, user_prompt: str, model: str) -> str:
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model or "claude-sonnet-4-20250514",
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "max_tokens": 2048,
            "temperature": 0.3,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(ANTHROPIC_API, json=payload, headers=headers)
                if resp.status_code != 200:
                    body = resp.text[:300]
                    logger.warning("anthropic_api_error", status=resp.status_code, body=body)
                    return ""

                data = resp.json()
                content_blocks = data.get("content", [])
                texts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
                return "\n".join(texts)

        except Exception as exc:
            logger.warning("anthropic_request_failed", error=str(exc)[:120])
            return ""
