from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import structlog
from fastapi import FastAPI

from app.routes.health import router as health_router
from app.routes.run import router as run_router
from app.routes.stream import router as stream_router
from app.routes.tools import router as tools_router
from app.routes.sessions import router as sessions_router
from app.runtime import runtime

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("agent_engine_starting")
    yield
    await runtime.close()
    log.info("agent_engine_stopped")


app = FastAPI(title="vCenter Agent Engine", lifespan=lifespan)
app.include_router(health_router)
app.include_router(run_router)
app.include_router(stream_router)
app.include_router(tools_router)
app.include_router(sessions_router)
