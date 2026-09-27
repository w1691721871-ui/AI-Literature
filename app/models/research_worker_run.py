"""Persistent, user-visible records for bounded Research Worker executions."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchWorkerRun(Base):
    """Execution state only; never stores hidden model reasoning or raw files."""

    __tablename__ = "research_worker_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    current_step: Mapped[str] = mapped_column(String(300), nullable=False, default="等待规划")
    current_phase: Mapped[str] = mapped_column(String(40), nullable=False, default="planning")
    plan: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    selected_tools: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    tool_results: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    reflection: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    execution_history: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    output_file: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
