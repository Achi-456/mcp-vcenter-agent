"""Models page: per-provider card + live model grid."""
from __future__ import annotations

from nicegui import ui, app as ng_app

from app.ui.state import provider_info, list_provider_models


def render_models(state: dict) -> None:
    with ui.row().classes("q-gutter-md wrap w-full items-start"):
        for prov in provider_info():
            _provider_card(prov, state)


def _provider_card(prov: dict, state: dict) -> None:
    with ui.card().style("min-width:360px;max-width:440px;flex:1"):
        with ui.row().classes("items-center"):
            ui.icon("memory").classes("text-primary")
            ui.label(prov["label"]).classes("text-subtitle1 text-weight-medium")
            ui.space()
            if prov["configured"]:
                ui.badge("configured", color="positive")
            else:
                ui.badge("no key", color="negative")
        ui.label(f"Default model: {prov['default_model']}").classes("text-caption text-grey-7")

        search = ui.input(placeholder="Filter models…").props("dense outlined clearable").classes("w-full q-mt-sm")

        grid = ui.aggrid(
            {
                "columnDefs": [
                    {"headerName": "Model", "field": "display", "filter": True, "sortable": True},
                    {"headerName": "ID", "field": "id", "filter": True, "sortable": True},
                ],
                "rowData": [],
                "rowSelection": "single",
                "pagination": True,
                "paginationPageSize": 10,
            }
        ).classes("w-full").style("height:280px")

        def _reload():
            rows = list_provider_models(prov["id"]) if prov["configured"] else []
            q = (search.value or "").lower()
            if q:
                rows = [r for r in rows if q in r.get("id", "").lower() or q in r.get("display", "").lower()]
            grid.options["rowData"] = rows
            grid.update()

        async def _set_default():
            sel = await grid.get_selected_row()
            if not sel:
                ui.notify("Pick a row first", type="warning")
                return
            state["provider"] = prov["id"]
            state["model"] = sel["id"]
            ng_app.storage.user["provider"] = prov["id"]
            ng_app.storage.user[f"model:{prov['id']}"] = sel["id"]
            ui.notify(f"Default set: {prov['label']} / {sel['display']}", type="positive")

        with ui.row().classes("q-gutter-sm q-mt-sm"):
            ui.button("Refresh", icon="refresh", on_click=_reload).props("flat")
            ui.button("Set as default", icon="check", on_click=_set_default).props("unelevated color=primary")

        search.on("update:model-value", lambda e: _reload())
        _reload()
