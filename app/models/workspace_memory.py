"""Workspace-scoped, reviewable ResearchOS memory summaries."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkspaceMemory(Base):
    """Stores compact product memory, never prompts, CoT, or source documents."""

    __tablename__ = "workspace_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    mission_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    memory_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    references_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="USER_CONFIRMED")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    importance_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    lifecycle_state: Mapped[str] = mapped_column(String(30), nullable=False, default="CREATED")
    use_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
