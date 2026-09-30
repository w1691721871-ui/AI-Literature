"""Approval-gated Computer Lab proposals generated for an FDE solution draft."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SolutionComputerMission(Base):
    """A proposal only; it is never an executable Computer Agent command."""

    __tablename__ = "solution_computer_missions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    solution_project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="MEDIUM")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="WAITING_APPROVAL")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
