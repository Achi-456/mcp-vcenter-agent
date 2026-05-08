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
    alarms_data = list_alarms(si, content)

    powered_on = sum(1 for v in vms_data if v["power_state"] == "poweredOn")
    powered_off = sum(1 for v in vms_data if v["power_state"] == "poweredOff")
    suspended = sum(1 for v in vms_data if v["power_state"] == "suspended")

    connected = sum(1 for h in hosts_data if h["connection_state"] == "connected")
    maintenance = sum(1 for h in hosts_data if h["connection_state"] == "maintenance")
    disconnected = sum(1 for h in hosts_data if h["connection_state"] in ("disconnected", "notResponding"))

    ds_total_cap = sum(d["capacity_gb"] for d in ds_data)
    ds_total_free = sum(d["free_gb"] for d in ds_data)

    critical_alarms = sum(1 for a in alarms_data if a["severity"] == "critical" or a["severity"] == "red")
    warning_alarms = sum(1 for a in alarms_data if a["severity"] == "warning" or a["severity"] == "yellow")

    return {
        "vms": {"total": len(vms_data), "powered_on": powered_on, "powered_off": powered_off, "suspended": suspended},
        "hosts": {"total": len(hosts_data), "connected": connected, "maintenance": maintenance, "disconnected": disconnected},
        "datastores": {
            "total": len(ds_data),
            "capacity_gb": round(ds_total_cap, 1),
            "free_gb": round(ds_total_free, 1),
            "used_percent": round(((ds_total_cap - ds_total_free) / ds_total_cap) * 100, 1) if ds_total_cap > 0 else 0,
        },
        "networks": {"total": len(nets_data)},
        "alarms": {"total": len(alarms_data), "critical": critical_alarms, "warning": warning_alarms},
    }


# ── Alarms ──────────────────────────────────────────────────────────────────

def list_alarms(si, content) -> list[dict]:
    try:
        am = content.alarmManager
        if not am:
            return []
        alarms = am.GetAlarm(content.rootFolder)
        result = []
        for alarm in alarms:
            info = alarm.info
            result.append({
                "id": alarm._moId if hasattr(alarm, '_moId') else str(hash(alarm)),
                "name": info.name,
                "entity": info.entity.name if info.entity else "Global",
                "entity_type": info.entity._type if info.entity and hasattr(info.entity, '_type') else "unknown",
                "severity": info.overallStatus if hasattr(info, 'overallStatus') else "unknown",
                "acknowledged": getattr(alarm, 'acknowledged', False),
                "time": getattr(info, 'creationEventId', None),
                "description": getattr(info, 'description', '') or '',
            })
        return result
    except Exception:
        return []


# ── Events ──────────────────────────────────────────────────────────────────

def list_events(si, content, limit: int = 50) -> list[dict]:
    try:
        em = content.eventManager
        if not em:
            return []
        collector = em.CreateCollectorForEvents(
            vim.event.EventFilterSpec(maxCount=limit, time=vim.event.EventFilterSpec.ByTime())
        )
        try:
            collector.ResetCollector()
            events_page = collector.ReadNextEvents(limit)
            if not events_page:
                return []
            result = []
            for ev in events_page:
                result.append({
                    "id": ev.key,
                    "type": ev.__class__.__name__,
                    "message": ev.fullFormattedMessage,
                    "username": getattr(ev, 'userName', ''),
                    "created_at": str(ev.createdTime) if ev.createdTime else None,
                    "severity": _event_severity(ev),
                    "entity": getattr(ev, 'entityName', ''),
                    "entity_type": ev.entity._type if ev.entity and hasattr(ev.entity, '_type') else "unknown",
                })
            return result
        finally:
            collector.DestroyCollector()
    except Exception:
        return []


def _event_severity(ev) -> str:
    if isinstance(ev, vim.event.ErrorEvent):
        return "error"
    if isinstance(ev, vim.event.WarningEvent):
        return "warning"
    return "info"


# ── Context helpers ─────────────────────────────────────────────────────────

def context_environment(si, content) -> dict:
    ov = get_inventory_overview(si, content)
    return {
        "summary": (
            f"vCenter environment has {ov['hosts']['total']} ESXi hosts "
            f"({ov['hosts']['connected']} connected), "
            f"{ov['vms']['total']} VMs ({ov['vms']['powered_on']} powered on, "
            f"{ov['vms']['powered_off']} powered off), "
            f"{ov['datastores']['total']} datastores ({ov['datastores']['used_percent']}% used), "
            f"{ov['networks']['total']} networks, "
            f"{ov['alarms']['total']} alarms ({ov['alarms']['critical']} critical)."
        ),
        "overview": ov,
    }


def context_powered_off_vms(si, content) -> dict:
    vms = list_vms(si, content)
    off = [v for v in vms if v["power_state"] != "poweredOn"]
    return {
        "count": len(off),
        "summary": f"{len(off)} VMs are not powered on." if off else "All VMs are powered on.",
        "vms": off[:20],
    }


def context_datastore_health(si, content) -> dict:
    ds_data = list_datastores(si, content)
    critical = [d for d in ds_data if d["used_percent"] >= 85]
    warning = [d for d in ds_data if 70 <= d["used_percent"] < 85]
    healthy = [d for d in ds_data if d["used_percent"] < 70]
    return {
        "healthy": len(healthy),
        "warning": len(warning),
        "critical": len(critical),
        "summary": (
            f"{len(healthy)} healthy, {len(warning)} warning (70-85%), {len(critical)} critical (>85%)."
        ),
        "datastores": ds_data,
    }


def context_active_alarms(si, content) -> dict:
    alarms = list_alarms(si, content)
    critical = [a for a in alarms if a["severity"] in ("critical", "red")]
    warning = [a for a in alarms if a["severity"] in ("warning", "yellow")]
    return {
        "total": len(alarms),
        "critical": len(critical),
        "warning": len(warning),
        "summary": f"{len(alarms)} active alarms: {len(critical)} critical, {len(warning)} warning.",
        "alarms": sorted(critical + warning + [a for a in alarms if a["severity"] not in ("critical", "red", "warning", "yellow")], key=lambda a: 0 if a["severity"] in ("critical", "red") else 1 if a["severity"] in ("warning", "yellow") else 2)[:30],
    }


def context_recent_events(si, content) -> dict:
    events = list_events(si, content, limit=30)
    errors = [e for e in events if e["severity"] == "error"]
    warnings = [e for e in events if e["severity"] == "warning"]
    return {
        "total": len(events),
        "errors": len(errors),
        "warnings": len(warnings),
        "summary": f"{len(events)} recent events: {len(errors)} errors, {len(warnings)} warnings.",
        "events": events,
    }


def context_rke2_vms(si, content) -> dict:
    vms = list_vms(si, content)
    patterns = ("agentic", "rke2", "cp-0", "worker-0", "db-0", "utility-0")
    rke2 = [v for v in vms if any(p.lower() in v["name"].lower() for p in patterns)]
    return {
        "count": len(rke2),
        "summary": f"Found {len(rke2)} RKE2-related VMs." if rke2 else "No RKE2-related VMs found.",
        "vms": rke2,
    }
