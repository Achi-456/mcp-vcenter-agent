"""vSphere-style app shell: top bar + inventory tree + tabs + tasks drawer."""
from __future__ import annotations

import asyncio

from nicegui import ui, app as ng_app

from app.ui.theme import apply_head, brand_colors
from app.ui.state import vcenter_status, provider_info, default_provider_id, list_provider_models
from app.ui.inventory_tree import InventoryPanel
from app.ui.recent_tasks import RecentTasksBar


CONTENT_TABS = [
    ("summary", "Summary"),
    ("vms", "VMs"),
    ("hosts", "Hosts & Clusters"),
    ("datastores", "Datastores"),
    ("networks", "Networks"),
    ("alarms", "Alarms"),
    ("agent", "AI Assistant"),
    ("models", "Models"),
    ("settings", "Settings"),
]


def _topbar(state: dict, inv_ref: dict) -> None:
    with ui.element("div").classes("vc-topbar"):
        with ui.row().classes("items-center no-wrap").style("width:100%;margin:0"):
            ui.icon("menu").style("margin-right:10px;cursor:pointer").on(
                "click", lambda: _toggle_inventory(inv_ref)
            )
            ui.html('<span class="vc-brand">vCenter <span class="accent">AI</span> Admin</span>')

            ui.space()

            # Search / command palette
            search_open = {"v": False}
            search_inp = ui.input(placeholder="Search inventory or actions (Ctrl+K)").classes(
                "vc-search"
            ).style("color:#fff")

            ui.space()

            # Connection badge
            vs = vcenter_status()
            dot_color = "#1d7c4a" if vs.connected else "#c92100"
            dot = ui.html(
                f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{dot_color};margin-right:6px"></span>'
                f'<span style="font-size:12px">{"Connected" if vs.connected else "Disconnected"}</span>'
            )

            # Provider select
            providers = provider_info()
            def _plabel(p):
                return p["label"] + ("" if p["configured"] else " (no key)")
            provider_opts = {p["id"]: _plabel(p) for p in providers}
            configured_ids = [p["id"] for p in providers if p["configured"]]
            default_id = default_provider_id()
            initial_prov = state.get("provider") or (default_id if default_id in configured_ids else (configured_ids[0] if configured_ids else default_id))
            state["provider"] = initial_prov

            prov_sel = ui.select(
                provider_opts,
                value=initial_prov,
            ).props("dense borderless dark options-dense").style(
                "min-width:150px;color:#fff;background:rgba(255,255,255,0.08);border-radius:3px;padding:2px 6px;margin-right:8px"
            )

            # Seed with preloaded models (from the async page handler) so no timer is needed
            preloaded_models = state.get("_preloaded_models") or []
            initial_opts = {m["id"]: m.get("display", m["id"]) for m in preloaded_models} or {"": "(no models)"}
            saved_model = ng_app.storage.user.get(f"model:{initial_prov}")
            default_model = next(iter(initial_opts.keys()), "")
            state["model"] = saved_model if saved_model in initial_opts else default_model
            model_sel = ui.select(
                initial_opts,
                value=state["model"],
            ).props("dense borderless dark options-dense").style(
                "min-width:200px;color:#fff;background:rgba(255,255,255,0.08);border-radius:3px;padding:2px 6px;margin-right:8px"
            )

            async def _load_models_async(provider_id: str) -> None:
                try:
                    models = await asyncio.to_thread(list_provider_models, provider_id)
                except Exception:
                    models = []
                opts = {m["id"]: m.get("display", m["id"]) for m in models} or {"": "(no models)"}
                model_sel.options = opts
                saved = ng_app.storage.user.get(f"model:{provider_id}")
                default_m = next(iter(opts.keys()), "")
                val = saved if saved in opts else default_m
                state["model"] = val
                model_sel.value = val
                try:
                    model_sel.update()
                except Exception:
                    pass

            def _on_prov_change(e):
                val = e.value if hasattr(e, "value") else e.args
                if isinstance(val, dict):
                    val = val.get("value")
                state["provider"] = val
                ng_app.storage.user["provider"] = val
                # Background task — does NOT capture a slot context
                asyncio.create_task(_load_models_async(val))

            def _on_model_change(e):
                val = e.value if hasattr(e, "value") else e.args
                if isinstance(val, dict):
                    val = val.get("value")
                state["model"] = val
                prov = state.get("provider") or ""
                ng_app.storage.user[f"model:{prov}"] = val

            prov_sel.on("update:model-value", _on_prov_change)
            model_sel.on("update:model-value", _on_model_change)

            dark = ui.dark_mode(value=ng_app.storage.user.get("dark", False))

            def _toggle_dark():
                dark.toggle()
                ng_app.storage.user["dark"] = bool(dark.value)

            ui.button(icon="dark_mode", on_click=_toggle_dark).props("flat round dense").tooltip("Toggle dark mode")
            ui.button(icon="help_outline", on_click=lambda: ui.notify("vCenter AI Admin — NiceGUI UI", type="info")).props("flat round dense")


