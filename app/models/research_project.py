"""SQLite model for a lightweight ResearchOS project lifecycle."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ResearchProject(Base):
    """A research project and its editable planning artefacts."""

    __tablename__ = "research_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    enterprise_requirement: Mapped[str] = mapped_column(Text, nullable=False, default="")
    research_goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    technology_route: Mapped[str] = mapped_column(Text, nullable=False, default="")
    paper_plan: Mapped[str] = mapped_column(Text, nullable=False, default="")
    patent_plan: Mapped[str] = mapped_column(Text, nullable=False, default="")
    outcome_management: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="planning")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
