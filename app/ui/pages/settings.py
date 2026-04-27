"""Settings page: agent config, vCenter connection, tools reload."""
from __future__ import annotations

import os
from nicegui import ui, app as ng_app

import app.tools.vcenter as vc
from app.tools.combined import build_combined_tools, reload_all_tools
from app.ui.state import vcenter_status


def render_settings(state: dict) -> None:
    with ui.row().classes("q-gutter-md wrap w-full items-start"):
        _agent_card()
        _vcenter_card()
        _integrations_card()


def _agent_card() -> None:
    with ui.card().style("min-width:340px;max-width:440px;flex:1"):
        ui.label("Agent").classes("text-subtitle1 text-weight-medium")
        with ui.row().classes("q-gutter-sm"):
            ui.label("Max turns").classes("text-grey-7").style("min-width:120px")
            ui.label(os.environ.get("AGENT_MAX_TURNS", "25")).classes("text-body2")
        with ui.row().classes("q-gutter-sm"):
            ui.label("Max tokens").classes("text-grey-7").style("min-width:120px")
            ui.label(os.environ.get("AGENT_MAX_TOKENS", "4096")).classes("text-body2")
        with ui.row().classes("q-gutter-sm"):
            ui.label("Planner").classes("text-grey-7").style("min-width:120px")
            ui.label("on" if os.environ.get("AGENT_PLANNER", "").lower() in ("1", "true", "yes", "on") else "off").classes("text-body2")
        ui.label("Change these via env vars and restart the container.").classes("text-caption text-grey-7 q-mt-sm")


def _vcenter_card() -> None:
    with ui.card().style("min-width:340px;max-width:440px;flex:1"):
        ui.label("vCenter").classes("text-subtitle1 text-weight-medium")
        host_lbl = ui.label("").classes("text-body2")
        status_lbl = ui.label("").classes("text-body2")

        def _refresh():
            vs = vcenter_status()
            host_lbl.set_text(f"Host: {vs.host or '(none)'}")
            status_lbl.set_text(f"Status: {'Connected' if vs.connected else 'Disconnected'}")
            status_lbl.classes(replace=("text-positive" if vs.connected else "text-negative"))

        with ui.row().classes("q-gutter-sm q-mt-sm"):
            ui.button("Refresh", icon="refresh", on_click=_refresh).props("flat")
            def _reconnect():
                try:
                    msg = vc.connect_vcenter()
                    ui.notify(msg, type="info")
                except Exception as e:
                    ui.notify(f"Error: {e}", type="negative")
                _refresh()

            ui.button("Reconnect", icon="cable", on_click=_reconnect).props("unelevated")

        _refresh()


def _integrations_card() -> None:
    with ui.card().style("min-width:340px;max-width:440px;flex:1"):
        ui.label("Integrations").classes("text-subtitle1 text-weight-medium")
        _kv("govc", "present on PATH (in container)", ok=True)
        _kv("TAVILY_API_KEY", "set" if os.environ.get("TAVILY_API_KEY") else "not set", ok=bool(os.environ.get("TAVILY_API_KEY")))

        def _reload():
            try:
                reload_all_tools()
                tools, _ = build_combined_tools()
                ui.notify(f"Tools reloaded ({len(tools)})", type="positive")
            except Exception as e:
                ui.notify(f"Reload failed: {e}", type="negative")

        ui.button("Reload tools", icon="refresh", on_click=_reload).props("flat").classes("q-mt-sm")


def _kv(k: str, v: str, ok: bool) -> None:
    with ui.row().classes("q-gutter-sm items-center"):
        ui.label(k).classes("text-grey-7").style("min-width:160px")
        ui.badge(v, color="positive" if ok else "negative")
