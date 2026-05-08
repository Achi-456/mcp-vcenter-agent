import httpx
import structlog

from app.llm.base import LLMClient

logger = structlog.get_logger()


class GeminiClient(LLMClient):
    def __init__(self, api_key: str):
        self._api_key = api_key
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def generate(self, system_prompt: str, user_prompt: str, model: str) -> str:
        url = f"{self._base_url}/models/{model}:generateContent?key={self._api_key}"

        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    body = resp.text[:300]
                    logger.warning("gemini_api_error", status=resp.status_code, body=body)
                    return ""

                data = resp.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    return ""

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                texts = [p.get("text", "") for p in parts if "text" in p]
                return "\n".join(texts)

        except Exception as exc:
            logger.warning("gemini_request_failed", error=str(exc)[:120])
            return ""
