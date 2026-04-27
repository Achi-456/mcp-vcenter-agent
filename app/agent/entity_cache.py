"""Lightweight in-memory cache of vCenter entities discovered during a session.

After the agent calls list_vms, list_hosts, list_datastores, etc., this cache
stores the names so they can be injected as a compact context block at the start
of each LLM turn — preventing redundant inventory re-queries.
"""
from __future__ import annotations

import json
import logging

log = logging.getLogger(__name__)

# Tool names whose results contain lists of entities we want to cache.
_VM_TOOLS = {"list_vms", "get_vm_details", "get_vm_stats"}
_HOST_TOOLS = {"list_hosts", "get_host_details"}
_DATASTORE_TOOLS = {"list_datastores"}
_CLUSTER_TOOLS = {"list_clusters"}
_NETWORK_TOOLS = {"list_networks"}


def _extract_names(data, *fields: str) -> list[str]:
    """Return unique non-empty name strings from a list-of-dicts or a single dict."""
    names: list[str] = []
    items = data if isinstance(data, list) else [data]
    for item in items:
        if not isinstance(item, dict):
            continue
        for field in fields:
            val = item.get(field)
            if val and isinstance(val, str):
                names.append(val)
                break
    return names


class EntityCache:
    """Accumulate entity names from tool results and format a compact context block."""

    def __init__(self) -> None:
        self._vms: dict[str, bool] = {}         # name -> True (ordered-dict acts as ordered set)
        self._hosts: dict[str, bool] = {}
        self._datastores: dict[str, bool] = {}
        self._clusters: dict[str, bool] = {}
        self._networks: dict[str, bool] = {}

    def update(self, tool_name: str, result_json: str) -> None:
        """Parse *result_json* and extract entity names based on *tool_name*."""
        if not result_json:
            return
        try:
            data = json.loads(result_json)
        except Exception:
            return

        # Unwrap common envelope shapes: {"status":"ok","data":[...]} or {"data":[...]}
        if isinstance(data, dict):
            inner = data.get("data") or data.get("result")
            if inner is not None:
                data = inner

        try:
            if tool_name in _VM_TOOLS:
                for name in _extract_names(data, "name", "vm_name"):
                    self._vms[name] = True
            elif tool_name in _HOST_TOOLS:
                for name in _extract_names(data, "name", "host", "hostname"):
                    self._hosts[name] = True
            elif tool_name in _DATASTORE_TOOLS:
                for name in _extract_names(data, "name", "datastore"):
                    self._datastores[name] = True
            elif tool_name in _CLUSTER_TOOLS:
                for name in _extract_names(data, "name", "cluster"):
                    self._clusters[name] = True
            elif tool_name in _NETWORK_TOOLS:
                for name in _extract_names(data, "name", "network"):
                    self._networks[name] = True
        except Exception as exc:
            log.debug("EntityCache.update skipped %s: %s", tool_name, exc)

    def is_empty(self) -> bool:
        return not any([self._vms, self._hosts, self._datastores, self._clusters, self._networks])

    def format_context_block(self) -> str:
        """Return a compact multi-line context string, or '' if nothing is cached."""
        if self.is_empty():
            return ""

        lines: list[str] = ["[Known vCenter entities — do not re-query unless checking for changes]"]
        if self._vms:
            names = list(self._vms)
            preview = ", ".join(names[:20])
            suffix = f" … (+{len(names) - 20} more)" if len(names) > 20 else ""
            lines.append(f"VMs ({len(names)}): {preview}{suffix}")
        if self._hosts:
            names = list(self._hosts)
            lines.append(f"Hosts ({len(names)}): {', '.join(names[:20])}")
        if self._datastores:
            names = list(self._datastores)
            lines.append(f"Datastores ({len(names)}): {', '.join(names[:20])}")
        if self._clusters:
            names = list(self._clusters)
            lines.append(f"Clusters ({len(names)}): {', '.join(names[:10])}")
        if self._networks:
            names = list(self._networks)
            lines.append(f"Networks ({len(names)}): {', '.join(names[:10])}")

        return "\n".join(lines)
