import json
import uuid
from typing import Any, AsyncIterator

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse

from app.clients.backend_client import backend_health
from app.graph.events import event_payload, sse
from app.graph.workflow import get_graph
from app.schemas.run import RunRequest


app = FastAPI(title="vCenter Agent Engine", version="0.3.0-langgraph")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> JSONResponse:
    backend_ok = await backend_health()
    return JSONResponse(
        {
            "status": "ready" if backend_ok else "degraded",
            "engine": "ok",
            "langgraph": "ok",
            "backend": "ok" if backend_ok else "degraded",
        }
    )


@app.post("/run")
@app.post("/api/v1/agent/run")
async def run_agent(request: RunRequest) -> StreamingResponse:
    session_id = request.session_id or str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    async def events() -> AsyncIterator[str]:
        yield sse(event_payload("start", session_id=session_id, run_id=run_id))
        initial_state = {
            "session_id": session_id,
            "run_id": run_id,
            "user_message": request.message,
            "original_user_message": request.message,
            "conversation_context": request.conversation_context or {},
            "errors": [],
            "findings": [],
            "tool_input": {},
        }
        try:
            final_state = await get_graph().ainvoke(initial_state)
        except Exception as exc:
            yield sse(event_payload("error", error_code="INTERNAL_ERROR", message=str(exc)))
            yield sse(event_payload("done"))
            return

        yield sse(
            event_payload(
                "intent",
                domain=final_state.get("domain"),
                task_type=final_state.get("task_type"),
                object_type=final_state.get("object_type"),
                entity=final_state.get("entity"),
                tool=final_state.get("tool_name"),
                confidence=1.0,
            )
        )
        yield sse(
            event_payload(
                "safety_check",
                risk_level=final_state.get("risk_level", "read_only"),
                allowed=final_state.get("allowed", True),
                error_code=final_state.get("error_code"),
                message=final_state.get("block_reason"),
            )
        )

        if final_state.get("selected_agent"):
            yield sse(event_payload("agent_start", agent=final_state["selected_agent"]))

        tool_responses = final_state.get("tool_responses") or []
        if final_state.get("allowed", True) and tool_responses:
            for result in tool_responses:
                yield sse(
                    event_payload(
                        "tool_call",
                        tool=result.get("tool_name"),
                        risk_level=final_state.get("risk_level", "read_only"),
                        input_summary=_input_summary(result.get("tool_input") or {}),
                    )
                )
                tool_response = result.get("response")
                ok = tool_response.get("ok", True) if isinstance(tool_response, dict) else True
                yield sse(
                    event_payload(
                        "tool_result",
                        tool=result.get("tool_name"),
                        ok=ok,
                        output_summary=_tool_summary(tool_response),
                    )
                )
                if isinstance(tool_response, dict) and tool_response.get("ok") is False:
                    yield sse(
                        event_payload(
                            "error",
                            error_code=tool_response.get("error_code", "BACKEND_ERROR"),
                            message=tool_response.get("message", "Backend tool failed."),
                        )
                    )
        elif final_state.get("allowed", True) and final_state.get("tool_name"):
            yield sse(
                event_payload(
                    "tool_call",
                    tool=final_state.get("tool_name"),
                    risk_level=final_state.get("risk_level", "read_only"),
                    input_summary=_input_summary(final_state.get("tool_input") or {}),
                )
            )
            tool_response = final_state.get("tool_response")
            ok = tool_response.get("ok", True) if isinstance(tool_response, dict) else True
            yield sse(
                event_payload(
                    "tool_result",
                    tool=final_state.get("tool_name"),
                    ok=ok,
                    output_summary=_tool_summary(tool_response),
                )
            )
            if isinstance(tool_response, dict) and tool_response.get("ok") is False:
                yield sse(
                    event_payload(
                        "error",
                        error_code=tool_response.get("error_code", "BACKEND_ERROR"),
                        message=tool_response.get("message", "Backend tool failed."),
                    )
                )

        if final_state.get("web_search_queries") or final_state.get("web_search_error"):
            yield sse(event_payload("agent_start", agent="web_research_agent"))
            yield sse(
                event_payload(
                    "tool_call",
                    tool="tavily_search",
                    risk_level="read_only",
                    input_summary=_web_search_input_summary(final_state.get("web_search_queries") or []),
                )
            )
            yield sse(
                event_payload(
                    "tool_result",
                    tool="tavily_search",
                    ok=not bool(final_state.get("web_search_error")),
                    output_summary=_web_search_summary(final_state),
                )
            )

        yield sse(event_payload("validation", **(final_state.get("validation") or {"status": "passed"})))
        review = final_state.get("llm_review") or {}
        yield sse(
            event_payload(
                "final",
                content=final_state.get("final_answer", ""),
                final_answer_source=final_state.get("final_answer_source", "deterministic"),
                llm_used=final_state.get("llm_used", False),
                llm_provider=final_state.get("llm_provider"),
                llm_model=final_state.get("llm_model"),
                reviewer_passed=review.get("passed") if isinstance(review, dict) else None,
                fallback_reason=final_state.get("fallback_reason") or final_state.get("llm_error"),
            )
        )
        yield sse(event_payload("done"))

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "found": False,
        "values": {},
        "next": [],
        "metadata": {"mode": "langgraph-phase-3-no-checkpointer"},
    }


def _input_summary(tool_input: dict[str, Any]) -> str:
    if not tool_input:
        return "no arguments"
    if "text" in tool_input:
        return f"text_length={len(str(tool_input.get('text', '')))}"
    return ", ".join(f"{key}={value}" for key, value in tool_input.items())


def _tool_summary(tool_response: Any) -> str:
    if isinstance(tool_response, dict) and tool_response.get("ok") is False:
        return f"{tool_response.get('error_code')}: {tool_response.get('message')}"
    data = tool_response.get("data") if isinstance(tool_response, dict) else tool_response
    if isinstance(data, list):
        return f"{len(data)} item(s) returned"
    if isinstance(data, dict):
        scalar_items = {key: value for key, value in data.items() if not isinstance(value, (dict, list))}
        if scalar_items:
            return json.dumps({key: scalar_items[key] for key in list(scalar_items.keys())[:5]}, default=str)
        return f"{len(data)} field(s) returned"
    return "result returned"


def _web_search_input_summary(queries: list[Any]) -> str:
    if not queries:
        return "no search query"
    return f"{len(queries)} query(s)"


def _web_search_summary(state: dict[str, Any]) -> str:
    if state.get("web_search_error"):
        return f"{state.get('web_search_error')}: web search skipped"
    results = state.get("web_search_results") or []
    if not results:
        return str(state.get("web_search_skipped_reason") or "no web results")
    official = sum(1 for item in results if str(item.get("source_type", "")).startswith("official"))
    return f"{len(results)} result(s), {official} official source(s)"
