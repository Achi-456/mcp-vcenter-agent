from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_database_url() -> str | None:
    return get_settings().db_url


def get_engine() -> AsyncEngine | None:
    global _engine
    db_url = get_database_url()
    if not db_url:
        return None
    if _engine is None:
        _engine = create_async_engine(db_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession] | None:
    global _session_factory
    engine = get_engine()
    if engine is None:
        return None
    if _session_factory is None:
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return _session_factory


async def session_scope() -> AsyncIterator[AsyncSession]:
    session_factory = get_session_factory()
    if session_factory is None:
        raise RuntimeError("DB_URL is not configured")
    async with session_factory() as session:
        yield session


async def ping_postgres() -> bool:
    from sqlalchemy import text

    engine = get_engine()
    if engine is None:
        return False
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return True
