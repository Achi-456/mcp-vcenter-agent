from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.llm.base import LLMMessage, LLMProvider, LLMProviderError, LLMProviderTimeoutError


class GeminiReportProvider(LLMProvider):
    provider_name = "gemini"

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float, temperature: float) -> None:
        self.api_key = api_key
        self.model = model.removeprefix("models/")
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    async def complete(self, messages: list[LLMMessage]) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        prompt = "\n\n".join(f"{message.role.upper()}:\n{message.content}" for message in messages)
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": self.temperature},
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await asyncio.wait_for(
                    client.post(url, params={"key": self.api_key}, json=payload),
                    timeout=self.timeout_seconds,
                )
            response.raise_for_status()
            body = response.json()
        except TimeoutError as exc:
            raise LLMProviderTimeoutError("LLM provider request timed out.") from exc
        except httpx.TimeoutException as exc:
            raise LLMProviderTimeoutError("LLM provider request timed out.") from exc
        except Exception as exc:
            raise LLMProviderError("LLM provider request failed.") from exc

        text = _extract_text(body)
        if not text.strip():
            raise LLMProviderError("LLM provider returned an empty response.")
        return text.strip()


def _extract_text(body: dict[str, Any]) -> str:
    chunks: list[str] = []
    for candidate in body.get("candidates", []) or []:
        content = candidate.get("content") or {}
        for part in content.get("parts", []) or []:
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks)
