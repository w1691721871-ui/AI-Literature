"""A user-readable progress projection over an existing controlled Computer Use task."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Integer, String
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
