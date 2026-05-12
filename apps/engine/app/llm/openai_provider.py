from __future__ import annotations

import asyncio
from typing import Any

from app.llm.base import LLMMessage, LLMProvider, LLMProviderError, LLMProviderTimeoutError


class OpenAIReportProvider(LLMProvider):
    provider_name = "openai"

    def __init__(self, *, api_key: str, model: str, timeout_seconds: float, temperature: float) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature

    async def complete(self, messages: list[LLMMessage]) -> str:
        try:
            from openai import AsyncOpenAI
        except ImportError as exc:
            raise LLMProviderError("OpenAI SDK is not installed.") from exc

        client = AsyncOpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
        input_items = [{"role": message.role, "content": message.content} for message in messages]
        try:
            response = await asyncio.wait_for(
                client.responses.create(
                    model=self.model,
                    input=input_items,
                    temperature=self.temperature,
                ),
                timeout=self.timeout_seconds,
            )
        except TimeoutError as exc:
            raise LLMProviderTimeoutError("LLM provider request timed out.") from exc
        except Exception as exc:
            raise LLMProviderError("LLM provider request failed.") from exc

        text = _extract_response_text(response)
        if not text.strip():
            raise LLMProviderError("LLM provider returned an empty response.")
        return text.strip()


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if isinstance(text, str):
                chunks.append(text)
    return "\n".join(chunks)
