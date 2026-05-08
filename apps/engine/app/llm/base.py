from abc import ABC, abstractmethod


class LLMClient(ABC):
    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str, model: str) -> str:
        ...


class LLMProviderFactory:
    def get_client(self, provider: str) -> LLMClient | None:
        raise NotImplementedError
