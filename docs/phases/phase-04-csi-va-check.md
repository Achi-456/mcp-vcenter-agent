# Phase 4 - CSI VA Check

## Goal

Add read-only Kubernetes and vCenter storage validation for vSphere CSI health.

## Planned Work

- Add in-cluster Kubernetes readonly client with local kubeconfig fallback.
- Add Kubernetes RBAC for `agentic-api` with get/list/watch only.
- Add endpoints for nodes, CSI pods, CSIDrivers, StorageClasses, PVCs, PVs, VolumeAttachments, and events.
- Add `get_csi_va_check` workflow combining Kubernetes CSI state and vCenter datastore/alarm/event state.
- Add AI quick action later in the frontend: `CSI VA Check`.

## Boundaries

- No Kubernetes patch/delete/scale.
- No PVC/PV modification.
- No datastore or CNS mutation.
- CNS deep query can wait if pyVmomi support is not sufficient; start with PV `volumeHandle` mapping and datastore health.

## Acceptance Criteria

- `run CSI VA check` returns a clear Healthy/Warning/Critical report.
- Pending PVCs and stuck VolumeAttachments are identified.
- StorageClasses using `csi.vsphere.vmware.com` are summarized.
- All operations are read-only.

