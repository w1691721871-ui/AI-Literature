"""A user-readable progress projection over an existing controlled Computer Use task."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ComputerMission(Base):
    __tablename__ = "computer_missions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    task_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    mission_name: Mapped[str] = mapped_column(String(240), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    current_stage: Mapped[str] = mapped_column(String(60), nullable=False, default="ANALYZING")
    # P24 fields are optional so the existing P18 progress projection remains
    # readable. They persist only user-readable plans, diffs and verification.
    mission_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    task: Mapped[str] = mapped_column(Text, nullable=False, default="")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False, default="LOW")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="CREATED")
    action_plan_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    diff_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    approval_status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    execution_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    workspace_profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    execution_log_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    verification_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
