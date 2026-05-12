from fastapi.testclient import TestClient

from app.api.deps import llm_model_dep
from app.api.main import app


class FakeLLMModelService:
    def providers(self):
        return [{"id": "gemini", "name": "Google Gemini", "configured": True}]

    def status(self):
        return {"enabled": True, "provider": "gemini", "model": "gemini-test", "configured": True, "status": "ready"}

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
    assert response.json()["data"]["status"] == "ready"
