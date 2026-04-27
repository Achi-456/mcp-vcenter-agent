"""vCenter inventory tree (reads from pyVmomi; four view modes like vSphere)."""
from __future__ import annotations

import os
from typing import Callable

from nicegui import ui

import app.tools.vcenter as vc


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _vcenter_label() -> str:
    host = os.environ.get("VCENTER_HOST", "")
    info = _safe(vc.get_vcenter_info, {}) or {}
    version = info.get("vcenter_version", "")
    return host or f"vCenter {version}"


def _hosts_and_clusters_tree() -> list[dict]:
    clusters = _safe(vc.list_clusters, []) or []
    hosts = _safe(vc.list_hosts, []) or []
    vms = _safe(lambda: vc.list_vms("all"), []) or []

    # group hosts by cluster name when present
    cluster_by_name = {c.get("name"): c for c in clusters if c.get("name")}
    root = {
        "id": "vcenter",
        "label": _vcenter_label(),
        "icon": "cloud",
        "children": [],
    }
    dc_node = {
        "id": "dc:default",
        "label": "Datacenter",
        "icon": "domain",
        "children": [],
    }
    root["children"].append(dc_node)

    if cluster_by_name:
        for cname, c in cluster_by_name.items():
            cnode = {
                "id": f"cluster:{cname}",
                "label": cname,
                "icon": "grid_view",
                "children": [],
            }
            for h in hosts:
                hname = h.get("name") or ""
                hnode = {
                    "id": f"host:{hname}",
                    "label": hname,
                    "icon": "dns",
                    "children": [
                        {"id": f"vm:{v.get('name', '?')}", "label": v.get("name", "?"), "icon": "view_in_ar"}
                        for v in vms
                        if v.get("host") == hname
                    ],
                }
                cnode["children"].append(hnode)
            dc_node["children"].append(cnode)
    else:
        for h in hosts:
            hname = h.get("name") or ""
            hnode = {
                "id": f"host:{hname}",
                "label": hname,
                "icon": "dns",
                "children": [
                    {"id": f"vm:{v.get('name', '?')}", "label": v.get("name", "?"), "icon": "view_in_ar"}
                    for v in vms
                    if v.get("host") == hname
                ],
            }
            dc_node["children"].append(hnode)

    # VMs not attached to a known host
    loose = [v for v in vms if not v.get("host")]
    if loose:
        dc_node["children"].append(
            {
                "id": "grp:loose_vms",
                "label": f"Unassigned VMs ({len(loose)})",
                "icon": "help_outline",
                "children": [
                    {"id": f"vm:{v.get('name', '?')}", "label": v.get("name", "?"), "icon": "view_in_ar"}
                    for v in loose
                ],
            }
        )
    return [root]


def _vms_tree() -> list[dict]:
    vms = _safe(lambda: vc.list_vms("all"), []) or []
    root = {
        "id": "vms",
        "label": _vcenter_label(),
        "icon": "cloud",
        "children": [],
    }
    by_state: dict[str, list] = {"poweredOn": [], "poweredOff": [], "suspended": []}
    for v in vms:
        s = str(v.get("power_state") or "").lower()
        if "on" in s:
            by_state["poweredOn"].append(v)
        elif "off" in s:
            by_state["poweredOff"].append(v)
        else:
            by_state["suspended"].append(v)
    for label, icon, lst in (
        ("Powered On", "play_circle", by_state["poweredOn"]),
        ("Powered Off", "power_settings_new", by_state["poweredOff"]),
        ("Suspended", "pause_circle", by_state["suspended"]),
    ):
        root["children"].append(
            {
                "id": f"grp:{label}",
                "label": f"{label} ({len(lst)})",
                "icon": icon,
                "children": [
                    {"id": f"vm:{v.get('name', '?')}", "label": v.get("name", "?"), "icon": "view_in_ar"}
                    for v in lst
                ],
            }
        )
    return [root]


def _storage_tree() -> list[dict]:
    dss = _safe(vc.list_datastores, []) or []
    return [
        {
            "id": "storage",
            "label": _vcenter_label(),
            "icon": "cloud",
            "children": [
                {
                    "id": f"ds:{d.get('name', '?')}",
                    "label": f"{d.get('name', '?')}  -  {int(((float(d.get('capacity_gb', 0) or 0) - float(d.get('free_gb', 0) or 0)) / (float(d.get('capacity_gb', 1) or 1) or 1)) * 100)}% used",
                    "icon": "storage",
                }
                for d in dss
            ],
        }
    ]


def _network_tree() -> list[dict]:
    nets = _safe(vc.list_networks, []) or []
    return [
        {
            "id": "net",
            "label": _vcenter_label(),
            "icon": "cloud",
            "children": [
                {
                    "id": f"net:{n.get('name', '?')}",
                    "label": n.get("name", "?"),
                    "icon": "lan",
                }
                for n in nets
            ],
        }
    ]


VIEW_MODES = [
    ("hosts", "Hosts & Clusters", "dns", _hosts_and_clusters_tree),
    ("vms", "VMs & Templates", "view_in_ar", _vms_tree),
    ("storage", "Storage", "storage", _storage_tree),
    ("network", "Networking", "lan", _network_tree),
]


