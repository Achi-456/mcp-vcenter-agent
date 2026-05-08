import httpx
import structlog

from app.llm.base import LLMClient

logger = structlog.get_logger()


class OpenAICompatibleClient(LLMClient):
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def generate(self, system_prompt: str, user_prompt: str, model: str) -> str:
        url = f"{self._base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    body = resp.text[:300]
                    logger.warning("openai_api_error", status=resp.status_code, body=body)
                    return ""

                data = resp.json()
                choices = data.get("choices", [])
                if not choices:
                    return ""

                return choices[0].get("message", {}).get("content", "")

        except Exception as exc:
            logger.warning("openai_request_failed", error=str(exc)[:120])
            return ""
