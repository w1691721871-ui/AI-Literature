"""Summary-only document understanding output; raw customer text is not persisted here."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base


def utc_now(): return datetime.now(timezone.utc)


class DocumentSummary(Base):
    __tablename__ = "document_summaries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    file_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    key_points_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    entities_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    limitations: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
