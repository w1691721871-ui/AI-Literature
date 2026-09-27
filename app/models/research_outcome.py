"""Project outcome records for the ResearchOS decision-to-delivery loop."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


class ResearchOutcome(Base):
    """A planned or delivered paper, patent, report, or experiment result."""

    __tablename__ = "research_outcomes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    outcome_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="规划中")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    knowledge_status: Mapped[str] = mapped_column(String(30), nullable=False, default="未沉淀")
    source_action_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
