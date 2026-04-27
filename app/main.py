"""
vcenter_api_server.py
=====================
FastAPI REST API backend for the vCenter Web Dashboard.
Wraps vcenter_tools.py and also integrates Claude AI for natural-language commands.

Requirements:
    pip install fastapi uvicorn anthropic pyVmomi python-dotenv

Run:
    uvicorn vcenter_api_server:app --reload --port 8000

API Base URL: http://localhost:8000
Swagger Docs: http://localhost:8000/docs
"""

import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from dotenv import load_dotenv
import time
import logging

log = logging.getLogger(__name__)

# Thread pool for running sync agent engine without blocking the async event loop
_AGENT_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agent")

import app.tools.vcenter as vc
from app.tools.combined import build_combined_tools, reload_all_tools
from app.agent import engine
from app.agent.prompts import VCENTER_SYSTEM_WEB, build_system
from app.agent.config import (
    destructive_web_env_allowed,
    get_max_tokens,
    get_max_turns,
    minitask_llm_enabled,
    planner_enabled,
    reflection_enabled,
    reviewer_enabled,
    session_store_enabled,
    tool_cache_enabled,
)
from app.agent.session_store import (
    SessionRecord,
    _extract_key_findings,
    _extract_open_questions,
    get_store,
)
from app.agent.safety import needs_cli_confirmation
from app.llm.factory import (
    get_provider,
    list_configured_providers,
    PROVIDERS,
    clear_provider_cache,
)
from app.settings_llm import (
    ENV_AGENT_PROVIDER,
    ENV_ANTHROPIC,
    ENV_GOOGLE,
    ENV_MOONSHOT,
    ENV_MOONSHOT_BASE_URL,
    ENV_MOONSHOT_MODEL,
    ENV_OPENAI,
    ENV_XAI,
    apply_env_to_process,
    env_file_path,
    upsert_env_file,
)

load_dotenv()

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────

