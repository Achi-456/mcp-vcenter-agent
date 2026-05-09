from fastapi import APIRouter
from pydantic import BaseModel
from app.runtime import runtime
from app.settings import get_settings
import asyncpg

router = APIRouter()

@router.get("/sessions")
async def list_sessions() -> dict[str, object]:
    dsn = get_settings().postgres_dsn
    if not dsn:
        return {"items": []}
    
    try:
        conn = await asyncpg.connect(dsn)
        rows = await conn.fetch("SELECT id, title, created_at, message_count FROM sessions ORDER BY updated_at DESC")
        await conn.close()
        items = [
            {
                "id": r["id"],
                "title": r["title"],
                "created_at": r["created_at"].isoformat(),
                "message_count": r["message_count"]
            }
            for r in rows
        ]
        return {"items": items}
    except Exception as e:
        return {"items": [], "error": str(e)}

@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, object]:
    graph = await runtime.graph()
    config = {"configurable": {"thread_id": session_id}}
    snapshot = await graph.aget_state(config)

    values = getattr(snapshot, "values", None)
    metadata = getattr(snapshot, "metadata", None)
    next_nodes = getattr(snapshot, "next", None)
    
    # We need to serialize LangChain messages if they exist
    safe_values = {}
    if values:
        for k, v in values.items():
            if k == "messages":
                safe_values[k] = [{"type": m.type, "content": m.content, "tool_calls": getattr(m, "tool_calls", [])} for m in v]
            else:
                safe_values[k] = v

    return {
        "session_id": session_id,
        "found": bool(values),
        "values": safe_values,
        "next": list(next_nodes or []),
        "metadata": metadata or {},
    }

class RenameRequest(BaseModel):
    title: str

@router.patch("/sessions/{session_id}")
async def rename_session(session_id: str, request: RenameRequest) -> dict[str, object]:
    dsn = get_settings().postgres_dsn
    if not dsn:
        return {"ok": False, "error": "No database connection"}
    
    try:
        conn = await asyncpg.connect(dsn)
        await conn.execute("UPDATE sessions SET title = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2", request.title, session_id)
        await conn.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

