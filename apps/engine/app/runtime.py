import asyncio
import logging
from contextlib import AbstractAsyncContextManager
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.cache import cache_ping, close_cache
from app.graph.workflow import build_graph
from app.settings import get_settings

logger = logging.getLogger(__name__)


class EngineRuntime:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._checkpointer_cm: AbstractAsyncContextManager[Any] | None = None
        self._checkpointer: Any | None = None
        self._graph: Any | None = None

    async def ensure_ready(self) -> None:
        async with self._lock:
            if self._checkpointer is None:
                try:
                    dsn = get_settings().postgres_dsn
                    cm = AsyncPostgresSaver.from_conn_string(dsn)
                    self._checkpointer_cm = cm
                    self._checkpointer = await cm.__aenter__()
                    await self._checkpointer.setup()
                except Exception as exc:
                    logger.warning(f"Failed to initialize Postgres checkpointer, falling back to MemorySaver: {exc}")
                    self._checkpointer = MemorySaver()
                    self._checkpointer_cm = None
                
                self._graph = build_graph(self._checkpointer)

        try:
            await cache_ping()
        except Exception as exc:
            logger.warning(f"Failed to ping Redis cache: {exc}")

    async def graph(self) -> Any:
        await self.ensure_ready()
        if self._graph is None:
            raise RuntimeError("LangGraph runtime is not initialized")
        return self._graph

    async def close(self) -> None:
        try:
            await close_cache()
        except Exception as exc:
            logger.warning(f"Failed to close cache: {exc}")

        if self._checkpointer_cm is not None:
            await self._checkpointer_cm.__aexit__(None, None, None)
            self._checkpointer_cm = None
            
        self._checkpointer = None
        self._graph = None


runtime = EngineRuntime()

