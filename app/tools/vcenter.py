"""
vcenter_tools.py
================
Core VMware vCenter operations using pyVmomi.
All functions return plain dicts/strings — easy to serialize for MCP/LLM tools.

Requirements:
    pip install pyVmomi
"""

import ssl
import atexit
from datetime import datetime
from typing import Any

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim, vmodl


# ─────────────────────────────────────────────
# Connection Manager
# ─────────────────────────────────────────────

class VCenterConnection:
    """Thread-safe vCenter connection wrapper."""

    def __init__(self):
        self.si = None          # ServiceInstance
        self.content = None     # ServiceContent

    def connect(self, host: str, user: str, password: str, port: int = 443) -> str:
        """Connect to vCenter. Returns success/error message."""
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE  # For self-signed certs; harden in prod

            self.si = SmartConnect(
                host=host, user=user, pwd=password,
                port=port, sslContext=context
            )
            atexit.register(Disconnect, self.si)
            self.content = self.si.RetrieveContent()
            return f"✅ Connected to vCenter: {host}"
        except Exception as e:
            return f"❌ Connection failed: {e}"

    def disconnect(self):
        if self.si:
            Disconnect(self.si)
            self.si = None
            self.content = None
            return "Disconnected from vCenter."
        return "Not connected."

    def is_connected(self) -> bool:
        return self.si is not None

    def require_connection(self):
        if not self.is_connected():
            raise RuntimeError("Not connected to vCenter. Call connect() first.")


# Global connection singleton
_conn = VCenterConnection()


def connect_vcenter(host: str = "", user: str = "", password: str = "", port: int = 0) -> str:
    """Connect to vCenter. If any field is empty, the server will fall back to VCENTER_HOST/USER/PASSWORD/PORT env vars. If already connected, returns the current status. Call this with no arguments to use server credentials."""
    import os as _os

    if _conn.is_connected():
        return f"Already connected to vCenter: {_os.environ.get('VCENTER_HOST', '(unknown host)')}"
    host = host or _os.environ.get("VCENTER_HOST", "")
    user = user or _os.environ.get("VCENTER_USER", "")
    password = password or _os.environ.get("VCENTER_PASSWORD", "")
    port = port or int(_os.environ.get("VCENTER_PORT", "443"))
    if not (host and user and password):
        return "Not connected and no credentials available (env vars missing)."
    return _conn.connect(host, user, password, port)

def disconnect() -> str:
    return _conn.disconnect()


# ─────────────────────────────────────────────
# Helper Utilities
# ─────────────────────────────────────────────

def _get_all_objs(vimtype: list, folder=None) -> list:
    """Retrieve all vSphere objects of given type."""
    _conn.require_connection()
    container = _conn.content.viewManager.CreateContainerView(
        folder or _conn.content.rootFolder, vimtype, True
    )
    objects = list(container.view)
    container.Destroy()
    return objects


def _find_vm(name: str):
    """Find a VM by exact name."""
    for vm in _get_all_objs([vim.VirtualMachine]):
        if vm.name == name:
            return vm
    return None


def _find_host(name: str):
    for host in _get_all_objs([vim.HostSystem]):
        if host.name == name:
            return host
    return None


def _task_wait(task) -> dict:
    """Poll a task until complete. Returns status dict."""
    while task.info.state in (vim.TaskInfo.State.running, vim.TaskInfo.State.queued):
        pass  # For simplicity; use task.WaitForTask() in production
    state = task.info.state
    if state == vim.TaskInfo.State.success:
        return {"status": "success", "result": str(task.info.result)}
    else:
        return {"status": "error", "error": str(task.info.error.msg)}


def _vm_summary(vm) -> dict:
    """Serialize a VM object to a dict."""
    summary = vm.summary
    config = summary.config
    runtime = summary.runtime
    guest = summary.guest or vm.guest

    return {
        "name": config.name,
        "guest_os": config.guestFullName,
        "power_state": str(runtime.powerState),
        "cpu_count": config.numCpu,
        "memory_mb": config.memorySizeMB,
        "ip_address": getattr(guest, "ipAddress", "N/A"),
        "hostname": getattr(guest, "hostName", "N/A"),
        "tools_status": str(getattr(guest, "toolsStatus", "N/A")),
        "datastore": config.vmPathName.split("]")[0].strip("[") if config.vmPathName else "N/A",
        "annotation": config.annotation or "",
        "uuid": config.uuid,
    }


