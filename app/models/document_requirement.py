"""Provisional, customer-confirmed requirements extracted from supplied material."""
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.services.database import Base


def utc_now(): return datetime.now(timezone.utc)


class DocumentRequirement(Base):
    __tablename__ = "document_requirements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    file_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="NEEDS_CONFIRMATION")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utc_now)
