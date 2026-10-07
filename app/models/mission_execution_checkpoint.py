"""Durable, user-readable checkpoints for the bounded AI Worker."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MissionExecutionCheckpoint(Base):
    """The durable execution fact; intentionally excludes prompts and raw payloads."""

    __tablename__ = "mission_execution_checkpoints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(40), nullable=False, default="CREATED")
    goal_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    current_objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    next_action: Mapped[str] = mapped_column(String(160), nullable=False, default="")
    completed_steps_summary: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    last_observation_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    last_evaluation_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    action_key: Mapped[str] = mapped_column(String(180), nullable=False, default="")
    action_status: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    action_safety: Mapped[str] = mapped_column(String(30), nullable=False, default="")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recovery_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    waiting_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    resume_policy: Mapped[str] = mapped_column(String(40), nullable=False, default="RESUME_ELIGIBLE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class MissionExecutionLease(Base):
    """A short-lived worker claim, never the source of Mission truth."""

    __tablename__ = "mission_execution_leases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    worker_id: Mapped[str] = mapped_column(String(80), nullable=False)
    lease_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    lease_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