# ─────────────────────────────────────────────
# VM Operations
# ─────────────────────────────────────────────

def list_vms(filter_state: str = "all") -> list[dict]:
    """
    List all VMs. filter_state: 'all' | 'poweredOn' | 'poweredOff' | 'suspended'
    """
    vms = _get_all_objs([vim.VirtualMachine])
    result = []
    for vm in vms:
        if vm.config is None:
            continue
        state = str(vm.runtime.powerState)
        if filter_state != "all" and filter_state not in state:
            continue
        result.append(_vm_summary(vm))
    return sorted(result, key=lambda x: x["name"])


def get_vm_details(vm_name: str) -> dict:
    """Get detailed info for a specific VM."""
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}

    details = _vm_summary(vm)

    # Disks
    disks = []
    for device in vm.config.hardware.device:
        if isinstance(device, vim.vm.device.VirtualDisk):
            disks.append({
                "label": device.deviceInfo.label,
                "size_gb": round(device.capacityInKB / 1024 / 1024, 2),
                "datastore": str(device.backing.datastore) if hasattr(device.backing, "datastore") else "N/A"
            })
    details["disks"] = disks

    # Network adapters
    nics = []
    for device in vm.config.hardware.device:
        if isinstance(device, vim.vm.device.VirtualEthernetCard):
            nics.append({
                "label": device.deviceInfo.label,
                "mac": device.macAddress,
                "connected": device.connectable.connected if device.connectable else False
            })
    details["network_adapters"] = nics

    # Snapshots
    details["snapshots"] = list_snapshots(vm_name)

    return details


def power_on_vm(vm_name: str) -> dict:
    """Power on a VM."""
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
    if str(vm.runtime.powerState) == "poweredOn":
        return {"status": "already_on", "vm": vm_name}
    task = vm.PowerOn()
    result = _task_wait(task)
    result["vm"] = vm_name
    return result


def power_off_vm(vm_name: str, force: bool = False) -> dict:
    """
    Power off a VM.
    force=False → graceful shutdown (requires VMware Tools)
    force=True  → hard power off
    """
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
    if str(vm.runtime.powerState) == "poweredOff":
        return {"status": "already_off", "vm": vm_name}
    if force:
        task = vm.PowerOff()
        return {**_task_wait(task), "vm": vm_name, "method": "hard"}
    else:
        try:
            vm.ShutdownGuest()
            return {"status": "success", "vm": vm_name, "method": "graceful"}
        except Exception as e:
            return {"error": str(e), "hint": "VMware Tools may not be running. Use force=True."}


def reset_vm(vm_name: str) -> dict:
    """Hard reset a VM."""
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
    task = vm.Reset()
    return {**_task_wait(task), "vm": vm_name}


def suspend_vm(vm_name: str) -> dict:
    """Suspend a VM."""
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
    task = vm.Suspend()
    return {**_task_wait(task), "vm": vm_name}


def reboot_guest(vm_name: str) -> dict:
    """Graceful guest reboot (requires VMware Tools)."""
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
    try:
        vm.RebootGuest()
        return {"status": "success", "vm": vm_name, "action": "guest_reboot"}
    except Exception as e:
        return {"error": str(e)}


def clone_vm(vm_name: str, clone_name: str, datastore_name: str = None) -> dict:
    """Clone a VM."""
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
    
    folder = vm.parent
    if datastore_name:
        datastore = None
        for ds in _get_all_objs([vim.Datastore]):
            if ds.name == datastore_name:
                datastore = ds
                break
        if not datastore:
            return {"error": f"Datastore '{datastore_name}' not found."}
    else:
        datastore = None

    relospec = vim.vm.RelocateSpec()
    if datastore:
        relospec.datastore = datastore
    
    relospec.pool = vm.resourcePool

    clonespec = vim.vm.CloneSpec()
    clonespec.location = relospec
    clonespec.powerOn = False

    task = vm.Clone(folder=folder, name=clone_name, spec=clonespec)
    return {**_task_wait(task), "vm": vm_name, "clone": clone_name}


def delete_vm(vm_name: str) -> dict:
    """Delete a VM from disk."""
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
    if str(vm.runtime.powerState) == "poweredOn":
        return {"error": "VM must be powered off before deletion."}
    
    task = vm.Destroy_Task()
    return {**_task_wait(task), "vm": vm_name, "action": "deleted"}


