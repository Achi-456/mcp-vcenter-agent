import pytest
from pyVmomi import vim

from app.core.errors import ErrorCode
from app.services.vcenter_session import VCenterError, VCenterSession


class FakeSecretStore:
    def __init__(self, values=None):
        self.values = values or {}

    async def read_values(self, *args, **kwargs):
        return self.values


async def test_vcenter_session_reads_supported_secret_keys() -> None:
    session = VCenterSession(
        secret_store=FakeSecretStore(
            {
                "VCENTER_HOST": "vcsa.dclab.local",
                "VCENTER_USER": "administrator@vsphere.local",
                "VCENTER_PASSWORD": "dummy-sensitive-value",
                "VCENTER_VERIFY_SSL": "false",
            }
        )
    )

    credentials = await session.load_credentials()

    assert credentials.host == "vcsa.dclab.local"
    assert credentials.username == "administrator@vsphere.local"
    assert credentials.verify_ssl is False
    assert "password" not in credentials.safe_summary()


async def test_vcenter_session_reads_url_and_username_variants() -> None:
    session = VCenterSession(
        secret_store=FakeSecretStore(
            {
                "VCENTER_URL": "https://vcsa.dclab.local:443",
                "VCENTER_USERNAME": "administrator@vsphere.local",
                "VCENTER_PASSWORD": "dummy-sensitive-value",
            }
        )
    )

    credentials = await session.load_credentials()

    assert credentials.host == "vcsa.dclab.local"
    assert credentials.port == 443


async def test_missing_vcenter_secret_maps_to_not_configured() -> None:
    session = VCenterSession(secret_store=FakeSecretStore({}))

    with pytest.raises(VCenterError) as exc:
        await session.load_credentials()

    assert exc.value.error_code == ErrorCode.VCENTER_NOT_CONFIGURED


async def test_not_authenticated_reconnects_once(monkeypatch) -> None:
    session = VCenterSession(
        secret_store=FakeSecretStore(
            {
                "VCENTER_HOST": "vcsa.dclab.local",
                "VCENTER_USER": "user",
                "VCENTER_PASSWORD": "dummy-sensitive-value",
            }
        )
    )
    calls = {"connect": 0, "run": 0}

    async def fake_connect(_credentials):
        calls["connect"] += 1
        return object()

    async def fake_has_current_session(_service_instance):
        return False

    async def fake_disconnect_locked():
        return None

    async def fake_run_with_instance(_service_instance, _func):
        calls["run"] += 1
        raise vim.fault.NotAuthenticated()

    monkeypatch.setattr(session, "_connect", fake_connect)
    monkeypatch.setattr(session, "_has_current_session", fake_has_current_session)
    monkeypatch.setattr(session, "_disconnect_locked", fake_disconnect_locked)
    monkeypatch.setattr(session, "_run_with_instance", fake_run_with_instance)

    with pytest.raises(VCenterError) as exc:
        await session.run(lambda _si, _content: None)

    assert exc.value.error_code == ErrorCode.VCENTER_SESSION_EXPIRED
    assert calls == {"connect": 2, "run": 2}
