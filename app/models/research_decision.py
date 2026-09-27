"""Human-in-the-loop decision records for ResearchOS suggestions."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


class ResearchDecision(Base):
    """Stores the latest human confirmation state for one research action."""

    __tablename__ = "research_decisions"
    __table_args__ = (UniqueConstraint("action_id", name="uq_research_decision_action"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(30), nullable=False, default="待确认")
    decided_by: Mapped[str] = mapped_column(String(100), nullable=False, default="科研负责人")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