app = FastAPI(
    title="vCenter AI Admin API",
    description="REST API for VMware vCenter administration powered by Claude AI",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Auto-connect on startup
# ─────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    host = os.environ.get("VCENTER_HOST")
    user = os.environ.get("VCENTER_USER")
    pwd  = os.environ.get("VCENTER_PASSWORD")
    port = int(os.environ.get("VCENTER_PORT", 443))
    if host and user and pwd:
        result = vc.connect_vcenter(host, user, pwd, port)
        print(f"[Startup] {result}")


# ─────────────────────────────────────────────
# Request / Response Models
# ─────────────────────────────────────────────

class ConnectRequest(BaseModel):
    host: str
    user: str
    password: str
    port: int = 443

class SnapshotRequest(BaseModel):
    snapshot_name: str
    description: str = ""
    memory: bool = False

class CloneRequest(BaseModel):
    clone_name: str
    datastore_name: Optional[str] = None

class AICommandRequest(BaseModel):
    message: str
    history: list = []
    provider: Optional[str] = None
    model: Optional[str] = None
    # When true, high-risk vCenter / govc tool calls are allowed in one request (use with care).
    confirm_destructive: bool = False
    # Session persistence — supply a stable UUID to enable cross-restart context.
    session_id: Optional[str] = None
    resume_session: bool = False   # inject prior session summary when True + session_id set

class PowerOffRequest(BaseModel):
    force: bool = False

class CreateVMRequest(BaseModel):
    vm_name: str
    cpu: int = 2
    memory_mb: int = 2048
    datastore_name: Optional[str] = None


class LLMSettingsBody(BaseModel):
    """Omit a field to leave it unchanged; set a field to null to clear that entry in `.env`."""

    model_config = ConfigDict(extra="forbid")

    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    xai_api_key: Optional[str] = None
    moonshot_api_key: Optional[str] = None
    moonshot_base_url: Optional[str] = None
    moonshot_model: Optional[str] = None
    agent_provider: Optional[str] = None


_LLM_FIELD_ENV: dict[str, str] = {
    "anthropic_api_key": ENV_ANTHROPIC,
    "openai_api_key": ENV_OPENAI,
    "google_api_key": ENV_GOOGLE,
    "xai_api_key": ENV_XAI,
    "moonshot_api_key": ENV_MOONSHOT,
    "moonshot_base_url": ENV_MOONSHOT_BASE_URL,
    "moonshot_model": ENV_MOONSHOT_MODEL,
    "agent_provider": ENV_AGENT_PROVIDER,
}


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────

def _ok(data: Any) -> dict:
    return {"status": "ok", "data": data}

def _err(msg: str, code: int = 400):
    raise HTTPException(status_code=code, detail=msg)


# ─────────────────────────────────────────────
# Connection Endpoints
# ─────────────────────────────────────────────

@app.post("/api/connect", tags=["Connection"])
def connect(req: ConnectRequest):
    result = vc.connect_vcenter(req.host, req.user, req.password, req.port)
    if "❌" in result:
        _err(result, 503)
    return _ok(result)

@app.post("/api/disconnect", tags=["Connection"])
def disconnect():
    return _ok(vc.disconnect())

@app.get("/api/status", tags=["Connection"])
def status():
    connected = vc._conn.is_connected()
    return _ok({"connected": connected})


# ─────────────────────────────────────────────
# Overview / Summary
# ─────────────────────────────────────────────

@app.get("/api/overview", tags=["Overview"])
def overview():
    return _ok(vc.get_vcenter_info())

@app.get("/api/dashboard", tags=["Overview"])
def dashboard():
    """Single call to fetch everything needed for the dashboard."""
    return _ok({
        "summary":    vc.get_vcenter_info(),
        "vms":        vc.list_vms(),
        "hosts":      vc.list_hosts(),
        "datastores": vc.list_datastores(),
        "clusters":   vc.list_clusters(),
        "alarms":     vc.get_active_alarms(),
        "events":     vc.get_recent_events(10),
    })


# ─────────────────────────────────────────────
# VM Endpoints
# ─────────────────────────────────────────────

@app.get("/api/vms", tags=["VMs"])
def list_vms(state: str = "all"):
    return _ok(vc.list_vms(state))

@app.get("/api/vms/{vm_name}", tags=["VMs"])
def get_vm(vm_name: str):
    result = vc.get_vm_details(vm_name)
    if "error" in result:
        _err(result["error"], 404)
    return _ok(result)

@app.post("/api/vms/{vm_name}/power-on", tags=["VMs"])
def power_on(vm_name: str):
    result = vc.power_on_vm(vm_name)
    if "error" in result:
        _err(result["error"])
    return _ok(result)

@app.post("/api/vms/{vm_name}/power-off", tags=["VMs"])
def power_off(vm_name: str, req: PowerOffRequest = PowerOffRequest()):
    result = vc.power_off_vm(vm_name, req.force)
    if "error" in result:
        _err(result["error"])
    return _ok(result)

@app.post("/api/vms/{vm_name}/reset", tags=["VMs"])
def reset_vm(vm_name: str):
    result = vc.reset_vm(vm_name)
    if "error" in result:
        _err(result["error"])
    return _ok(result)

@app.post("/api/vms/{vm_name}/suspend", tags=["VMs"])
def suspend_vm(vm_name: str):
    result = vc.suspend_vm(vm_name)
    if "error" in result:
        _err(result["error"])
    return _ok(result)

@app.post("/api/vms/{vm_name}/reboot-guest", tags=["VMs"])
def reboot_guest(vm_name: str):
    result = vc.reboot_guest(vm_name)
    if "error" in result:
        _err(result["error"])
    return _ok(result)

@app.post("/api/vms/{vm_name}/clone", tags=["VMs"])
def clone_vm(vm_name: str, req: CloneRequest):
    result = vc.clone_vm(vm_name, req.clone_name, req.datastore_name)
    if "error" in result:
        _err(result["error"])
    return _ok(result)

@app.delete("/api/vms/{vm_name}", tags=["VMs"])
def delete_vm(vm_name: str):
    result = vc.delete_vm(vm_name)
    if "error" in result:
        _err(result["error"])
    return _ok(result)

@app.get("/api/vms/{vm_name}/stats", tags=["VMs"])
def get_vm_stats(vm_name: str):
    result = vc.get_vm_stats(vm_name)
    if "error" in result:
        _err(result["error"], 404)
    return _ok(result)

@app.post("/api/vms", tags=["VMs"])
def create_vm(req: CreateVMRequest):
    result = vc.create_vm(req.vm_name, req.cpu, req.memory_mb, req.datastore_name)
    if "error" in result:
        _err(result["error"])
    return _ok(result)


# ─────────────────────────────────────────────
# Snapshot Endpoints
# ─────────────────────────────────────────────

@app.get("/api/vms/{vm_name}/snapshots", tags=["Snapshots"])
def list_snapshots(vm_name: str):
    return _ok(vc.list_snapshots(vm_name))

@app.post("/api/vms/{vm_name}/snapshots", tags=["Snapshots"])
def create_snapshot(vm_name: str, req: SnapshotRequest):
    result = vc.create_snapshot(vm_name, req.snapshot_name, req.description, req.memory)
    if "error" in result:
        _err(result["error"])
    return _ok(result)

@app.post("/api/vms/{vm_name}/snapshots/{snap_name}/revert", tags=["Snapshots"])
def revert_snapshot(vm_name: str, snap_name: str):
    result = vc.revert_to_snapshot(vm_name, snap_name)
    if "error" in result:
        _err(result["error"])
    return _ok(result)

@app.delete("/api/vms/{vm_name}/snapshots/{snap_name}", tags=["Snapshots"])
def delete_snapshot(vm_name: str, snap_name: str, remove_children: bool = False):
    result = vc.delete_snapshot(vm_name, snap_name, remove_children)
    if "error" in result:
        _err(result["error"])
    return _ok(result)


# ─────────────────────────────────────────────
# Host Endpoints
# ─────────────────────────────────────────────

@app.get("/api/hosts", tags=["Hosts"])
def list_hosts():
    return _ok(vc.list_hosts())

@app.get("/api/hosts/{host_name}", tags=["Hosts"])
def get_host(host_name: str):
    result = vc.get_host_details(host_name)
    if "error" in result:
        _err(result["error"], 404)
    return _ok(result)

@app.post("/api/hosts/{host_name}/maintenance/enter", tags=["Hosts"])
def enter_maintenance(host_name: str):
    result = vc.enter_maintenance_mode(host_name)
    if "error" in result:
        _err(result["error"])
    return _ok(result)

@app.post("/api/hosts/{host_name}/maintenance/exit", tags=["Hosts"])
def exit_maintenance(host_name: str):
    result = vc.exit_maintenance_mode(host_name)
    if "error" in result:
        _err(result["error"])
    return _ok(result)


# ─────────────────────────────────────────────
# Infrastructure Endpoints
# ─────────────────────────────────────────────

@app.get("/api/datastores", tags=["Infrastructure"])
def list_datastores():
    return _ok(vc.list_datastores())

@app.get("/api/clusters", tags=["Infrastructure"])
def list_clusters():
    return _ok(vc.list_clusters())

@app.get("/api/resource-pools", tags=["Infrastructure"])
def list_resource_pools():
    return _ok(vc.list_resource_pools())

@app.get("/api/networks", tags=["Infrastructure"])
def list_networks():
    return _ok(vc.list_networks())


# ─────────────────────────────────────────────
# Dynamic Tools 
# ─────────────────────────────────────────────

@app.post("/api/tools/reload", tags=["Tools"])
def reload_tools():
    try:
        reload_all_tools()
        tools, _ = build_combined_tools()
        return _ok(
            {
                "message": "Tools reloaded successfully (vcenter + govc + web search)",
                "tool_count": len(tools),
            }
        )
    except Exception as e:
        _err(str(e))


# ─────────────────────────────────────────────
# Events & Alarms
# ─────────────────────────────────────────────

@app.get("/api/events", tags=["Events"])
def get_events(max_events: int = 20):
    return _ok(vc.get_recent_events(max_events))

@app.get("/api/alarms", tags=["Events"])
def get_alarms():
    return _ok(vc.get_active_alarms())


# ─────────────────────────────────────────────
# LLM Providers & Models
# ─────────────────────────────────────────────

_MODELS_CACHE: dict[str, tuple[float, list[dict]]] = {}
_MODELS_TTL_SEC = 300


def _default_provider_id() -> str:
    want = (os.environ.get("AGENT_PROVIDER") or "anthropic").strip().lower()
    if any(p["id"] == want for p in PROVIDERS):
        return want
    return "anthropic"


@app.get("/api/llm/providers", tags=["LLM"])
def list_providers():
    return _ok({
        "default": _default_provider_id(),
        "providers": list_configured_providers(),
    })


@app.get("/api/llm/models", tags=["LLM"])
def list_models(provider: str):
    try:
        inst = get_provider(provider)
    except ValueError:
        _err(f"Unknown provider: {provider}", 404)
    now = time.monotonic()
    cached = _MODELS_CACHE.get(provider)
    if cached and (now - cached[0]) < _MODELS_TTL_SEC:
        return _ok({"provider": provider, "default": inst.default_model, "models": cached[1]})
    try:
        models = inst.list_models()
    except Exception as e:
        _err(f"Failed to list models for {provider}: {e}", 502)
    _MODELS_CACHE[provider] = (now, models)
    return _ok({"provider": provider, "default": inst.default_model, "models": models})


@app.get("/api/settings/llm", tags=["Settings"])
def get_llm_settings():
    """Return which LLM keys are set (never return secret values)."""

    def has(k: str) -> bool:
        return bool(os.environ.get(k, "").strip())

    return _ok(
        {
            "requires_token": bool(os.environ.get("LLM_SETTINGS_TOKEN", "").strip()),
            "keys_present": {
                "anthropic": has(ENV_ANTHROPIC),
                "openai": has(ENV_OPENAI),
                "gemini": has(ENV_GOOGLE),
                "grok": has(ENV_XAI),
                "kimi": has(ENV_MOONSHOT),
            },
            "moonshot_base_url": os.environ.get(ENV_MOONSHOT_BASE_URL, "").strip()
            or None,
            "moonshot_model": os.environ.get(ENV_MOONSHOT_MODEL, "").strip() or None,
            "agent_provider": os.environ.get(ENV_AGENT_PROVIDER, "").strip() or None,
        }
    )


@app.post("/api/settings/llm", tags=["Settings"])
def post_llm_settings(request: Request, body: LLMSettingsBody):
    """
    Write LLM-related keys to the project `.env`, update `os.environ`, and clear the LLM client cache.
    If `LLM_SETTINGS_TOKEN` is set in the environment, require header `X-LLM-Settings-Token` with the same value.
    """
    gate = os.environ.get("LLM_SETTINGS_TOKEN", "").strip()
    if gate:
        hdr = (request.headers.get("X-LLM-Settings-Token") or "").strip()
        if hdr != gate:
            _err("Invalid or missing X-LLM-Settings-Token", 403)

    raw = body.model_dump(exclude_unset=True)
    env_updates: dict[str, str | None] = {}
    for field, env_key in _LLM_FIELD_ENV.items():
        if field not in raw:
            continue
        v = raw[field]
        if v is None:
            env_updates[env_key] = None
        elif isinstance(v, str):
            s = v.strip()
            env_updates[env_key] = s if s else None
        else:
            env_updates[env_key] = None

    if ENV_AGENT_PROVIDER in env_updates and env_updates[ENV_AGENT_PROVIDER]:
        ap = env_updates[ENV_AGENT_PROVIDER].strip().lower()
        if not any(p["id"] == ap for p in PROVIDERS):
            _err(f"Unknown agent_provider: {ap}")
        env_updates[ENV_AGENT_PROVIDER] = ap

    if not env_updates:
        return _ok({"updated": False, "message": "No fields to update"})

    try:
        upsert_env_file(env_file_path(), env_updates)
    except ValueError as e:
        _err(str(e))
    except OSError as e:
        _err(f"Failed to write .env: {e}", 500)

    apply_env_to_process(env_updates)
    clear_provider_cache()
    _MODELS_CACHE.clear()
    return _ok({"updated": True, "keys": list(env_updates.keys())})


# ─────────────────────────────────────────────
# AI agent config (for dashboard turn limit and feature flags)
# ─────────────────────────────────────────────

@app.get("/api/ai/agent-config", tags=["AI"])
def ai_agent_config():
    return _ok(
        {
            "max_turns": get_max_turns(),
            "max_tokens": get_max_tokens(),
            "planner": planner_enabled(),
            "reflection": reflection_enabled(),
            "reviewer": reviewer_enabled(),
            "tool_cache": tool_cache_enabled(),
            "minitask_llm": minitask_llm_enabled(),
        }
    )


# ─────────────────────────────────────────────
# AI Chat Endpoint (Streaming)
# ─────────────────────────────────────────────

@app.post("/api/ai/chat", tags=["AI"])
async def ai_chat_stream(req: AICommandRequest):
    """Stream AI responses via Server-Sent Events (multi-provider, multi-turn, govc, web search)."""
    provider_id = (req.provider or _default_provider_id()).strip().lower()
    try:
        provider = get_provider(provider_id)
    except ValueError:
        async def _bad():
            yield f"data: {json.dumps({'type':'error','error':f'Unknown provider: {provider_id}'})}\n\n"
            yield f"data: {json.dumps({'type':'done','summary':''})}\n\n"
        return StreamingResponse(_bad(), media_type="text/event-stream")

    if not provider.is_configured():
        async def _noauth():
            msg = (
                f"{provider_id} is not configured. Set {provider.env_key} "
                "(dashboard: LLM API keys / .env)."
            )
            yield f"data: {json.dumps({'type':'error','error': msg})}\n\n"
            yield f"data: {json.dumps({'type':'done','summary':''})}\n\n"
        return StreamingResponse(_noauth(), media_type="text/event-stream")

    model = (req.model or os.environ.get("AGENT_MODEL") or provider.default_model).strip()

    async def generate():
        messages = list(req.history) + [{"role": "user", "content": req.message}]

        # Inject prior session context when resuming.
        if req.resume_session and req.session_id and session_store_enabled():
            try:
                prior = get_store().load(req.session_id)
                if prior and prior.full_summary:
                    messages.insert(0, {
                        "role": "user",
                        "content": f"[Previous session context]\n{prior.full_summary}",
                    })
                    log.info("session resumed: %s", req.session_id)
            except Exception as exc:
                log.warning("session resume failed for %s: %s", req.session_id, exc)

        def web_cli_confirm(name: str, tool_input: dict) -> bool:
            if not needs_cli_confirmation(name, tool_input):
                return True
            if req.confirm_destructive or destructive_web_env_allowed():
                return True
            return False

        loop = asyncio.get_event_loop()
        # asyncio.Queue bridges the sync generator thread → async SSE stream
        queue: asyncio.Queue = asyncio.Queue(maxsize=256)
        _SENTINEL = object()  # signals producer is done

        def _producer():
            """Runs in thread pool — calls the synchronous agent engine."""
            try:
                for ev in engine.stream_agent_events(
                    provider,
                    build_system(VCENTER_SYSTEM_WEB),
                    messages,
                    model=model,
                    max_tokens=get_max_tokens(),
                    max_turns=get_max_turns(),
                    on_reload_modules=False,
                    cli_confirm=web_cli_confirm,
                ):
                    loop.call_soon_threadsafe(queue.put_nowait, ev)
            except Exception as exc:
                log.exception("Agent engine error: %s", exc)
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"type": "error", "error": f"{type(exc).__name__}: {exc}"},
                )
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, _SENTINEL)

        # Start the producer in the background thread pool
        loop.run_in_executor(_AGENT_EXECUTOR, _producer)

        # Drain the queue and yield SSE lines; capture done event for session save.
        while True:
            try:
                ev = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                log.warning("agent SSE: 120 s queue timeout — forcing done")
                yield f"data: {json.dumps({'type': 'error', 'error': 'Agent timed out (120 s with no event)'})}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'summary': ''})}\n\n"
                break
            if ev is _SENTINEL:
                break
            # Persist session summary when a session_id was supplied.
            if ev.get("type") == "done" and req.session_id and session_store_enabled():
                try:
                    full_summary = ev.get("full_text") or ev.get("summary") or ""
                    record = SessionRecord(
                        session_id=req.session_id,
                        vcenter_host=os.environ.get("VCENTER_HOST", ""),
                        objective=req.message[:500],
                        key_findings=_extract_key_findings(full_summary),
                        open_questions=_extract_open_questions(full_summary),
                        full_summary=full_summary,
                    )
                    get_store().save(record)
                except Exception as exc:
                    log.warning("session save failed for %s: %s", req.session_id, exc)
            yield f"data: {json.dumps(ev, default=str)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
