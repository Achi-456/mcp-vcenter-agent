from typing import Any

from pyVmomi import vim

from app.core.errors import ErrorCode
from app.services.vcenter_session import VCenterError, VCenterSession, get_vcenter_session

BYTES_PER_GB = 1024**3
RKE2_MARKERS = ("agentic-", "rke2", "k8s", "worker", "cp-01", "db-01", "utility-01")


def _safe_name(obj: Any) -> str | None:
    return getattr(obj, "name", None) if obj is not None else None


def _enum_value(value: Any) -> str | None:
    return str(value) if value is not None else None


def _gb(value: int | float | None) -> float | None:
    if value is None:
        return None
    return round(float(value) / BYTES_PER_GB, 2)


def _container_view(content: Any, vim_type: type) -> list[Any]:
    view = content.viewManager.CreateContainerView(content.rootFolder, [vim_type], True)
    try:
        return list(view.view)
    finally:
        view.Destroy()


def normalize_vm(vm: Any) -> dict[str, Any]:
    summary = vm.summary
    config = summary.config
    runtime = summary.runtime
    guest = summary.guest
    datastore = vm.datastore[0] if getattr(vm, "datastore", None) else None
    return {
        "name": vm.name,
        "power_state": _enum_value(runtime.powerState),
        "cpu": config.numCpu,
        "memory_gb": round(float(config.memorySizeMB) / 1024, 2) if config.memorySizeMB is not None else None,
        "guest_os": config.guestFullName,
        "ip_address": guest.ipAddress,
        "host": _safe_name(runtime.host),
        "datastore": _safe_name(datastore),
        "tools_status": _enum_value(guest.toolsStatus),
    }


def normalize_host(host: Any) -> dict[str, Any]:
    summary = host.summary
    hardware = summary.hardware
    runtime = summary.runtime
    config = summary.config
    return {
        "name": host.name,
        "connection_state": _enum_value(runtime.connectionState),
        "power_state": _enum_value(runtime.powerState),
        "version": config.product.version if config and config.product else None,
        "build": config.product.build if config and config.product else None,
        "vendor": hardware.vendor,
        "model": hardware.model,
        "cpu_cores": hardware.numCpuCores,
        "memory_gb": _gb(hardware.memorySize),
        "vm_count": len(getattr(host, "vm", []) or []),
    }


def normalize_datastore(datastore: Any) -> dict[str, Any]:
    summary = datastore.summary
    capacity_gb = _gb(summary.capacity)
    free_gb = _gb(summary.freeSpace)
    used_percent = None
    if summary.capacity:
        used_percent = round(((summary.capacity - summary.freeSpace) / summary.capacity) * 100, 2)
    return {
        "name": datastore.name,
        "type": summary.type,
        "capacity_gb": capacity_gb,
        "free_gb": free_gb,
        "used_percent": used_percent,
        "accessible": summary.accessible,
    }


def datastore_status(used_percent: float | None) -> str:
    if used_percent is None:
        return "unknown"
    if used_percent >= 90:
        return "critical"
    if used_percent >= 80:
        return "warning"
    return "healthy"


def looks_like_host_name(name: str) -> bool:
    lowered = name.lower()
    return lowered.startswith("esxi") or lowered.startswith("esx-") or ".esx" in lowered


class VCenterInventoryService:
    def __init__(self, session: VCenterSession | None = None) -> None:
        self.session = session or get_vcenter_session()

    async def list_vms(self) -> list[dict[str, Any]]:
        return await self.session.run(lambda _si, content: [normalize_vm(vm) for vm in _container_view(content, vim.VirtualMachine)])

    async def list_hosts(self) -> list[dict[str, Any]]:
        return await self.session.run(lambda _si, content: [normalize_host(host) for host in _container_view(content, vim.HostSystem)])

    async def list_datastores(self) -> list[dict[str, Any]]:
        return await self.session.run(lambda _si, content: [normalize_datastore(ds) for ds in _container_view(content, vim.Datastore)])

    async def get_vm_details(self, name: str) -> dict[str, Any]:
        if looks_like_host_name(name):
            raise VCenterError(ErrorCode.WRONG_OBJECT_TYPE, f"'{name}' looks like an ESXi host, not a VM.")
        vms = await self.list_vms()
        for vm in vms:
            if vm["name"].lower() == name.lower():
                return vm
        raise VCenterError(ErrorCode.VM_NOT_FOUND, f"No VM named '{name}' was found.")

    async def get_host_details(self, name: str) -> dict[str, Any]:
        hosts = await self.list_hosts()
        for host in hosts:
            if host["name"].lower() == name.lower() or host["name"].split(".")[0].lower() == name.split(".")[0].lower():
                return host
        raise VCenterError(ErrorCode.HOST_NOT_FOUND, f"No ESXi host named '{name}' was found.")

    async def get_datastore_health(self) -> list[dict[str, Any]]:
        datastores = await self.list_datastores()
        return [{**ds, "status": datastore_status(ds["used_percent"])} for ds in datastores]

    async def get_rke2_vms(self) -> list[dict[str, Any]]:
        vms = await self.list_vms()
        return [vm for vm in vms if any(marker in vm["name"].lower() for marker in RKE2_MARKERS)]

    async def get_environment_overview(self) -> dict[str, Any]:
        vms = await self.list_vms()
        hosts = await self.list_hosts()
        datastore_health = await self.get_datastore_health()
        rke2_vms = await self.get_rke2_vms()
        critical = [ds for ds in datastore_health if ds["status"] == "critical"]
        warning = [ds for ds in datastore_health if ds["status"] == "warning"]
        return {
            "vm_count": len(vms),
            "host_count": len(hosts),
            "datastore_count": len(datastore_health),
            "critical_datastore_count": len(critical),
            "warning_datastore_count": len(warning),
            "rke2_vm_count": len(rke2_vms),
        }
