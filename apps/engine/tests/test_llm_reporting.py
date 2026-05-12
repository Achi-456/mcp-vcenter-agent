import pytest

from app.clients import backend_client
from app.core.config import get_settings
from app.graph.workflow import get_graph
from app.llm import factory
from app.llm.base import LLMMessage, LLMProvider, LLMProviderTimeoutError
from app.llm.gemini_provider import GeminiReportProvider
from app.llm.schemas import build_report_writer_prompt


class FakeProvider(LLMProvider):
    provider_name = "fake"

    def __init__(self, responses: list[str], seen_prompts: list[list[LLMMessage]] | None = None) -> None:
        self.responses = responses
        self.seen_prompts = seen_prompts if seen_prompts is not None else []

    async def complete(self, messages: list[LLMMessage]) -> str:
        self.seen_prompts.append(messages)
        return self.responses.pop(0)


class TimeoutProvider(LLMProvider):
    provider_name = "timeout"

    async def complete(self, messages: list[LLMMessage]) -> str:
        raise LLMProviderTimeoutError("timed out")


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("LLM_ENABLED", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    yield
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_llm_disabled_uses_deterministic_answer(monkeypatch) -> None:
    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": {"name": params["name"], "power_state": "poweredOn"}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "inspect roshellevm02"})

    assert state["final_answer_source"] == "deterministic"
    assert state["llm_used"] is False
    assert state["llm_error"] == "LLM_DISABLED"
    assert state["final_answer"] == state["deterministic_answer"]


@pytest.mark.asyncio
async def test_missing_api_key_uses_deterministic_answer(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    get_settings.cache_clear()

    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": {"name": params["name"], "power_state": "poweredOn"}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "inspect roshellevm02"})

    assert state["final_answer_source"] == "deterministic"
    assert state["llm_used"] is False
    assert state["llm_error"] == "LLM_PROVIDER_UNCONFIGURED"


@pytest.mark.asyncio
async def test_llm_report_with_reviewer_pass_becomes_final(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
    report = "## Issue Summary\n\nLLM report.\n\n## Actions Taken\n\nNo action was taken."
    provider = FakeProvider(
        [
            report,
            '{"passed": true, "safe_to_return": true, "issues": [], "fallback_required": false}',
        ]
    )

    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": {"name": params["name"], "power_state": "poweredOn"}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    monkeypatch.setattr(factory, "create_llm_provider", lambda settings=None: provider)

    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "inspect roshellevm02"})

    assert state["final_answer"] == report
    assert state["final_answer_source"] == "llm"
    assert state["llm_used"] is True
    assert state["llm_review"]["passed"] is True


@pytest.mark.asyncio
async def test_reviewer_fail_uses_deterministic_fallback(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
    provider = FakeProvider(
        [
            "## Issue Summary\n\nUnsafe report.\n\n## Actions Taken\n\nNo action was taken.",
            '{"passed": false, "safe_to_return": false, "issues": ["invented data"], "fallback_required": true}',
        ]
    )

    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": {"name": params["name"], "power_state": "poweredOn"}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    monkeypatch.setattr(factory, "create_llm_provider", lambda settings=None: provider)

    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "inspect roshellevm02"})

    assert state["final_answer_source"] == "deterministic"
    assert state["llm_used"] is False
    assert state["final_answer"] == state["deterministic_answer"]
    assert state["llm_review"]["fallback_required"] is True


@pytest.mark.asyncio
async def test_provider_timeout_uses_deterministic_fallback(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()

    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": {"name": params["name"], "power_state": "poweredOn"}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    monkeypatch.setattr(factory, "create_llm_provider", lambda settings=None: TimeoutProvider())

    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "inspect roshellevm02"})

    assert state["final_answer_source"] == "deterministic"
    assert state["llm_used"] is False
    assert state["llm_error"] == "LLMProviderTimeoutError"


def test_redaction_removes_secrets_before_llm_call() -> None:
    prompt = build_report_writer_prompt(
        {
            "user_message": "inspect vm",
            "risk_level": "read_only",
            "allowed": True,
            "tool_name": "get_vm_details",
            "tool_endpoint": "/api/v1/context/vm-details",
            "tool_input": {"name": "vm1", "authorization": "Bearer secret"},
            "tool_response": {
                "ok": True,
                "data": {
                    "name": "vm1",
                    "password": "hidden",
                    "nested": {"INTERNAL_TOOL_API_TOKEN": "hidden"},
                },
            },
            "deterministic_answer": "No action was taken.",
        },
        max_chars=60000,
    )

    assert "hidden" not in prompt
    assert "Bearer secret" not in prompt
    assert "[REDACTED]" in prompt


@pytest.mark.asyncio
async def test_llm_report_missing_no_action_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
    provider = FakeProvider(["## Issue Summary\n\nLLM report without required action statement."])

    async def fake_get(self, endpoint, params=None):
        return {"ok": True, "data": {"name": params["name"], "power_state": "poweredOn"}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    monkeypatch.setattr(factory, "create_llm_provider", lambda settings=None: provider)

    state = await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "inspect roshellevm02"})

    assert state["final_answer_source"] == "deterministic"
    assert state["llm_error"] == "LLM_LOCAL_REVIEW_FAILED"
    assert "Missing required read-only action statement." in state["llm_review"]["issues"]


@pytest.mark.asyncio
async def test_llm_does_not_execute_tools_directly(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    get_settings.cache_clear()
    provider = FakeProvider(
        [
            "## Issue Summary\n\nLLM report.\n\n## Actions Taken\n\nNo action was taken.",
            '{"passed": true, "safe_to_return": true, "issues": [], "fallback_required": false}',
        ]
    )
    calls = []

    async def fake_get(self, endpoint, params=None):
        calls.append((endpoint, params))
        return {"ok": True, "data": {"name": params["name"], "power_state": "poweredOn"}}

    monkeypatch.setattr(backend_client.BackendClient, "get", fake_get)
    monkeypatch.setattr(factory, "create_llm_provider", lambda settings=None: provider)

    await get_graph().ainvoke({"session_id": "s1", "run_id": "r1", "user_message": "inspect roshellevm02"})

    assert calls == [("/api/v1/context/vm-details", {"name": "roshellevm02"})]
    assert len(provider.seen_prompts) == 2


def test_factory_creates_gemini_provider(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_MODEL", "models/gemini-test")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()

    provider = factory.create_llm_provider()

    assert isinstance(provider, GeminiReportProvider)
    assert provider.model == "gemini-test"
