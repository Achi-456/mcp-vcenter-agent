from datetime import datetime, timezone

from pyVmomi import vim


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def list_vms(si, content) -> list[dict]:
    view = content.viewManager.CreateContainerView(content.rootFolder, [vim.VirtualMachine], True)
    try:
        result = []
        for vm in view.view:
            s = vm.summary
            g = s.guest
            h = s.runtime.host.name if s.runtime.host else None
            result.append({
                "id": vm._moId,
                "name": s.config.name,
                "power_state": s.runtime.powerState,
                "cpu": s.config.numCpu,
                "memory_gb": round(s.config.memorySizeMB / 1024, 1) if s.config.memorySizeMB else 0,
                "guest_os": s.config.guestFullName,
                "ip_address": g.ipAddress if g else None,
                "host": h,
                "cluster": None,
                "datastore": None,
                "tools_status": g.toolsStatus if g else "unknown",
                "uptime_seconds": vm.summary.quickStats.uptimeSeconds if vm.summary.quickStats else None,
                "path": s.config.vmPathName,
            })
        return result
    finally:
        view.Destroy()


def list_hosts(si, content) -> list[dict]:
    view = content.viewManager.CreateContainerView(content.rootFolder, [vim.HostSystem], True)
    try:
        result = []
        for host in view.view:
            s = host.summary
            hw = s.hardware
            result.append({
                "id": host._moId,
                "name": host.name,
                "connection_state": s.runtime.connectionState,
                "power_state": s.runtime.powerState,
                "cpu_cores": hw.numCpuCores,
                "cpu_threads": hw.numCpuThreads,
                "memory_gb": round(hw.memorySize / (1024**3), 1),
                "vm_count": len(host.vm) if host.vm else 0,
                "vendor": hw.vendor,
                "model": hw.model,
                "version": s.config.product.version if s.config.product else None,
                "cluster": None,
            })
        return result
    finally:
        view.Destroy()


def list_datastores(si, content) -> list[dict]:
    view = content.viewManager.CreateContainerView(content.rootFolder, [vim.Datastore], True)
    try:
        result = []
        for ds in view.view:
            s = ds.summary
            cap = s.capacity
            free = s.freeSpace
            used = cap - free
            result.append({
                "id": ds._moId,
                "name": s.name,
                "type": s.type,
                "capacity_gb": round(cap / (1024**3), 1),
                "free_gb": round(free / (1024**3), 1),
                "used_gb": round(used / (1024**3), 1),
                "used_percent": round((used / cap) * 100, 1) if cap > 0 else 0,
                "accessible": s.accessible,
                "multiple_host_access": s.multipleHostAccess,
            })
        return result
    finally:
        view.Destroy()


def list_networks(si, content) -> list[dict]:
    view = content.viewManager.CreateContainerView(content.rootFolder, [vim.Network], True)
    try:
        result = []
        for net in view.view:
            result.append({
                "id": net._moId,
                "name": net.name,
                "type": net.__class__.__name__,
                "accessible": net.summary.accessible if hasattr(net, "summary") else True,
            })
        return result
    finally:
        view.Destroy()


def list_clusters(si, content) -> list[dict]:
    view = content.viewManager.CreateContainerView(content.rootFolder, [vim.ClusterComputeResource], True)
    try:
        result = []
        for cluster in view.view:
            s = cluster.summary
            result.append({
                "id": cluster._moId,
                "name": cluster.name,
                "num_hosts": s.numHosts,
                "num_vms": s.numVmotion if hasattr(s, "numVmotion") else 0,
                "total_cpu_mhz": s.totalCpu,
                "total_memory_mb": s.totalMemory,
            })
        return result
    finally:
        view.Destroy()


def get_inventory_overview(si, content) -> dict:
    vms_data = list_vms(si, content)
    hosts_data = list_hosts(si, content)
    ds_data = list_datastores(si, content)
    nets_data = list_networks(si, content)

    powered_on = sum(1 for v in vms_data if v["power_state"] == "poweredOn")
    powered_off = sum(1 for v in vms_data if v["power_state"] == "poweredOff")
    suspended = sum(1 for v in vms_data if v["power_state"] == "suspended")

    connected = sum(1 for h in hosts_data if h["connection_state"] == "connected")

    ds_total_cap = sum(d["capacity_gb"] for d in ds_data)
    ds_total_free = sum(d["free_gb"] for d in ds_data)

    return {
        "vms": {"total": len(vms_data), "powered_on": powered_on, "powered_off": powered_off, "suspended": suspended},
        "hosts": {"total": len(hosts_data), "connected": connected, "maintenance": 0, "disconnected": 0},
        "datastores": {
            "total": len(ds_data),
            "capacity_gb": round(ds_total_cap, 1),
            "free_gb": round(ds_total_free, 1),
            "used_percent": round(((ds_total_cap - ds_total_free) / ds_total_cap) * 100, 1) if ds_total_cap > 0 else 0,
        },
        "networks": {"total": len(nets_data)},
    }
