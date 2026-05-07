from fastapi import APIRouter

from app.runtime import runtime

router = APIRouter()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, object]:
    graph = await runtime.graph()
    config = {"configurable": {"thread_id": session_id}}
    snapshot = await graph.aget_state(config)

    values = getattr(snapshot, "values", None)
    metadata = getattr(snapshot, "metadata", None)
    next_nodes = getattr(snapshot, "next", None)

    return {
        "session_id": session_id,
        "found": bool(values),
        "values": values or {},
        "next": list(next_nodes or []),
        "metadata": metadata or {},
    }

