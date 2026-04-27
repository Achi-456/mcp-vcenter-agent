"""Shared UI helpers: direct in-process access to vCenter tools and LLM providers."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import app.tools.vcenter as vc
from app.llm.factory import get_provider, list_configured_providers, PROVIDERS


@dataclass
class VCenterStatus:
    connected: bool
    host: str


def vcenter_status() -> VCenterStatus:
    try:
        connected = vc._conn.is_connected()
    except Exception:
        connected = False
    return VCenterStatus(connected=connected, host=os.environ.get("VCENTER_HOST", ""))


def try_reconnect() -> str:
    return vc.connect_vcenter()


def dashboard_snapshot() -> dict[str, Any]:
    """One shot of everything Home needs, using pyVmomi directly (no HTTP)."""
    try:
        summary = vc.get_vcenter_info()
    except Exception as e:
        return {"error": str(e)}
    try:
        vms = vc.list_vms()
    except Exception:
        vms = []
    try:
        hosts = vc.list_hosts()
    except Exception:
        hosts = []
    try:
        datastores = vc.list_datastores()
    except Exception:
        datastores = []
    try:
        alarms = vc.get_active_alarms()
    except Exception:
        alarms = []
    try:
        events = vc.get_recent_events(10)
    except Exception:
        events = []
    return {
        "summary": summary,
        "vms": vms,
        "hosts": hosts,
        "datastores": datastores,
        "alarms": alarms,
        "events": events,
    }


def default_provider_id() -> str:
    want = (os.environ.get("AGENT_PROVIDER") or "anthropic").strip().lower()
    if any(p["id"] == want for p in PROVIDERS):
        return want
    return "anthropic"


def provider_info() -> list[dict]:
    return list_configured_providers()


def list_provider_models(provider_id: str) -> list[dict]:
    try:
        inst = get_provider(provider_id)
        return inst.list_models()
    except Exception:
        return []
