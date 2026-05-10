from types import SimpleNamespace

import pytest

from app.core.errors import ErrorCode
from app.services.vcenter_inventory_service import (
    datastore_status,
    looks_like_host_name,
    normalize_datastore,
    normalize_host,
    normalize_vm,
)
from app.services.vcenter_session import VCenterError


def test_normalize_vm_object() -> None:
    host = SimpleNamespace(name="esxi01.dclab.com")
    datastore = SimpleNamespace(name="Datastore01")
    vm = SimpleNamespace(
        name="roshellevm02",
        datastore=[datastore],
        summary=SimpleNamespace(
            config=SimpleNamespace(numCpu=4, memorySizeMB=8192, guestFullName="Ubuntu Linux"),
            runtime=SimpleNamespace(powerState="poweredOn", host=host),
            guest=SimpleNamespace(ipAddress="10.0.0.10", toolsStatus="toolsOk"),
        ),
    )

    assert normalize_vm(vm) == {
        "name": "roshellevm02",
        "power_state": "poweredOn",
        "cpu": 4,
        "memory_gb": 8.0,
        "guest_os": "Ubuntu Linux",
        "ip_address": "10.0.0.10",
        "host": "esxi01.dclab.com",
        "datastore": "Datastore01",
        "tools_status": "toolsOk",
    }


def test_normalize_host_object() -> None:
    host = SimpleNamespace(
        name="esxi01.dclab.com",
        vm=[object(), object()],
        summary=SimpleNamespace(
            hardware=SimpleNamespace(
                vendor="Dell",
                model="PowerEdge",
                numCpuCores=32,
                memorySize=128 * 1024**3,
            ),
            runtime=SimpleNamespace(connectionState="connected", powerState="poweredOn"),
            config=SimpleNamespace(product=SimpleNamespace(version="8.0.3", build="24022510")),
        ),
    )

    data = normalize_host(host)

    assert data["name"] == "esxi01.dclab.com"
    assert data["cpu_cores"] == 32
    assert data["memory_gb"] == 128.0
    assert data["vm_count"] == 2


def test_normalize_datastore_object() -> None:
    datastore = SimpleNamespace(
        name="DS01",
        summary=SimpleNamespace(
            type="VMFS",
            capacity=100 * 1024**3,
            freeSpace=25 * 1024**3,
            accessible=True,
        ),
    )

    data = normalize_datastore(datastore)

    assert data["capacity_gb"] == 100.0
    assert data["free_gb"] == 25.0
    assert data["used_percent"] == 75.0
    assert data["accessible"] is True


def test_datastore_status_thresholds() -> None:
    assert datastore_status(79.99) == "healthy"
    assert datastore_status(80) == "warning"
    assert datastore_status(90) == "critical"


def test_host_name_detection() -> None:
    assert looks_like_host_name("esxi01.dclab.com") is True
    assert looks_like_host_name("esx-prod-01") is True
    assert looks_like_host_name("roshellevm02") is False


async def test_vm_details_blocks_host_like_name() -> None:
    from app.services.vcenter_inventory_service import VCenterInventoryService

    service = VCenterInventoryService(session=SimpleNamespace())

    with pytest.raises(VCenterError) as exc:
        await service.get_vm_details("esxi01.dclab.com")

    assert exc.value.error_code == ErrorCode.WRONG_OBJECT_TYPE