def _toggle_inventory(inv_ref: dict) -> None:
    col = inv_ref.get("col")
    if not col:
        return
    inv_ref["visible"] = not inv_ref.get("visible", True)
    col.style("display:none" if not inv_ref["visible"] else "display:flex")


def build_app_shell(default_tab: str = "summary", preloaded: dict | None = None) -> None:
    brand_colors()
    apply_head()
    # Strip default NiceGUI padding/margins on page content to get a chrome-less desktop feel
    ui.query(".nicegui-content").classes("q-pa-none")
    ui.query("body").style("overflow:hidden")

    preloaded = preloaded or {}
    state: dict = {
        "provider": ng_app.storage.user.get("provider") or preloaded.get("provider"),
        "model": None,
        "selected": {"type": "vcenter", "name": ""},
        "_preloaded_models": preloaded.get("models") or [],
        "_preloaded_snapshot": preloaded.get("snapshot") or {},
    }
    if state["provider"]:
        state["model"] = ng_app.storage.user.get(f"model:{state['provider']}")

    inv_ref: dict = {"col": None, "visible": True}
    _topbar(state, inv_ref)

    # Full-bleed body: inventory | right pane. Right pane: tabs + content + tasks bar.
    with ui.row().classes("no-wrap").style("width:100%;height:calc(100vh - 44px);margin:0;gap:0"):
        # ── Inventory panel ─────────────────
        inv_col = ui.element("div").style("display:flex")
        inv_ref["col"] = inv_col
        with inv_col:
            panel = InventoryPanel(on_select=lambda prefix, name: _on_inventory_select(state, prefix, name))

        # ── Right pane (tabs + content + tasks) ───
        with ui.column().classes("col").style("min-width:0;flex:1;gap:0"):
            # Tabs bar (custom styling via our CSS)
            active_tab = {"key": default_tab}
            tabs_html = ui.element("div").classes("vc-tabs")
            tab_nodes: dict[str, ui.element] = {}
            with tabs_html:
                for key, label in CONTENT_TABS:
                    cls = "vc-tab" + (" active" if key == default_tab else "")
                    tab = ui.element("div").classes(cls)
                    with tab:
                        ui.label(label)
                    tab.on("click", lambda k=key: _switch_tab(k))
                    tab_nodes[key] = tab

            # Entity header
            ent_hd = ui.element("div").classes("vc-ent-hd")
            with ent_hd:
                ent_icon = ui.html('<div class="vc-ent-icon">V</div>')
                with ui.column().classes("q-gutter-none").style("margin-left:4px"):
                    ent_name = ui.label("vCenter").classes("vc-ent-name")
                    ent_sub = ui.label("").classes("vc-ent-sub")
                ui.space()
                ui.button("Actions", icon="more_horiz").props("outline size=sm")

            # Content container
            content = ui.column().classes("col").style(
                "overflow:auto;padding:14px;gap:14px;background:var(--bg);flex:1"
            )

            # Recent tasks bar (sticky bottom)
            tasks_bar = RecentTasksBar()

            def _switch_tab(key: str) -> None:
                active_tab["key"] = key
                for k, node in tab_nodes.items():
                    # remove both classes, then re-add what's appropriate
                    try:
                        node.classes(remove="active")
                    except Exception:
                        pass
                    if k == key:
                        node.classes(add="active")
                _render_tab_content(key, state, content, ent_name, ent_sub, ent_icon)

            # initial render
            _render_tab_content(default_tab, state, content, ent_name, ent_sub, ent_icon)

            state["_switch_tab"] = _switch_tab
            state["_tabs_bar_refresh"] = tasks_bar.refresh

    _install_command_palette(state)


