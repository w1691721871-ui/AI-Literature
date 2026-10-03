"""Workspace-scoped control state for long-running, reviewable Missions."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MissionControlState(Base):
    __tablename__ = "mission_control_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    prior_status: Mapped[str] = mapped_column(String(40), nullable=False, default="CREATED")
    paused_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    pause_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    recovery_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_recoveries: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