def get_vm_stats(vm_name: str) -> dict:
    """Get real-time performance stats for a VM."""
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
    
    summary = vm.summary
    quick_stats = summary.quickStats
    
    return {
        "vm": vm_name,
        "power_state": str(summary.runtime.powerState),
        "cpu_usage_mhz": getattr(quick_stats, "overallCpuUsage", 0),
        "cpu_demand_mhz": getattr(quick_stats, "overallCpuDemand", 0),
        "guest_memory_usage_mb": getattr(quick_stats, "guestMemoryUsage", 0),
        "host_memory_usage_mb": getattr(quick_stats, "hostMemoryUsage", 0),
        "uptime_seconds": getattr(quick_stats, "uptimeSeconds", 0),
        "consolidation_needed": getattr(summary, "needsConsolidation", False)
    }


def create_vm(vm_name: str, cpu: int = 2, memory_mb: int = 2048, datastore_name: str = None) -> dict:
    """Create a new blank virtual machine."""
    _conn.require_connection()
    
    # Find resource pool
    pools = _get_all_objs([vim.ResourcePool])
    if not pools:
        return {"error": "No resource pool found to deploy VM."}
    resource_pool = pools[0]

    # Find VM folder
    folders = _get_all_objs([vim.Folder])
    vm_folder = next((f for f in folders if f.childType and "VirtualMachine" in f.childType), None)
    if not vm_folder:
        return {"error": "No VM folder found."}

    # Set datastore syntax
    ds_path = f"[{datastore_name}]" if datastore_name else "[]"
    
    config = vim.vm.ConfigSpec(
        name=vm_name,
        memoryMB=memory_mb,
        numCPUs=cpu,
        files=vim.vm.FileInfo(logDirectory=None, snapshotDirectory=None, suspendDirectory=None, vmPathName=ds_path),
        guestId="otherGuest",
        version="vmx-14"
    )

    try:
        task = vm_folder.CreateVM_Task(config=config, pool=resource_pool)
        return {**_task_wait(task), "vm": vm_name, "action": "created"}
    except Exception as e:
        return {"error": str(e)}


def migrate_vm(vm_name: str, host_name: str = None, datastore_name: str = None) -> dict:
    """
    Migrate a running VM (vMotion) to a new host or datastore.
    You must provide either a target host_name or datastore_name.
    """
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
        
    if not host_name and not datastore_name:
        return {"error": "Must provide a target host_name or datastore_name for migration."}
        
    host = None
    if host_name:
        for ds_host in _get_all_objs([vim.HostSystem]):
            if ds_host.name == host_name:
                host = ds_host
                break
        if not host:
            return {"error": f"Target host '{host_name}' not found."}
            
    datastore = None
    if datastore_name:
        for ds in _get_all_objs([vim.Datastore]):
            if ds.name == datastore_name:
                datastore = ds
                break
        if not datastore:
            return {"error": f"Target datastore '{datastore_name}' not found."}
            
    pool = None
    if host:
        try:
            # Usually parent is a ClusterComputeResource or ComputeResource
            pool = host.parent.resourcePool
        except AttributeError:
            pass

    relospec = vim.vm.RelocateSpec()
    if datastore:
        relospec.datastore = datastore
    if host:
        relospec.host = host
    if pool:
        relospec.pool = pool

    try:
        task = vm.RelocateVM_Task(
            spec=relospec,
            priority=vim.VirtualMachine.MovePriority.defaultPriority
        )
        return {**_task_wait(task), "vm": vm_name, "action": "migrated"}
    except Exception as e:
        return {"error": str(e)}


def rename_vm(vm_name: str, new_name: str) -> dict:
    """
    Rename an existing Virtual Machine to a new name.
    """
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}

    try:
        task = vm.Rename_Task(newName=new_name)
        return {**_task_wait(task), "old_name": vm_name, "new_name": new_name, "action": "renamed"}
    except Exception as e:
        return {"error": str(e)}

