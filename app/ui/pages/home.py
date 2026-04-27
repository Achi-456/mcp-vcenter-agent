"""Summary page: vSphere-style layout with version card, gauges, issues, and health."""
from __future__ import annotations

import asyncio
from nicegui import ui

from app.ui.state import dashboard_snapshot


def render_home(state: dict) -> None:
    # Header with Refresh action. Data loads asynchronously off the event loop
    # so it never blocks websocket heartbeats.
    with ui.row().classes("items-center w-full").style("margin-bottom:10px"):
        ui.label("vCenter Summary").classes("text-h6")
        ui.space()
        refresh_btn = ui.button("Load / Refresh", icon="refresh").props("unelevated size=sm")

    body = ui.column().classes("w-full").style("gap:14px")

    async def _load() -> None:
        body.clear()
        with body:
            with ui.row().classes("items-center"):
                ui.spinner(size="sm")
                ui.label("Loading vCenter summary…").classes("text-grey-7")
        refresh_btn.props("loading")
        try:
            data = await asyncio.to_thread(dashboard_snapshot)
        except Exception as e:
            data = {"error": str(e)}
        refresh_btn.props(remove="loading")
        body.clear()
        if "error" in data and not data.get("summary"):
            with body:
                ui.label(f"Error: {data['error']}").classes("text-negative")
            return
        summary = data.get("summary") or {}
        hosts = data.get("hosts") or []
        datastores = data.get("datastores") or []
        alarms = data.get("alarms") or []
        vms = data.get("vms") or []
        with body:
            _render_body(summary, hosts, datastores, alarms, vms)

    refresh_btn.on("click", _load)

    # Render a placeholder immediately; user clicks Refresh to load.
    with body:
        with ui.element("div").classes("vc-card").style("width:100%;text-align:center;padding:40px"):
            ui.icon("cloud", size="48px").style("color:var(--primary);margin-bottom:8px")
            ui.label("vCenter Summary").classes("text-subtitle1")
            ui.label("Click 'Load / Refresh' to fetch the latest inventory, datastores, and alarms.").classes("text-grey-7 q-mt-sm")


def _render_body(summary: dict, hosts: list, datastores: list, alarms: list, vms: list) -> None:
    # ── Row 1: version + gauges ───────────────
    with ui.row().classes("no-wrap").style("gap:14px;width:100%"):
        # Version / build card
        with ui.element("div").classes("vc-card").style("flex:1;min-width:360px"):
            with ui.row().classes("no-wrap items-start").style("gap:14px"):
                ui.html(
                    '<div style="width:72px;height:72px;border-radius:6px;background:#e8eff7;display:flex;align-items:center;justify-content:center">'
                    '<span style="color:var(--primary);font-size:36px;font-weight:700">V</span></div>'
                )
                with ui.column().classes("q-gutter-none"):
                    ui.element("dl").classes("vc-kv").props("id=sum-ver").tooltip("")
                    _kv_table([
                        ("Version:", summary.get("vcenter_version", "-")),
                        ("Build:", summary.get("vcenter_build", "-")),
                        ("Last Updated:", summary.get("last_updated", "Unknown")),
                        ("Last File-Based Backup:", summary.get("last_backup", "Not scheduled")),
                    ])
                    ui.element("div").style("height:8px")
                    _kv_table([
                        ("Clusters:", str(summary.get("total_clusters", 0))),
                        ("Hosts:", str(summary.get("total_hosts", len(hosts)))),
                        ("Virtual Machines:", str(summary.get("total_vms", len(vms)))),
                    ])

        # Gauges card (CPU / Memory / Storage)
        with ui.element("div").classes("vc-card").style("flex:1;min-width:320px"):
            cpu_total, cpu_used = _aggregate(hosts, "cpu_mhz_total", "cpu_mhz_used")
            mem_total, mem_used = _aggregate(hosts, "memory_mb_total", "memory_mb_used")
            ds_total, ds_used = _ds_totals(datastores)
            _gauge("CPU", cpu_used, cpu_total, _fmt_hz)
            _gauge("Memory", mem_used, mem_total, _fmt_mb)
            _gauge("Storage", ds_used, ds_total, _fmt_gb)

    # ── Row 2: Issues panel (big) ─────────────
    red_alarms = [a for a in alarms if str(a.get("status", "")).lower() in ("red", "error")]
    if red_alarms:
        with ui.element("div").classes("vc-issues").style("width:100%"):
            for a in red_alarms[:5]:
                with ui.row().classes("row"):
                    ui.html('<span class="dot"></span>')
                    entity = a.get("entity", "")
                    alarm = a.get("alarm", "")
                    ui.label(f"{entity}: {alarm}").style("flex:1")
                    ui.html('<a href="javascript:void(0)">Acknowledge</a>')
                    ui.html('<a href="javascript:void(0)" style="margin-left:12px">Reset To Green</a>')
            if len(red_alarms) > 5:
                ui.html(f'<div style="padding-top:4px"><a href="javascript:void(0)">View all issues ({len(red_alarms)})</a></div>')

    # ── Row 3: Custom Attributes + Health Status ──
    with ui.row().classes("no-wrap").style("gap:14px;width:100%"):
        with ui.element("div").classes("vc-card").style("flex:1;min-width:360px"):
            ui.html('<div class="vc-card-title">Custom Attributes</div>')
            _kv_table([("Attribute", "Value"), ("com.vicm.snapshot", "")])
        with ui.element("div").classes("vc-card").style("flex:1;min-width:260px"):
            ui.html('<div class="vc-card-title">Health Status</div>')
            with ui.row().classes("items-center no-wrap"):
                ui.label("Overall Health").style("flex:1")
                ui.html('<span style="display:inline-flex;align-items:center;gap:6px;color:var(--ok);font-weight:600">'
                        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" fill="#1d7c4a"/>'
                        '<path d="M7 12l3.5 3.5L17 9" stroke="#fff" stroke-width="2" fill="none"/></svg>Good</span>')


