from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class LLMProviderError(Exception):
    """Base exception for sanitized LLM provider failures."""


class LLMProviderTimeoutError(LLMProviderError):
    """Raised when a provider request times out."""


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


class LLMProvider(ABC):
    provider_name: str

    @abstractmethod
    async def complete(self, messages: list[LLMMessage]) -> str:
        """Return text generated from the supplied messages."""
