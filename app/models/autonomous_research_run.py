"""Persistent, user-visible autonomous ResearchOS execution records."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AutonomousResearchRun(Base):
    """One bounded Research Brain run, excluding private model reasoning."""

    __tablename__ = "autonomous_research_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    task_plan: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    execution_timeline: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    tool_results: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    environment_profile: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    memory_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    reflection: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    final_output: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    current_step: Mapped[str] = mapped_column(String(300), nullable=False, default="等待执行")
    current_tool: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    completed_tasks: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    next_plan: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
