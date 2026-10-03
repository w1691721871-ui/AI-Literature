"""Persisted, public-safe state for a workspace-bound autonomous Mission."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MissionState(Base):
    """Stores status summaries only; prompts and internal reasoning are excluded."""

    __tablename__ = "mission_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    current_phase: Mapped[str] = mapped_column(String(40), nullable=False, default="CREATED")
    completed_tasks: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    pending_tasks: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    blocked_reason: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    replan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_replan_count: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    quality_status: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_EVALUATED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
