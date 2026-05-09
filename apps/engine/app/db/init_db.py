import asyncpg
import logging
from app.settings import get_settings

logger = logging.getLogger(__name__)

async def init_db() -> None:
    dsn = get_settings().postgres_dsn
    if not dsn:
        logger.warning("No Postgres DSN found, skipping database initialization")
        return
        
    try:
        conn = await asyncpg.connect(dsn)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0
            );
        """)
        await conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
