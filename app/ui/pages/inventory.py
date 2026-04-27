"""Inventory tab renderers used by the new vSphere-style layout."""
from __future__ import annotations

from nicegui import ui

import app.tools.vcenter as vc


# ───────────────── VMs ─────────────────

def render_vms_table(state: dict) -> None:
    sel = state.get("selected") or {}
    focus_vm = sel.get("name") if sel.get("type") == "vm" else None

    with ui.row().classes("no-wrap items-center").style("gap:8px;width:100%"):
        search = ui.input(placeholder="Search VMs…").props("dense outlined clearable").style("min-width:280px")
        power_filter = ui.select(
            {"all": "All", "poweredOn": "Powered On", "poweredOff": "Powered Off", "suspended": "Suspended"},
            value="all",
        ).props("dense outlined").style("min-width:160px")
        ui.space()
        ui.button("Refresh", icon="refresh", on_click=lambda: _load()).props("flat size=sm")

    grid = ui.aggrid(
        {
            "columnDefs": [
                {"headerName": "Name", "field": "name", "filter": True, "sortable": True, "checkboxSelection": True, "flex": 2},
                {"headerName": "Power", "field": "power_state", "width": 130, "sortable": True, "filter": True},
                {"headerName": "CPU", "field": "cpu", "width": 80},
                {"headerName": "RAM (MB)", "field": "memory_mb", "width": 110},
                {"headerName": "OS", "field": "guest_os", "filter": True, "flex": 1},
                {"headerName": "IP", "field": "ip_address", "filter": True, "flex": 1},
            ],
            "rowData": [],
            "rowSelection": "single",
            "pagination": True,
            "paginationPageSize": 25,
            "animateRows": True,
            "suppressCellFocus": True,
        }
    ).classes("w-full").style("height:440px")

    def _load():
        q = (search.value or "").lower().strip()
        ps = power_filter.value or "all"
        try:
            rows = vc.list_vms(ps)
        except Exception as e:
            ui.notify(f"Error: {e}", type="negative")
            return
        if focus_vm:
            rows = [r for r in rows if (r.get("name") or "") == focus_vm] or rows
        if q:
            rows = [r for r in rows if q in (r.get("name") or "").lower() or q in (r.get("ip_address") or "").lower()]
        grid.options["rowData"] = rows
        grid.update()

    search.on("update:model-value", lambda e: _load())
    power_filter.on("update:model-value", lambda e: _load())

    def _open_details(name: str) -> None:
        try:
            details = vc.get_vm_details(name)
        except Exception as e:
            ui.notify(f"Error: {e}", type="negative")
            return
        d = ui.dialog().props("position=right")
        with d, ui.card().style("min-width:460px;max-width:680px"):
            with ui.row().classes("items-center w-full"):
                ui.label(name).classes("text-h6")
                ui.space()
                ui.button(icon="close", on_click=d.close).props("flat round dense")
            if "error" in details:
                ui.label(details["error"]).classes("text-negative")
            else:
                for k, v in details.items():
                    if isinstance(v, (dict, list)):
                        with ui.expansion(str(k)).classes("w-full"):
                            ui.json_editor({"content": {"json": v}}).classes("w-full").style("min-height:120px")
                    else:
                        with ui.row().classes("q-gutter-sm"):
                            ui.label(str(k)).classes("text-grey-7").style("min-width:150px")
                            ui.label(str(v)).classes("text-body2")
                with ui.row().classes("q-gutter-sm q-mt-sm"):
                    ui.button("Power On", icon="play_arrow", on_click=lambda: _safe(lambda: vc.power_on_vm(name), f"Powered on {name}")).props("unelevated color=positive size=sm")
                    ui.button("Power Off", icon="stop", on_click=lambda: _confirm_then(f"Power off {name}?", lambda: vc.power_off_vm(name))).props("size=sm")
                    ui.button("Reset", icon="restart_alt", on_click=lambda: _confirm_then(f"Reset {name}?", lambda: vc.reset_vm(name))).props("size=sm")
        d.open()

    grid.on("rowDoubleClicked", lambda e: _open_details((e.args or {}).get("data", {}).get("name", "")))
    _load()


