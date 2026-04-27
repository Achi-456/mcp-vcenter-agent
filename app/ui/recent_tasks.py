"""Bottom 'Recent Tasks / Alarms' strip styled like vSphere."""
from __future__ import annotations

from nicegui import ui

import app.tools.vcenter as vc


class RecentTasksBar:
    def __init__(self) -> None:
        self._container: ui.element | None = None
        self._tab = "tasks"
        self._render()

    def _render(self) -> None:
        with ui.element("div").classes("vc-tasks") as root:
            with ui.row().classes("hd no-wrap").style("margin:0"):
                ui.icon("expand_less").style("margin-right:4px")
                self._btn_tasks = ui.label("Recent Tasks").style("cursor:pointer")
                self._btn_alarms = ui.label("Alarms").style("cursor:pointer;color:var(--text3)")
                ui.space()
                ui.button(icon="refresh", on_click=self._async_refresh).props("flat round dense size=sm")
            self._body = ui.column().classes("w-full").style("padding:0;margin:0")
            self._container = root
            self._btn_tasks.on("click", lambda: self._switch("tasks"))
            self._btn_alarms.on("click", lambda: self._switch("alarms"))
        # Idle placeholder; user clicks refresh to load (blocking I/O runs via to_thread)
        with self._body:
            with ui.row().classes("items-center q-pa-sm"):
                ui.label("Click refresh to load recent tasks.").classes("text-caption text-grey-7")

    def _switch(self, which: str) -> None:
        self._tab = which
        self._btn_tasks.style(f"cursor:pointer;color:{'var(--text)' if which=='tasks' else 'var(--text3)'}")
        self._btn_alarms.style(f"cursor:pointer;color:{'var(--text)' if which=='alarms' else 'var(--text3)'}")
        self.refresh()

    def refresh(self) -> None:
        if self._body is None:
            return
        self._body.clear()
        with self._body:
            if self._tab == "tasks":
                self._render_tasks()
            else:
                self._render_alarms()

    async def _async_refresh(self) -> None:
        """Fetch tasks/alarms off-loop via asyncio.to_thread."""
        import asyncio
        if self._body is None:
            return
        self._body.clear()
        with self._body:
            with ui.row().classes("items-center q-pa-sm"):
                ui.spinner(size="sm")
                ui.label("Loading…").classes("text-grey-7")
        try:
            if self._tab == "tasks":
                data = await asyncio.to_thread(vc.get_recent_events, 20)
            else:
                data = await asyncio.to_thread(vc.get_active_alarms)
        except Exception as e:
            self._body.clear()
            with self._body:
                ui.label(f"Error: {e}").classes("text-negative q-pa-sm")
            return
        self._body.clear()
        with self._body:
            if self._tab == "tasks":
                self._render_tasks_rows(data or [])
            else:
                self._render_alarms_rows(data or [])

    def _render_tasks(self) -> None:
        try:
            events = vc.get_recent_events(20) or []
        except Exception as e:
            ui.label(f"Error: {e}").classes("text-negative q-pa-sm")
            return
        self._render_tasks_rows(events)

    def _render_tasks_rows(self, events: list[dict]) -> None:
        html = ['<table><thead><tr>',
                '<th>Task Name</th><th>Target</th><th>Status</th><th>Details</th><th>Initiator</th><th>Start Time</th>',
                '</tr></thead><tbody>']
        for e in events[:40]:
            ts = str(e.get("time") or "")[:19]
            status = str(e.get("status") or "completed")
            html.append(
                f"<tr><td>{_html_escape(e.get('event_type') or e.get('type') or 'event')}</td>"
                f"<td>{_html_escape(e.get('target') or e.get('vm') or '')}</td>"
                f"<td>{_html_escape(status)}</td>"
                f"<td>{_html_escape((e.get('message') or e.get('full_formatted_message') or '')[:120])}</td>"
                f"<td>{_html_escape(e.get('user') or '')}</td>"
                f"<td>{_html_escape(ts)}</td></tr>"
            )
        html.append("</tbody></table>")
        ui.html("".join(html))

    def _render_alarms(self) -> None:
        try:
            alarms = vc.get_active_alarms() or []
        except Exception as e:
            ui.label(f"Error: {e}").classes("text-negative q-pa-sm")
            return
        self._render_alarms_rows(alarms)

    def _render_alarms_rows(self, alarms: list[dict]) -> None:
        if not alarms:
            ui.label("No active alarms").classes("text-grey-7 q-pa-sm")
            return
        html = ['<table><thead><tr>',
                '<th>Alarm</th><th>Entity</th><th>Severity</th><th>Time</th>',
                '</tr></thead><tbody>']
        for a in alarms[:60]:
            sev = str(a.get("status") or "").lower()
            color = "#c92100" if sev in ("red", "error") else ("#ad7100" if sev in ("yellow", "warning") else "#737373")
            html.append(
                f"<tr><td>{_html_escape(a.get('alarm', ''))}</td>"
                f"<td>{_html_escape(a.get('entity', ''))}</td>"
                f"<td><span style='color:{color};font-weight:600'>{_html_escape(sev or '?')}</span></td>"
                f"<td>{_html_escape(str(a.get('time', ''))[:19])}</td></tr>"
            )
        html.append("</tbody></table>")
        ui.html("".join(html))


def _html_escape(s: str) -> str:
    return (str(s) if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
