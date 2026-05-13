from fastapi.testclient import TestClient

from app.api.deps import llm_model_dep
from app.api.main import app


class FakeLLMModelService:
    async def providers(self):
        return [{"id": "gemini", "name": "Google Gemini", "configured": True}]

    async def status(self):
        return {
            "llm_enabled": True,
            "active_provider": "gemini",
            "active_model": "gemini-test",
            "backend_discovery_configured": True,
            "engine_runtime_configured": False,
            "missing_requirements": ["agent-engine provider credential for gemini is not mounted"],
            "status": "not_configured",
        }

    async def list_models(self, provider: str):
        return {
            "provider": provider,
            "configured": True,
            "models": [
                {
                    "id": "gemini-test",
                    "name": "models/gemini-test",
                    "display_name": "Gemini Test",
                    "input_token_limit": 1000,
                    "output_token_limit": 100,
                }
            ],
        }

    async def configure_provider(self, provider: str, api_key: str):
        return {
            "provider": provider,
            "backend_discovery_configured": True,
            "engine_runtime_configured": False,
            "engine_runtime_updated": False,
            "message": "Backend discovery secret saved. Agent Engine runtime was not changed.",
        }


def client() -> TestClient:
    app.dependency_overrides[llm_model_dep] = lambda: FakeLLMModelService()
    return TestClient(app)


def teardown_function() -> None:
    app.dependency_overrides.clear()


def test_llm_providers_route() -> None:
    response = client().get("/api/v1/llm/providers")
    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "gemini"


def test_llm_models_route_uses_provider_query() -> None:
    response = client().get("/api/v1/llm/models?provider=gemini")
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["provider"] == "gemini"
    assert payload["models"][0]["id"] == "gemini-test"


def test_llm_status_route() -> None:
    response = client().get("/api/v1/llm/status")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["backend_discovery_configured"] is True
    assert data["engine_runtime_configured"] is False
    assert "agent-engine provider credential for gemini is not mounted" in data["missing_requirements"]


def test_llm_configure_route_does_not_claim_engine_runtime_update() -> None:
    response = client().post("/api/v1/llm/configure", json={"provider": "gemini", "api_key": "secret-value"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["backend_discovery_configured"] is True
    assert data["engine_runtime_configured"] is False
    assert data["engine_runtime_updated"] is False
    assert "secret-value" not in response.text


def test_llm_routes_do_not_return_secrets() -> None:
    for path in ["/api/v1/llm/providers", "/api/v1/llm/models?provider=gemini", "/api/v1/llm/status"]:
        response = client().get(path)
        assert response.status_code == 200
        assert "secret-value" not in response.text
        assert "api_key" not in response.text.lower()
