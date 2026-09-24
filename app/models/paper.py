"""SQLite model for a persisted research paper."""

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.services.database import Base


def utc_now() -> datetime:
    """Return a timezone-aware timestamp for paper metadata."""
    return datetime.now(timezone.utc)


class Paper(Base):
    """Persisted source file metadata and extracted text for one research paper."""

    __tablename__ = "papers"

    paper_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    upload_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    file_path: Mapped[str] = mapped_column(String(1_000), nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    analysis_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="parsed"
    )
    # A product-facing knowledge-base readiness state.  ``analysis_status``
    # remains unchanged for compatibility with the earlier paper library API.
    quality_status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="parsed"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
