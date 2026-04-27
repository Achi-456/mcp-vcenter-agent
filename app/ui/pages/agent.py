"""Agent page: in-process streaming from stream_agent_events (unused; NiceGUI UI not mounted)."""
from __future__ import annotations

import asyncio
import json
from nicegui import ui

from app.agent import engine
from app.agent.prompts import VCENTER_SYSTEM_WEB, build_system
from app.agent.config import destructive_web_env_allowed, get_max_tokens, get_max_turns
from app.agent.safety import needs_cli_confirmation
from app.llm.factory import get_provider


def render_agent(state: dict) -> None:
    history: list[dict] = []
    current_run: dict = {"streaming": False}

    with ui.row().classes("w-full q-gutter-md items-stretch").style("min-height:560px"):
        # ── Chat column ────────────────────────
        with ui.column().classes("col").style("flex:1;min-width:360px"):
            with ui.card().classes("w-full").style("min-height:560px;display:flex;flex-direction:column"):
                with ui.row().classes("items-center w-full"):
                    ui.label("Agent").classes("text-h6")
                    ui.space()
                    step_pill = ui.badge("Ready", color="grey").props("outline")
                msg_col = ui.column().classes("w-full q-pa-sm q-gutter-sm").style("overflow-y:auto;max-height:480px;flex:1")
                # Initial greeting
                _assistant_bubble(
                    msg_col,
                    "Hi — I'm your vCenter copilot. Try: *'Give me an environment overview'* or *'List the top 3 datastores by usage'*.",
                )

                with ui.row().classes("w-full items-end"):
                    user_in = ui.textarea(placeholder="Ask the copilot…").props("autogrow outlined").classes("col").style("max-height:160px")
                    send_btn = ui.button(icon="send").props("round color=primary")

                with ui.row().classes("q-gutter-xs q-mt-xs"):
                    for p in ("Environment overview", "Powered-off VMs", "Datastore health", "Active alarms", "Recent events"):
                        ui.button(p, on_click=lambda t=p: _set_and_send(user_in, t, _on_send)).props("flat dense")

        # ── Run log column ─────────────────────
        with ui.column().classes("col-4").style("min-width:320px"):
            with ui.card().classes("w-full").style("min-height:560px;display:flex;flex-direction:column"):
                ui.label("Run log").classes("text-subtitle1 text-weight-medium")
                run_col = ui.column().classes("w-full q-gutter-xs").style("overflow-y:auto;max-height:520px;flex:1")
                report_card = ui.column().classes("w-full")
                usage_row = ui.row().classes("text-caption text-grey-7 q-gutter-sm")

    async def _on_send() -> None:
        if current_run["streaming"]:
            return
        prompt = (user_in.value or "").strip()
        if not prompt:
            return
        user_in.value = ""
        history.append({"role": "user", "content": prompt})
        _user_bubble(msg_col, prompt)
        reply_container = _assistant_bubble(msg_col, "")
        reply_md = reply_container["md"]
        accumulated_text = {"value": ""}

        provider_id = state.get("provider") or "anthropic"
        model = state.get("model") or ""
        provider = get_provider(provider_id)
        if not provider.is_configured():
            reply_md.set_content(f"`{provider_id}` is not configured. Set `{provider.env_key}` in .env.")
            return
        if not model:
            model = provider.default_model

        current_run["streaming"] = True
        send_btn.props("loading")
        report_card.clear()
        run_col.clear()
        usage_row.clear()

        tool_chip_by_key: dict[str, dict] = {}

        def handle(ev: dict):
            t = ev.get("type")
            if t == "iteration":
                step_pill.text = f"Step {ev.get('n')}/{ev.get('max')}"
                step_pill.props("color=primary")
                with run_col:
                    ui.label(
                        f"Turn {ev.get('n')}/{ev.get('max')} — waiting for model…"
                    ).classes("text-caption text-grey-7")
            elif t == "busy":
                with run_col:
                    ui.label(f"… {ev.get('message') or ev.get('phase', 'Working…')}").classes(
                        "text-caption text-grey-7"
                    )
            elif t == "text":
                accumulated_text["value"] += ev.get("content", "")
                reply_md.set_content(accumulated_text["value"])
            elif t == "tool_call":
                key = f"{ev.get('tool')}:{id(ev)}"
                with run_col:
                    chip = ui.element("div").classes("tool-chip tool-chip--run w-full")
                    with chip:
                        with ui.row().classes("items-center q-gutter-xs"):
                            ui.spinner(size="14px")
                            ui.label(ev.get("tool", "?")).classes("text-weight-medium")
                        args_str = json.dumps(ev.get("args") or {}, default=str)[:200]
                        ui.label(args_str).classes("text-caption text-grey-7")
                tool_chip_by_key[key] = {"chip": chip, "args": ev.get("args")}
            elif t == "checkpoint":
                with run_col:
                    ck_parts = [str(ev.get("summary") or "")]
                    if ev.get("llm_note"):
                        ck_parts.append(str(ev["llm_note"]))
                    if ev.get("plan_steps_estimate") is not None:
                        ck_parts.append(f"plan ~{ev['plan_steps_estimate']} steps")
                    ui.label("[Checkpoint] " + " — ".join(p for p in ck_parts if p)).classes(
                        "text-caption text-grey-8"
                    )
            elif t == "tool_result":
                # Find the last 'run' chip and mark it done
                last = next(reversed(list(tool_chip_by_key.values())), None)
                if last and "chip" in last:
                    last["chip"].classes(remove="tool-chip--run")
                    last["chip"].classes("tool-chip")
                    # Append a preview + 'show' button inside the chip
                    with last["chip"]:
                        preview = str(ev.get("result", ""))[:240]
                        if ev.get("cached"):
                            preview = "(cached) " + preview
                        ui.label(preview).classes("text-caption text-grey-8")
                        full = ev.get("full") or ""
                        if full:
                            ui.button("Show full", on_click=lambda f=full, n=ev.get("tool"): _show_full(n, f)).props("flat dense")
            elif t == "report":
                report_card.clear()
                with report_card:
                    with ui.card().classes("report-card w-full q-mt-sm"):
                        ui.label("Report").classes("text-subtitle2 text-weight-medium")
                        ui.markdown(ev.get("text", ""))
            elif t == "planner":
                with run_col:
                    with ui.expansion("Auto plan", icon="checklist").classes("w-full"):
                        ui.markdown(ev.get("content", ""))
            elif t == "usage":
                with usage_row:
                    usage_row.clear()
                    ui.label(f"in {ev.get('input_tokens', 0)}  |  out {ev.get('output_tokens', 0)} tokens")
            elif t == "error":
                with run_col:
                    ui.label(ev.get("error", "error")).classes("text-negative")
            elif t == "reflection":
                with run_col:
                    used = ev.get("nudges_used")
                    max_n = ev.get("max_nudges")
                    badge = (
                        f" ({used}/{max_n})" if used is not None and max_n is not None else ""
                    )
                    ui.label(f"Reflection{badge}: {ev.get('nudge', '')}").classes("text-caption")
            elif t == "needs_human":
                with run_col:
                    ui.label(
                        f"Action needed: {ev.get('message', 'Operator input required.')}"
                    ).classes("text-warning text-weight-medium")
            elif t == "reviewer":
                with run_col:
                    with ui.expansion("Peer review", icon="rate_review").classes("w-full"):
                        ui.markdown(ev.get("text", ""))
            elif t == "done" and ev.get("full_text"):
                accumulated_text["value"] = ev.get("full_text", "") or accumulated_text["value"]
                reply_md.set_content(accumulated_text["value"])

        def _ng_cli_confirm(n: str, inp: dict) -> bool:
            if not needs_cli_confirmation(n, inp):
                return True
            return destructive_web_env_allowed()

        try:
            for ev in engine.stream_agent_events(
                provider,
                build_system(VCENTER_SYSTEM_WEB),
                [{"role": m["role"], "content": m["content"]} for m in history],
                model=model,
                max_tokens=get_max_tokens(),
                max_turns=get_max_turns(),
                on_reload_modules=False,
                cli_confirm=_ng_cli_confirm,
            ):
                handle(ev)
                await asyncio.sleep(0)
                if ev.get("type") == "done":
                    break
        except Exception as e:
            with run_col:
                ui.label(f"Engine error: {e}").classes("text-negative")

        history.append({"role": "assistant", "content": accumulated_text["value"]})
        current_run["streaming"] = False
        send_btn.props(remove="loading")
        step_pill.text = "Ready"
        step_pill.props("color=grey")

    def _show_full(name: str, full: str) -> None:
        d = ui.dialog()
        with d, ui.card().style("min-width:480px;max-width:820px"):
            with ui.row().classes("items-center w-full"):
                ui.label(name or "tool").classes("text-h6")
                ui.space()
                ui.button(icon="close", on_click=d.close).props("flat round dense")
            try:
                obj = json.loads(full)
                ui.json_editor({"content": {"json": obj}}).classes("w-full").style("min-height:280px")
            except Exception:
                ui.code(full).classes("w-full")
        d.open()

    send_btn.on("click", _on_send)
    user_in.on("keydown.enter", lambda e: (_should_send_on_enter(e) and asyncio.create_task(_on_send())))


def _user_bubble(col: ui.column, text: str) -> None:
    with col:
        with ui.card().classes("q-pa-sm").style("background:#e8f3ee;align-self:flex-end;max-width:80%"):
            ui.label("You").classes("text-caption text-grey-8")
            ui.label(text).classes("text-body2")


def _assistant_bubble(col: ui.column, text: str) -> dict:
    with col:
        card = ui.card().classes("q-pa-sm").style("background:#ffffff;max-width:90%")
        with card:
            ui.label("Assistant").classes("text-caption text-grey-7")
            md = ui.markdown(text or "…")
    return {"card": card, "md": md}


def _set_and_send(box, text: str, fn) -> None:
    box.value = text
    import asyncio
    asyncio.create_task(fn())


def _should_send_on_enter(e) -> bool:
    try:
        return not bool(getattr(e, "modifiers", {}).get("shift", False))
    except Exception:
        return True