# ───────────────── Hosts ─────────────────

def render_hosts(state: dict) -> None:
    sel = state.get("selected") or {}
    focus_host = sel.get("name") if sel.get("type") == "host" else None

    try:
        hosts = vc.list_hosts() or []
    except Exception as e:
        ui.label(f"Error: {e}").classes("text-negative")
        return
    if focus_host:
        hosts = [h for h in hosts if h.get("name") == focus_host] or hosts

    if not hosts:
        ui.label("No hosts").classes("text-grey-7")
        return

    with ui.row().classes("no-wrap wrap").style("gap:14px"):
        for h in hosts:
            state_txt = str(h.get("connection_state") or h.get("state") or "?")
            ok = state_txt.lower() == "connected"
            with ui.element("div").classes("vc-card").style("min-width:320px;max-width:360px"):
                with ui.row().classes("items-center no-wrap"):
                    ui.icon("dns", size="20px").style("color:var(--primary)")
                    ui.label(h.get("name", "host")).classes("text-subtitle1 text-weight-medium")
                    ui.space()
                    ui.html(f'<span style="color:{"var(--ok)" if ok else "var(--bad)"};font-size:11px;font-weight:600">{_esc(state_txt)}</span>')
                ui.html('<div style="height:1px;background:var(--border);margin:8px 0"></div>')
                _kv([
                    ("CPU Model", h.get("cpu_model", "")),
                    ("Cores", h.get("cores", "?")),
                    ("Memory", f"{h.get('memory_gb', '?')} GB"),
                    ("Version", h.get("version", "?")),
                    ("Maintenance", "yes" if h.get("in_maintenance") else "no"),
                ])
                with ui.row().classes("q-gutter-sm q-mt-sm"):
                    hn = h.get("name") or ""
                    ui.button("Enter MM", icon="pause", on_click=lambda n=hn: _safe(lambda: vc.enter_maintenance_mode(n), f"{n} entering maintenance")).props("flat size=sm")
                    ui.button("Exit MM", icon="play_arrow", on_click=lambda n=hn: _safe(lambda: vc.exit_maintenance_mode(n), f"{n} exited maintenance")).props("flat size=sm")


# ───────────────── Datastores ─────────────────

def render_datastores(state: dict) -> None:
    sel = state.get("selected") or {}
    focus_ds = sel.get("name") if sel.get("type") == "ds" else None
    try:
        dss = vc.list_datastores() or []
    except Exception as e:
        ui.label(f"Error: {e}").classes("text-negative")
        return
    if focus_ds:
        dss = [d for d in dss if d.get("name") == focus_ds] or dss

    with ui.row().classes("no-wrap wrap").style("gap:14px"):
        for d in dss:
            cap = float(d.get("capacity_gb", 0) or 0)
            free = float(d.get("free_gb", 0) or 0)
            used = max(cap - free, 0)
            pct = int(used / cap * 100) if cap else 0
            color = "var(--bad)" if pct >= 90 else ("var(--warn)" if pct >= 75 else "var(--ok)")
            with ui.element("div").classes("vc-card").style("min-width:280px;max-width:340px"):
                ui.label(d.get("name", "datastore")).classes("text-subtitle1 text-weight-medium")
                ui.label(f"{d.get('type', '?')}  ·  {int(cap)} GB").classes("text-caption text-grey-7")
                ui.html(
                    f'<div class="vc-gauge" style="margin-top:8px">'
                    f'<div class="lbl"><span>Used</span><span style="color:{color};font-weight:600">{pct}%</span></div>'
                    f'<div class="bar"><div class="fill" style="width:{pct}%;background:{color}"></div></div>'
                    f'<div class="lbl"><span>Free: {int(free)} GB</span><span>Capacity: {int(cap)} GB</span></div>'
                    f'</div>'
                )


