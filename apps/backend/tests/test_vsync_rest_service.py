import pytest

from app.core.errors import ErrorCode
from app.services.vcenter_session import VCenterError
from app.services.vsphere_rest_service import VSphereRestService


class FakeSecretStore:
    async def read_values(self, secret_name: str):
        return {
            "VCENTER_HOST": "vcenter.local",
            "VCENTER_USERNAME": "administrator",
            "VCENTER_PASSWORD": "secret-password",
            "VCENTER_VERIFY_SSL": "false",
        }


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.text = text

    def json(self):
        return self._payload


class FakeClient:
    responses = []
    requests = []

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, endpoint, auth=None, json=None):
        self.requests.append(("POST", endpoint, auth, json))
        return self.responses.pop(0)

    async def request(self, method, endpoint, headers=None, json=None):
        self.requests.append((method, endpoint, headers, json))
        return self.responses.pop(0)


def service() -> VSphereRestService:
    FakeClient.requests = []
    return VSphereRestService(secret_store=FakeSecretStore(), client_factory=FakeClient)


@pytest.mark.asyncio
async def test_rest_login_does_not_return_token() -> None:
    FakeClient.responses = [
        FakeResponse(payload={"value": "token-1"}),
        FakeResponse(payload={"value": {"version": "7.0"}}),
    ]

    result = await service().about()

    assert result["data"] == {"version": "7.0"}
    assert "token-1" not in str(result)


@pytest.mark.asyncio
async def test_rest_auth_failure_maps_clean_error() -> None:
    FakeClient.responses = [FakeResponse(status_code=401, payload={}, text="no")]

    with pytest.raises(VCenterError) as exc:
        await service().about()

    assert exc.value.error_code == ErrorCode.VCENTER_AUTH_FAILED


@pytest.mark.asyncio
async def test_rest_unauthorized_retries_login_once() -> None:
    FakeClient.responses = [
        FakeResponse(payload={"value": "token-1"}),
        FakeResponse(status_code=401, payload={}, text="expired"),
        FakeResponse(payload={"value": "token-2"}),
        FakeResponse(payload={"value": ["tag-1"]}),
    ]

    result = await service().list_tags()

    assert result["data"] == ["tag-1"]
    login_calls = [request for request in FakeClient.requests if request[0] == "POST" and request[1] == "/rest/com/vmware/cis/session"]
    assert len(login_calls) == 2


@pytest.mark.asyncio
async def test_rest_unsupported_endpoint_returns_clean_error() -> None:
    FakeClient.responses = [
        FakeResponse(payload={"value": "token-1"}),
        FakeResponse(status_code=404, payload={}, text="missing"),
    ]

    with pytest.raises(VCenterError) as exc:
        await service().list_recent_tasks()

    assert exc.value.error_code == ErrorCode.VCENTER_INVENTORY_ERROR
    assert "unsupported" in exc.value.message
