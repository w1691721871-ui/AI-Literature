"""Persistent, user-readable Mission Contract and unified runtime state."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MissionContract(Base):
    __tablename__ = "mission_contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    task_type: Mapped[str] = mapped_column(String(30), nullable=False, default="RESEARCH")
    input_context: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    available_skills: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    evidence_refs: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    artifact_refs: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    approval_state: Mapped[str] = mapped_column(String(40), nullable=False, default="HUMAN_REVIEW_REQUIRED")
    execution_state: Mapped[str] = mapped_column(String(40), nullable=False, default="CREATED")
    stop_reason: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class RuntimeExecutionState(Base):
    __tablename__ = "runtime_execution_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    current_step: Mapped[str] = mapped_column(String(100), nullable=False, default="Created")
    current_skill: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    observation_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    evaluation_result: Mapped[str] = mapped_column(Text, nullable=False, default="")
    next_action: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    stop_reason: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