# ───────────────── helpers ─────────────────

def _kv_table(rows: list[tuple[str, str]]) -> None:
    html = ['<dl class="vc-kv">']
    for k, v in rows:
        html.append(f"<dt>{_esc(k)}</dt><dd>{_esc(v)}</dd>")
    html.append("</dl>")
    ui.html("".join(html))


def _esc(s) -> str:
    s = "" if s is None else str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _gauge(label: str, used: float, total: float, fmt) -> None:
    pct = 0 if not total else max(0, min(100, used / total * 100))
    klass = "bar" + (" bad" if pct >= 90 else " warn" if pct >= 75 else "")
    free_txt = f"Free: {fmt(max(total - used, 0))}"
    cap_txt = f"Capacity: {fmt(total)}"
    ui.html(
        f'<div class="vc-gauge">'
        f'<div class="lbl"><span>{_esc(label)}</span><span>{free_txt}</span></div>'
        f'<div class="{klass}"><div class="fill" style="width:{pct:.0f}%"></div></div>'
        f'<div class="lbl"><span>Used: {fmt(used)}</span><span>{cap_txt}</span></div>'
        f'</div>'
    )


def _aggregate(hosts: list[dict], total_key: str, used_key: str) -> tuple[float, float]:
    tot = sum(float(h.get(total_key, 0) or 0) for h in hosts)
    used = sum(float(h.get(used_key, 0) or 0) for h in hosts)
    return tot, used


def _ds_totals(dss: list[dict]) -> tuple[float, float]:
    tot = sum(float(d.get("capacity_gb", 0) or 0) for d in dss)
    free = sum(float(d.get("free_gb", 0) or 0) for d in dss)
    return tot, max(tot - free, 0)


def _fmt_mb(v: float) -> str:
    if v <= 0:
        return "0 MB"
    if v >= 1024 * 1024:
        return f"{v / 1024 / 1024:.1f} TB"
    if v >= 1024:
        return f"{v / 1024:.1f} GB"
    return f"{v:.0f} MB"


def _fmt_gb(v: float) -> str:
    if v <= 0:
        return "0 GB"
    if v >= 1024:
        return f"{v / 1024:.1f} TB"
    return f"{v:.1f} GB"


def _fmt_hz(v: float) -> str:
    if v <= 0:
        return "0 GHz"
    if v >= 1000:
        return f"{v / 1000:.1f} GHz"
    return f"{v:.0f} MHz"
