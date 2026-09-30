"""Persistent, review-first FDE solution project metadata."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SolutionProject(Base):
    __tablename__ = "solution_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    customer_need: Mapped[str] = mapped_column(Text, nullable=False)
    industry: Mapped[str] = mapped_column(String(120), nullable=False, default="Research")
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Status names describe a reviewable FDE lifecycle, never customer acceptance.
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="CREATED")
    review_status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    review_note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)
