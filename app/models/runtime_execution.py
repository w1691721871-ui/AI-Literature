"""Persisted, user-readable records for the unified AI Worker lifecycle."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RuntimeExecution(Base):
    """A bounded Skill action record, intentionally excluding prompts and CoT."""

    __tablename__ = "runtime_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    mission_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    step_id: Mapped[str] = mapped_column(String(80), nullable=False)
    skill: Mapped[str] = mapped_column(String(80), nullable=False)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PLANNED")
    observation_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    result_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
