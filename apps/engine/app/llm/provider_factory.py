import os

from app.llm.base import LLMClient, LLMProviderFactory
from app.llm.gemini_client import GeminiClient
from app.llm.openai_compatible import OpenAICompatibleClient
from app.llm.anthropic_client import AnthropicClient


class ProviderFactory(LLMProviderFactory):
    def __init__(self):
        self._providers: dict[str, LLMClient] = {}

        gemini_key = os.getenv("GOOGLE_API_KEY", "")
        if gemini_key:
            self._providers["gemini"] = GeminiClient(api_key=gemini_key)

        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key:
            self._providers["openai"] = OpenAICompatibleClient(
                api_key=openai_key,
                base_url="https://api.openai.com/v1",
            )

        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_key:
            self._providers["anthropic"] = AnthropicClient(api_key=anthropic_key)

    def get_client(self, provider: str) -> LLMClient | None:
        return self._providers.get(provider.lower())

    def is_configured(self, provider: str) -> bool:
        return provider.lower() in self._providers

    def available_providers(self) -> list[str]:
        return list(self._providers.keys())


factory = ProviderFactory()