def _on_inventory_select(state: dict, prefix: str, name: str) -> None:
    """Called when a tree node is clicked. Updates selection + re-renders."""
    state["selected"] = {"type": prefix or "vcenter", "name": name}
    # Jump to the most relevant tab
    jump = {
        "vm": "vms",
        "host": "hosts",
        "cluster": "hosts",
        "ds": "datastores",
        "net": "networks",
    }.get(prefix, "summary")
    fn = state.get("_switch_tab")
    if callable(fn):
        fn(jump)


def _render_tab_content(key: str, state: dict, container, ent_name, ent_sub, ent_icon) -> None:
    container.clear()
    # Update entity header based on selection
    sel = state.get("selected") or {"type": "vcenter", "name": ""}
    stype = sel.get("type") or "vcenter"
    sname = sel.get("name") or ""
    icon_letter = {"vm": "V", "host": "H", "cluster": "C", "ds": "D", "net": "N", "vcenter": "V"}.get(stype, "V")
    ent_icon.content = f'<div class="vc-ent-icon">{icon_letter}</div>'
    if stype == "vcenter":
        ent_name.set_text("vCenter")
        ent_sub.set_text("")
    else:
        ent_name.set_text(sname or stype)
        ent_sub.set_text(stype.upper())

    with container:
        if key == "summary":
            from app.ui.pages.home import render_home
            render_home(state)
        elif key == "vms":
            from app.ui.pages.inventory import render_vms_table
            render_vms_table(state)
        elif key == "hosts":
            from app.ui.pages.inventory import render_hosts
            render_hosts(state)
        elif key == "datastores":
            from app.ui.pages.inventory import render_datastores
            render_datastores(state)
        elif key == "networks":
            from app.ui.pages.inventory import render_networks
            render_networks(state)
        elif key == "alarms":
            from app.ui.pages.inventory import render_alarms
            render_alarms(state)
        elif key == "agent":
            from app.ui.pages.agent import render_agent
            render_agent(state)
        elif key == "models":
            from app.ui.pages.models import render_models
            render_models(state)
        elif key == "settings":
            from app.ui.pages.settings import render_settings
            render_settings(state)


def _install_command_palette(state: dict) -> None:
    palette = ui.dialog().props("position=top")
    with palette:
        with ui.card().style("min-width:480px;max-width:640px"):
            inp = ui.input(placeholder="Go to tab, switch provider, or run action…").props(
                "autofocus dense outlined"
            ).classes("w-full")
            results_container = ui.column().classes("w-full q-gutter-xs")
            switch_tab = state.get("_switch_tab")

            actions: list[tuple[str, callable]] = []
            for key, label in CONTENT_TABS:
                actions.append((f"Go to {label}", lambda k=key: (switch_tab(k) if switch_tab else None, palette.close())))
            actions.append(("Reload tools", _reload_tools_and_notify))

            def _refresh(q: str = ""):
                results_container.clear()
                ql = (q or "").lower().strip()
                hits = [a for a in actions if not ql or ql in a[0].lower()]
                with results_container:
                    for text, cb in hits[:10]:
                        ui.button(text, on_click=cb).props("flat align=left").classes("w-full")

            inp.on("update:model-value", lambda e: _refresh(e.args if isinstance(e.args, str) else getattr(e, "value", "")))
            _refresh("")

    ui.keyboard(on_key=lambda e: palette.open() if (e.action.keydown and e.modifiers.ctrl and e.key == "k") else None)


def _reload_tools_and_notify() -> None:
    from app.tools.combined import build_combined_tools, reload_all_tools

    try:
        reload_all_tools()
        tools, _ = build_combined_tools()
        ui.notify(f"Tools reloaded ({len(tools)})", type="positive")
    except Exception as e:
        ui.notify(f"Reload failed: {e}", type="negative")
