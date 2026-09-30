"""Persistent, bounded P17 autonomous Computer Agent runtime state."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime: return datetime.now(timezone.utc)


class ComputerRuntimeSession(Base):
    __tablename__ = "computer_runtime_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    computer_task_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    user_goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="CREATED", index=True)
    plan_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    loop_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
