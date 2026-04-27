"""SQLite-backed persistent session store for cross-restart agent context.

Sessions are keyed by a client-supplied session_id (UUID string). When a session
resumes, the prior session's full_summary is injected as a user message so the
model has immediate context without re-running discovery tools.

Schema
------
sessions(
    session_id   TEXT PRIMARY KEY,
    timestamp    REAL,          -- Unix epoch (time.time())
    vcenter_host TEXT,
    objective    TEXT,          -- first user message of the session
    key_findings TEXT,          -- extracted from summary heuristic
    open_questions TEXT,
    full_summary TEXT           -- verbatim full_text from the done event
)
"""
from __future__ import annotations

import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class SessionRecord:
    session_id: str
    timestamp: float = field(default_factory=time.time)
    vcenter_host: str = ""
    objective: str = ""
    key_findings: str = ""
    open_questions: str = ""
    full_summary: str = ""


_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id    TEXT PRIMARY KEY,
    timestamp     REAL    NOT NULL,
    vcenter_host  TEXT    NOT NULL DEFAULT '',
    objective     TEXT    NOT NULL DEFAULT '',
    key_findings  TEXT    NOT NULL DEFAULT '',
    open_questions TEXT   NOT NULL DEFAULT '',
    full_summary  TEXT    NOT NULL DEFAULT ''
)
"""

_UPSERT = """
INSERT INTO sessions
    (session_id, timestamp, vcenter_host, objective, key_findings, open_questions, full_summary)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(session_id) DO UPDATE SET
    timestamp      = excluded.timestamp,
    vcenter_host   = excluded.vcenter_host,
    objective      = excluded.objective,
    key_findings   = excluded.key_findings,
    open_questions = excluded.open_questions,
    full_summary   = excluded.full_summary
"""

_SELECT = """
SELECT session_id, timestamp, vcenter_host, objective, key_findings, open_questions, full_summary
FROM sessions WHERE session_id = ?
"""


class SessionStore:
    """Thread-safe SQLite session store (one connection per call via context manager)."""

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=10, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def save(self, record: SessionRecord) -> None:
        """Upsert *record* into the store. Silently logs on error."""
        try:
            with self._connect() as conn:
                conn.execute(
                    _UPSERT,
                    (
                        record.session_id,
                        record.timestamp,
                        record.vcenter_host,
                        record.objective,
                        record.key_findings,
                        record.open_questions,
                        record.full_summary,
                    ),
                )
                conn.commit()
            log.debug("session saved: %s", record.session_id)
        except Exception as exc:
            log.warning("SessionStore.save failed for %s: %s", record.session_id, exc)

    def load(self, session_id: str) -> SessionRecord | None:
        """Return the stored record for *session_id*, or None if not found."""
        try:
            with self._connect() as conn:
                row = conn.execute(_SELECT, (session_id,)).fetchone()
            if row is None:
                return None
            return SessionRecord(
                session_id=row["session_id"],
                timestamp=row["timestamp"],
                vcenter_host=row["vcenter_host"],
                objective=row["objective"],
                key_findings=row["key_findings"],
                open_questions=row["open_questions"],
                full_summary=row["full_summary"],
            )
        except Exception as exc:
            log.warning("SessionStore.load failed for %s: %s", session_id, exc)
            return None

    def delete(self, session_id: str) -> None:
        """Remove a session record (e.g. on explicit reset)."""
        try:
            with self._connect() as conn:
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
                conn.commit()
        except Exception as exc:
            log.warning("SessionStore.delete failed for %s: %s", session_id, exc)


def _extract_key_findings(summary: str) -> str:
    """Heuristic: pull the first 500 chars of the summary as key findings."""
    return (summary or "").strip()[:500]


def _extract_open_questions(summary: str) -> str:
    """Heuristic: look for an 'open questions' section in the summary."""
    import re
    m = re.search(r"(?i)open\s+questions?[:\s]+([\s\S]{1,400})", summary or "")
    return m.group(1).strip() if m else ""


# Module-level singleton — lazily initialised on first use.
_store: SessionStore | None = None


def get_store() -> SessionStore:
    """Return (or lazily create) the module-level SessionStore instance."""
    global _store
    if _store is None:
        from app.agent.config import get_session_db_path
        _store = SessionStore(get_session_db_path())
    return _store
