"""
Copilot memory models for LogiSight — CockroachDB.
Session tracking, memory events, and charge embeddings for semantic matching.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CopilotSession(Base):
    """One row per Copilot conversation."""

    __tablename__ = "copilot_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )  # active | closed


class CopilotMemoryEvent(Base):
    """Structured memory of what the agent did/decided during a conversation."""

    __tablename__ = "copilot_memory_events"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("copilot_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # query | tool_call | decision | user_message | agent_message
    content: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ChargeEmbedding(Base):
    """Vector memory for semantic charge matching (Bedrock Titan Embeddings)."""

    __tablename__ = "charge_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    charge_name: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # charge_master | invoice_line | learned_mapping
    # embedding column is VECTOR(1536) — handled in migration DDL
    # We store it as a raw column since SQLAlchemy doesn't natively support VECTOR type
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CopilotMemoryEmbedding(Base):
    """Vector memory for semantic cross-session memory recall."""

    __tablename__ = "copilot_memory_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("copilot_sessions.id", ondelete="CASCADE"), nullable=False
    )
    memory_event_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("copilot_memory_events.id", ondelete="CASCADE"), nullable=False
    )
    summary_text: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    # embedding_v is VECTOR(1536) — handled in migration DDL
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