def change_vm_network(vm_name: str, network_name: str) -> dict:
    """
    Change the network configuration of the primary Network Adapter on the VM.
    Supports both Standard Networks and Distributed Virtual Switches.
    """
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}

    # Find the target network
    target_net = None
    for net in _get_all_objs([vim.Network]):
        if net.name == network_name:
            target_net = net
            break
            
    if not target_net:
        # Fallback to DistributedVirtualPortgroup if standard network fails
        for pg in _get_all_objs([vim.dvs.DistributedVirtualPortgroup]):
            if pg.name == network_name:
                target_net = pg
                break
                
    if not target_net:
        return {"error": f"Network '{network_name}' not found in vCenter."}

    # Find the first NIC on the VM
    nic_device = None
    for dev in vm.config.hardware.device:
        if isinstance(dev, vim.vm.device.VirtualEthernetCard):
            nic_device = dev
            break
            
    if not nic_device:
        return {"error": f"No network adapter found on VM '{vm_name}'."}

    # Update the NIC backing
    nic_spec = vim.vm.device.VirtualDeviceSpec()
    nic_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
    nic_spec.device = nic_device

    # Handle Distributed vs Standard Switch
    if hasattr(target_net, 'config') and hasattr(target_net.config, 'distributedVirtualSwitch'):
        # Distributed Switch Portgroup
        portconnection = vim.dvs.PortConnection()
        portconnection.portgroupKey = target_net.key
        portconnection.switchUuid = target_net.config.distributedVirtualSwitch.uuid
        nic_device.backing = vim.vm.device.VirtualEthernetCard.DistributedVirtualPortBackingInfo()
        nic_device.backing.port = portconnection
    else:
        # Standard Network
        nic_device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
        nic_device.backing.network = target_net
        nic_device.backing.deviceName = network_name

    # Ensure it's connected
    nic_device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
    nic_device.connectable.startConnected = True
    nic_device.connectable.allowGuestControl = True
    nic_device.connectable.connected = vm.runtime.powerState == vim.VirtualMachine.PowerState.poweredOn

    config_spec = vim.vm.ConfigSpec(deviceChange=[nic_spec])
    try:
        task = vm.ReconfigVM_Task(spec=config_spec)
        return {**_task_wait(task), "vm": vm_name, "new_network": network_name, "action": "network_changed"}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# Snapshot Operations
# ─────────────────────────────────────────────

def _parse_snapshots(snapshot_list, result=None) -> list[dict]:
    if result is None:
        result = []
    for snap in (snapshot_list or []):
        result.append({
            "name": snap.name,
            "description": snap.description,
            "created": str(snap.createTime),
            "id": snap.id,
        })
        _parse_snapshots(snap.childSnapshotList, result)
    return result


def list_snapshots(vm_name: str) -> list[dict]:
    """List all snapshots for a VM."""
    vm = _find_vm(vm_name)
    if not vm:
        return [{"error": f"VM '{vm_name}' not found."}]
    if not vm.snapshot:
        return []
    return _parse_snapshots(vm.snapshot.rootSnapshotList)


def create_snapshot(vm_name: str, snapshot_name: str,
                    description: str = "", memory: bool = False) -> dict:
    """Create a snapshot of a VM."""
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
    task = vm.CreateSnapshot(name=snapshot_name, description=description,
                              memory=memory, quiesce=False)
    return {**_task_wait(task), "vm": vm_name, "snapshot": snapshot_name}


def revert_to_snapshot(vm_name: str, snapshot_name: str) -> dict:
    """Revert a VM to a named snapshot."""
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
    if not vm.snapshot:
        return {"error": "No snapshots found."}

    def find_snap(snap_list, name):
        for snap in snap_list:
            if snap.name == name:
                return snap.snapshot
            found = find_snap(snap.childSnapshotList, name)
            if found:
                return found
        return None

    snap_obj = find_snap(vm.snapshot.rootSnapshotList, snapshot_name)
    if not snap_obj:
        return {"error": f"Snapshot '{snapshot_name}' not found."}
    task = snap_obj.RevertToSnapshot_Task()
    return {**_task_wait(task), "vm": vm_name, "snapshot": snapshot_name}


