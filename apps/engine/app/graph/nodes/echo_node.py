from app.cache import get_cache
from app.graph.state import AgentState


async def echo_node(state: AgentState) -> dict[str, object]:
    session_id = state["session_id"]
    user_message = state["user_message"]
    turn = int(state.get("turn", 0)) + 1
    cache_key = f"echo:{session_id}:{user_message}"

    cache = await get_cache()
    cached = await cache.get(cache_key)
    if cached:
        return {
            "final_answer": f"[CACHED] {cached}",
            "cached_result": cached,
            "turn": turn,
        }

    result = (
        "Agent engine skeleton is working. "
        f"Session: {session_id} | "
        f"Message received: {user_message} | "
        f"Turn: {turn} | "
        "Checkpointer: Postgres | "
        "Cache: Redis"
    )
    await cache.setex(cache_key, 60, result)

    return {
        "final_answer": result,
        "cached_result": None,
        "turn": turn,
    }

