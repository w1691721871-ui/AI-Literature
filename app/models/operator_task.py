"""Persistent, approval-gated Research Operator tasks.

The record deliberately contains public execution summaries only.  It never
stores prompts, hidden model reasoning, or source document bodies.
"""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OperatorTask(Base):
    __tablename__ = "operator_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    user_goal: Mapped[str] = mapped_column(Text, nullable=False)
    task_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="planned", index=True)
    plan_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    tool_execution_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    evidence_refs_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    artifact_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    approval_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending", index=True)
    reviewer_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