def delete_snapshot(vm_name: str, snapshot_name: str,
                    remove_children: bool = False) -> dict:
    """Delete a named snapshot."""
    vm = _find_vm(vm_name)
    if not vm:
        return {"error": f"VM '{vm_name}' not found."}
    if not vm.snapshot:
        return {"error": "No snapshots found."}

    def find_snap(snap_list, name):
        for snap in snap_list:
            if snap.name == name:
                return snap.snapshot
            found = find_snap(snap.childSnapshotList, name)
            if found:
                return found
        return None

    snap_obj = find_snap(vm.snapshot.rootSnapshotList, snapshot_name)
    if not snap_obj:
        return {"error": f"Snapshot '{snapshot_name}' not found."}
    task = snap_obj.RemoveSnapshot_Task(removeChildren=remove_children)
    return {**_task_wait(task), "vm": vm_name, "snapshot": snapshot_name}


# ─────────────────────────────────────────────
# Host Operations
# ─────────────────────────────────────────────

def list_hosts() -> list[dict]:
    """List all ESXi hosts."""
    hosts = _get_all_objs([vim.HostSystem])
    result = []
    for host in hosts:
        summary = host.summary
        hardware = summary.hardware
        result.append({
            "name": host.name,
            "state": str(summary.runtime.connectionState),
            "power_state": str(summary.runtime.powerState),
            "cpu_model": hardware.cpuModel if hardware else "N/A",
            "cpu_cores": hardware.numCpuCores if hardware else 0,
            "memory_gb": round(hardware.memorySize / 1024**3, 1) if hardware else 0,
            "uptime_hours": round(summary.quickStats.uptime / 3600, 1) if summary.quickStats else 0,
            "version": summary.config.product.version,
        })
    return sorted(result, key=lambda x: x["name"])


def get_host_details(host_name: str) -> dict:
    """Get detailed info for a specific ESXi host."""
    host = _find_host(host_name)
    if not host:
        return {"error": f"Host '{host_name}' not found."}

    vms_on_host = [vm.name for vm in host.vm] if host.vm else []
    return {
        "name": host.name,
        "state": str(host.runtime.connectionState),
        "cpu_usage_mhz": host.summary.quickStats.overallCpuUsage,
        "memory_usage_mb": host.summary.quickStats.overallMemoryUsage,
        "memory_total_gb": round(host.hardware.memorySize / 1024**3, 1),
        "vms": vms_on_host,
        "vm_count": len(vms_on_host),
        "in_maintenance": host.runtime.inMaintenanceMode,
    }


def enter_maintenance_mode(host_name: str) -> dict:
    """Put a host into maintenance mode."""
    host = _find_host(host_name)
    if not host:
        return {"error": f"Host '{host_name}' not found."}
    task = host.EnterMaintenanceMode(timeout=300, evacuatePoweredOffVms=True)
    return {**_task_wait(task), "host": host_name, "action": "enter_maintenance"}


def exit_maintenance_mode(host_name: str) -> dict:
    """Take a host out of maintenance mode."""
    host = _find_host(host_name)
    if not host:
        return {"error": f"Host '{host_name}' not found."}
    task = host.ExitMaintenanceMode(timeout=300)
    return {**_task_wait(task), "host": host_name, "action": "exit_maintenance"}


# ─────────────────────────────────────────────
# Datastore Operations
# ─────────────────────────────────────────────

def list_datastores() -> list[dict]:
    """List all datastores."""
    datastores = _get_all_objs([vim.Datastore])
    result = []
    for ds in datastores:
        summary = ds.summary
        capacity_gb = round(summary.capacity / 1024**3, 1)
        free_gb = round(summary.freeSpace / 1024**3, 1)
        result.append({
            "name": summary.name,
            "type": summary.type,
            "capacity_gb": capacity_gb,
            "free_gb": free_gb,
            "used_gb": round(capacity_gb - free_gb, 1),
            "usage_pct": round((1 - free_gb / capacity_gb) * 100, 1) if capacity_gb > 0 else 0,
            "accessible": summary.accessible,
            "url": summary.url,
        })
    return sorted(result, key=lambda x: x["name"])


# ─────────────────────────────────────────────
# Cluster & Resource Pool
# ─────────────────────────────────────────────

def list_clusters() -> list[dict]:
    """List all compute clusters."""
    clusters = _get_all_objs([vim.ClusterComputeResource])
    result = []
    for cluster in clusters:
        summary = cluster.summary.usageSummary if hasattr(cluster.summary, "usageSummary") else None
        result.append({
            "name": cluster.name,
            "host_count": len(cluster.host),
            "drs_enabled": cluster.configuration.drsConfig.enabled,
            "ha_enabled": cluster.configuration.dasConfig.enabled,
            "total_cpu_mhz": cluster.summary.totalCpu if cluster.summary else 0,
            "total_memory_gb": round(cluster.summary.totalMemory / 1024**3, 1) if cluster.summary else 0,
        })
    return sorted(result, key=lambda x: x["name"])


