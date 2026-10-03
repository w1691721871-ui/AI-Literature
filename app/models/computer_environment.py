"""Persisted, public-safe environment summaries for controlled Computer Skill work."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ComputerEnvironmentState(Base):
    """A workspace-scoped summary; never stores screenshots, prompts, or model output."""

    __tablename__ = "computer_environment_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    application: Mapped[str] = mapped_column(String(160), nullable=False, default="Controlled Workspace")
    page_state: Mapped[str] = mapped_column(String(120), nullable=False, default="unknown")
    available_actions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    current_goal: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    blocking_condition: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    verification_target: Mapped[str] = mapped_column(String(240), nullable=False, default="")
    risk_level: Mapped[str] = mapped_column(String(30), nullable=False, default="LOW")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