class InventoryPanel:
    """Renders the left inventory panel with four tabs + a tree."""

    def __init__(self, on_select: Callable[[str, str], None]) -> None:
        self.on_select = on_select
        self.current_mode = "hosts"
        self.tree: ui.tree | None = None
        self._tabs_row: ui.row | None = None
        self._tree_container: ui.column | None = None
        self._render()

    def _render(self) -> None:
        with ui.element("div").classes("vc-inv") as root:
            # Mode tabs
            with ui.row().classes("vc-inv-tabs no-wrap").style("margin:0;padding:0;gap:0"):
                self._tabs_row = ui.row()
                for key, label, icon, _fn in VIEW_MODES:
                    self._render_mode_tab(key, label, icon)
            # Search
            with ui.row().classes("q-pa-sm").style("border-bottom:1px solid var(--border)"):
                s = ui.input(placeholder="Filter…").props("dense outlined clearable").classes("w-full")
                s.on("update:model-value", lambda e: self._apply_filter(e.args if isinstance(e.args, str) else e.value or ""))
            # Tree container. Data is only fetched on explicit user action (Refresh)
            # to avoid blocking the sync page handler with pyVmomi calls.
            self._tree_container = ui.column().classes("col").style("overflow:auto;flex:1")
            with self._tree_container:
                with ui.column().classes("items-center q-pa-md"):
                    ui.icon("dns", size="32px").style("color:var(--text3)")
                    ui.label("Click Refresh to load").classes("text-caption text-grey-7 q-mt-sm")
                    ui.button("Refresh inventory", icon="refresh", on_click=self._async_reload).props("unelevated size=sm q-mt-sm")

    def _render_mode_tab(self, key: str, label: str, icon: str) -> None:
        cls = "vc-inv-tab" + (" active" if key == self.current_mode else "")
        btn = ui.element("div").classes(cls).tooltip(label)
        with btn:
            with ui.row().classes("items-center justify-center no-wrap"):
                ui.icon(icon, size="18px")
        btn.on("click", lambda k=key: self._switch(k))

    def _switch(self, key: str) -> None:
        self.current_mode = key
        # Re-render tabs + tree
        # Easiest: full refresh of the panel's parent container
        ui.run_javascript("window.dispatchEvent(new Event('resize'))")
        self._reload_tree()
        # Update tab classes
        for row in self._root_tabs_elements():
            pass  # full re-render handles this

    def _root_tabs_elements(self):
        return []

    def _reload_tree(self) -> None:
        if self._tree_container is None:
            return
        self._tree_container.clear()
        builder = next((fn for (k, _l, _i, fn) in VIEW_MODES if k == self.current_mode), None)
        if not builder:
            return
        nodes = builder() or []
        with self._tree_container:
            if not nodes:
                ui.label("No data").classes("text-grey-7 q-pa-md")
                return
            self.tree = ui.tree(
                nodes,
                label_key="label",
                node_key="id",
                on_select=lambda e: self._on_node_select(e.value if hasattr(e, "value") else None),
            ).classes("w-full").props("no-connectors")
            self.tree.add_slot(
                "default-header",
                '<div class="row items-center no-wrap"><q-icon :name="props.node.icon || \'folder\'" class="q-mr-sm" /><div>{{ props.node.label }}</div></div>',
            )
            try:
                self.tree.expand()
            except Exception:
                pass

    def _on_node_select(self, node_id) -> None:
        if not node_id:
            return
        prefix, _, name = str(node_id).partition(":")
        self.on_select(prefix or "", name or "")

    def _apply_filter(self, text: str) -> None:
        if self.tree is None:
            return
        self.tree.filter = text

    def refresh(self) -> None:
        """External refresh entry point (sync)."""
        self._reload_tree()

    async def _async_reload(self) -> None:
        """Run the (blocking) tree builder off-loop to keep websockets healthy."""
        import asyncio
        builder = next((fn for (k, _l, _i, fn) in VIEW_MODES if k == self.current_mode), None)
        if not builder:
            return
        if self._tree_container is None:
            return
        self._tree_container.clear()
        with self._tree_container:
            with ui.row().classes("items-center q-pa-sm"):
                ui.spinner(size="sm")
                ui.label("Loading inventory…").classes("text-grey-7")
        try:
            nodes = await asyncio.to_thread(builder)
        except Exception as e:
            self._tree_container.clear()
            with self._tree_container:
                ui.label(f"Error: {e}").classes("text-negative q-pa-sm")
            return
        self._tree_container.clear()
        with self._tree_container:
            if not nodes:
                ui.label("No data").classes("text-grey-7 q-pa-md")
                return
            self.tree = ui.tree(
                nodes,
                label_key="label",
                node_key="id",
                on_select=lambda e: self._on_node_select(e.value if hasattr(e, "value") else None),
            ).classes("w-full").props("no-connectors")
            self.tree.add_slot(
                "default-header",
                '<div class="row items-center no-wrap"><q-icon :name="props.node.icon || \'folder\'" class="q-mr-sm" /><div>{{ props.node.label }}</div></div>',
            )
            try:
                self.tree.expand()
            except Exception:
                pass