# ───────────────── Networks ─────────────────

def render_networks(state: dict) -> None:
    try:
        nets = vc.list_networks() or []
    except Exception as e:
        ui.label(f"Error: {e}").classes("text-negative")
        return
    with ui.row().classes("no-wrap wrap").style("gap:14px"):
        for n in nets:
            with ui.element("div").classes("vc-card").style("min-width:240px"):
                with ui.row().classes("items-center"):
                    ui.icon("lan").style("color:var(--primary)")
                    ui.label(n.get("name", "?")).classes("text-subtitle1")
                ui.label(str(n.get("type", ""))).classes("text-caption text-grey-7")


# ───────────────── Alarms ─────────────────

def render_alarms(state: dict) -> None:
    try:
        alarms = vc.get_active_alarms() or []
    except Exception as e:
        ui.label(f"Error: {e}").classes("text-negative")
        return
    if not alarms:
        ui.label("No active alarms").classes("text-grey-7")
        return
    red = [a for a in alarms if str(a.get("status", "")).lower() in ("red", "error")]
    yellow = [a for a in alarms if str(a.get("status", "")).lower() in ("yellow", "warning")]
    with ui.element("div").classes("vc-card").style("width:100%"):
        ui.html(f'<div class="vc-card-title">Active alarms ({len(alarms)})</div>')
        html = ['<table style="width:100%;font-size:13px;border-collapse:collapse"><thead>',
                '<tr><th align="left" style="padding:6px 10px;border-bottom:1px solid var(--border);color:var(--text3)">Severity</th>',
                '<th align="left" style="padding:6px 10px;border-bottom:1px solid var(--border);color:var(--text3)">Alarm</th>',
                '<th align="left" style="padding:6px 10px;border-bottom:1px solid var(--border);color:var(--text3)">Entity</th>',
                '<th align="left" style="padding:6px 10px;border-bottom:1px solid var(--border);color:var(--text3)">Time</th>',
                '</tr></thead><tbody>']
        for a in (red + yellow):
            sev = str(a.get("status", "")).lower()
            color = "var(--bad)" if sev in ("red", "error") else "var(--warn)"
            html.append(
                f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'><span style='color:{color};font-weight:600'>{_esc(sev.upper())}</span></td>"
                f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{_esc(a.get('alarm', ''))}</td>"
                f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{_esc(a.get('entity', ''))}</td>"
                f"<td style='padding:6px 10px;border-bottom:1px solid #eee'>{_esc(str(a.get('time', ''))[:19])}</td></tr>"
            )
        html.append("</tbody></table>")
        ui.html("".join(html))


# ───────────────── utils ─────────────────

def _kv(rows):
    html = ['<dl class="vc-kv">']
    for k, v in rows:
        html.append(f"<dt>{_esc(k)}</dt><dd>{_esc(v)}</dd>")
    html.append("</dl>")
    ui.html("".join(html))


def _esc(s) -> str:
    s = "" if s is None else str(s)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _safe(fn, success_msg: str) -> None:
    try:
        result = fn()
        if isinstance(result, dict) and "error" in result:
            ui.notify(f"Error: {result['error']}", type="negative")
        else:
            ui.notify(success_msg, type="positive")
    except Exception as e:
        ui.notify(f"Error: {e}", type="negative")


def _confirm_then(text: str, fn) -> None:
    d = ui.dialog()
    with d, ui.card():
        ui.label(text).classes("text-body1")
        with ui.row().classes("q-gutter-sm q-mt-sm"):
            ui.button("Cancel", on_click=d.close).props("flat")
            def _go():
                d.close()
                _safe(fn, "Done")
            ui.button("Confirm", on_click=_go).props("unelevated color=negative")
    d.open()
