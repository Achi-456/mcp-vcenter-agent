import subprocess

import pytest

from app.core.errors import ErrorCode
from app.services.govc_service import GovcService
from app.services.vcenter_session import VCenterError


class FakeSecretStore:
    async def read_values(self, secret_name: str):
        return {
            "VCENTER_HOST": "vcenter.local",
            "VCENTER_USERNAME": "administrator",
            "VCENTER_PASSWORD": "secret-password",
            "VCENTER_VERIFY_SSL": "false",
        }


def test_govc_blocks_unknown_command() -> None:
    service = GovcService(secret_store=FakeSecretStore())

    with pytest.raises(VCenterError) as exc:
        service._validate_command("vm.power")

    assert exc.value.error_code == ErrorCode.TOOL_POLICY_BLOCKED


@pytest.mark.asyncio
async def test_govc_uses_list_args_shell_false_and_hides_password() -> None:
    calls = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout='{"ok": true}', stderr="")

    result = await GovcService(secret_store=FakeSecretStore(), runner=runner).vm_info("vm01")

    args, kwargs = calls[0]
    assert args == ["govc", "vm.info", "-json", "vm01"]
    assert kwargs["shell"] is False
    assert kwargs["env"]["GOVC_PASSWORD"] == "secret-password"
    assert "secret-password" not in str(result)


@pytest.mark.asyncio
async def test_govc_volume_ls_failure_returns_clean_error() -> None:
    def runner(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="volume command unsupported")

    with pytest.raises(VCenterError) as exc:
        await GovcService(secret_store=FakeSecretStore(), runner=runner).volume_ls()

    assert exc.value.error_code == ErrorCode.VCENTER_INVENTORY_ERROR
    assert "volume.ls" in exc.value.message
