"""phase12 chat persistence context

Revision ID: 20260514_0002
Revises: 20260510_0001
Create Date: 2026-05-14 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260514_0002"
down_revision: str | None = "20260510_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("last_message_preview", sa.Text(), nullable=True))
    op.add_column("chat_sessions", sa.Column("last_entities_json", sa.JSON(), nullable=True))
    op.add_column("chat_sessions", sa.Column("last_intent", sa.String(length=64), nullable=True))
    op.create_index("ix_chat_sessions_updated_at", "chat_sessions", ["updated_at"])

    op.add_column("agent_runs", sa.Column("final_answer_source", sa.String(length=32), nullable=True))
    op.add_column("agent_runs", sa.Column("llm_used", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("agent_runs", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("agent_runs", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("tool_calls", sa.Column("summary_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("tool_calls", "summary_json")

    op.drop_column("agent_runs", "completed_at")
    op.drop_column("agent_runs", "started_at")
    op.drop_column("agent_runs", "llm_used")
    op.drop_column("agent_runs", "final_answer_source")

    op.drop_index("ix_chat_sessions_updated_at", table_name="chat_sessions")
    op.drop_column("chat_sessions", "last_intent")
    op.drop_column("chat_sessions", "last_entities_json")
    op.drop_column("chat_sessions", "last_message_preview")