def list_resource_pools() -> list[dict]:
    """List all resource pools."""
    pools = _get_all_objs([vim.ResourcePool])
    result = []
    for pool in pools:
        result.append({
            "name": pool.name,
            "cpu_limit": pool.config.cpuAllocation.limit,
            "memory_limit_mb": pool.config.memoryAllocation.limit,
            "vm_count": len(pool.vm),
        })
    return sorted(result, key=lambda x: x["name"])


# ─────────────────────────────────────────────
# Network Operations
# ─────────────────────────────────────────────

def list_networks() -> list[dict]:
    """List all networks/port groups."""
    networks = _get_all_objs([vim.Network])
    result = []
    for net in networks:
        result.append({
            "name": net.name,
            "accessible": net.summary.accessible,
            "type": type(net).__name__,
        })
    return sorted(result, key=lambda x: x["name"])


# ─────────────────────────────────────────────
# Events & Alarms
# ─────────────────────────────────────────────

def get_recent_events(max_events: int = 20) -> list[dict]:
    """Fetch recent vCenter events."""
    _conn.require_connection()
    event_manager = _conn.content.eventManager
    filter_spec = vim.event.EventFilterSpec()
    filter_spec.maxCount = max_events
    events = event_manager.QueryEvents(filter_spec)
    result = []
    for event in events:
        result.append({
            "time": str(event.createdTime),
            "type": type(event).__name__,
            "message": event.fullFormattedMessage,
            "user": event.userName,
        })
    return result


def get_active_alarms() -> list[dict]:
    """Get all triggered alarms in the datacenter."""
    _conn.require_connection()
    result = []
    for dc in _get_all_objs([vim.Datacenter]):
        for alarm in dc.triggeredAlarmState:
            result.append({
                "entity": str(alarm.entity),
                "alarm": str(alarm.alarm),
                "status": str(alarm.overallStatus),
                "time": str(alarm.time),
            })
    return result


# ─────────────────────────────────────────────
# VM Cloning
# ─────────────────────────────────────────────

def clone_vm(source_vm_name: str, clone_name: str,
             datacenter_name: str = None, datastore_name: str = None) -> dict:
    """Clone a VM (thin clone from current state)."""
    vm = _find_vm(source_vm_name)
    if not vm:
        return {"error": f"Source VM '{source_vm_name}' not found."}

    # Find destination folder (same as source by default)
    dest_folder = vm.parent

    # Datastore
    if datastore_name:
        ds_list = _get_all_objs([vim.Datastore])
        datastore = next((d for d in ds_list if d.name == datastore_name), None)
        if not datastore:
            return {"error": f"Datastore '{datastore_name}' not found."}
    else:
        datastore = vm.datastore[0]

    # Build clone spec
    relocate_spec = vim.vm.RelocateSpec(datastore=datastore)
    clone_spec = vim.vm.CloneSpec(
        location=relocate_spec,
        powerOn=False,
        template=False
    )
    task = vm.Clone(folder=dest_folder, name=clone_name, spec=clone_spec)
    return {**_task_wait(task), "source": source_vm_name, "clone": clone_name}


# ─────────────────────────────────────────────
# vCenter Info
# ─────────────────────────────────────────────

def get_vcenter_info() -> dict:
    """Return high-level vCenter environment summary."""
    _conn.require_connection()
    about = _conn.content.about
    vms = _get_all_objs([vim.VirtualMachine])
    hosts = _get_all_objs([vim.HostSystem])
    datastores = _get_all_objs([vim.Datastore])
    clusters = _get_all_objs([vim.ClusterComputeResource])

    powered_on = sum(1 for v in vms if str(v.runtime.powerState) == "poweredOn")

    return {
        "vcenter_version": about.version,
        "vcenter_build": about.build,
        "full_name": about.fullName,
        "total_vms": len(vms),
        "powered_on_vms": powered_on,
        "powered_off_vms": len(vms) - powered_on,
        "total_hosts": len(hosts),
        "total_datastores": len(datastores),
        "total_clusters": len(clusters),
    }
